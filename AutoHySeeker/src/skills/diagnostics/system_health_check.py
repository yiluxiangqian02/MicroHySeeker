"""D2 — SystemHealthCheckSkill: rule-based system health assessment."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.types import HealthStatus
from src.skills.base import BaseSkill, SkillResult


# Number of most-recent experiment runs to consider for success-rate check
_DEFAULT_RECENT_N = 10
# Threshold: error-log-line rate (errors / total lines) that triggers a warning
_ERROR_RATE_WARN = 0.05
_ERROR_RATE_CRIT = 0.15
# Pump calibration file name patterns
_PUMP_CAL_PATTERNS = ("pump_cal*.json", "calibration*.json", "pump*.json")


def _count_error_lines(log_path: Path) -> tuple[int, int]:
    """Return (error_count, total_count) for a log file."""
    error_count = 0
    total_count = 0
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    error_re = re.compile(r"\[ERROR\]|\[CRITICAL\]", re.IGNORECASE)
    for line in text.splitlines():
        if line.strip():
            total_count += 1
            if error_re.search(line):
                error_count += 1
    return error_count, total_count


def _find_recent_run_dirs(data_dir: Path, n: int) -> list[Path]:
    """Return up to *n* most-recently-modified subdirectories of *data_dir*."""
    try:
        subdirs = [p for p in data_dir.iterdir() if p.is_dir()]
    except OSError:
        return []
    subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return subdirs[:n]


class SystemHealthCheckSkill(BaseSkill):
    """Assess system health across four dimensions:

    1. Recent experiment success rate
    2. Data directory accessibility
    3. Log ERROR frequency
    4. Pump calibration data completeness
    """

    name = "system_health_check"
    description = "检查系统健康状态：成功率、目录可访问性、日志错误频率、泵校准完整性"
    required_tools: list[str] = []

    async def execute(self, data_dir: str = "", recent_n: int = _DEFAULT_RECENT_N, **kwargs: Any) -> SkillResult:
        """Run system health checks.

        Args:
            data_dir: Root directory that contains individual experiment run folders.
            recent_n: How many recent runs to include in the success-rate check.
            **kwargs: Ignored additional arguments.

        Returns:
            SkillResult whose ``data`` field is a list of
            :class:`~src.common.types.HealthStatus` dicts.
        """
        now = datetime.now()
        health: list[HealthStatus] = []

        # ── Check 1: data directory accessibility ─────────────────────────────
        data_path = Path(data_dir) if data_dir else None
        if data_path is None or not data_path.exists():
            health.append(
                HealthStatus(
                    component="data_directory",
                    status="error",
                    message=f"Data directory not accessible: '{data_dir}'",
                    last_checked=now,
                )
            )
            # Cannot continue meaningful checks without data dir
            return SkillResult(
                success=True,
                data=[h.model_dump() for h in health],
                message="Data directory is inaccessible — health check aborted",
                artifacts=[],
            )

        health.append(
            HealthStatus(
                component="data_directory",
                status="ok",
                message=f"Data directory accessible: {data_path}",
                last_checked=now,
            )
        )

        # ── Check 2: recent experiment success rate ───────────────────────────
        run_dirs = _find_recent_run_dirs(data_path, recent_n)
        total_runs = len(run_dirs)
        successful_runs = 0
        for rd in run_dirs:
            summary_file = rd / "run_summary.json"
            if summary_file.exists():
                try:
                    with summary_file.open("r", encoding="utf-8") as fp:
                        s: dict[str, Any] = json.load(fp)
                    if s.get("success", False):
                        successful_runs += 1
                except (json.JSONDecodeError, OSError):
                    pass  # count as failure

        if total_runs == 0:
            health.append(
                HealthStatus(
                    component="experiment_success_rate",
                    status="unknown",
                    message="No recent experiment runs found",
                    last_checked=now,
                )
            )
        else:
            rate = successful_runs / total_runs
            if rate >= 0.8:
                status: str = "ok"
            elif rate >= 0.5:
                status = "warning"
            else:
                status = "error"
            health.append(
                HealthStatus(
                    component="experiment_success_rate",
                    status=status,  # type: ignore[arg-type]
                    message=(
                        f"Recent {total_runs} run(s): "
                        f"{successful_runs} succeeded ({rate:.0%})"
                    ),
                    last_checked=now,
                )
            )

        # ── Check 3: ERROR frequency in most recent log files ─────────────────
        total_errors = 0
        total_lines = 0
        checked_logs = 0
        for rd in run_dirs[:5]:  # limit to most recent 5 for speed
            log_file = rd / "run_log.log"
            if log_file.exists():
                errs, lines = _count_error_lines(log_file)
                total_errors += errs
                total_lines += lines
                checked_logs += 1

        if checked_logs == 0:
            health.append(
                HealthStatus(
                    component="log_error_rate",
                    status="unknown",
                    message="No run_log.log files found in recent runs",
                    last_checked=now,
                )
            )
        else:
            error_rate = total_errors / total_lines if total_lines > 0 else 0.0
            if error_rate >= _ERROR_RATE_CRIT:
                log_status = "error"
            elif error_rate >= _ERROR_RATE_WARN:
                log_status = "warning"
            else:
                log_status = "ok"
            health.append(
                HealthStatus(
                    component="log_error_rate",
                    status=log_status,  # type: ignore[arg-type]
                    message=(
                        f"Checked {checked_logs} log(s): "
                        f"{total_errors}/{total_lines} lines are ERROR/CRITICAL "
                        f"({error_rate:.1%})"
                    ),
                    last_checked=now,
                )
            )

        # ── Check 4: pump calibration data completeness ───────────────────────
        cal_files: list[Path] = []
        for pattern in _PUMP_CAL_PATTERNS:
            cal_files.extend(data_path.glob(pattern))
            # Also check one level deep
            cal_files.extend(data_path.glob(f"*/{pattern}"))

        if cal_files:
            health.append(
                HealthStatus(
                    component="pump_calibration",
                    status="ok",
                    message=f"Found {len(cal_files)} pump calibration file(s)",
                    last_checked=now,
                )
            )
        else:
            health.append(
                HealthStatus(
                    component="pump_calibration",
                    status="warning",
                    message="No pump calibration files found under data directory",
                    last_checked=now,
                )
            )

        overall_statuses = {h.status for h in health}
        if "error" in overall_statuses:
            summary_msg = "System health check: ISSUES DETECTED"
        elif "warning" in overall_statuses:
            summary_msg = "System health check: warnings present"
        else:
            summary_msg = "System health check: all systems OK"

        return SkillResult(
            success=True,
            data=[h.model_dump() for h in health],
            message=summary_msg,
            artifacts=[],
        )

    def get_schema(self) -> dict:
        """Return JSON Schema for this skill's inputs."""
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "data_dir": {
                    "type": "string",
                    "description": "Root data directory containing experiment run folders",
                },
                "recent_n": {
                    "type": "integer",
                    "description": "Number of most-recent runs to include in success-rate check",
                    "default": _DEFAULT_RECENT_N,
                },
            },
            "required": ["data_dir"],
        }
