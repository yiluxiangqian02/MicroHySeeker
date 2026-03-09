"""Experiment supervisor agent."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.agents.base import BaseAgent
from src.agents.data_analyst import DataAnalystAgent
from src.agents.diagnostics import DiagnosticsExpertAgent
from src.agents.exp_designer import ExperimentDesignerAgent
from src.skills.base import SkillResult
from src.skills.experiment_execution.realtime_monitor import RealtimeMonitorSkill

_logger = logging.getLogger("autohyseeker.exp_supervisor")

# Severity ordering for threshold comparisons
_SEVERITY_ORDER: dict[str, int] = {"warning": 0, "error": 1, "critical": 2}


def _has_anomalies_above_threshold(
    anomalies: list[dict[str, Any]],
    threshold: str,
) -> bool:
    """Return True if any anomaly severity meets or exceeds *threshold*.

    Args:
        anomalies: List of anomaly dicts with a ``severity`` field.
        threshold: Minimum severity level: ``"warning"``, ``"error"``, or
            ``"critical"``.

    Returns:
        True when at least one anomaly qualifies; False otherwise.
    """
    min_level = _SEVERITY_ORDER.get(threshold.lower(), 2)
    return any(
        _SEVERITY_ORDER.get(str(a.get("severity", "")).lower(), -1) >= min_level
        for a in anomalies
    )


class ExperimentSupervisorAgent(BaseAgent):
    """Supervises running experiments by orchestrating real-time monitoring
    and coordinating specialist agents based on observed conditions.

    Workflow
    --------
    1. :meth:`monitor_experiment` starts :class:`~src.skills.experiment_execution\
.realtime_monitor.RealtimeMonitorSkill` to poll experiment status.
    2. Critical (or threshold-matching) anomalies → invoke
       :class:`~src.agents.diagnostics.DiagnosticsExpertAgent`.
    3. Experiment completes successfully → invoke
       :class:`~src.agents.data_analyst.DataAnalystAgent`.
    4. Optionally (``request_optimization=True``) → invoke
       :class:`~src.agents.exp_designer.ExperimentDesignerAgent`.

    Monitoring can be cancelled at any time via :meth:`stop_monitoring`.
    """

    def __init__(self) -> None:
        super().__init__(
            name="exp_supervisor",
            system_prompt=(
                "You are the ExperimentSupervisor agent. Coordinate experiment lifecycle tasks, "
                "operational decisions, and safe execution sequencing."
            ),
        )
        # Holds the currently running asyncio monitoring Task (if any)
        self._monitor_task: asyncio.Task[Any] | None = None

    # ── Public API ─────────────────────────────────────────────────────────────

    async def monitor_experiment(
        self,
        exp_id: str = "",
        run_dir: str = "",
        poll_interval: float = 2.0,
        max_duration: float = 3600.0,
        anomaly_threshold: str = "critical",
        request_optimization: bool = False,
        optimization_goal: str = "",
    ) -> dict[str, Any]:
        """Monitor a running experiment and coordinate specialist agents.

        Args:
            exp_id: Experiment / run ID forwarded to
                :class:`~src.skills.experiment_execution.realtime_monitor\
.RealtimeMonitorSkill`.
            run_dir: Path to the run output directory forwarded to
                :class:`~src.agents.data_analyst.DataAnalystAgent`.
            poll_interval: Seconds between status polls (default ``2.0``).
            max_duration: Maximum total monitoring time in seconds
                (default ``3600``).
            anomaly_threshold: Minimum anomaly severity that triggers
                :class:`~src.agents.diagnostics.DiagnosticsExpertAgent`.
                One of ``"warning"``, ``"error"``, ``"critical"``
                (default ``"critical"``).
            request_optimization: When True, always invoke
                :class:`~src.agents.exp_designer.ExperimentDesignerAgent` after
                monitoring regardless of outcome.
            optimization_goal: Free-text goal hint forwarded to the designer
                agent when *request_optimization* is True.

        Returns:
            A dict with keys:

            - ``exp_id`` (*str*): echoed experiment ID.
            - ``monitor`` (*dict*): raw ``data`` from
              :class:`~src.skills.base.SkillResult`.
            - ``stopped_manually`` (*bool*): True if :meth:`stop_monitoring`
              was called before the experiment ended naturally.
            - ``diagnostics`` (*dict | None*): diagnostics agent response, or
              an ``{"agent": ..., "error": ...}`` dict on failure.
            - ``analysis`` (*dict | None*): data analyst response or error
              dict.
            - ``optimization`` (*dict | None*): designer agent response or
              error dict.
        """
        _logger.info(
            "ExperimentSupervisorAgent: start monitor_experiment exp_id=%r "
            "poll_interval=%.1fs max_duration=%.0fs anomaly_threshold=%r",
            exp_id,
            poll_interval,
            max_duration,
            anomaly_threshold,
        )

        result: dict[str, Any] = {
            "exp_id": exp_id,
            "monitor": {},
            "stopped_manually": False,
            "diagnostics": None,
            "analysis": None,
            "optimization": None,
        }

        # ── Phase 1: Real-time monitoring ──────────────────────────────────────
        skill = RealtimeMonitorSkill()
        self._monitor_task = asyncio.create_task(
            skill.execute(
                exp_id=exp_id,
                poll_interval=poll_interval,
                max_duration=max_duration,
            )
        )

        try:
            skill_result: SkillResult = await self._monitor_task
            result["monitor"] = skill_result.data
            _logger.info(
                "ExperimentSupervisorAgent: monitoring complete — "
                "polls=%s anomalies=%d",
                skill_result.data.get("poll_count"),
                len(skill_result.data.get("anomalies", [])),
            )
        except asyncio.CancelledError:
            result["stopped_manually"] = True
            _logger.info(
                "ExperimentSupervisorAgent: monitoring stopped manually for exp_id=%r",
                exp_id,
            )
            return result
        finally:
            self._monitor_task = None

        # ── Phase 2: Dispatch on anomalies ─────────────────────────────────────
        anomalies: list[dict[str, Any]] = skill_result.data.get("anomalies", [])
        if _has_anomalies_above_threshold(anomalies, anomaly_threshold):
            _logger.info(
                "ExperimentSupervisorAgent: %d qualifying anomaly(ies) detected, "
                "invoking DiagnosticsExpertAgent",
                len(anomalies),
            )
            result["diagnostics"] = await self._run_diagnostics(
                anomalies=anomalies,
                suggestions=skill_result.data.get("suggestions", []),
                last_status=skill_result.data.get("status", {}),
                exp_id=exp_id,
            )

        # ── Phase 3: Dispatch on successful completion ─────────────────────────
        last_status: dict[str, Any] = skill_result.data.get("status", {})
        last_state: str = last_status.get("state", "")
        experiment_completed = last_state in ("completed", "idle") and not last_status.get(
            "has_error"
        )
        if experiment_completed:
            _logger.info(
                "ExperimentSupervisorAgent: experiment completed (state=%r), "
                "invoking DataAnalystAgent",
                last_state,
            )
            result["analysis"] = await self._run_analysis(
                exp_id=exp_id,
                run_dir=run_dir,
                monitor_data=skill_result.data,
            )

        # ── Phase 4: Optional optimisation ────────────────────────────────────
        if request_optimization:
            _logger.info(
                "ExperimentSupervisorAgent: optimisation requested, "
                "invoking ExperimentDesignerAgent"
            )
            result["optimization"] = await self._run_optimization(
                exp_id=exp_id,
                analysis=result.get("analysis"),
                goal=optimization_goal,
                monitor_data=skill_result.data,
            )

        _logger.info(
            "ExperimentSupervisorAgent: monitor_experiment finished for exp_id=%r",
            exp_id,
        )
        return result

    def stop_monitoring(self) -> None:
        """Cancel an in-progress monitoring task.

        Safe to call at any time — a no-op when no monitoring is active.
        """
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            _logger.info("ExperimentSupervisorAgent: stop_monitoring() called")

    @property
    def is_monitoring(self) -> bool:
        """True while a monitoring task is running."""
        return self._monitor_task is not None and not self._monitor_task.done()

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _run_diagnostics(
        self,
        anomalies: list[dict[str, Any]],
        suggestions: list[str],
        last_status: dict[str, Any],
        exp_id: str,
    ) -> dict[str, Any]:
        """Invoke DiagnosticsExpertAgent with anomaly context."""
        agent = DiagnosticsExpertAgent()
        task: dict[str, Any] = {
            "type": "diagnose_anomalies",
            "exp_id": exp_id,
            "anomalies": anomalies,
            "suggestions": suggestions,
        }
        context: dict[str, Any] = {"last_status": last_status}
        try:
            return await agent.invoke(task=task, context=context)
        except Exception as exc:  # noqa: BLE001
            _logger.error(
                "ExperimentSupervisorAgent: DiagnosticsExpertAgent error: %s", exc
            )
            return {"agent": "diagnostics", "error": str(exc)}

    async def _run_analysis(
        self,
        exp_id: str,
        run_dir: str,
        monitor_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke DataAnalystAgent with completed-run context."""
        agent = DataAnalystAgent()
        task: dict[str, Any] = {
            "type": "analyze_completed_experiment",
            "exp_id": exp_id,
            "run_dir": run_dir,
        }
        context: dict[str, Any] = {
            "monitor_summary": {
                "poll_count": monitor_data.get("poll_count"),
                "elapsed_seconds": monitor_data.get("elapsed_seconds"),
                "anomalies": monitor_data.get("anomalies", []),
                "final_state": monitor_data.get("status", {}).get("state"),
            }
        }
        try:
            return await agent.invoke(task=task, context=context)
        except Exception as exc:  # noqa: BLE001
            _logger.error(
                "ExperimentSupervisorAgent: DataAnalystAgent error: %s", exc
            )
            return {"agent": "data_analyst", "error": str(exc)}

    async def _run_optimization(
        self,
        exp_id: str,
        analysis: dict[str, Any] | None,
        goal: str,
        monitor_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke ExperimentDesignerAgent for next-experiment suggestions."""
        agent = ExperimentDesignerAgent()
        task: dict[str, Any] = {
            "type": "suggest_next_experiment",
            "exp_id": exp_id,
            "goal": goal,
        }
        context: dict[str, Any] = {
            "analysis_result": analysis,
            "anomalies": monitor_data.get("anomalies", []),
        }
        try:
            return await agent.invoke(task=task, context=context)
        except Exception as exc:  # noqa: BLE001
            _logger.error(
                "ExperimentSupervisorAgent: ExperimentDesignerAgent error: %s", exc
            )
            return {"agent": "exp_designer", "error": str(exc)}

