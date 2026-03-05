"""Shared Pydantic types for AutoHySeeker."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


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


# ── Experiment plan types ─────────────────────────────────────────────────────

class ProgStep(BaseModel):
    """A single programmable step within an :class:`ExperimentPlan`."""

    step_index: int
    step_type: str  # "cv", "lsv", "eis", "prep_sol", "flush", "transfer", "blank", "evacuate"
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    expected_duration_s: Optional[float] = None


class ExperimentPlan(BaseModel):
    """Full experiment plan assembled for a single run."""

    name: str
    description: str = ""
    steps: list[ProgStep] = Field(default_factory=list)
    combo_params: Optional[dict[str, Any]] = None  # parameter combination for this run
    created_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)


# ── System / hardware status types ───────────────────────────────────────────

class SystemConfig(BaseModel):
    """Runtime system configuration read from system.json or equivalent."""

    device_id: str = ""
    pump_ports: list[str] = Field(default_factory=list)
    echem_port: str = ""
    data_dir: str = ""
    log_dir: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class EngineStatus(BaseModel):
    """Current state of the MicroHySeeker experiment engine."""

    state: Literal["idle", "running", "paused", "error", "unknown"] = "unknown"
    current_run_id: Optional[str] = None
    current_step_index: Optional[int] = None
    message: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


class RunStatus(BaseModel):
    """Live status snapshot of an ongoing experiment run."""

    run_id: str
    exp_name: str
    state: Literal["pending", "running", "paused", "completed", "failed", "aborted"]
    progress_pct: float = 0.0  # 0.0 – 100.0
    current_step: Optional[int] = None
    total_steps: int = 0
    elapsed_seconds: float = 0.0
    message: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


# ── Knowledge / literature types ─────────────────────────────────────────────

class KnowledgeChunk(BaseModel):
    """A retrieved chunk from the knowledge base."""

    chunk_id: str
    content: str
    source: str  # e.g. file path, DOI, or URL
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiteratureRef(BaseModel):
    """A parsed literature reference entry."""

    title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    abstract: str = ""
    keywords: list[str] = Field(default_factory=list)
    source_file: Optional[str] = None
