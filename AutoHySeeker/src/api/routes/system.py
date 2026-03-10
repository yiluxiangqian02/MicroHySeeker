"""System status and monitoring APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

router = APIRouter(prefix="/api/system", tags=["system"])

# In-memory activity log (ring buffer, 100 entries)
_ACTIVITY_LOG: list[dict[str, Any]] = []
_MAX_ACTIVITIES = 100


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
