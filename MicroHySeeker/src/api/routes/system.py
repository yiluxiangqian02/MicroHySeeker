"""系统控制路由。

端点：
  GET  /api/system/health    健康检查
  GET  /api/system/logs      获取近期日志
  POST /api/system/restart   重启 MicroHySeeker 进程
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger("microhyseeker.api.routes.system")
router = APIRouter()


def _get_bridge(request: Request):
    bridge = getattr(request.app.state, "bridge", None)
    if bridge is None:
        raise HTTPException(503, "API bridge not available")
    return bridge


# ── 端点 ──────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """健康检查。"""
    try:
        status = bridge.get_status()
        uptime = bridge.get_uptime()
    except Exception as exc:
        raise HTTPException(500, f"健康检查失败: {exc}") from exc

    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 1),
        "engine_state": status.get("state", "unknown"),
        "pid": os.getpid(),
        "python": sys.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/logs")
async def get_logs(
    n: int = Query(default=100, ge=1, le=500, description="返回最近 n 条日志"),
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """获取近期运行日志（来自 ExperimentRunner 的 log_message 信号）。"""
    try:
        logs = bridge.get_recent_logs(n)
    except Exception as exc:
        raise HTTPException(500, f"日志获取失败: {exc}") from exc

    return {
        "count": len(logs),
        "logs": logs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class RestartRequest(BaseModel):
    confirm: bool = False


@router.post("/restart")
async def restart_app(
    body: RestartRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """重启 MicroHySeeker 进程。

    需要传入 `{"confirm": true}` 才会执行，防止误触。
    重启通过替换当前进程（os.execv）实现，Qt 窗口会重新启动。
    """
    if not body.confirm:
        raise HTTPException(
            400,
            "需要确认：请传入 {\"confirm\": true} 以执行重启。",
        )

    logger.warning("Restart requested via API — restarting process")

    # 停止当前实验（如有）
    try:
        bridge.stop_experiment()
    except Exception:
        pass

    import threading

    def _do_restart():
        import time
        time.sleep(0.5)  # 给 HTTP 响应时间发出
        os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=_do_restart, daemon=True).start()

    return {
        "status": "restarting",
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
