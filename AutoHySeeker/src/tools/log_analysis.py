"""Log analysis tools for AutoHySeeker run directories."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.types import DiagnosticResult, LogEntry, RunSummary, StepResult

# Log line pattern: [YYYY-MM-DD HH:MM:SS.mmm] [LEVEL] [SOURCE] message
_LOG_PATTERN = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]\s+"
    r"\[(\w+)\]\s+\[([^\]]+)\]\s+(.*)"
)

_PUMP_KEYWORDS = re.compile(
    r"pump|泵", re.IGNORECASE
)
_PUMP_ANOMALY_KEYWORDS = re.compile(
    r"timeout|timed.?out|fail|error|anomal|stop|超时|失败|异常|停止", re.IGNORECASE
)


def _read_log_file(log_path: str) -> str:
    path = Path(log_path)
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return path.read_text(errors="replace")


def parse_run_log(log_path: str) -> list[LogEntry]:
    """Parse run_log.log into LogEntry objects."""
    text = _read_log_file(log_path)
    entries: list[LogEntry] = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        m = _LOG_PATTERN.match(line)
        if m:
            ts_str, level, source, message = m.groups()
            # Normalize timestamp – pad or truncate microseconds
            try:
                timestamp = datetime.strptime(ts_str[:23], "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                try:
                    timestamp = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
            entries.append(
                LogEntry(
                    timestamp=timestamp,
                    level=level.upper(),
                    source=source.strip(),
                    message=message.strip(),
                    raw=line,
                )
            )
    return entries


def classify_errors(entries: list[LogEntry]) -> dict[str, list[LogEntry]]:
    """Group ERROR-level log entries by source."""
    result: dict[str, list[LogEntry]] = {}
    for entry in entries:
        if entry.level == "ERROR":
            result.setdefault(entry.source, []).append(entry)
    return result


def detect_pump_anomalies(entries: list[LogEntry]) -> list[DiagnosticResult]:
    """Detect pump-related anomalies (timeout, failure, abnormal stop)."""
    results: list[DiagnosticResult] = []
    pump_errors: list[str] = []
    for entry in entries:
        combined = f"{entry.source} {entry.message}"
        if _PUMP_KEYWORDS.search(combined) and _PUMP_ANOMALY_KEYWORDS.search(combined):
            pump_errors.append(entry.raw)

    if pump_errors:
        results.append(
            DiagnosticResult(
                severity="error",
                category="pump",
                message=f"Detected {len(pump_errors)} pump anomaly event(s)",
                suggestion="Check pump hardware connections and flow rate settings.",
                evidence=pump_errors[:10],
            )
        )
    return results


def extract_step_timeline(entries: list[LogEntry]) -> list[dict[str, Any]]:
    """Extract step start/end events and compute durations."""
    step_start_pattern = re.compile(
        r"[Ss]tep\s+(?:start[ed]*|begin[ning]*)\s*[:\-]?\s*(.*)|"
        r"[Ss]tarting\s+step\s+(.*)",
        re.IGNORECASE,
    )
    step_end_pattern = re.compile(
        r"[Ss]tep\s+(?:finish[ed]*|complet[ed]*|done|end[ed]*)\s*[:\-]?\s*(.*)|"
        r"[Ss]tep\s+(.*)\s+(?:finished|completed|done)",
        re.IGNORECASE,
    )

    timeline: list[dict[str, Any]] = []
    open_steps: dict[str, datetime] = {}

    for entry in entries:
        if step_start_pattern.search(entry.message):
            open_steps[entry.source] = entry.timestamp
            timeline.append(
                {
                    "event": "start",
                    "source": entry.source,
                    "timestamp": entry.timestamp.isoformat(),
                    "message": entry.message,
                    "duration_s": None,
                    "status": "running",
                }
            )
        elif step_end_pattern.search(entry.message):
            start_ts = open_steps.pop(entry.source, None)
            duration = (
                (entry.timestamp - start_ts).total_seconds() if start_ts else None
            )
            status = "failed" if entry.level in ("ERROR", "CRITICAL") else "done"
            timeline.append(
                {
                    "event": "end",
                    "source": entry.source,
                    "timestamp": entry.timestamp.isoformat(),
                    "message": entry.message,
                    "duration_s": duration,
                    "status": status,
                }
            )

    return timeline


def summarize_run(run_dir: str) -> RunSummary:
    """Build RunSummary from run_log.log + run_summary.json."""
    run_path = Path(run_dir)
    log_file = run_path / "run_log.log"
    summary_file = run_path / "run_summary.json"

    entries = parse_run_log(str(log_file)) if log_file.exists() else []

    raw_summary: dict[str, Any] = {}
    if summary_file.exists():
        with summary_file.open("r", encoding="utf-8") as fp:
            raw_summary = json.load(fp)

    errors = [e.message for e in entries if e.level == "ERROR"]
    warnings = [e.message for e in entries if e.level == "WARNING"]

    started_at: datetime
    finished_at: datetime | None = None

    if entries:
        started_at = entries[0].timestamp
        finished_at = entries[-1].timestamp
    else:
        started_at = datetime.now()

    elapsed = (
        (finished_at - started_at).total_seconds()
        if finished_at
        else 0.0
    )

    step_results: list[StepResult] = []
    for i, step in enumerate(raw_summary.get("steps", [])):
        step_results.append(
            StepResult(
                step_index=i,
                step_id=step.get("id", f"step_{i}"),
                step_type=step.get("type", "unknown"),
                success=step.get("success", True),
                details=step.get("details", ""),
                data_file=step.get("data_file"),
                duration_s=step.get("duration_s"),
            )
        )

    return RunSummary(
        run_id=raw_summary.get("run_id", run_path.name),
        exp_name=raw_summary.get("exp_name", run_path.name),
        success=raw_summary.get("success", len(errors) == 0),
        elapsed_seconds=raw_summary.get("elapsed_seconds", elapsed),
        step_results=step_results,
        errors=errors,
        warnings=warnings,
        started_at=started_at,
        finished_at=finished_at,
    )
