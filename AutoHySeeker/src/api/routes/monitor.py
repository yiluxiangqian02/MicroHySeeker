"""Monitor control APIs for realtime and heartbeat monitoring."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.agents.exp_executor import get_shared_executor_agent
from src.common.config import MONITOR_CONFIG

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


class MonitorToggleRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable L2 heartbeat monitoring.")


class MonitorConfigUpdateRequest(BaseModel):
    heartbeat_enabled: bool | None = None
    heartbeat_interval_s: float | None = Field(default=None, ge=1.0)
    heartbeat_model: str | None = None


@router.post("/toggle")
async def toggle_monitoring(req: MonitorToggleRequest) -> dict[str, Any]:
    executor = get_shared_executor_agent()
    executor.set_heartbeat_enabled(req.enabled)

    heartbeat_cfg = MONITOR_CONFIG.setdefault("heartbeat_inspector", {})
    heartbeat_cfg["enabled"] = req.enabled

    return {
        "ok": True,
        "heartbeat_enabled": req.enabled,
        "monitor_status": executor.get_monitor_status(),
    }


@router.get("/status")
async def get_monitor_status() -> dict[str, Any]:
    executor = get_shared_executor_agent()
    heartbeat_cfg = MONITOR_CONFIG.get("heartbeat_inspector", {})
    realtime_cfg = MONITOR_CONFIG.get("realtime_monitor", {})
    return {
        "heartbeat_enabled": bool(heartbeat_cfg.get("enabled", False)),
        "heartbeat_interval_s": heartbeat_cfg.get("interval_s", 30),
        "heartbeat_model": heartbeat_cfg.get("model", "qwen3-max"),
        "realtime_monitor_enabled": bool(realtime_cfg.get("enabled", True)),
        "monitor_status": executor.get_monitor_status(),
    }


@router.put("/config")
async def update_monitor_config(req: MonitorConfigUpdateRequest) -> dict[str, Any]:
    heartbeat_cfg = MONITOR_CONFIG.setdefault("heartbeat_inspector", {})
    if req.heartbeat_enabled is not None:
        heartbeat_cfg["enabled"] = req.heartbeat_enabled
    if req.heartbeat_interval_s is not None:
        heartbeat_cfg["interval_s"] = req.heartbeat_interval_s
    if req.heartbeat_model is not None:
        heartbeat_cfg["model"] = req.heartbeat_model

    executor = get_shared_executor_agent()
    executor.update_monitor_config(heartbeat=heartbeat_cfg)

    return {
        "ok": True,
        "config": {
            "heartbeat_enabled": heartbeat_cfg.get("enabled", False),
            "heartbeat_interval_s": heartbeat_cfg.get("interval_s", 30),
            "heartbeat_model": heartbeat_cfg.get("model", "qwen3-max"),
        },
        "monitor_status": executor.get_monitor_status(),
    }
