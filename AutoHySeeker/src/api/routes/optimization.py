"""Optimization loop management API.

Endpoints for starting, stopping, and querying the AutoHySeeker closed-loop
optimization process.  The MicroHySeeker dashboard polls these endpoints to
display real-time agent status.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

_logger = logging.getLogger("autohyseeker.api.optimization")
router = APIRouter(prefix="/api/optimization", tags=["optimization"])

# ── In-process optimization state ────────────────────────────────────────────

_loop_instance: Any = None          # OptimizationLoop instance (lazy init)
_loop_task: asyncio.Task | None = None
_last_state: dict[str, Any] = {}    # snapshot of the most recent loop state
_start_time: str | None = None
_config: dict[str, Any] = {}


# ── Request / response models ─────────────────────────────────────────────────

class OptimizationStartRequest(BaseModel):
    goal: str = "最小化 Fe-Co-Ni 三元合金 HER 过电位"
    max_rounds: int = Field(default=10, ge=1, le=100)
    target_metric: str = "overpotential_mV"
    direction: str = "minimize"
    template_id: str = "tpl_her_standard"
    elements: list[str] = Field(default_factory=lambda: ["Fe", "Co", "Ni"])
    dry_run: bool = False


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_optimization_status() -> Dict[str, Any]:
    """Return current optimization loop status.

    Polled by MicroHySeeker dashboard every few seconds.
    """
    global _loop_instance, _loop_task

    running = (
        _loop_instance is not None
        and getattr(_loop_instance, "is_running", False)
        and _loop_task is not None
        and not _loop_task.done()
    )

    # Refresh snapshot from live loop
    if _loop_instance is not None:
        live_state = getattr(_loop_instance, "current_state", None)
        if live_state:
            _last_state.update(live_state)

    best = _last_state.get("best_result")
    optimization = _last_state.get("optimization", {})

    return {
        "running": running,
        "status": "running" if running else _last_state.get("status", "idle"),
        "current_round": _last_state.get("current_round", 0),
        "max_rounds": optimization.get("max_rounds", _config.get("max_rounds", 0)),
        "best_result": best,
        "goal": optimization.get("goal", _config.get("goal", "")),
        "target_metric": optimization.get("target_metric", _config.get("target_metric", "")),
        "errors": _last_state.get("errors", [])[-5:],  # last 5 errors
        "start_time": _start_time,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/start")
async def start_optimization(
    req: OptimizationStartRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """Start a new optimization loop run.

    Returns immediately; the loop runs in the background.
    Raises 409 if a loop is already running.
    """
    global _loop_instance, _loop_task, _last_state, _start_time, _config

    # Check already running
    if (
        _loop_instance is not None
        and getattr(_loop_instance, "is_running", False)
        and _loop_task is not None
        and not _loop_task.done()
    ):
        raise HTTPException(status_code=409, detail="Optimization loop is already running")

    # Save config
    _config = req.model_dump()
    _last_state = {}
    _start_time = datetime.now(timezone.utc).isoformat()

    async def _run() -> None:
        global _loop_instance, _last_state
        try:
            from src.run_optimization import run_optimization
            result = await run_optimization(
                goal=req.goal,
                max_rounds=req.max_rounds,
                target_metric=req.target_metric,
                direction=req.direction,
                template_id=req.template_id,
                elements=req.elements,
                dry_run=req.dry_run,
            )
            _last_state = {
                "status": "completed",
                "current_round": result.get("total_rounds", 0),
                "best_result": result.get("best_result"),
                "optimization": _config,
                "errors": [],
            }
        except Exception as exc:
            _logger.exception("Optimization loop failed")
            _last_state["status"] = "error"
            _last_state.setdefault("errors", []).append(str(exc))

    # Launch as background task
    _loop_task = asyncio.ensure_future(_run())

    _logger.info(
        "Optimization loop started: goal=%r rounds=%d metric=%s",
        req.goal, req.max_rounds, req.target_metric,
    )
    return {
        "status": "started",
        "goal": req.goal,
        "max_rounds": req.max_rounds,
        "start_time": _start_time,
    }


@router.post("/stop")
async def stop_optimization() -> Dict[str, Any]:
    """Request the running optimization loop to stop gracefully."""
    global _loop_instance

    if _loop_instance is None or not getattr(_loop_instance, "is_running", False):
        return {"status": "not_running"}

    _loop_instance.stop()
    _logger.info("Optimization loop stop requested via API")
    return {"status": "stop_requested"}


@router.get("/history")
async def get_optimization_history() -> Dict[str, Any]:
    """Return the experiment history from the current/last run."""
    return {
        "history": _last_state.get("experiment_history", []),
        "best_result": _last_state.get("best_result"),
        "total_rounds": _last_state.get("current_round", 0),
    }


@router.delete("/reset")
async def reset_optimization() -> Dict[str, Any]:
    """Clear the current optimization state (only when not running)."""
    global _loop_instance, _loop_task, _last_state, _start_time, _config

    if (
        _loop_instance is not None
        and getattr(_loop_instance, "is_running", False)
        and _loop_task is not None
        and not _loop_task.done()
    ):
        raise HTTPException(status_code=409, detail="Cannot reset while optimization is running")

    _loop_instance = None
    _loop_task = None
    _last_state = {}
    _start_time = None
    _config = {}

    return {"status": "reset"}
