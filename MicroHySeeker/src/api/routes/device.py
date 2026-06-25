"""设备级控制路由 — 供 AutoHySeeker agents 直接操控硬件。

端点：
  ── 泵控制 ────────────────────────────────────────────
  POST /api/device/pump/start          启动单个泵
  POST /api/device/pump/stop           停止单个泵
  POST /api/device/pump/stop-all       紧急停止所有泵
  GET  /api/device/pump/status         查询所有泵状态
  GET  /api/device/pump/{address}      查询单个泵状态

  ── 清洗控制 ──────────────────────────────────────────
  POST /api/device/flusher/start       启动清洗循环
  POST /api/device/flusher/stop        停止清洗
  GET  /api/device/flusher/status      查询清洗器状态

  ── 配液控制 ──────────────────────────────────────────
  POST /api/device/diluter/start       启动配液
  POST /api/device/diluter/stop        停止配液
  GET  /api/device/diluter/{channel}/status  查询配液通道状态

  ── 系统级 ────────────────────────────────────────────
  POST /api/device/emergency-stop      紧急停止一切
  GET  /api/device/connection          查询 RS485 连接状态
  POST /api/device/connect             打开串口
  POST /api/device/disconnect          关闭串口
  GET  /api/device/ports               列出可用串口
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("microhyseeker.api.routes.device")
router = APIRouter()


# ── 依赖注入 ──────────────────────────────────────────────────────────────────

def _get_bridge(request: Request):
    bridge = getattr(request.app.state, "bridge", None)
    if bridge is None:
        raise HTTPException(503, "API bridge not available")
    return bridge


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 请求模型 ──────────────────────────────────────────────────────────────────

class PumpStartRequest(BaseModel):
    address: int = Field(..., ge=1, le=12, description="泵地址 (1-12)")
    direction: str = Field("FWD", description="方向: FWD / REV")
    rpm: int = Field(..., ge=0, le=300, description="转速 (0-300 RPM)")


class PumpStopRequest(BaseModel):
    address: int = Field(..., ge=1, le=12, description="泵地址 (1-12)")


class FlushStartRequest(BaseModel):
    cycles: int = Field(3, ge=1, le=20, description="清洗循环数")
    channel_id: Optional[int] = Field(None, description="清洗通道ID (可选)")


class DiluterStartRequest(BaseModel):
    channel_id: int = Field(..., ge=0, description="配液通道ID")
    volume_ul: float = Field(..., gt=0, description="注液体积 (μL)")
    rpm: Optional[int] = Field(None, ge=0, le=300, description="转速 (可选, 默认使用配置值)")


class DiluterStopRequest(BaseModel):
    channel_id: int = Field(..., ge=0, description="配液通道ID")


class ConnectRequest(BaseModel):
    port: str = Field(..., description="串口名称 (如 COM3)")
    baudrate: int = Field(38400, description="波特率")


# ── 泵控制端点 ────────────────────────────────────────────────────────────────

@router.post("/pump/start")
async def pump_start(
    body: PumpStartRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """启动单个泵。

    安全限制：RPM 不得超过 300。
    """
    try:
        success = bridge.device_pump_start(body.address, body.direction, body.rpm)
    except Exception as exc:
        raise HTTPException(500, f"泵启动失败: {exc}") from exc

    if not success:
        raise HTTPException(400, f"泵 {body.address} 启动失败 (可能未连接或参数无效)")

    return {
        "status": "started",
        "address": body.address,
        "direction": body.direction,
        "rpm": body.rpm,
        "timestamp": _ts(),
    }


@router.post("/pump/stop")
async def pump_stop(
    body: PumpStopRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """停止单个泵。"""
    try:
        success = bridge.device_pump_stop(body.address)
    except Exception as exc:
        raise HTTPException(500, f"泵停止失败: {exc}") from exc

    return {
        "status": "stopped" if success else "failed",
        "address": body.address,
        "timestamp": _ts(),
    }


@router.post("/pump/stop-all")
async def pump_stop_all(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """紧急停止所有泵。"""
    try:
        success = bridge.device_stop_all_pumps()
    except Exception as exc:
        raise HTTPException(500, f"停止所有泵失败: {exc}") from exc

    return {
        "status": "all_stopped" if success else "partial_failure",
        "timestamp": _ts(),
    }


@router.get("/pump/status")
async def pump_status_all(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询所有泵状态。"""
    try:
        statuses = bridge.device_get_all_pump_status()
    except Exception as exc:
        raise HTTPException(500, f"状态查询失败: {exc}") from exc

    return {
        "pumps": statuses,
        "timestamp": _ts(),
    }


