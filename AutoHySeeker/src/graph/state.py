"""State model for AutoHySeeker supervisor graph."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

try:
    from langchain_core.messages import BaseMessage
except ImportError:  # pragma: no cover - dependency availability dependent
    class BaseMessage:  # type: ignore[no-redef]
        """Fallback type placeholder when langchain-core is unavailable."""

        pass


class AutoHySeekerState(TypedDict):
    messages: list[BaseMessage]
    current_agent: str
    task: dict[str, Any]
    context: dict[str, Any]
    error: Optional[str]
    result: Optional[dict[str, Any]]

    # Optimization loop state (populated when running closed-loop optimization)
    optimization: Optional[dict[str, Any]]
    experiment_history: list[dict[str, Any]]
    current_round: int
    best_result: Optional[dict[str, Any]]


def make_initial_optimization(
    goal: str,
    target_metric: str,
    optimization_direction: str,
    search_space: dict[str, Any],
    constraints: dict[str, Any] | None = None,
    template_id: str = "",
    total_volume_ul: float = 1000.0,
    max_rounds: int = 20,
) -> dict[str, Any]:
    """Create an initial optimization config dict for the state."""
    return {
        "goal": goal,
        "target_metric": target_metric,
        "optimization_direction": optimization_direction,
        "search_space": search_space,
        "constraints": constraints or {"sum_equals": 1.0, "min_component": 0.05},
        "template_id": template_id,
        "total_volume_ul": total_volume_ul,
        "max_rounds": max_rounds,
        "status": "idle",  # idle → designing → executing → analyzing → evaluating → completed
    }

