"""Experiment execution skills package — A1/A2.

A1 — :class:`ExecutionMonitorSkill`
    Post-execution quality assessment and reporting.

A2 — :class:`SmartSchedulerSkill`
    Multi-experiment scheduling with dependency resolution.
"""

from src.skills.experiment_execution.execution_monitor import ExecutionMonitorSkill
from src.skills.experiment_execution.smart_scheduler import SmartSchedulerSkill

# Convenience singleton instances
execution_monitor_skill = ExecutionMonitorSkill()
smart_scheduler_skill = SmartSchedulerSkill()

__all__ = [
    "ExecutionMonitorSkill",
    "SmartSchedulerSkill",
    "execution_monitor_skill",
    "smart_scheduler_skill",
]
