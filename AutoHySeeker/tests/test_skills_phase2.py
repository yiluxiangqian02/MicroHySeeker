"""Phase 2 tests — Skills A1 (SingleExperimentAnalysis) and B1 (GenerateExperimentPlan)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


def _write_csv(path: Path, technique: str = "cv") -> None:
    path.write_text(
        "Potential(V),Current(A)\n0.0,0.001\n0.25,0.002\n0.5,0.003\n"
        "0.75,0.002\n1.0,0.001\n0.75,-0.001\n0.5,-0.002\n0.25,-0.001\n"
    )


# ── A1 — SingleExperimentAnalysisSkill ────────────────────────────────────────

class TestSingleExperimentAnalysisSkill:
    def test_import(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        skill = SingleExperimentAnalysisSkill()
        assert skill.name == "single_experiment_analysis"

    def test_singleton_exported(self) -> None:
        from src.skills import single_experiment_analysis_skill
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        assert isinstance(single_experiment_analysis_skill, SingleExperimentAnalysisSkill)

    def test_missing_run_dir(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute())
        assert result.success is False
        assert "run_dir" in result.message

    def test_nonexistent_dir(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir="/no/such/directory"))
        assert result.success is False

    def test_empty_dir(self, tmp_path: Path) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert result.data == []
        assert "No electrochemical" in result.message

    def test_analyse_cv_files(self, tmp_path: Path) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        _write_csv(tmp_path / "cv_001.csv", "cv")
        _write_csv(tmp_path / "cv_002.csv", "cv")

        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert len(result.data) == 2
        for item in result.data:
            assert item["technique"] == "cv"
            assert "potential_range" in item

    def test_artifacts_contain_file_paths(self, tmp_path: Path) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        _write_csv(tmp_path / "cv_test.csv")
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert len(result.artifacts) == 1
        assert "cv_test" in result.artifacts[0]

    def test_validate_inputs_schema(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        skill = SingleExperimentAnalysisSkill()
        assert skill.validate_inputs(run_dir="/some/path")
        assert not skill.validate_inputs()  # missing run_dir

    def test_get_schema(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        skill = SingleExperimentAnalysisSkill()
        schema = skill.get_schema()
        assert schema["type"] == "object"
        assert "run_dir" in schema["properties"]
        assert "run_dir" in schema["required"]


# ── B1 — GenerateExperimentPlanSkill ─────────────────────────────────────────

class TestGenerateExperimentPlanSkill:
    def test_import(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill
        skill = GenerateExperimentPlanSkill()
        assert skill.name == "generate_experiment_plan"

    def test_singleton_exported(self) -> None:
        from src.skills import generate_experiment_plan_skill
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill
        assert isinstance(generate_experiment_plan_skill, GenerateExperimentPlanSkill)

    def test_no_goal_no_specs_fails(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute())
        assert result.success is False

    def test_her_goal_generates_plan(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(goal="HER activity screening", name="her_test"))
        assert result.success is True
        assert len(result.data) == 1
        plan_dict = result.data[0]
        assert plan_dict["name"] == "her_test"
        assert len(plan_dict["steps"]) > 0

    def test_oer_goal_generates_plan(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(goal="OER stability"))
        assert result.success is True
        assert len(result.data) == 1

    def test_stability_goal(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(goal="stability test"))
        assert result.success is True
        # Stability template has CA step
        steps = result.data[0]["steps"]
        types = [s["step_type"] for s in steps]
        assert "ca" in types

    def test_generic_goal(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(goal="run some experiment"))
        assert result.success is True

    def test_custom_step_specs(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(
            step_specs=[{"step_type": "cv"}, {"step_type": "eis"}],
            name="custom_plan",
        ))
        assert result.success is True
        plan = result.data[0]
        assert plan["name"] == "custom_plan"
        assert len(plan["steps"]) == 2

    def test_param_grid_generates_multiple_plans(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(
            goal="HER",
            name="her_grid",
            param_ranges={"scan_rate": [0.005, 0.01, 0.02]},
            target_step_index=2,  # target the CV step
        ))
        assert result.success is True
        assert len(result.data) == 3
        for plan_dict in result.data:
            assert "_validation" in plan_dict

    def test_plan_has_validation_key(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(goal="cv characterisation"))
        plan = result.data[0]
        assert "_validation" in plan
        assert "valid" in plan["_validation"]

    def test_plan_serialisable(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(goal="HER", name="ser_test"))
        # Plan dicts must be JSON-serialisable
        dumped = json.dumps(result.data)
        assert "ser_test" in dumped

    def test_get_schema(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        schema = skill.get_schema()
        assert schema["type"] == "object"
        assert "goal" in schema["properties"]
        assert "param_ranges" in schema["properties"]

    def test_tags_applied(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        result = run_async(skill.execute(
            goal="HER",
            name="tagged",
            tags=["phase2", "test"],
        ))
        plan = result.data[0]
        assert "phase2" in plan["tags"]

    def test_required_tools(self) -> None:
        from src.skills.generate_experiment_plan import GenerateExperimentPlanSkill

        skill = GenerateExperimentPlanSkill()
        assert "build_experiment_plan" in skill.required_tools
        assert "validate_plan" in skill.required_tools


# ── skills __init__ exports ───────────────────────────────────────────────────

class TestSkillsInit:
    def test_a1_exported(self) -> None:
        from src.skills import SingleExperimentAnalysisSkill, single_experiment_analysis_skill
        assert SingleExperimentAnalysisSkill is not None
        assert single_experiment_analysis_skill is not None

    def test_b1_exported(self) -> None:
        from src.skills import GenerateExperimentPlanSkill, generate_experiment_plan_skill
        assert GenerateExperimentPlanSkill is not None
        assert generate_experiment_plan_skill is not None

    def test_all_skills_in_all(self) -> None:
        import src.skills as skills_mod
        for name in [
            "SingleExperimentAnalysisSkill",
            "single_experiment_analysis_skill",
            "GenerateExperimentPlanSkill",
            "generate_experiment_plan_skill",
        ]:
            assert name in skills_mod.__all__, f"{name} missing from __all__"
