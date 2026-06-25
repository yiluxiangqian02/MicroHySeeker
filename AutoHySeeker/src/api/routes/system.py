"""System status and monitoring APIs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

# MHS IPv4 transport factory (Windows localhost → IPv6 回退问题)
# transport 不能跨 AsyncClient 复用，所以每次创建新的
def _mhs_transport() -> httpx.AsyncHTTPTransport:
    return httpx.AsyncHTTPTransport(local_address="0.0.0.0")

# In-memory activity log (ring buffer, 100 entries)
_ACTIVITY_LOG: list[dict[str, Any]] = []
_MAX_ACTIVITIES = 100

# ---------------------------------------------------------------------------
# System config (pumps, channels, calibration)
# MHS 为唯一编辑权限，AHS 只读。直接从 MHS 磁盘文件加载，文件修改后自动生效。
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # workspace root
_MHS_CONFIG = _PROJECT_ROOT / "MicroHySeeker" / "config" / "system.json"
_SYSTEM_CONFIG: dict[str, Any] | None = None
_CONFIG_MTIME: float = 0.0  # 上次加载时文件的 mtime


def _load_system_config(*, force: bool = False) -> dict[str, Any]:
    """从 MHS 的 config/system.json 加载配置（只读）。

    通过 mtime 检测文件变更，文件被 MHS 修改后自动重新加载。
    """
    global _SYSTEM_CONFIG, _CONFIG_MTIME

    if _MHS_CONFIG.exists():
        try:
            mtime = _MHS_CONFIG.stat().st_mtime
            if _SYSTEM_CONFIG is not None and not force and mtime == _CONFIG_MTIME:
                return _SYSTEM_CONFIG
            raw = json.loads(_MHS_CONFIG.read_text(encoding="utf-8"))
            _SYSTEM_CONFIG = raw
            _CONFIG_MTIME = mtime
            logger.info("Loaded system config from %s (mtime=%.2f)", _MHS_CONFIG, mtime)
            return _SYSTEM_CONFIG
        except Exception:
            logger.exception("Failed to load config from %s", _MHS_CONFIG)

    if _SYSTEM_CONFIG is not None:
        return _SYSTEM_CONFIG
    _SYSTEM_CONFIG = {}
    return _SYSTEM_CONFIG


# Load on module import
_load_system_config()


def record_activity(activity_type: str, description: str) -> None:
    """Record an activity to the in-memory log."""
    _ACTIVITY_LOG.append(
        {
            "id": f"act_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": activity_type,
            "description": description,
        }
    )
    if len(_ACTIVITY_LOG) > _MAX_ACTIVITIES:
        del _ACTIVITY_LOG[:-_MAX_ACTIVITIES]


@router.get("/status")
async def get_system_status() -> dict[str, Any]:
    """Return current system status."""
    mhs_info: dict[str, Any] = {"online": False, "rs485_connected": False, "mock_mode": True, "port": ""}
    try:
        async with httpx.AsyncClient(timeout=3.0, transport=_mhs_transport()) as client:
            # 健康检查
            resp = await client.get("http://127.0.0.1:8100/api/system/health")
            if resp.status_code == 200:
                mhs_info["online"] = True
            # RS485 连接状态
            conn_resp = await client.get("http://127.0.0.1:8100/api/device/connection")
            if conn_resp.status_code == 200:
                conn = conn_resp.json()
                mhs_info["rs485_connected"] = conn.get("connected", False)
                mhs_info["mock_mode"] = conn.get("mock_mode", True)
                mhs_info["port"] = conn.get("port", "")
    except Exception:
        pass

    from src.common.agent_manager import agent_manager  # local import avoids circular

    agents = agent_manager.get_all_status()
    running = sum(1 for a in agents.values() if a.get("status") == "running")

    return {
        "autohyseeker": True,
        "microhyseeker": mhs_info["online"],
        "mhs": mhs_info,
        "database": True,
        "agents": {"running": running, "total": len(agents)},
    }


@router.get("/activities")
async def get_activities(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent activity log entries."""
    return list(reversed(_ACTIVITY_LOG))[:limit]


