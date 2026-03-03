"""Build and cache the LangGraph supervisor orchestrator."""

from __future__ import annotations

import asyncio
from typing import Any

from src.graph.nodes import (
    format_response,
    route_intent,
    run_data_analyst,
    run_diagnostics,
    run_exp_designer,
    run_exp_supervisor,
    run_knowledge_mgr,
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
            "data_analyst": run_data_analyst,
            "exp_designer": run_exp_designer,
            "exp_supervisor": run_exp_supervisor,
            "diagnostics": run_diagnostics,
            "knowledge_mgr": run_knowledge_mgr,
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
    graph.add_node("data_analyst", run_data_analyst)
    graph.add_node("exp_designer", run_exp_designer)
    graph.add_node("exp_supervisor", run_exp_supervisor)
    graph.add_node("diagnostics", run_diagnostics)
    graph.add_node("knowledge_mgr", run_knowledge_mgr)
    graph.add_node("format_response", format_response)

    graph.add_edge(START, "route_intent")
    graph.add_conditional_edges(
        "route_intent",
        select_agent_node,
        {
            "data_analyst": "data_analyst",
            "exp_designer": "exp_designer",
            "exp_supervisor": "exp_supervisor",
            "diagnostics": "diagnostics",
            "knowledge_mgr": "knowledge_mgr",
        },
    )

    graph.add_edge("data_analyst", "format_response")
    graph.add_edge("exp_designer", "format_response")
    graph.add_edge("exp_supervisor", "format_response")
    graph.add_edge("diagnostics", "format_response")
    graph.add_edge("knowledge_mgr", "format_response")
    graph.add_edge("format_response", END)
    return graph.compile()


_SUPERVISOR_GRAPH: Any | None = None


def get_supervisor_graph() -> Any:
    global _SUPERVISOR_GRAPH
    if _SUPERVISOR_GRAPH is None:
        _SUPERVISOR_GRAPH = build_supervisor_graph()
    return _SUPERVISOR_GRAPH

