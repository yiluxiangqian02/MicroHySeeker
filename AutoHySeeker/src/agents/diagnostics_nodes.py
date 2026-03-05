"""LangGraph node functions and router for the DiagnosticsExpert subgraph."""

from __future__ import annotations

from typing import Any

from src.skills.diagnostics.diagnose_failure import DiagnoseFailureSkill
from src.skills.diagnostics.system_health_check import SystemHealthCheckSkill


async def analyze_failure(state: dict[str, Any]) -> dict[str, Any]:
    """Node: run DiagnoseFailureSkill on the run directory from task params.

    Expects ``state['task']['run_dir']``.
    Writes results into ``state['diagnostics_results']``.
    """
    task = state.get("task", {})
    run_dir: str = task.get("run_dir", "")

    skill = DiagnoseFailureSkill()
    result = await skill.execute(run_dir=run_dir)

    return {
        "diagnostics_results": result.data if result.success else [],
        "error": None if result.success else result.message,
    }


async def check_health(state: dict[str, Any]) -> dict[str, Any]:
    """Node: run SystemHealthCheckSkill on the data directory from task params.

    Expects ``state['task']['data_dir']`` and optionally ``state['task']['recent_n']``.
    Writes results into ``state['diagnostics_results']``.
    """
    task = state.get("task", {})
    data_dir: str = task.get("data_dir", "")
    recent_n: int = int(task.get("recent_n", 10))

    skill = SystemHealthCheckSkill()
    result = await skill.execute(data_dir=data_dir, recent_n=recent_n)

    return {
        "diagnostics_results": result.data if result.success else [],
        "error": None if result.success else result.message,
    }


async def generate_diagnosis_report(state: dict[str, Any]) -> dict[str, Any]:
    """Node: aggregate diagnostics_results into the top-level result field."""
    diagnostics = state.get("diagnostics_results", [])
    task = state.get("task", {})
    action = task.get("action", "unknown")

    # Count severity levels across all results
    severity_counts: dict[str, int] = {}
    for item in diagnostics:
        sev = item.get("severity") or item.get("status") or "info"
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    report = {
        "action": action,
        "total_findings": len(diagnostics),
        "severity_counts": severity_counts,
        "findings": diagnostics,
    }

    return {"result": report}


def route_diagnostics(state: dict[str, Any]) -> str:
    """Conditional edge: route to the appropriate skill node.

    Reads ``state['task']['action']``:
    - ``"analyze_failure"`` → ``"analyze_failure"``
    - ``"check_health"``    → ``"check_health"``
    - anything else         → ``"check_health"`` (safe default)
    """
    action: str = state.get("task", {}).get("action", "")
    if action == "analyze_failure":
        return "analyze_failure"
    return "check_health"
