"""Experiment execution skills package — A1/A2/A3.

A1 — :class:`ExecutionMonitorSkill`
    Post-execution quality assessment and reporting.

A2 — :class:`SmartSchedulerSkill`
    Multi-experiment scheduling with dependency resolution.

A3 — :class:`RealtimeMonitorSkill`
    Real-time polling of MicroHySeeker status with anomaly detection.
"""

from src.skills.experiment_execution.execution_monitor import ExecutionMonitorSkill
from src.skills.experiment_execution.realtime_monitor import RealtimeMonitorSkill
from src.skills.experiment_execution.smart_scheduler import SmartSchedulerSkill

# Convenience singleton instances
execution_monitor_skill = ExecutionMonitorSkill()
smart_scheduler_skill = SmartSchedulerSkill()
realtime_monitor_skill = RealtimeMonitorSkill()

__all__ = [
    "ExecutionMonitorSkill",
    "SmartSchedulerSkill",
    "RealtimeMonitorSkill",
    "execution_monitor_skill",
    "smart_scheduler_skill",
    "realtime_monitor_skill",
]
