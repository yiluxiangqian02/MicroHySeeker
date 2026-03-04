"""Experiment supervisor graph for AutoHySeeker."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from src.graph.state import AutoHySeekerState
from src.skills.diagnostics.interactive_troubleshooting import (
    InteractiveTroubleshootingSkill,
)
from src.skills.experiment_execution.execution_monitor import ExecutionMonitorSkill
from src.skills.experiment_execution.smart_scheduler import SmartSchedulerSkill


def route_task(state: AutoHySeekerState) -> Literal["monitor", "schedule", "diagnose"]:
    """Route to appropriate skill based on task type."""
    task = state.get("task", {})
    task_type = task.get("type", "")

    if task_type == "monitor":
        return "monitor"
    elif task_type == "schedule":
        return "schedule"
    elif task_type == "diagnose":
        return "diagnose"
    else:
        # Default to monitor
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


def build_supervisor_graph() -> StateGraph:
    """Build the ExperimentSupervisor subgraph.

    Returns:
        Compiled StateGraph for experiment supervision
    """
    graph = StateGraph(AutoHySeekerState)

    # Add nodes
    graph.add_node("monitor", monitor_node)
    graph.add_node("schedule", schedule_node)
    graph.add_node("diagnose", diagnose_node)

    # Add routing from entry point
    graph.set_conditional_entry_point(
        route_task,
        {
            "monitor": "monitor",
            "schedule": "schedule",
            "diagnose": "diagnose",
        },
    )

    # All nodes lead to END
    graph.add_edge("monitor", END)
    graph.add_edge("schedule", END)
    graph.add_edge("diagnose", END)

    return graph.compile()
