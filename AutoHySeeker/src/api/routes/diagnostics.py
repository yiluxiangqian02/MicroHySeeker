"""Diagnostics API routes — invoke DiagnosticsExpert subgraph directly."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.graph.diagnostics_graph import get_diagnostics_graph

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class DiagnosticsRequest(BaseModel):
    """Request body for the diagnostics invoke endpoint.

    Attributes:
        action: ``"analyze_failure"`` (D1) or ``"check_health"`` (D2).
        run_dir: Path to the failed experiment run directory (required for D1).
        data_dir: Path to the data directory to scan (required for D2).
        recent_n: Number of recent experiments to evaluate in health check.
        context: Optional extra context forwarded into the graph state.
    """

    action: str = Field("check_health", description="'analyze_failure' or 'check_health'")
    run_dir: str = Field("", description="Run directory for analyze_failure action")
    data_dir: str = Field("", description="Data directory for check_health action")
    recent_n: int = Field(10, ge=1, le=200)
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/invoke")
async def invoke_diagnostics(request: DiagnosticsRequest) -> dict[str, Any]:
    """Invoke the DiagnosticsExpert subgraph.

    Routes to D1 (analyze_failure) or D2 (check_health) based on ``action``.

    Returns a diagnosis report with findings and severity counts.
    """
    graph = get_diagnostics_graph()
    state: dict[str, Any] = {
        "messages": [],
        "current_agent": "diagnostics",
        "task": {
            "action": request.action,
            "run_dir": request.run_dir,
            "data_dir": request.data_dir,
            "recent_n": request.recent_n,
        },
        "context": request.context,
        "error": None,
        "result": None,
        "diagnostics_results": [],
    }

    try:
        result_state = await graph.ainvoke(state)
        return {
            "ok": not bool(result_state.get("error")),
            "action": request.action,
            "result": result_state.get("result"),
            "error": result_state.get("error"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze-failure")
async def analyze_failure_endpoint(run_dir: str = "") -> dict[str, Any]:
    """Shortcut to invoke D1 DiagnoseFailureSkill via the diagnostics subgraph."""
    req = DiagnosticsRequest(action="analyze_failure", run_dir=run_dir)
    return await invoke_diagnostics(req)


@router.post("/check-health")
async def check_health_endpoint(data_dir: str = "", recent_n: int = 10) -> dict[str, Any]:
    """Shortcut to invoke D2 SystemHealthCheckSkill via the diagnostics subgraph."""
    req = DiagnosticsRequest(action="check_health", data_dir=data_dir, recent_n=recent_n)
    return await invoke_diagnostics(req)
