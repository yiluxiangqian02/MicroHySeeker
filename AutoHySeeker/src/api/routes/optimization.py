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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_logger = logging.getLogger("autohyseeker.api.optimization")
router = APIRouter(prefix="/api/optimization", tags=["optimization"])

# ── In-process optimization state ────────────────────────────────────────────

_loop_instance: Any = None          # OptimizationLoop instance (lazy init)
_loop_task: asyncio.Task | None = None
_last_state: dict[str, Any] = {}    # snapshot of the most recent loop state
_start_time: str | None = None
_config: dict[str, Any] = {}


class _ManagedOptimizationRun:
    """Tracks the background optimization task for status polling and stop control."""

    def __init__(self, config: dict[str, Any], start_time: str) -> None:
        self._stop_requested = False
        self._is_running = True
        self._state: dict[str, Any] = {
            "status": "starting",
            "current_round": 0,
            "best_result": None,
            "experiment_history": [],
            "errors": [],
            "optimization": config,
            "start_time": start_time,
            "final_decision": None,
        }

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def current_state(self) -> dict[str, Any]:
        return dict(self._state)

    def publish(self, snapshot: dict[str, Any]) -> None:
        self._state.update(snapshot)

    def stop(self) -> None:
        self._stop_requested = True
        self._state["status"] = "stopping"

    def should_stop(self) -> bool:
        return self._stop_requested

    def finish(self, result: dict[str, Any]) -> None:
        if "current_round" not in result and "total_rounds" in result:
            result = dict(result)
            result["current_round"] = result["total_rounds"]
        self._state.update(result)
        self._is_running = False

    def fail(self, exc: Exception) -> None:
        self._state["status"] = "error"
        self._state.setdefault("errors", []).append(str(exc))
        self._is_running = False


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
    _loop_instance = _ManagedOptimizationRun(_config, _start_time)
    _last_state = _loop_instance.current_state

    async def _run() -> None:
        global _loop_instance, _last_state
        def _runner() -> dict[str, Any]:
            from src.run_optimization import run_optimization
            return asyncio.run(run_optimization(
                goal=req.goal,
                max_rounds=req.max_rounds,
                target_metric=req.target_metric,
                direction=req.direction,
                template_id=req.template_id,
                elements=req.elements,
                dry_run=req.dry_run,
                progress_callback=_loop_instance.publish,
                should_stop=_loop_instance.should_stop,
            ))

        try:
            # Yield once so the HTTP response can flush before the loop starts heavy work.
            await asyncio.sleep(0)
            result = await asyncio.to_thread(_runner)
            _loop_instance.finish(result)
            _last_state = _loop_instance.current_state
        except Exception as exc:
            _logger.exception("Optimization loop failed")
            if _loop_instance is not None:
                _loop_instance.fail(exc)
                _last_state = _loop_instance.current_state
            else:
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
