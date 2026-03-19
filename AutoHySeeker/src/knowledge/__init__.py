"""Knowledge layer primitives for AutoHySeeker.

This package provides:

1. ``OpenVikingClient`` — partition-aware wrapper around OpenViking SDK.
2. Partition data models used by knowledge skills and API routes.
"""

from src.knowledge.schema import (
    AnalysisRecord,
    ExperimentRecord,
    KnowledgePartition,
    LiteratureRecord,
    OperationRecord,
    ProjectRecord,
)
from src.knowledge.viking_client import OpenVikingClient

__all__ = [
    "OpenVikingClient",
    "KnowledgePartition",
    "LiteratureRecord",
    "ExperimentRecord",
    "OperationRecord",
    "AnalysisRecord",
    "ProjectRecord",
]
