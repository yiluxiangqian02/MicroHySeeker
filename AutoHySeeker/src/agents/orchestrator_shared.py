"""Shared OrchestratorAgent accessor."""

from __future__ import annotations

from src.agents.orchestrator import OrchestratorAgent

_SHARED_ORCHESTRATOR: OrchestratorAgent | None = None


def get_shared_orchestrator_agent() -> OrchestratorAgent:
    """Return the shared orchestrator instance used by routes and loops."""
    global _SHARED_ORCHESTRATOR
    if _SHARED_ORCHESTRATOR is None:
        _SHARED_ORCHESTRATOR = OrchestratorAgent()
    return _SHARED_ORCHESTRATOR