@router.get("/health")
async def get_system_health() -> dict[str, Any]:
    """Return system health metrics (CPU, memory, response time)."""
    if _PSUTIL_AVAILABLE:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
    else:
        cpu = 0.0
        mem = 0.0

    now = datetime.now(timezone.utc).isoformat()
    return {
        "cpu": [cpu] * 24,
        "memory": [mem] * 24,
        "apiResponseTime": [50] * 24,
        "timestamps": [now] * 24,
    }


@router.get("/config")
async def get_system_config() -> dict[str, Any]:
    """Return pump/channel/calibration configuration.

    直接从 MHS 的 config/system.json 读取（只读），通过 mtime 自动检测文件变更。
    MHS 拥有编辑权限，AHS 只读。
    """
    cfg = _load_system_config()
    if not cfg:
        logger.warning("System config is empty – MHS config file not found at %s", _MHS_CONFIG)
    return cfg


@router.post("/config/reload")
async def reload_system_config() -> dict[str, Any]:
    """Force reload system config from disk."""
    cfg = _load_system_config(force=True)
    record_activity("system", "系统配置已重新加载")
    return {"status": "ok", "keys": list(cfg.keys())}


# ---------------------------------------------------------------------------
# MHS RS485 proxy endpoints — 代理 MHS 设备控制 API，供前端直接调用
# ---------------------------------------------------------------------------

@router.get("/mhs/ports")
async def list_mhs_ports() -> dict[str, Any]:
    """列出 MHS 可用串口 + 系统配置的首选端口。"""
    cfg = _load_system_config()
    preferred_port = cfg.get("rs485_port", "")
    baudrate = cfg.get("rs485_baudrate", 38400)

    try:
        async with httpx.AsyncClient(timeout=3.0, transport=_mhs_transport()) as client:
            resp = await client.get("http://127.0.0.1:8100/api/device/ports")
            if resp.status_code == 200:
                ports = resp.json().get("ports", [])
                return {
                    "ports": ports,
                    "preferred_port": preferred_port,
                    "baudrate": baudrate,
                }
    except Exception:
        pass
    return {"ports": [], "preferred_port": preferred_port, "baudrate": baudrate}


class _ConnectRequest(BaseModel):
    port: str
    baudrate: int = 38400


@router.post("/mhs/connect")
async def connect_mhs_rs485(req: _ConnectRequest) -> dict[str, Any]:
    """连接 MHS RS485 到指定 COM 端口。"""
    try:
        async with httpx.AsyncClient(timeout=5.0, transport=_mhs_transport()) as client:
            resp = await client.post(
                "http://127.0.0.1:8100/api/device/connect",
                json={"port": req.port, "baudrate": req.baudrate},
            )
            if resp.status_code == 200:
                record_activity("system", f"RS485 已连接到 {req.port}")
                return resp.json()
            try:
                payload = resp.json()
                error = payload.get("detail") or payload.get("error") or resp.text
            except Exception:
                error = resp.text
            return {"error": error, "status_code": resp.status_code}
    except httpx.ConnectError:
        return {"error": "MHS 离线，无法连接"}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/mhs/disconnect")
async def disconnect_mhs_rs485() -> dict[str, Any]:
    """断开 MHS RS485 连接。"""
    try:
        async with httpx.AsyncClient(timeout=3.0, transport=_mhs_transport()) as client:
            resp = await client.post("http://127.0.0.1:8100/api/device/disconnect")
            if resp.status_code == 200:
                record_activity("system", "RS485 已断开")
                return resp.json()
            return {"error": resp.text}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/mhs/launch")
async def launch_mhs_service() -> dict[str, Any]:
    """尝试启动 MHS 无头服务（如果未运行）。"""
    from src.api.main import _ensure_mhs_running
    try:
        await _ensure_mhs_running()
        return {"status": "ok", "message": "MHS 服务已启动或已在运行"}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/mhs/experiment/logs")
async def get_mhs_experiment_logs(n: int = 200) -> dict[str, Any]:
    """代理获取 MHS 实验引擎的详细执行日志。"""
    try:
        async with httpx.AsyncClient(timeout=5.0, transport=_mhs_transport()) as client:
            resp = await client.get(
                f"http://127.0.0.1:8100/api/experiment/logs?n={min(n, 500)}"
            )
            if resp.status_code == 200:
                return resp.json()
            return {"logs": [], "error": resp.text}
    except httpx.ConnectError:
        return {"logs": [], "error": "MHS 离线"}
    except Exception as exc:
        return {"logs": [], "error": str(exc)}
