"""C2 — SuggestNextExperimentSkill: recommend the next experiment from context.

Uses the context produced by :class:`~src.skills.contextualize_experiment.
ContextualizeExperimentSkill` (C1) together with optional explicit constraints
to recommend a follow-up experiment plan.  The skill is **LLM-free**: it
applies rule-based heuristics to select the most informative next step.

Decision logic:

* If anomalous metrics were detected → schedule a targeted diagnostic run.
* If a metric is trending downward   → schedule a stability / recovery run.
* If all metrics look healthy         → advance toward the next optimisation goal.
* Falls back to a generic ``"generic"`` plan template.
"""

from __future__ import annotations

from typing import Any

from src.skills.base import BaseSkill, SkillResult
from src.tools.experiment_builder import (
    build_experiment_plan,
    plan_to_dict,
    validate_plan,
)


# ── Suggestion heuristics ─────────────────────────────────────────────────────

# Step specs keyed by intent
_INTENT_STEPS: dict[str, list[dict[str, Any]]] = {
    "diagnostic_run": [
        {"step_type": "prep_sol", "description": "Prepare fresh electrolyte"},
        {"step_type": "flush", "description": "Flush flow cell"},
        {"step_type": "cv", "description": "Diagnostic CV",
         "params": {"e_start": 0.0, "e_end": -0.6, "e_vertex1": -0.6,
                    "e_vertex2": 0.0, "scan_rate": 0.05, "n_cycles": 3}},
        {"step_type": "eis", "description": "Impedance diagnostic"},
        {"step_type": "flush"},
    ],
    "stability_run": [
        {"step_type": "prep_sol"},
        {"step_type": "cv", "description": "Baseline CV"},
        {"step_type": "ca", "description": "Stability chronoamperometry",
         "params": {"e_step": -0.3, "duration_s": 1800.0}},
        {"step_type": "cv", "description": "Post-stability CV"},
    ],
    "optimisation_run": [
        {"step_type": "prep_sol"},
        {"step_type": "cv", "description": "Scan-rate optimisation CV",
         "params": {"e_start": 0.0, "e_end": -0.6, "e_vertex1": -0.6,
                    "e_vertex2": 0.0, "scan_rate": 0.02, "n_cycles": 5}},
        {"step_type": "lsv", "description": "Performance LSV",
         "params": {"e_start": 0.0, "e_end": -0.6, "scan_rate": 0.005}},
        {"step_type": "eis", "description": "Post-optimisation EIS"},
        {"step_type": "flush"},
    ],
    "generic": [
        {"step_type": "prep_sol"},
        {"step_type": "cv"},
        {"step_type": "lsv"},
        {"step_type": "eis"},
        {"step_type": "flush"},
    ],
}


def _choose_intent(
    context_data: dict[str, Any],
    goal: str,
) -> tuple[str, str]:
    """Return (intent_key, rationale) based on context data and goal."""
    anomalies: list[str] = context_data.get("anomalies", [])
    trend: dict[str, str] = context_data.get("trend", {})
    declining = [k for k, v in trend.items() if v == "declining"]

    goal_lower = goal.lower()

    if anomalies:
        reason = (
            f"Anomalous metrics detected ({', '.join(anomalies[:3])}); "
            "scheduling a targeted diagnostic run."
        )
        return "diagnostic_run", reason

    if declining:
        reason = (
            f"Metrics showing decline ({', '.join(declining[:3])}); "
            "scheduling a stability check run."
        )
        return "stability_run", reason

    if any(kw in goal_lower for kw in ("optim", "scan", "sweep", "grid")):
        return "optimisation_run", "Goal requests optimisation; advancing to parameter sweep."

    if any(kw in goal_lower for kw in ("stable", "durabil", "chronic")):
        return "stability_run", "Goal requests stability testing."

    if any(kw in goal_lower for kw in ("diagnos", "debug", "check")):
        return "diagnostic_run", "Goal requests diagnostic check."

    return "generic", "No specific issues detected; proceeding with generic protocol."


