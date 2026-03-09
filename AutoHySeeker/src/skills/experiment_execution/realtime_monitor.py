"""Real-time monitoring skill for live experiment surveillance.

Polls MicroHySeeker status at regular intervals, detects pump faults,
communication timeouts and stall conditions, and returns a structured
monitoring report with suggestions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.skills.base import BaseSkill, SkillResult
from src.tools.experiment_ctrl import (
    MicroHySeekerAPIError,
    MicroHySeekerUnavailableError,
    get_experiment_status,
)

_logger = logging.getLogger("autohyseeker.realtime_monitor")

# Stall detection: how many consecutive polls with unchanged step count
_STALL_CONSECUTIVE_POLLS: int = 5
# Communication timeout: how many consecutive unreachable polls trigger anomaly
_COMM_TIMEOUT_MAX_FAILURES: int = 3
# Pump status values considered healthy
_HEALTHY_PUMP_STATUSES: frozenset[str] = frozenset(
    {"ok", "normal", "running", "idle", ""}
)


class RealtimeMonitorSkill(BaseSkill):
    """Real-time experiment monitoring via periodic status polling.

    Polls ``get_experiment_status()`` from ``experiment_ctrl`` at a configurable
    interval, accumulates anomaly events, and returns a final monitoring report
    once the experiment ends or ``max_duration`` is reached.

    Detected anomaly types:
    - ``pump_fault``: pump_status field is in an abnormal state.
    - ``communication_timeout``: MicroHySeeker is unreachable for several
      consecutive polls.
    - ``stall``: current_step has not advanced for ``_STALL_CONSECUTIVE_POLLS``
      polls, or the ``is_stalled`` flag is set.
    - ``experiment_error``: the status payload carries ``has_error=True``.
    - ``api_error``: an unexpected API-level error occurred.
    """

    name = "realtime_monitor"
    description = (
        "Poll MicroHySeeker experiment status in real time, detecting pump faults, "
        "communication timeouts, and data anomalies."
    )
    required_tools = ["get_experiment_status"]

    async def execute(
        self,
        exp_id: str = "",
        poll_interval: float = 2.0,
        max_duration: float = 3600.0,
        **kwargs: Any,
    ) -> SkillResult:
        """Monitor a running experiment in real time.

        Args:
            exp_id: Experiment / run ID to monitor.  Used for identity checks;
                ``get_experiment_status()`` is global (not per-run).
            poll_interval: Seconds between consecutive status polls.
                Must be > 0.  Defaults to 2.
            max_duration: Maximum total monitoring time in seconds.
                Must be > 0.  Defaults to 3600.
            **kwargs: Ignored extra keyword arguments.

        Returns:
            :class:`~src.skills.base.SkillResult` where ``data`` contains:

            - ``status`` (*dict*): last observed status payload from MicroHySeeker.
            - ``anomalies`` (*list[dict]*): deduplicated list of detected anomaly
              dicts, each with keys ``type``, ``severity``, ``message``,
              ``detail``.
            - ``suggestions`` (*list[str]*): recommended actions based on the
              detected anomalies and final state.
            - ``poll_count`` (*int*): number of successful status polls performed.
            - ``elapsed_seconds`` (*float*): total monitoring wall-clock time.

            ``success`` is ``True`` when no *critical*-severity anomalies were
            recorded.
        """
        if poll_interval <= 0:
            return SkillResult(
                success=False,
                data={},
                message="poll_interval must be positive",
                artifacts=[],
            )
        if max_duration <= 0:
            return SkillResult(
                success=False,
                data={},
                message="max_duration must be positive",
                artifacts=[],
            )

        anomalies: list[dict[str, Any]] = []
        last_status: dict[str, Any] = {}
        poll_count: int = 0
        consecutive_comm_failures: int = 0

        # Stall-detection state
        last_step: int | None = None
        stall_count: int = 0

        loop = asyncio.get_event_loop()
        start_time: float = loop.time()

        _logger.info(
            "RealtimeMonitorSkill: start monitoring exp_id=%r "
            "poll_interval=%.1fs max_duration=%.0fs",
            exp_id,
            poll_interval,
            max_duration,
        )

        while True:
            elapsed: float = loop.time() - start_time
            if elapsed >= max_duration:
                _logger.info("RealtimeMonitorSkill: max_duration reached, stopping")
                break

            # ── Poll status ──────────────────────────────────────────────────
            try:
                status: dict[str, Any] = await asyncio.to_thread(get_experiment_status)
                last_status = status
                consecutive_comm_failures = 0
                poll_count += 1
            except MicroHySeekerUnavailableError as exc:
                consecutive_comm_failures += 1
                _logger.warning(
                    "RealtimeMonitorSkill: comm failure #%d: %s",
                    consecutive_comm_failures,
                    exc,
                )
                if consecutive_comm_failures >= _COMM_TIMEOUT_MAX_FAILURES:
                    anomalies.append(
                        {
                            "type": "communication_timeout",
                            "severity": "critical",
                            "message": (
                                f"MicroHySeeker unreachable for "
                                f"{consecutive_comm_failures} consecutive polls"
                            ),
                            "detail": str(exc),
                        }
                    )
                    _logger.error(
                        "RealtimeMonitorSkill: communication_timeout anomaly recorded"
                    )
                    break
                await asyncio.sleep(poll_interval)
                continue
            except MicroHySeekerAPIError as exc:
                _logger.error("RealtimeMonitorSkill: API error: %s", exc)
                anomalies.append(
                    {
                        "type": "api_error",
                        "severity": "error",
                        "message": "MicroHySeeker API returned an error response",
                        "detail": str(exc),
                    }
                )
                await asyncio.sleep(poll_interval)
                continue

            # ── Experiment identity check ────────────────────────────────────
            if exp_id and status.get("run_id") and status["run_id"] != exp_id:
                _logger.debug(
                    "RealtimeMonitorSkill: status run_id=%s != target exp_id=%s; "
                    "target experiment may have finished",
                    status.get("run_id"),
                    exp_id,
                )

            # ── Anomaly: explicit error flag ─────────────────────────────────
            if status.get("has_error"):
                anomalies.append(
                    {
                        "type": "experiment_error",
                        "severity": "critical",
                        "message": "Experiment status reports an error (has_error=True)",
                        "detail": status.get("error_message", ""),
                    }
                )

            # ── Anomaly: pump fault ──────────────────────────────────────────
            pump_status: str = str(status.get("pump_status", "")).strip().lower()
            if pump_status not in _HEALTHY_PUMP_STATUSES:
                anomalies.append(
                    {
                        "type": "pump_fault",
                        "severity": "critical",
                        "message": f"Pump status abnormal: {status.get('pump_status')!r}",
                        "detail": f"pump_status={status.get('pump_status')!r}",
                    }
                )

            # ── Anomaly: stall detection ─────────────────────────────────────
            if status.get("is_stalled"):
                anomalies.append(
                    {
                        "type": "stall",
                        "severity": "warning",
                        "message": "Experiment is stalled (is_stalled=True)",
                        "detail": f"run_id={status.get('run_id')!r} "
                                  f"current_step={status.get('current_step')}",
                    }
                )
            elif status.get("is_running"):
                current_step = status.get("current_step")
                if current_step is not None:
                    if current_step == last_step:
                        stall_count += 1
                    else:
                        stall_count = 0
                        last_step = current_step

                    if stall_count >= _STALL_CONSECUTIVE_POLLS:
                        stalled_secs = stall_count * poll_interval
                        anomalies.append(
                            {
                                "type": "stall",
                                "severity": "warning",
                                "message": (
                                    f"Experiment appears stalled: step {current_step} "
                                    f"unchanged for {stall_count} polls "
                                    f"({stalled_secs:.0f}s)"
                                ),
                                "detail": (
                                    f"current_step={current_step}, "
                                    f"stall_count={stall_count}"
                                ),
                            }
                        )
                        stall_count = 0  # reset to avoid repeated identical reports
                else:
                    stall_count = 0

            # ── Stop condition: experiment no longer running ─────────────────
            state: str = status.get("state", "")
            if state in ("idle", "completed", "failed", "error") and not status.get(
                "is_running"
            ):
                _logger.info(
                    "RealtimeMonitorSkill: experiment ended, state=%r", state
                )
                break

            await asyncio.sleep(poll_interval)

        total_elapsed: float = loop.time() - start_time

        # ── Deduplicate anomalies by (type, message) ─────────────────────────
        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for anomaly in anomalies:
            key = (anomaly.get("type", ""), anomaly.get("message", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(anomaly)
        anomalies = deduped

        # ── Build suggestions ────────────────────────────────────────────────
        suggestions: list[str] = _build_suggestions(anomalies, last_status)

        critical_count = sum(
            1 for a in anomalies if a.get("severity") == "critical"
        )
        final_state = last_status.get("state", "unknown")

        _logger.info(
            "RealtimeMonitorSkill: done. polls=%d elapsed=%.1fs "
            "anomalies=%d critical=%d",
            poll_count,
            total_elapsed,
            len(anomalies),
            critical_count,
        )

        return SkillResult(
            success=critical_count == 0,
            data={
                "status": last_status,
                "anomalies": anomalies,
                "suggestions": suggestions,
                "poll_count": poll_count,
                "elapsed_seconds": round(total_elapsed, 2),
            },
            message=(
                f"Monitoring complete: state={final_state}, "
                f"{len(anomalies)} anomaly(ies) detected"
            ),
            artifacts=[],
        )

    def get_schema(self) -> dict:
        """Return JSON Schema for this skill's inputs."""
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "exp_id": {
                    "type": "string",
                    "description": "Experiment / run ID to monitor",
                    "default": "",
                },
                "poll_interval": {
                    "type": "number",
                    "description": "Seconds between status polls",
                    "default": 2.0,
                    "minimum": 0.1,
                },
                "max_duration": {
                    "type": "number",
                    "description": "Maximum monitoring duration in seconds",
                    "default": 3600.0,
                    "minimum": 1.0,
                },
            },
            "required": [],
        }