@router.get("/pump/{address}")
async def pump_status_single(
    address: int,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """查询单个泵状态。"""
    if address < 1 or address > 12:
        raise HTTPException(400, "泵地址必须在 1-12 范围内")

    try:
        status = bridge.device_get_pump_status(address)
    except Exception as exc:
        raise HTTPException(500, f"状态查询失败: {exc}") from exc

    return {
        **status,
        "timestamp": _ts(),
    }


# ── 清洗控制端点 ──────────────────────────────────────────────────────────────

@router.post("/flusher/start")
async def flusher_start(
    body: FlushStartRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """启动清洗循环。"""
    try:
        success = bridge.device_flusher_start(
            cycles=body.cycles,
            channel_id=body.channel_id,
        )
    except Exception as exc:
        raise HTTPException(500, f"清洗启动失败: {exc}") from exc

    if not success:
        raise HTTPException(400, "清洗启动失败 (可能未配置或正在运行)")

    return {
        "status": "flushing",
        "cycles": body.cycles,
        "timestamp": _ts(),
    }


@router.post("/flusher/stop")
async def flusher_stop(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """停止清洗。"""
    try:
        success = bridge.device_flusher_stop()
    except Exception as exc:
        raise HTTPException(500, f"清洗停止失败: {exc}") from exc

    return {
        "status": "stopped" if success else "failed",
        "timestamp": _ts(),
    }


@router.get("/flusher/status")
async def flusher_status(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询清洗器状态。"""
    try:
        status = bridge.device_get_flusher_status()
    except Exception as exc:
        raise HTTPException(500, f"状态查询失败: {exc}") from exc

    return {
        **status,
        "timestamp": _ts(),
    }


# ── 配液控制端点 ──────────────────────────────────────────────────────────────

@router.post("/diluter/start")
async def diluter_start(
    body: DiluterStartRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """启动配液。"""
    try:
        success = bridge.device_diluter_start(
            channel_id=body.channel_id,
            volume_ul=body.volume_ul,
            rpm=body.rpm,
        )
    except Exception as exc:
        raise HTTPException(500, f"配液启动失败: {exc}") from exc

    if not success:
        raise HTTPException(400, f"配液通道 {body.channel_id} 启动失败")

    return {
        "status": "infusing",
        "channel_id": body.channel_id,
        "volume_ul": body.volume_ul,
        "timestamp": _ts(),
    }


@router.post("/diluter/stop")
async def diluter_stop(
    body: DiluterStopRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """停止配液。"""
    try:
        success = bridge.device_diluter_stop(body.channel_id)
    except Exception as exc:
        raise HTTPException(500, f"配液停止失败: {exc}") from exc

    return {
        "status": "stopped" if success else "failed",
        "channel_id": body.channel_id,
        "timestamp": _ts(),
    }


@router.get("/diluter/{channel_id}/status")
async def diluter_status(
    channel_id: int,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """查询配液通道状态。"""
    try:
        status = bridge.device_get_diluter_status(channel_id)
    except Exception as exc:
        raise HTTPException(500, f"状态查询失败: {exc}") from exc

    return {
        **status,
        "timestamp": _ts(),
    }


# ── 系统级端点 ────────────────────────────────────────────────────────────────

@router.post("/emergency-stop")
async def emergency_stop(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """紧急停止一切：所有泵 + 清洗 + 配液 + 实验。"""
    results = {}
    try:
        results["experiment_stopped"] = bridge.device_emergency_stop()
    except Exception as exc:
        results["error"] = str(exc)

    return {
        "status": "emergency_stop_executed",
        **results,
        "timestamp": _ts(),
    }


@router.get("/connection")
async def connection_status(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询 RS485 连接状态。"""
    try:
        info = bridge.device_get_connection_info()
    except Exception as exc:
        raise HTTPException(500, f"查询失败: {exc}") from exc

    return {
        **info,
        "timestamp": _ts(),
    }


@router.get("/ports")
async def list_ports(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """列出可用串口。"""
    try:
        ports = bridge.device_list_ports()
    except Exception as exc:
        raise HTTPException(500, f"查询失败: {exc}") from exc

    return {
        "ports": ports,
        "timestamp": _ts(),
    }


@router.post("/connect")
async def connect_port(
    body: ConnectRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """打开串口连接。"""
    try:
        success = bridge.device_connect(body.port, body.baudrate)
    except Exception as exc:
        raise HTTPException(500, f"连接失败: {exc}") from exc

    if not success:
        detail = f"打开串口 {body.port} 失败"
        try:
            rs485 = bridge._get_rs485()
            last_error = getattr(rs485, "_last_error", "")
            if last_error:
                detail = f"{detail}: {last_error}"
        except Exception:
            pass
        raise HTTPException(400, detail)

    return {
        "status": "connected",
        "port": body.port,
        "baudrate": body.baudrate,
        "timestamp": _ts(),
    }


@router.post("/disconnect")
async def disconnect_port(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """关闭串口连接。"""
    try:
        bridge.device_disconnect()
    except Exception as exc:
        raise HTTPException(500, f"断开失败: {exc}") from exc

    return {
        "status": "disconnected",
        "timestamp": _ts(),
    }
