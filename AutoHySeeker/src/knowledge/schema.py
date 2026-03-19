"""Knowledge partition data models.

Defines canonical schema for the five partition namespaces:

- literature
- experiments
- operations
- analysis
- projects
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class KnowledgePartition(str, Enum):
    """Logical OpenViking partitions used by AutoHySeeker."""

    LITERATURE = "literature"
    EXPERIMENTS = "experiments"
    OPERATIONS = "operations"
    ANALYSIS = "analysis"
    PROJECTS = "projects"


PARTITION_URIS: dict[KnowledgePartition, str] = {
    KnowledgePartition.LITERATURE: "viking://resources/literature/",
    KnowledgePartition.EXPERIMENTS: "viking://resources/experiments/",
    KnowledgePartition.OPERATIONS: "viking://resources/operations/",
    KnowledgePartition.ANALYSIS: "viking://resources/analysis/",
    KnowledgePartition.PROJECTS: "viking://resources/projects/",
}


class KnowledgeRecordBase(BaseModel):
    """Base metadata shared by all knowledge records."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class LiteratureRecord(KnowledgeRecordBase):
    partition: Literal[KnowledgePartition.LITERATURE] = KnowledgePartition.LITERATURE
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    abstract: str = ""
    content: str = ""
    source: str = ""
    keywords: list[str] = Field(default_factory=list)


class ExperimentRecord(KnowledgeRecordBase):
    partition: Literal[KnowledgePartition.EXPERIMENTS] = KnowledgePartition.EXPERIMENTS
    run_id: str
    project_id: str = "default"
    round_num: int | None = None
    params: dict[str, float] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    data_quality: dict[str, Any] = Field(default_factory=dict)
    interpretation: str = ""
    status: str = "completed"
    data_path: str | None = None


class OperationRecord(KnowledgeRecordBase):
    partition: Literal[KnowledgePartition.OPERATIONS] = KnowledgePartition.OPERATIONS
    event_type: str
    severity: Literal["info", "warning", "error", "critical"] = "info"
    message: str
    component: str = "system"
    run_id: str | None = None
    action_taken: str = ""
    resolved: bool = False


class AnalysisRecord(KnowledgeRecordBase):
    partition: Literal[KnowledgePartition.ANALYSIS] = KnowledgePartition.ANALYSIS
    run_id: str
    target_metric: str
    direction: Literal["minimize", "maximize"] = "minimize"
    metric_value: float | None = None
    score: float | None = None
    quality_passed: bool | None = None
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)


class ProjectRecord(KnowledgeRecordBase):
    partition: Literal[KnowledgePartition.PROJECTS] = KnowledgePartition.PROJECTS
    project_id: str
    name: str
    goal: str
    target_metric: str = "overpotential_mV"
    direction: Literal["minimize", "maximize"] = "minimize"
    elements: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


KnowledgeRecord = (
    LiteratureRecord
    | ExperimentRecord
    | OperationRecord
    | AnalysisRecord
    | ProjectRecord
)
