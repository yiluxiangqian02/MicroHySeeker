"""Lazy exports for experiment execution skills."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "ExecutionMonitorSkill": "src.skills.experiment_execution.execution_monitor",
    "RealtimeMonitorSkill": "src.skills.experiment_execution.realtime_monitor",
    "SmartSchedulerSkill": "src.skills.experiment_execution.smart_scheduler",
}

_SINGLETON_FACTORIES = {
    "execution_monitor_skill": ("src.skills.experiment_execution.execution_monitor", "ExecutionMonitorSkill"),
    "realtime_monitor_skill": ("src.skills.experiment_execution.realtime_monitor", "RealtimeMonitorSkill"),
    "smart_scheduler_skill": ("src.skills.experiment_execution.smart_scheduler", "SmartSchedulerSkill"),
}

__all__ = list(_EXPORTS) + list(_SINGLETON_FACTORIES)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is not None:
        module = import_module(module_name)
        return getattr(module, name)

    factory = _SINGLETON_FACTORIES.get(name)
    if factory is None:
        raise AttributeError(name)

    module = import_module(factory[0])
    cls = getattr(module, factory[1])
    instance = cls()
    globals()[name] = instance
    return instance
