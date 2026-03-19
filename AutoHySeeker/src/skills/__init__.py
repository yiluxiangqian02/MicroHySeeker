"""Lazy exports for built-in skills."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "analyze_cv_skill": "src.skills.analyze_cv",
    "diagnose_experiment_skill": "src.skills.diagnose_exp",
    "DiagnoseFailureSkill": "src.skills.diagnostics",
    "InteractiveTroubleshootingSkill": "src.skills.diagnostics",
    "SystemHealthCheckSkill": "src.skills.diagnostics",
    "diagnose_failure_skill": "src.skills.diagnostics",
    "interactive_troubleshooting_skill": "src.skills.diagnostics",
    "system_health_check_skill": "src.skills.diagnostics",
    "SingleExperimentAnalysisSkill": "src.skills.single_experiment_analysis",
    "single_experiment_analysis_skill": "src.skills.single_experiment_analysis",
    "GenerateExperimentPlanSkill": "src.skills.generate_experiment_plan",
    "generate_experiment_plan_skill": "src.skills.generate_experiment_plan",
    "ContextualizeExperimentSkill": "src.skills.contextualize_experiment",
    "contextualize_experiment_skill": "src.skills.contextualize_experiment",
    "SuggestNextExperimentSkill": "src.skills.suggest_next_experiment",
    "suggest_next_experiment_skill": "src.skills.suggest_next_experiment",
    "ExecutionMonitorSkill": "src.skills.experiment_execution",
    "RealtimeMonitorSkill": "src.skills.experiment_execution",
    "SmartSchedulerSkill": "src.skills.experiment_execution",
    "execution_monitor_skill": "src.skills.experiment_execution",
    "realtime_monitor_skill": "src.skills.experiment_execution",
    "smart_scheduler_skill": "src.skills.experiment_execution",
    "DataAnalysisSkill": "src.skills.data_analysis_skill",
    "data_analysis_skill": "src.skills.data_analysis_skill",
    "KnowledgeArchiveSkill": "src.skills.knowledge_archive_skill",
    "knowledge_archive_skill": "src.skills.knowledge_archive_skill",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(name)
    module = import_module(module_name)
    return getattr(module, name)
