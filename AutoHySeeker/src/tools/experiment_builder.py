"""Experiment plan builder tools for AutoHySeeker.

Provides helpers to construct :class:`~src.common.types.ExperimentPlan` objects
from templates and parameter grids, validate plans, and serialise them for
the experiment engine.
"""

from __future__ import annotations

import itertools
from datetime import datetime
from typing import Any

from src.common.types import ExperimentPlan, ProgStep


# ── Step templates ─────────────────────────────────────────────────────────────

# Default parameter sets for each step type.  These serve as fallback values
# when the caller does not supply all parameters.
_STEP_DEFAULTS: dict[str, dict[str, Any]] = {
    "cv": {
        "e_start": 0.0,
        "e_end": 1.0,
        "e_vertex1": 1.0,
        "e_vertex2": 0.0,
        "scan_rate": 0.05,       # V/s
        "n_cycles": 3,
        "sample_interval": 0.001,
    },
    "lsv": {
        "e_start": 0.0,
        "e_end": -0.5,
        "scan_rate": 0.005,
        "sample_interval": 0.001,
    },
    "eis": {
        "e_dc": 0.0,
        "freq_high": 100000.0,
        "freq_low": 0.1,
        "amplitude": 0.01,
        "points_per_decade": 10,
    },
    "ca": {
        "e_step": -0.3,
        "duration_s": 60.0,
        "sample_interval": 0.1,
    },
    "prep_sol": {
        "volume_ul": 200,
        "flush_before": True,
    },
    "flush": {
        "volume_ul": 500,
        "n_cycles": 2,
    },
    "transfer": {
        "volume_ul": 100,
    },
    "blank": {
        "wait_s": 10,
    },
    "evacuate": {
        "duration_s": 30,
    },
}

KNOWN_STEP_TYPES = set(_STEP_DEFAULTS.keys())


# ── single-step builder ────────────────────────────────────────────────────────

def build_step(
    step_index: int,
    step_type: str,
    params: dict[str, Any] | None = None,
    description: str = "",
    expected_duration_s: float | None = None,
) -> ProgStep:
    """Build a single :class:`~src.common.types.ProgStep`.

    Merges caller-supplied *params* over the built-in defaults for
    *step_type*.  Unknown step types are accepted without defaults.

    Args:
        step_index: Zero-based position of this step in the plan.
        step_type: One of the recognised step types (e.g. ``"cv"``, ``"eis"``).
        params: Override or extend the default parameters.
        description: Human-readable step description.
        expected_duration_s: Estimated duration in seconds.

    Returns:
        A fully populated :class:`~src.common.types.ProgStep`.
    """
    merged: dict[str, Any] = dict(_STEP_DEFAULTS.get(step_type, {}))
    if params:
        merged.update(params)
    return ProgStep(
        step_index=step_index,
        step_type=step_type,
        params=merged,
        description=description or f"{step_type} step {step_index}",
        expected_duration_s=expected_duration_s,
    )


# ── plan builder ───────────────────────────────────────────────────────────────

