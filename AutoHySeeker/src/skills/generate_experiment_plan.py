"""B1 — GenerateExperimentPlanSkill: LLM-free plan builder from a goal description.

Translates a high-level experiment goal + optional parameter hints into a
validated :class:`~src.common.types.ExperimentPlan` using the
:mod:`src.tools.experiment_builder` helpers.
"""

from __future__ import annotations

from typing import Any

from src.common.types import ExperimentPlan
from src.skills.base import BaseSkill, SkillResult
from src.tools.experiment_builder import (
    build_experiment_plan,
    build_plans_from_grid,
    generate_param_grid,
    plan_to_dict,
    validate_plan,
)


# ── Goal → step-spec templates ────────────────────────────────────────────────

_GOAL_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "her": [
        {"step_type": "prep_sol", "description": "Prepare electrolyte solution"},
        {"step_type": "flush",    "description": "Flush flow cell"},
        {"step_type": "cv",       "description": "Activation CV cycles",
         "params": {"e_start": 0.0, "e_end": -0.5, "e_vertex1": -0.5,
                    "e_vertex2": 0.0, "scan_rate": 0.05, "n_cycles": 5}},
        {"step_type": "lsv",      "description": "HER polarisation curve",
         "params": {"e_start": 0.0, "e_end": -0.6, "scan_rate": 0.005,
                    "direction": "cathodic"}},
        {"step_type": "eis",      "description": "EIS at onset potential"},
        {"step_type": "flush",    "description": "Post-run flush"},
    ],
    "oer": [
        {"step_type": "prep_sol"},
        {"step_type": "flush"},
        {"step_type": "cv", "params": {"e_start": 1.0, "e_end": 1.8,
                                        "e_vertex1": 1.8, "e_vertex2": 1.0,
                                        "scan_rate": 0.05, "n_cycles": 5}},
        {"step_type": "lsv", "params": {"e_start": 1.0, "e_end": 1.8,
                                         "scan_rate": 0.005, "direction": "anodic"}},
        {"step_type": "eis"},
        {"step_type": "flush"},
    ],
    "cv_characterise": [
        {"step_type": "prep_sol"},
        {"step_type": "cv", "description": "Full CV characterisation"},
        {"step_type": "eis", "description": "Impedance characterisation"},
    ],
    "stability": [
        {"step_type": "prep_sol"},
        {"step_type": "cv", "description": "Baseline CV"},
        {"step_type": "ca", "description": "Chronoamperometry stability test",
         "params": {"e_step": -0.3, "duration_s": 3600.0}},
        {"step_type": "cv", "description": "Post-stability CV"},
    ],
    "generic": [
        {"step_type": "prep_sol"},
        {"step_type": "cv"},
        {"step_type": "lsv"},
        {"step_type": "eis"},
        {"step_type": "flush"},
    ],
}


def _resolve_goal(goal: str) -> str:
    """Map a free-text goal string to the nearest template key."""
    goal_lower = goal.lower()
    if any(kw in goal_lower for kw in ("her", "hydrogen", "reduction")):
        return "her"
    if any(kw in goal_lower for kw in ("oer", "oxygen", "oxidation")):
        return "oer"
    if any(kw in goal_lower for kw in ("stability", "chronoamper", "durability")):
        return "stability"
    if any(kw in goal_lower for kw in ("cv", "characteris", "cyclic")):
        return "cv_characterise"
    return "generic"


