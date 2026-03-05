"""Diagnostics skills for AutoHySeeker — D1/D2/D3.

D1 — :class:`DiagnoseFailureSkill`
    Rule-based failure analysis for experiment runs.

D2 — :class:`SystemHealthCheckSkill`
    System-wide health assessment (success rate, log errors, calibration).

D3 — :class:`InteractiveTroubleshootingSkill`
    Decision-tree guided troubleshooting for common hardware/software issues.
"""

from src.skills.diagnostics.diagnose_failure import DiagnoseFailureSkill
from src.skills.diagnostics.interactive_troubleshooting import InteractiveTroubleshootingSkill
from src.skills.diagnostics.system_health_check import SystemHealthCheckSkill

# Convenience singleton instances
diagnose_failure_skill = DiagnoseFailureSkill()
system_health_check_skill = SystemHealthCheckSkill()
interactive_troubleshooting_skill = InteractiveTroubleshootingSkill()

__all__ = [
    "DiagnoseFailureSkill",
    "SystemHealthCheckSkill",
    "InteractiveTroubleshootingSkill",
    "diagnose_failure_skill",
    "system_health_check_skill",
    "interactive_troubleshooting_skill",
]

