"""DiagnosticsExpert subgraph for AutoHySeeker."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from src.graph.state import AutoHySeekerState
from src.agents.diagnostics_nodes import (
    analyze_failure,
    check_health,
    generate_diagnosis_report,
    route_diagnostics,
)


class DiagnosticsState(AutoHySeekerState, total=False):
    """Extended state for the DiagnosticsExpert subgraph.

    Inherits all fields from :class:`~src.graph.state.AutoHySeekerState`
    and adds:

    * ``diagnostics_results`` — list of serialized DiagnosticResult or
      HealthStatus dicts produced by the active skill.
    """

    diagnostics_results: list[dict[str, Any]]


def build_diagnostics_graph() -> Any:
    """Build and compile the DiagnosticsExpert subgraph.

    Graph topology::

        [entry] ──(route_diagnostics)──► analyze_failure ──► generate_diagnosis_report ──► END
                                     └──► check_health   ──┘

    The conditional entry point inspects ``state['task']['action']`` to choose
    between ``analyze_failure`` (D1) and ``check_health`` (D2).

    Returns:
        A compiled :class:`~langgraph.graph.StateGraph`.
    """
    graph: StateGraph = StateGraph(DiagnosticsState)

    # ── nodes ──────────────────────────────────────────────────────────────
    graph.add_node("analyze_failure", analyze_failure)
    graph.add_node("check_health", check_health)
    graph.add_node("generate_diagnosis_report", generate_diagnosis_report)

    # ── conditional entry: route based on task action ──────────────────────
    graph.set_conditional_entry_point(
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
