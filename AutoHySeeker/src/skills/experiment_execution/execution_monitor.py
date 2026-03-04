"""Execution monitor skill for post-experiment quality assessment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.types import DiagnosticResult
from src.skills.base import BaseSkill, SkillResult
from src.tools.log_analysis import (
    detect_pump_anomalies,
    parse_run_log,
    summarize_run,
)
from src.tools.report_generator import generate_run_report


class ExecutionMonitorSkill(BaseSkill):
    """Post-execution quality assessment and reporting."""

    name = "execution_monitor"
    description = "Analyze completed experiment runs for quality and generate reports"
    required_tools = ["summarize_run", "generate_run_report"]

    async def execute(self, run_dir: str = "", **kwargs: Any) -> SkillResult:
        """Analyze a completed experiment run.

        Args:
            run_dir: Path to experiment run directory
            **kwargs: Additional options

        Returns:
            SkillResult with quality assessment and report path
        """
        if not run_dir:
            return SkillResult(
                success=False,
                data={},
                message="run_dir parameter is required",
                artifacts=[],
            )

        run_path = Path(run_dir)
        if not run_path.exists():
            return SkillResult(
                success=False,
                data={},
                message=f"Run directory not found: {run_dir}",
                artifacts=[],
            )

        # Step 1: Parse run summary
        try:
            summary = summarize_run(run_dir)
        except Exception as exc:
            return SkillResult(
                success=False,
                data={},
                message=f"Failed to parse run summary: {exc}",
                artifacts=[],
            )

        # Step 2: Analyze step success rate
        total_steps = len(summary.step_results)
        successful_steps = sum(1 for s in summary.step_results if s.success)
        success_rate = successful_steps / total_steps if total_steps > 0 else 0.0

        # Step 3: Check data quality
        diagnostics: list[DiagnosticResult] = []

        # Check for pump anomalies
        log_file = run_path / "run_log.log"
        if log_file.exists():
            entries = parse_run_log(str(log_file))
            pump_diagnostics = detect_pump_anomalies(entries)
            diagnostics.extend(pump_diagnostics)

        # Check success rate
        if success_rate < 0.5:
            diagnostics.append(
                DiagnosticResult(
                    severity="critical",
                    category="quality",
                    message=f"Low step success rate: {success_rate:.1%}",
                    suggestion="Review failed steps and check hardware connections",
                    evidence=[
                        f"Total steps: {total_steps}",
                        f"Successful: {successful_steps}",
                        f"Failed: {total_steps - successful_steps}",
                    ],
                )
            )
        elif success_rate < 0.8:
            diagnostics.append(
                DiagnosticResult(
                    severity="warning",
                    category="quality",
                    message=f"Moderate step success rate: {success_rate:.1%}",
                    suggestion="Some steps failed, review logs for details",
                    evidence=[f"Success rate: {success_rate:.1%}"],
                )
            )

        # Check for errors
        if summary.errors:
            diagnostics.append(
                DiagnosticResult(
                    severity="error",
                    category="errors",
                    message=f"Detected {len(summary.errors)} error(s)",
                    suggestion="Review error messages and troubleshoot issues",
                    evidence=summary.errors[:5],
                )
            )

        # Step 4: Generate quality report
        report_path = run_path / "quality_report.md"
        try:
            generate_run_report(run_dir, str(report_path))
        except Exception as exc:
            return SkillResult(
                success=False,
                data={},
                message=f"Failed to generate report: {exc}",
                artifacts=[],
            )

        quality_assessment = {
            "run_id": summary.run_id,
            "success": summary.success,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "success_rate": success_rate,
            "error_count": len(summary.errors),
            "warning_count": len(summary.warnings),
            "diagnostics": [d.model_dump() for d in diagnostics],
            "report_path": str(report_path),
        }

        return SkillResult(
            success=True,
            data=quality_assessment,
            message=f"Quality assessment complete: {success_rate:.1%} success rate",
            artifacts=[str(report_path)],
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
                    "description": "Path to experiment run directory",
                }
            },
            "required": ["run_dir"],
        }