def _build_suggestions(
    anomalies: list[dict[str, Any]],
    last_status: dict[str, Any],
) -> list[str]:
    """Derive actionable suggestions from detected anomalies and final status.

    Args:
        anomalies: Deduplicated list of anomaly dicts produced during monitoring.
        last_status: Last status payload received from MicroHySeeker.

    Returns:
        List of human-readable suggestion strings.
    """
    suggestions: list[str] = []
    anomaly_types: set[str | None] = {a.get("type") for a in anomalies}

    if "communication_timeout" in anomaly_types:
        suggestions.append(
            "Check network connectivity to MicroHySeeker and verify the service is running."
        )
        suggestions.append(
            "Restart MicroHySeeker if the communication timeout persists."
        )

    if "pump_fault" in anomaly_types:
        suggestions.append(
            "Inspect pump hardware and tubing for blockages or leaks."
        )
        suggestions.append(
            "Stop the experiment and run a pump self-test before continuing."
        )

    if "stall" in anomaly_types:
        suggestions.append(
            "Experiment appears stalled; check whether a step is waiting for a "
            "response or has hit an internal timeout."
        )
        suggestions.append(
            "Review recent logs for step-level errors or instrument deadlocks."
        )

    if "experiment_error" in anomaly_types or "api_error" in anomaly_types:
        suggestions.append(
            "An error was reported by the experiment engine; review the run log for details."
        )

    state: str = last_status.get("state", "")
    if state == "failed":
        suggestions.append(
            "Experiment ended in a failed state; run diagnostics before re-running."
        )

    if not suggestions:
        if anomalies:
            suggestions.append("Review anomaly details and consult system logs.")
        else:
            suggestions.append("No anomalies detected; experiment completed normally.")

    return suggestions
