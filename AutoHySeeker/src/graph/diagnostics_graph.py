"""DiagnosticsExpert subgraph for AutoHySeeker."""

from __future__ import annotations

import asyncio
from typing import Any

from src.graph.state import AutoHySeekerState
from src.agents.diagnostics_nodes import (
    analyze_failure,
    check_health,
    generate_diagnosis_report,
    route_diagnostics,
)

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover - dependency availability dependent
    END = "END"  # type: ignore[assignment]
    START = "START"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]


class DiagnosticsState(AutoHySeekerState, total=False):
    """Extended state for the DiagnosticsExpert subgraph.

    Inherits all fields from :class:`~src.graph.state.AutoHySeekerState`
    and adds:

    * ``diagnostics_results`` — list of serialized DiagnosticResult or
      HealthStatus dicts produced by the active skill.
    """

    diagnostics_results: list[dict[str, Any]]


class _FallbackDiagnosticsGraph:
    """Fallback graph for environments without LangGraph."""

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = dict(state)
        node = route_diagnostics(merged)
        if node == "analyze_failure":
            merged.update(await analyze_failure(merged))
        else:
            merged.update(await check_health(merged))
        merged.update(await generate_diagnosis_report(merged))
        return merged

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self.ainvoke(state))


def build_diagnostics_graph() -> Any:
    """Build and compile the DiagnosticsExpert subgraph.

    Graph topology::

        START ──(route_diagnostics)──► analyze_failure ──► generate_diagnosis_report ──► END
                                   └──► check_health   ──┘

    The conditional entry inspects ``state['task']['action']`` to choose
    between ``analyze_failure`` (D1) and ``check_health`` (D2).

    Returns:
        A compiled :class:`~langgraph.graph.StateGraph` or a fallback graph.
    """
    if StateGraph is None:
        return _FallbackDiagnosticsGraph()

    graph: StateGraph = StateGraph(DiagnosticsState)

    # ── nodes ──────────────────────────────────────────────────────────────
    graph.add_node("analyze_failure", analyze_failure)
    graph.add_node("check_health", check_health)
    graph.add_node("generate_diagnosis_report", generate_diagnosis_report)

    # ── conditional entry from START: route based on task action ───────────
    graph.add_conditional_edges(
        START,
        route_diagnostics,
        {
            "analyze_failure": "analyze_failure",
            "check_health": "check_health",
        },
    )

    # ── edges: both skill nodes feed the report generator, then END ────────
    graph.add_edge("analyze_failure", "generate_diagnosis_report")
    graph.add_edge("check_health", "generate_diagnosis_report")
    graph.add_edge("generate_diagnosis_report", END)

    return graph.compile()


_DIAGNOSTICS_GRAPH: Any | None = None


def get_diagnostics_graph() -> Any:
    """Return a cached compiled diagnostics subgraph."""
    global _DIAGNOSTICS_GRAPH
    if _DIAGNOSTICS_GRAPH is None:
        _DIAGNOSTICS_GRAPH = build_diagnostics_graph()
    return _DIAGNOSTICS_GRAPH