class GenerateExperimentPlanSkill(BaseSkill):
    """Generate a validated :class:`~src.common.types.ExperimentPlan` from a goal.

    This skill is **LLM-free**.  It maps the *goal* string to a built-in step
    template, optionally applies a parameter grid to produce multiple plans,
    validates each plan, and returns the result(s) as serialised dicts.

    Typical usage::

        skill = GenerateExperimentPlanSkill()
        result = await skill.execute(
            goal="HER activity screening",
            name="her_scan",
            param_ranges={"scan_rate": [0.005, 0.01, 0.02]},
        )
        # result.data → list of plan dicts (one per scan-rate value)
    """

    name = "generate_experiment_plan"
    description = "根据实验目标和参数范围生成并验证实验方案"
    required_tools = [
        "build_experiment_plan",
        "generate_param_grid",
        "build_plans_from_grid",
        "validate_plan",
    ]

    async def execute(  # noqa: PLR0912
        self,
        goal: str = "",
        name: str = "",
        step_specs: list[dict[str, Any]] | None = None,
        param_ranges: dict[str, list[Any]] | None = None,
        target_step_index: int = 0,
        description: str = "",
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> SkillResult:
        """Generate one or more experiment plans.

        Args:
            goal: Free-text experiment goal (e.g. ``"HER activity screening"``).
                  Used to select a built-in step template when *step_specs* is
                  not provided.
            name: Base name for the generated plan(s).  Defaults to the
                  resolved template key.
            step_specs: Explicit list of step-spec dicts.  If provided,
                        overrides the template selected by *goal*.
            param_ranges: Optional dict mapping parameter names to candidate
                          value lists.  If given, one plan is generated per
                          combination (grid search).
            target_step_index: Index of the step that receives grid params
                               (default 0).
            description: Human-readable description for the plan(s).
            tags: Optional list of tag strings applied to all plans.
            **kwargs: Ignored.

        Returns:
            :class:`~src.skills.base.SkillResult` where ``data`` is a list of
            validated plan dicts (serialised via
            :func:`~src.tools.experiment_builder.plan_to_dict`).
        """
        if not goal and not step_specs:
            return SkillResult(
                success=False,
                data=[],
                message="Either 'goal' or 'step_specs' must be provided",
                artifacts=[],
            )

        # ── Resolve step specs ────────────────────────────────────────────────
        if step_specs is None:
            template_key = _resolve_goal(goal)
            step_specs = list(_GOAL_TEMPLATES[template_key])
        else:
            template_key = "custom"

        plan_name = name or template_key

        # ── Build plan(s) ─────────────────────────────────────────────────────
        plans: list[ExperimentPlan] = []
        if param_ranges:
            try:
                plans = build_plans_from_grid(
                    base_name=plan_name,
                    step_specs=step_specs,
                    param_ranges=param_ranges,
                    target_step_index=target_step_index,
                    description=description or f"{plan_name} grid search",
                    tags=tags,
                )
            except Exception as exc:
                return SkillResult(
                    success=False,
                    data=[],
                    message=f"Failed to build plans from grid: {exc}",
                    artifacts=[],
                )
        else:
            try:
                single_plan = build_experiment_plan(
                    name=plan_name,
                    step_specs=step_specs,
                    description=description,
                    tags=tags,
                )
                plans = [single_plan]
            except Exception as exc:
                return SkillResult(
                    success=False,
                    data=[],
                    message=f"Failed to build experiment plan: {exc}",
                    artifacts=[],
                )

        # ── Validate each plan ────────────────────────────────────────────────
        validated_plans: list[dict[str, Any]] = []
        all_valid = True
        validation_issues: list[str] = []

        for plan in plans:
            report = validate_plan(plan)
            plan_dict = plan_to_dict(plan)
            plan_dict["_validation"] = report
            if not report["valid"]:
                all_valid = False
                validation_issues.extend(report["errors"])
            validated_plans.append(plan_dict)

        n_plans = len(validated_plans)
        n_steps_each = len(plans[0].steps) if plans else 0

        msg_parts = [
            f"Generated {n_plans} plan(s) with {n_steps_each} step(s) each",
            f"template='{template_key}'",
        ]
        if not all_valid:
            msg_parts.append(
                f"— {len(validation_issues)} validation error(s): "
                + "; ".join(validation_issues[:3])
            )

        return SkillResult(
            success=all_valid,
            data=validated_plans,
            message=", ".join(msg_parts),
            artifacts=[],
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "goal": {
                    "type": "string",
                    "description": (
                        "Free-text goal, e.g. 'HER activity screening'. "
                        "Selects built-in template when step_specs not given."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Base plan name",
                },
                "step_specs": {
                    "type": "array",
                    "description": "Explicit step spec list (overrides goal template)",
                },
                "param_ranges": {
                    "type": "object",
                    "description": "Parameter grid: name → list of values",
                },
                "target_step_index": {
                    "type": "integer",
                    "description": "Step index receiving grid params (default 0)",
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
generate_experiment_plan_skill = GenerateExperimentPlanSkill()
