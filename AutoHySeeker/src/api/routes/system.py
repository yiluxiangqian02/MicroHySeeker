"""System status and monitoring APIs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

# In-memory activity log (ring buffer, 100 entries)
_ACTIVITY_LOG: list[dict[str, Any]] = []
_MAX_ACTIVITIES = 100

# ---------------------------------------------------------------------------
# System config (pumps, channels, calibration)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # workspace root
_LOCAL_CONFIG = _PROJECT_ROOT / "config" / "system.json"
_SYSTEM_CONFIG: dict[str, Any] | None = None


def _load_system_config() -> dict[str, Any]:
    """Load system config: try MicroHySeeker API first, then local file."""
    global _SYSTEM_CONFIG
    if _SYSTEM_CONFIG is not None:
        return _SYSTEM_CONFIG

    # Try local file (always available)
    if _LOCAL_CONFIG.exists():
        try:
            raw = json.loads(_LOCAL_CONFIG.read_text(encoding="utf-8"))
            _SYSTEM_CONFIG = raw
            logger.info("Loaded system config from %s", _LOCAL_CONFIG)
            return _SYSTEM_CONFIG
        except Exception:
            logger.exception("Failed to load local config from %s", _LOCAL_CONFIG)

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
    microhyseeker_ok = False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "http://localhost:8100/health", timeout=2.0
            )
            microhyseeker_ok = resp.status_code == 200
    except Exception:
        pass

    from src.common.agent_manager import agent_manager  # local import avoids circular

    agents = agent_manager.get_all_status()
    running = sum(1 for a in agents.values() if a.get("status") == "running")

    return {
        "autohyseeker": True,
        "microhyseeker": microhyseeker_ok,
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

    This endpoint powers the ExperimentCreateDialog pump selectors.
    It tries to fetch live config from MicroHySeeker first, then falls
    back to the local ``config/system.json``.
    """
    # Try live MicroHySeeker config (强制 IPv4，避免 Windows localhost → IPv6 失败)
    try:
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(timeout=3.0, transport=transport) as client:
            resp = await client.get("http://127.0.0.1:8100/api/template/config/system")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    # Fallback to cached local config
    cfg = _load_system_config()
    return cfg


@router.post("/config/reload")
async def reload_system_config() -> dict[str, Any]:
    """Force reload system config from disk."""
    global _SYSTEM_CONFIG
    _SYSTEM_CONFIG = None
    cfg = _load_system_config()
    record_activity("system", "系统配置已重新加载")
    return {"status": "ok", "keys": list(cfg.keys())}
