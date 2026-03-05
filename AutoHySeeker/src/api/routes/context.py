"""Context API routes — invoke C1 ContextualizeExperiment & C2 SuggestNextExperiment."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.graph.supervisor_graph import get_supervisor_graph

router = APIRouter(prefix="/context", tags=["context"])


class ContextRequest(BaseModel):
    """Request body for the context invoke endpoint.

    Attributes:
        action: ``"contextualize"`` (C1) or ``"suggest"`` (C2).
        run_dir: Path to the current experiment run directory (C1).
        history_dir: Parent directory with historical runs (C1).
        previous_results: Pre-computed metric dicts from previous runs (C1).
        metrics: Specific metric keys to contextualise (C1).
        threshold_sigma: σ threshold for anomaly detection in C1 (default 2.0).
        max_history: Max historical runs to load in C1 (default 20).
        context_data: C1 output forwarded to C2.  When ``action="suggest"``
                      and this is empty, C2 relies on *goal* alone.
        goal: Overarching experiment goal string (C2).
        name: Name for the suggested plan (C2).
        description: Plan description (C2).
        tags: Tags applied to the generated plan (C2).
        extra_context: Additional key-value pairs forwarded into graph state.
    """

    action: str = Field(
        "contextualize",
        description="'contextualize' (C1) or 'suggest' (C2)",
    )
    # C1 fields
    run_dir: str = Field("", description="Run directory for C1")
    history_dir: str = Field("", description="History directory for C1")
    previous_results: list[dict[str, Any]] = Field(
        default_factory=list, description="Pre-computed historical metric dicts"
    )
    metrics: list[str] = Field(default_factory=list, description="Metric keys to contextualise")
    threshold_sigma: float = Field(2.0, ge=0.5, le=10.0)
    max_history: int = Field(20, ge=1, le=200)
    # C2 fields
    context_data: dict[str, Any] = Field(
        default_factory=dict, description="C1 output (comparison/trend/anomalies)"
    )
    goal: str = Field("", description="Overarching experiment goal")
    name: str = Field("", description="Name for the suggested plan")
    description: str = Field("", description="Plan description")
    tags: list[str] = Field(default_factory=list)
    # Pass-through
    extra_context: dict[str, Any] = Field(default_factory=dict)


@router.post("/invoke")
async def invoke_context(request: ContextRequest) -> dict[str, Any]:
    """Invoke C1 or C2 via the supervisor subgraph.

    Routes to:

    * ``"contextualize"`` → C1 ContextualizeExperimentSkill
    * ``"suggest"``       → C2 SuggestNextExperimentSkill

    Returns the graph result state including ``result`` and optional ``error``.
    """
    graph = get_supervisor_graph()

    ctx: dict[str, Any] = dict(request.extra_context)
    if request.context_data:
        ctx["context_data"] = request.context_data

    task: dict[str, Any] = {
        "type": request.action,
        # C1
        "run_dir": request.run_dir,
        "history_dir": request.history_dir,
        "metrics": request.metrics or None,
        "threshold_sigma": request.threshold_sigma,
        "max_history": request.max_history,
        # C2
        "context_data": request.context_data or None,
        "goal": request.goal,
        "name": request.name,
        "description": request.description,
        "tags": request.tags or None,
    }
    if request.previous_results:
        task["previous_results"] = request.previous_results

    state: dict[str, Any] = {
        "messages": [],
        "current_agent": "context",
        "task": task,
        "context": ctx,
        "error": None,
        "result": None,
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


@router.post("/contextualize")
async def contextualize_endpoint(
    run_dir: str,
    history_dir: str = "",
    threshold_sigma: float = 2.0,
    max_history: int = 20,
) -> dict[str, Any]:
    """Shortcut to invoke C1 ContextualizeExperimentSkill."""
    req = ContextRequest(
        action="contextualize",
        run_dir=run_dir,
        history_dir=history_dir,
        threshold_sigma=threshold_sigma,
        max_history=max_history,
    )
    return await invoke_context(req)


@router.post("/suggest-next")
async def suggest_next_endpoint(
    goal: str = "",
    name: str = "",
) -> dict[str, Any]:
    """Shortcut to invoke C2 SuggestNextExperimentSkill (goal-only mode)."""
    req = ContextRequest(action="suggest", goal=goal, name=name)
    return await invoke_context(req)
