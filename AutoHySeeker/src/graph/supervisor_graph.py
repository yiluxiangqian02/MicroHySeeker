"""Experiment supervisor graph for AutoHySeeker."""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from src.graph.state import AutoHySeekerState
from src.skills.contextualize_experiment import ContextualizeExperimentSkill
from src.skills.diagnostics.interactive_troubleshooting import (
    InteractiveTroubleshootingSkill,
)
from src.skills.experiment_execution.execution_monitor import ExecutionMonitorSkill
from src.skills.experiment_execution.smart_scheduler import SmartSchedulerSkill
from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - dependency availability dependent
    END = "END"  # type: ignore[assignment]
    START = "START"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]


def route_task(
    state: AutoHySeekerState,
) -> Literal["monitor", "schedule", "diagnose", "contextualize", "suggest"]:
    """Route to appropriate skill based on task type."""
    task = state.get("task", {})
    task_type = task.get("type", "")

    if task_type == "monitor":
        return "monitor"
    elif task_type == "schedule":
        return "schedule"
    elif task_type == "diagnose":
        return "diagnose"
    elif task_type == "contextualize":
        return "contextualize"
    elif task_type == "suggest":
        return "suggest"
    else:
        return "monitor"


async def monitor_node(state: AutoHySeekerState) -> dict[str, Any]:
    """Execute execution monitoring."""
    task = state.get("task", {})
    run_dir = task.get("run_dir", "")

    skill = ExecutionMonitorSkill()
    result = await skill.execute(run_dir=run_dir)

    return {
        "result": result.model_dump(),
        "error": None if result.success else result.message,
    }


async def schedule_node(state: AutoHySeekerState) -> dict[str, Any]:
    """Execute smart scheduling."""
    task = state.get("task", {})
    experiments = task.get("experiments", [])

    skill = SmartSchedulerSkill()
    result = await skill.execute(experiments=experiments)

    return {
        "result": result.model_dump(),
        "error": None if result.success else result.message,
    }


async def diagnose_node(state: AutoHySeekerState) -> dict[str, Any]:
    """Execute interactive troubleshooting."""
    task = state.get("task", {})
    symptom = task.get("symptom", "")

    skill = InteractiveTroubleshootingSkill()
    result = await skill.execute(symptom=symptom)

    return {
        "result": result.model_dump(),
        "error": None if result.success else result.message,
    }


async def contextualize_node(state: AutoHySeekerState) -> dict[str, Any]:
    """Execute C1 ContextualizeExperimentSkill."""
    task = state.get("task", {})
    skill = ContextualizeExperimentSkill()
    result = await skill.execute(
        run_dir=task.get("run_dir", ""),
        history_dir=task.get("history_dir", ""),
        previous_results=task.get("previous_results"),
        metrics=task.get("metrics"),
        threshold_sigma=float(task.get("threshold_sigma", 2.0)),
        max_history=int(task.get("max_history", 20)),
        kb_path=task.get("kb_path", ""),
        kb_query=task.get("kb_query", ""),
        kb_limit=int(task.get("kb_limit", 5)),
        kb_score_threshold=float(task.get("kb_score_threshold", 0.3)),
    )

    # Propagate context_data into state context so C2 can use it
    ctx = dict(state.get("context", {}))
    ctx["context_data"] = result.data

    return {
        "result": result.model_dump(),
        "context": ctx,
        "error": None if result.success else result.message,
    }


async def suggest_node(state: AutoHySeekerState) -> dict[str, Any]:
    """Execute C2 SuggestNextExperimentSkill."""
    task = state.get("task", {})
    state_ctx = state.get("context", {})

    # Accept context_data from task payload or from C1 via state context
    context_data = task.get("context_data") or state_ctx.get("context_data") or {}

    skill = SuggestNextExperimentSkill()
    result = await skill.execute(
        context_data=context_data,
        goal=task.get("goal", ""),
        name=task.get("name", ""),
        description=task.get("description", ""),
        tags=task.get("tags"),
    )

    return {
        "result": result.model_dump(),
        "error": None if result.success else result.message,
    }


class _FallbackSupervisorGraph:
    """Fallback graph for environments without LangGraph."""

    _NODES: dict[str, Any] = {}  # populated after function definitions

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = dict(state)
        node_name = route_task(merged)  # type: ignore[arg-type]
        node_fn = {
            "monitor": monitor_node,
            "schedule": schedule_node,
            "diagnose": diagnose_node,
            "contextualize": contextualize_node,
            "suggest": suggest_node,
        }[node_name]
        merged.update(await node_fn(merged))
        return merged

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self.ainvoke(state))


def build_supervisor_graph() -> Any:
    """Build the ExperimentSupervisor subgraph.

    Graph topology::

        START ──(route_task)──► monitor       ──► END
                             ├──► schedule      ──► END
                             ├──► diagnose      ──► END
                             ├──► contextualize ──► END
                             └──► suggest       ──► END

    Returns:
        Compiled StateGraph (or fallback graph if LangGraph is unavailable).
    """
    if StateGraph is None:
        return _FallbackSupervisorGraph()

    graph: StateGraph = StateGraph(AutoHySeekerState)

    # Add nodes
    graph.add_node("monitor", monitor_node)
    graph.add_node("schedule", schedule_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("contextualize", contextualize_node)
    graph.add_node("suggest", suggest_node)

    # Conditional entry from START using add_conditional_edges (LangGraph >=0.2)
    graph.add_conditional_edges(
        START,
        route_task,
        {
            "monitor": "monitor",
            "schedule": "schedule",
            "diagnose": "diagnose",
            "contextualize": "contextualize",
            "suggest": "suggest",
        },
    )

    # All nodes lead to END
    graph.add_edge("monitor", END)
    graph.add_edge("schedule", END)
    graph.add_edge("diagnose", END)
    graph.add_edge("contextualize", END)
    graph.add_edge("suggest", END)

    return graph.compile()


_SUPERVISOR_GRAPH: Any | None = None


def get_supervisor_graph() -> Any:
    """Return a cached compiled supervisor subgraph."""
    global _SUPERVISOR_GRAPH
    if _SUPERVISOR_GRAPH is None:
        _SUPERVISOR_GRAPH = build_supervisor_graph()
    return _SUPERVISOR_GRAPH