class SuggestNextExperimentSkill(BaseSkill):
    """Suggest the next experiment based on contextualised current results.

    This skill is **LLM-free**.  It:

    1. Inspects the *context_data* produced by C1
       (:class:`~src.skills.contextualize_experiment.ContextualizeExperimentSkill`).
    2. Applies rule-based heuristics to select an intent
       (``"diagnostic_run"``, ``"stability_run"``, ``"optimisation_run"``,
       or ``"generic"``).
    3. Builds and validates an :class:`~src.common.types.ExperimentPlan` using
       the chosen step-spec template.
    4. Returns the plan dict + a human-readable ``rationale`` string.

    Typical usage::

        c1_result = await contextualize_experiment_skill.execute(
            run_dir="data/runs/run_042", history_dir="data/runs"
        )
        c2_result = await suggest_next_experiment_skill.execute(
            context_data=c1_result.data,
            goal="optimise HER activity",
            name="run_043",
        )
        plan_dict = c2_result.data["plan"]
        rationale  = c2_result.data["rationale"]
    """

    name = "suggest_next_experiment"
    description = "根据当前实验上下文，推荐下一步实验方案及理由"
    required_tools = ["build_experiment_plan", "validate_plan"]

    async def execute(
        self,
        context_data: dict[str, Any] | None = None,
        goal: str = "",
        name: str = "",
        description: str = "",
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> SkillResult:
        """Suggest the next experiment plan.

        Args:
            context_data: Output of C1 ``ContextualizeExperimentSkill.execute``
                          (the ``data`` field of its :class:`~src.skills.base.SkillResult`).
                          If ``None`` or empty, heuristics fall back to *goal* only.
            goal: Free-text description of the overarching experiment goal
                  (e.g. ``"optimise HER activity"``).
            name: Name for the suggested plan.  Defaults to the chosen intent key.
            description: Human-readable plan description.
            tags: Optional tag list applied to the generated plan.
            **kwargs: Ignored.

        Returns:
            :class:`~src.skills.base.SkillResult` where ``data`` is::

                {
                    "intent":    str,     # chosen intent key
                    "rationale": str,     # human-readable reasoning
                    "plan":      dict,    # serialised ExperimentPlan
                    "valid":     bool,    # whether plan passed validation
                }
        """
        ctx = context_data or {}

        # ── Choose intent & rationale ─────────────────────────────────────────
        intent, rationale = _choose_intent(ctx, goal)
        step_specs = list(_INTENT_STEPS[intent])
        plan_name = name or intent

        # ── Build plan ────────────────────────────────────────────────────────
        try:
            plan = build_experiment_plan(
                name=plan_name,
                step_specs=step_specs,
                description=description or f"Suggested next run ({intent}): {rationale}",
                tags=tags,
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                data={},
                message=f"Failed to build suggested plan: {exc}",
                artifacts=[],
            )

        # ── Validate plan ─────────────────────────────────────────────────────
        validation = validate_plan(plan)
        plan_dict = plan_to_dict(plan)
        plan_dict["_validation"] = validation

        result_data: dict[str, Any] = {
            "intent": intent,
            "rationale": rationale,
            "plan": plan_dict,
            "valid": validation["valid"],
        }

        return SkillResult(
            success=validation["valid"],
            data=result_data,
            message=(
                f"Suggested '{intent}' plan with {len(plan.steps)} step(s). "
                f"Rationale: {rationale}"
            ),
            artifacts=[],
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "context_data": {
                    "type": "object",
                    "description": (
                        "Output of ContextualizeExperimentSkill (comparison/trend/anomalies). "
                        "If omitted, only goal-based heuristics are applied."
                    ),
                },
                "goal": {
                    "type": "string",
                    "description": "Overarching experiment goal",
                },
                "name": {
                    "type": "string",
                    "description": "Name for the suggested plan",
                },
                "description": {"type": "string"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [],
        }


# Convenience singleton
suggest_next_experiment_skill = SuggestNextExperimentSkill()
