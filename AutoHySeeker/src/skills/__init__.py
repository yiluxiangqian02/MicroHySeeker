"""Built-in skills for AutoHySeeker."""

from src.skills.analyze_cv import analyze_cv_skill
from src.skills.diagnose_exp import diagnose_experiment_skill
from src.skills.diagnostics import (
    DiagnoseFailureSkill,
    InteractiveTroubleshootingSkill,
    SystemHealthCheckSkill,
    diagnose_failure_skill,
    interactive_troubleshooting_skill,
    system_health_check_skill,
)
from src.skills.single_experiment_analysis import (
    SingleExperimentAnalysisSkill,
    single_experiment_analysis_skill,
)
from src.skills.generate_experiment_plan import (
    GenerateExperimentPlanSkill,
    generate_experiment_plan_skill,
)

__all__ = [
    # Legacy function-based skills
    "analyze_cv_skill",
    "diagnose_experiment_skill",
    # D1 — rule-based failure diagnosis
    "DiagnoseFailureSkill",
    "diagnose_failure_skill",
    # D2 — system health check
    "SystemHealthCheckSkill",
    "system_health_check_skill",
    # D3 — interactive troubleshooting
    "InteractiveTroubleshootingSkill",
    "interactive_troubleshooting_skill",
    # A1 — single experiment analysis
    "SingleExperimentAnalysisSkill",
    "single_experiment_analysis_skill",
    # B1 — generate experiment plan
    "GenerateExperimentPlanSkill",
    "generate_experiment_plan_skill",
]