def build_experiment_plan(
    name: str,
    step_specs: list[dict[str, Any]],
    description: str = "",
    combo_params: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> ExperimentPlan:
    """Build an :class:`~src.common.types.ExperimentPlan` from a list of step specs.

    Each element of *step_specs* must be a dict with at minimum a
    ``"step_type"`` key.  Optional keys:

    * ``"params"`` — dict of parameter overrides
    * ``"description"`` — step description string
    * ``"expected_duration_s"`` — float seconds

    Args:
        name: Plan name (used as experiment identifier).
        step_specs: Ordered list of step specification dicts.
        description: Human-readable plan description.
        combo_params: Optional parameter combination dict (e.g. from a grid search).
        tags: Optional list of tag strings.

    Returns:
        :class:`~src.common.types.ExperimentPlan` instance.

    Raises:
        ValueError: If *step_specs* is empty or any spec lacks ``"step_type"``.
    """
    if not step_specs:
        raise ValueError("step_specs must not be empty")

    steps: list[ProgStep] = []
    for i, spec in enumerate(step_specs):
        if "step_type" not in spec:
            raise ValueError(f"step_specs[{i}] is missing required key 'step_type'")
        steps.append(
            build_step(
                step_index=i,
                step_type=spec["step_type"],
                params=spec.get("params"),
                description=spec.get("description", ""),
                expected_duration_s=spec.get("expected_duration_s"),
            )
        )

    return ExperimentPlan(
        name=name,
        description=description,
        steps=steps,
        combo_params=combo_params,
        tags=tags or [],
        created_at=datetime.now(),
    )


# ── parameter grid ─────────────────────────────────────────────────────────────

def generate_param_grid(
    param_ranges: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    """Generate all combinations from a parameter grid.

    Args:
        param_ranges: Mapping of parameter name → list of candidate values.

    Returns:
        List of dicts, each representing one parameter combination.

    Raises:
        ValueError: If *param_ranges* is empty.

    Example::

        grid = generate_param_grid({"scan_rate": [0.01, 0.05], "n_cycles": [3, 5]})
        # → [{"scan_rate": 0.01, "n_cycles": 3}, {"scan_rate": 0.01, "n_cycles": 5},
        #    {"scan_rate": 0.05, "n_cycles": 3}, {"scan_rate": 0.05, "n_cycles": 5}]
    """
    if not param_ranges:
        raise ValueError("param_ranges must not be empty")

    keys = list(param_ranges.keys())
    values = [param_ranges[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


# ── plan factory for grids ─────────────────────────────────────────────────────

def build_plans_from_grid(
    base_name: str,
    step_specs: list[dict[str, Any]],
    param_ranges: dict[str, list[Any]],
    target_step_index: int = 0,
    description: str = "",
    tags: list[str] | None = None,
) -> list[ExperimentPlan]:
    """Build multiple :class:`~src.common.types.ExperimentPlan` objects from a param grid.

    For each parameter combination, the params are merged into the step at
    *target_step_index*, and ``combo_params`` is set on the plan.

    Args:
        base_name: Base plan name; each plan is suffixed with ``_N``.
        step_specs: Step spec list (same structure as :func:`build_experiment_plan`).
        param_ranges: Parameter grid (see :func:`generate_param_grid`).
        target_step_index: Index of the step that receives the combo params.
        description: Plan description template.
        tags: Optional tags applied to all plans.

    Returns:
        List of :class:`~src.common.types.ExperimentPlan` objects.
    """
    combos = generate_param_grid(param_ranges)
    plans: list[ExperimentPlan] = []
    for i, combo in enumerate(combos):
        specs_copy = []
        for j, spec in enumerate(step_specs):
            s = dict(spec)
            if j == target_step_index:
                merged_params = dict(spec.get("params") or {})
                merged_params.update(combo)
                s["params"] = merged_params
            specs_copy.append(s)
        plan = build_experiment_plan(
            name=f"{base_name}_{i + 1}",
            step_specs=specs_copy,
            description=description or f"{base_name} combo {i + 1}/{len(combos)}",
            combo_params=combo,
            tags=list(tags or []),
        )
        plans.append(plan)
    return plans


# ── plan validation ────────────────────────────────────────────────────────────

def validate_plan(plan: ExperimentPlan) -> dict[str, Any]:
    """Validate an experiment plan and return a validation report.

    Checks performed:

    * Plan has at least one step.
    * All step types are known.
    * Required parameters exist for each step type.
    * Step indices are consecutive starting from 0.

    Args:
        plan: The :class:`~src.common.types.ExperimentPlan` to validate.

    Returns:
        Dict with keys:

        * ``valid`` — ``True`` if no errors were found
        * ``errors`` — list of error strings
        * ``warnings`` — list of warning strings
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not plan.steps:
        errors.append("Plan has no steps")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Check step index continuity
    for expected, step in enumerate(plan.steps):
        if step.step_index != expected:
            errors.append(
                f"Step at position {expected} has step_index={step.step_index} "
                f"(expected {expected})"
            )

    # Check step types and required params
    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "cv": ["e_start", "e_end", "scan_rate"],
        "lsv": ["e_start", "e_end", "scan_rate"],
        "eis": ["e_dc", "freq_high", "freq_low"],
        "ca": ["e_step", "duration_s"],
    }
    for step in plan.steps:
        if step.step_type not in KNOWN_STEP_TYPES:
            warnings.append(
                f"Step {step.step_index}: unknown step_type '{step.step_type}'"
            )
        required = _REQUIRED_PARAMS.get(step.step_type, [])
        for rp in required:
            if rp not in step.params:
                errors.append(
                    f"Step {step.step_index} ({step.step_type}): "
                    f"missing required parameter '{rp}'"
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ── serialisation ──────────────────────────────────────────────────────────────

def plan_to_dict(plan: ExperimentPlan) -> dict[str, Any]:
    """Serialise an :class:`~src.common.types.ExperimentPlan` to a plain dict.

    The result is JSON-serialisable (timestamps converted to ISO strings).
    """
    d = plan.model_dump()
    # Convert datetime objects to ISO strings for JSON serialisability
    d["created_at"] = plan.created_at.isoformat()
    for step in d.get("steps", []):
        pass  # ProgStep has no datetime fields
    return d


# ── register with global registry on import ──────────────────────────────────

def _register() -> None:
    try:
        from src.common.tool_registry import registry

        registry.register(
            "build_experiment_plan",
            build_experiment_plan,
            "Build an ExperimentPlan from a list of step specs",
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plan name"},
                    "step_specs": {
                        "type": "array",
                        "description": "List of step spec dicts with step_type and optional params",
                    },
                    "description": {"type": "string"},
                    "combo_params": {"type": "object"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "step_specs"],
            },
        )
        registry.register(
            "generate_param_grid",
            generate_param_grid,
            "Generate all parameter combinations from a dict of param→value_list",
            {
                "type": "object",
                "properties": {
                    "param_ranges": {
                        "type": "object",
                        "description": "Mapping of parameter name to list of candidate values",
                    }
                },
                "required": ["param_ranges"],
            },
        )
        registry.register(
            "build_plans_from_grid",
            build_plans_from_grid,
            "Build multiple ExperimentPlans from a parameter grid",
            {
                "type": "object",
                "properties": {
                    "base_name": {"type": "string"},
                    "step_specs": {"type": "array"},
                    "param_ranges": {"type": "object"},
                    "target_step_index": {"type": "integer"},
                },
                "required": ["base_name", "step_specs", "param_ranges"],
            },
        )
        registry.register(
            "validate_plan",
            validate_plan,
            "Validate an ExperimentPlan and return a dict with valid/errors/warnings",
            {
                "type": "object",
                "properties": {
                    "plan": {"description": "ExperimentPlan object to validate"},
                },
                "required": ["plan"],
            },
        )
    except Exception:
        pass


_register()
