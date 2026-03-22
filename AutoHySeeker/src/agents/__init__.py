"""Lazy agent exports for AutoHySeeker."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "ChatAgent": "src.agents.chat_agent",
    "DiagnosticsExpertAgent": "src.agents.diagnostics",
    "ExperimentDesignerAgent": "src.agents.exp_designer",
    "ExperimentExecutorAgent": "src.agents.exp_executor",
    "OrchestratorAgent": "src.agents.orchestrator",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(name)
    module = import_module(module_name)
    return getattr(module, name)
