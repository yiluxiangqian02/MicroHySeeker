"""D1 — DiagnoseFailureSkill: rule-based failure analysis for experiment runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.types import DiagnosticResult
from src.skills.base import BaseSkill, SkillResult
from src.tools.log_analysis import (
    classify_errors,
    detect_pump_anomalies,
    parse_run_log,
    summarize_run,
)


class DiagnoseFailureSkill(BaseSkill):
    """Analyze a failed experiment run and produce a list of DiagnosticResult objects.

    This skill is purely rule-based and does not call any LLM.
    """

    name = "diagnose_failure"
    description = "分析失败实验的原因并给出建议"
    required_tools = ["parse_run_log", "classify_errors", "detect_pump_anomalies", "summarize_run"]

    async def execute(self, run_dir: str = "", **kwargs: Any) -> SkillResult:
        """Diagnose a failed experiment run.

        Args:
            run_dir: Path to the experiment run directory (must contain
                     run_summary.json and run_log.log).
            **kwargs: Ignored additional arguments.

        Returns:
            SkillResult whose ``data`` field is a list of
            :class:`~src.common.types.DiagnosticResult` dicts.
        """
        if not run_dir:
            return SkillResult(
                success=False,
                data=[],
                message="run_dir parameter is required",
                artifacts=[],
            )

        run_path = Path(run_dir)
        if not run_path.exists():
            return SkillResult(
                success=False,
                data=[],
                message=f"Run directory not found: {run_dir}",
                artifacts=[],
            )

        # ── Step 1: read run_summary.json to confirm this run failed ──────────
        summary_file = run_path / "run_summary.json"
        if summary_file.exists():
            with summary_file.open("r", encoding="utf-8") as fp:
                raw_summary: dict[str, Any] = json.load(fp)
            run_succeeded: bool = raw_summary.get("success", True)
        else:
            raw_summary = {}
            run_succeeded = False  # no summary → treat as failed

        diagnostics: list[DiagnosticResult] = []

        if run_succeeded:
            # Run did not fail — return informational result
            return SkillResult(
                success=True,
                data=[],
                message="Run succeeded — no failure diagnostics needed",
                artifacts=[],
            )

        # ── Step 2: parse run_log.log ─────────────────────────────────────────
        log_file = run_path / "run_log.log"
        if not log_file.exists():
            diagnostics.append(
                DiagnosticResult(
                    severity="warning",
                    category="log",
                    message="run_log.log not found — cannot perform log analysis",
                    suggestion="Ensure the experiment runner writes a run_log.log file.",
                    evidence=[],
                )
            )
            entries = []
        else:
            try:
                entries = parse_run_log(str(log_file))
            except Exception as exc:
                return SkillResult(
                    success=False,
                    data=[],
                    message=f"Failed to parse run log: {exc}",
                    artifacts=[],
                )

        # ── Step 3: classify errors by source ────────────────────────────────
        if entries:
            error_groups = classify_errors(entries)
            if error_groups:
                for source, errs in error_groups.items():
                    diagnostics.append(
                        DiagnosticResult(
                            severity="error",
                            category="log_errors",
                            message=f"{len(errs)} ERROR(s) from source '{source}'",
                            suggestion=(
                                f"Investigate logs from [{source}] — "
                                "check hardware connectivity and software configuration."
                            ),
                            evidence=[e.raw for e in errs[:5]],
                        )
                    )

        # ── Step 4: detect pump anomalies ─────────────────────────────────────
        if entries:
            pump_diags = detect_pump_anomalies(entries)
            diagnostics.extend(pump_diags)

        # ── Step 5: correlate with step-level failures from run_summary ───────
        failed_steps = [
            s for s in raw_summary.get("steps", []) if not s.get("success", True)
        ]
        if failed_steps:
            evidence = [
                f"Step {s.get('id', '?')} ({s.get('type', '?')}): {s.get('details', '')}"
                for s in failed_steps[:5]
            ]
            diagnostics.append(
                DiagnosticResult(
                    severity="error",
                    category="step_failure",
                    message=f"{len(failed_steps)} step(s) reported failure in run_summary",
                    suggestion="Review each failed step's details and associated log entries.",
                    evidence=evidence,
                )
            )

        # ── Step 6: summarize via summarize_run for elapsed / overall view ─────
        try:
            run_summary = summarize_run(run_dir)
            elapsed = run_summary.elapsed_seconds
            total_errors = len(run_summary.errors)
        except Exception:
            elapsed = 0.0
            total_errors = len(raw_summary.get("errors", []))

        if not diagnostics:
            diagnostics.append(
                DiagnosticResult(
                    severity="info",
                    category="general",
                    message="Run marked as failed but no specific error signals detected",
                    suggestion="Manually inspect run_summary.json and run_log.log for clues.",
                    evidence=[],
                )
            )

        return SkillResult(
            success=True,
            data=[d.model_dump() for d in diagnostics],
            message=(
                f"Diagnosed {len(diagnostics)} issue(s) in {elapsed:.1f}s run "
                f"({total_errors} total ERROR log lines)"
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
                "run_dir": {
                    "type": "string",
                    "description": "Path to the experiment run directory",
                }
            },
            "required": ["run_dir"],
        }
