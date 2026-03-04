"""Shared Pydantic types for AutoHySeeker."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    source: str
    message: str
    raw: str


class StepResult(BaseModel):
    step_index: int
    step_id: str
    step_type: str
    success: bool
    details: str
    data_file: Optional[str] = None
    duration_s: Optional[float] = None


class RunSummary(BaseModel):
    run_id: str
    exp_name: str
    success: bool
    elapsed_seconds: float
    step_results: list[StepResult]
    errors: list[str]
    warnings: list[str]
    started_at: datetime
    finished_at: Optional[datetime] = None


class EchemData(BaseModel):
    technique: str
    data: Any  # pandas DataFrame
    file_path: str
    points: int
    metadata: dict


class DiagnosticResult(BaseModel):
    severity: Literal["info", "warning", "error", "critical"]
    category: str
    message: str
    suggestion: str
    evidence: list[str]


class HealthStatus(BaseModel):
    component: str
    status: Literal["ok", "warning", "error", "unknown"]
    message: str
    last_checked: datetime
