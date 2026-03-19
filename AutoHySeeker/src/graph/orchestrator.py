"""Build and cache the LangGraph supervisor orchestrator.

After agent consolidation (7→4), DataAnalyst / KnowledgeManager /
ExperimentSupervisor are skills of the Orchestrator.  The graph only
contains 4 specialist nodes; backward-compatible runner functions in
nodes.py silently redirect to the orchestrator.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.graph.nodes import (
    format_response,
    route_intent,
    run_diagnostics,
    run_exp_designer,
    run_exp_executor,
    run_orchestrator,
    select_agent_node,
)
from src.graph.state import AutoHySeekerState

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - dependency availability dependent
    END = "END"
    START = "START"
    StateGraph = None  # type: ignore[assignment]


class _FallbackGraph:
    """Fallback graph for environments without LangGraph."""

    async def ainvoke(self, state: AutoHySeekerState) -> AutoHySeekerState:
        merged: dict[str, Any] = dict(state)
        merged.update(route_intent(merged))
        node = select_agent_node(merged)  # type: ignore[arg-type]

        runners = {
            "orchestrator": run_orchestrator,
            "exp_designer": run_exp_designer,
            "exp_executor": run_exp_executor,
            "diagnostics": run_diagnostics,
        }
        merged.update(await runners[node](merged))  # type: ignore[arg-type]
        merged.update(format_response(merged))  # type: ignore[arg-type]
        return merged  # type: ignore[return-value]

    def invoke(self, state: AutoHySeekerState) -> AutoHySeekerState:
        return asyncio.run(self.ainvoke(state))


def build_supervisor_graph() -> Any:
    """Build a supervisor graph that routes intent then invokes one specialist agent."""
    if StateGraph is None:
        return _FallbackGraph()

    graph = StateGraph(AutoHySeekerState)
    graph.add_node("route_intent", route_intent)
    graph.add_node("orchestrator", run_orchestrator)
    graph.add_node("exp_designer", run_exp_designer)
    graph.add_node("exp_executor", run_exp_executor)
    graph.add_node("diagnostics", run_diagnostics)
    graph.add_node("format_response", format_response)

    graph.add_edge(START, "route_intent")
    graph.add_conditional_edges(
        "route_intent",
        select_agent_node,
        {
            "orchestrator": "orchestrator",
            "exp_designer": "exp_designer",
            "exp_executor": "exp_executor",
            "diagnostics": "diagnostics",
        },
    )

    graph.add_edge("orchestrator", "format_response")
    graph.add_edge("exp_designer", "format_response")
    graph.add_edge("exp_executor", "format_response")
    graph.add_edge("diagnostics", "format_response")
    graph.add_edge("format_response", END)
    return graph.compile()


_SUPERVISOR_GRAPH: Any | None = None


def get_supervisor_graph() -> Any:
    global _SUPERVISOR_GRAPH
    if _SUPERVISOR_GRAPH is None:
        _SUPERVISOR_GRAPH = build_supervisor_graph()
    return _SUPERVISOR_GRAPH
