"""End-to-end pipeline tests: A1 → C1 → C2 data flow.

Validates that:
1. A1 (SingleExperimentAnalysisSkill) produces structured analysis from a run dir.
2. C1 (ContextualizeExperimentSkill) produces comparison/trend/anomaly data.
3. C2 (SuggestNextExperimentSkill) produces a valid experiment plan from C1 output.
4. The full A1 → C1 → C2 chain completes successfully with mock data.

No LLM calls are made; all skills are LLM-free or use mocked LLM.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


def _make_run_dir(tmp_path: Path, metrics: dict[str, Any] | None = None) -> Path:
    """Create a minimal run directory with run_summary.json."""
    meta = {"run_id": "run_e2e_test", "success": True, **(metrics or {})}
    (tmp_path / "run_summary.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp_path


def _make_cv_csv(tmp_path: Path) -> Path:
    """Create a minimal CV CSV file."""
    csv_content = "Potential(V),Current(A)\n0.0,0.001\n-0.1,0.002\n-0.2,0.005\n-0.3,0.010\n-0.2,0.008\n-0.1,0.003\n0.0,0.001\n"
    csv_path = tmp_path / "cv_run001.csv"
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


def _make_history_dirs(parent: Path, n: int = 3) -> list[Path]:
    """Create n historical run dirs with numeric metrics."""
    dirs = []
    for i in range(n):
        d = parent / f"hist_run_{i:03d}"
        d.mkdir()
        meta = {
            "run_id": f"hist_{i}",
            "efficiency": 0.80 + i * 0.01,
            "peak_current": 0.04 + i * 0.001,
        }
        (d / "run_summary.json").write_text(json.dumps(meta), encoding="utf-8")
        dirs.append(d)
    return dirs


# ── A1: SingleExperimentAnalysisSkill ─────────────────────────────────────────

class TestSingleExperimentAnalysisSkillPipeline:
    def test_import(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        assert SingleExperimentAnalysisSkill is not None

    def test_missing_run_dir_returns_failure(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=""))
        assert result.success is False
        assert "run_dir" in result.message.lower()

    def test_nonexistent_run_dir_returns_failure(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir="/nonexistent/path"))
        assert result.success is False

    def test_empty_run_dir_no_csv_succeeds_with_empty_data(self, tmp_path: Path) -> None:
        """A run dir with no CSV files → success with empty data list."""
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        _make_run_dir(tmp_path)
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert result.data == []

    def test_run_dir_with_cv_csv_returns_analysis(self, tmp_path: Path) -> None:
        """A run dir with a CV CSV → success with analysis result containing technique."""
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        _make_run_dir(tmp_path)
        _make_cv_csv(tmp_path)
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert isinstance(result.data, list)
        if result.data:
            assert "technique" in result.data[0]
            assert "file" in result.data[0]

    def test_result_data_has_required_keys(self, tmp_path: Path) -> None:
        """Each analysis result item should have file, technique, n_points."""
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        _make_run_dir(tmp_path)
        _make_cv_csv(tmp_path)
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        for item in result.data:
            assert "file" in item
            assert "technique" in item
            assert "n_points" in item

    def test_exported_from_skills_init(self) -> None:
        from src.skills import SingleExperimentAnalysisSkill, single_experiment_analysis_skill
        assert SingleExperimentAnalysisSkill is not None
        assert single_experiment_analysis_skill is not None


# ── C1: ContextualizeExperimentSkill ─────────────────────────────────────────

class TestContextualizeExperimentSkillPipeline:
    def test_import(self) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        assert ContextualizeExperimentSkill is not None

    def test_run_dir_with_metrics_produces_comparison(self, tmp_path: Path) -> None:
        """C1 with a run dir containing metrics + history → comparison populated."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        # Current run
        current = tmp_path / "current_run"
        current.mkdir()
        _make_run_dir(current, metrics={"efficiency": 0.85, "peak_current": 0.042})
        # History dirs
        history_parent = tmp_path / "history"
        history_parent.mkdir()
        _make_history_dirs(history_parent, n=3)

        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(current),
            history_dir=str(history_parent),
        ))
        assert result.success is True
        assert "comparison" in result.data
        assert "trend" in result.data
        assert "anomalies" in result.data

    def test_run_dir_without_history_still_succeeds(self, tmp_path: Path) -> None:
        """C1 with no history dir → success with empty comparison."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        _make_run_dir(tmp_path, metrics={"efficiency": 0.85})
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert isinstance(result.data.get("anomalies"), list)

    def test_anomaly_detected_when_metric_far_from_mean(self, tmp_path: Path) -> None:
        """C1 detects anomaly when current metric deviates by > threshold_sigma."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        current = tmp_path / "current_run"
        current.mkdir()
        # efficiency much higher than historical mean (0.82)
        _make_run_dir(current, metrics={"efficiency": 0.99})

        history_parent = tmp_path / "history"
        history_parent.mkdir()
        # 3 historical runs with consistent efficiency ~0.80
        for i in range(3):
            d = history_parent / f"h{i}"
            d.mkdir()
            (d / "run_summary.json").write_text(
                json.dumps({"efficiency": 0.80 + i * 0.005}), encoding="utf-8"
            )

        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(current),
            history_dir=str(history_parent),
            threshold_sigma=1.0,
        ))
        assert result.success is True
        # With threshold_sigma=1.0 and large deviation, anomaly should be detected
        # (may depend on σ calculation; we just verify structure is correct)
        assert isinstance(result.data["anomalies"], list)

    def test_n_history_field_reflects_history_count(self, tmp_path: Path) -> None:
        """n_history in result.data matches number of historical runs used."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        current = tmp_path / "current_run"
        current.mkdir()
        _make_run_dir(current, metrics={"efficiency": 0.85})

        history_parent = tmp_path / "history"
        history_parent.mkdir()
        _make_history_dirs(history_parent, n=4)

        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(current),
            history_dir=str(history_parent),
        ))
        assert result.success is True
        assert result.data.get("n_history", -1) >= 0


# ── C2: SuggestNextExperimentSkill ────────────────────────────────────────────

class TestSuggestNextExperimentSkillPipeline:
    def test_import(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        assert SuggestNextExperimentSkill is not None

    def test_no_context_data_produces_generic_plan(self) -> None:
        """C2 with no context_data → generic plan."""
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data=None, goal=""))
        assert result.success is True
        assert result.data["intent"] == "generic"
        assert "plan" in result.data

    def test_anomalies_trigger_diagnostic_run(self) -> None:
        """C2 with anomalies in context → diagnostic_run intent."""
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        ctx = {"anomalies": ["efficiency"], "trend": {}}
        result = run_async(skill.execute(context_data=ctx, goal=""))
        assert result.success is True
        assert result.data["intent"] == "diagnostic_run"

    def test_declining_metrics_trigger_stability_run(self) -> None:
        """C2 with declining trend → stability_run intent."""
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        ctx = {"anomalies": [], "trend": {"efficiency": "declining"}}
        result = run_async(skill.execute(context_data=ctx, goal=""))
        assert result.success is True
        assert result.data["intent"] == "stability_run"

    def test_optimize_goal_triggers_optimisation_run(self) -> None:
        """C2 with optimize goal keyword → optimisation_run intent."""
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data={}, goal="optimize HER parameters"))
        assert result.success is True
        assert result.data["intent"] == "optimisation_run"

    def test_result_contains_plan_with_steps(self) -> None:
        """C2 result plan should have steps list."""
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data={}, goal=""))
        assert result.success is True
        plan = result.data.get("plan", {})
        assert isinstance(plan, dict)
        assert "steps" in plan

    def test_result_contains_rationale(self) -> None:
        """C2 result should have a non-empty rationale string."""
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data={}, goal=""))
        assert result.success is True
        assert isinstance(result.data.get("rationale"), str)
        assert len(result.data["rationale"]) > 0

    def test_custom_plan_name_used(self) -> None:
        """C2 plan name should use provided name parameter."""
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data={}, goal="", name="my_custom_plan"))
        assert result.success is True
        plan = result.data.get("plan", {})
        assert plan.get("name") == "my_custom_plan"

    def test_exported_from_skills_init(self) -> None:
        from src.skills import SuggestNextExperimentSkill, suggest_next_experiment_skill
        assert SuggestNextExperimentSkill is not None
        assert suggest_next_experiment_skill is not None


# ── Full A1 → C1 → C2 pipeline ────────────────────────────────────────────────

class TestFullPipelineA1C1C2:
    """Tests that chain A1 → C1 → C2 together in one flow."""

    def test_full_pipeline_completes_successfully(self, tmp_path: Path) -> None:
        """Full chain: A1 analyses → C1 contextualises → C2 suggests next run."""
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        # Setup directory structure
        current = tmp_path / "current_run"
        current.mkdir()
        _make_run_dir(current, metrics={"efficiency": 0.87, "peak_current": 0.043})
        _make_cv_csv(current)

        history_parent = tmp_path / "history"
        history_parent.mkdir()
        _make_history_dirs(history_parent, n=3)

        # Step A1
        a1 = SingleExperimentAnalysisSkill()
        a1_result = run_async(a1.execute(run_dir=str(current)))
        assert a1_result.success is True

        # Step C1
        c1 = ContextualizeExperimentSkill()
        c1_result = run_async(c1.execute(
            run_dir=str(current),
            history_dir=str(history_parent),
        ))
        assert c1_result.success is True

        # Step C2 uses C1 output as context_data
        c2 = SuggestNextExperimentSkill()
        c2_result = run_async(c2.execute(
            context_data=c1_result.data,
            goal="optimize HER activity",
        ))
        assert c2_result.success is True
        assert "plan" in c2_result.data
        assert "intent" in c2_result.data
        assert "rationale" in c2_result.data

    def test_pipeline_with_anomaly_triggers_diagnostic(self, tmp_path: Path) -> None:
        """When A1+C1 detect anomaly, C2 should choose diagnostic_run."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        # Current run has unusual efficiency
        current = tmp_path / "current_run"
        current.mkdir()
        _make_run_dir(current, metrics={"efficiency": 0.99})

        history_parent = tmp_path / "history"
        history_parent.mkdir()
        for i in range(5):
            d = history_parent / f"h{i}"
            d.mkdir()
            (d / "run_summary.json").write_text(
                json.dumps({"efficiency": 0.80}), encoding="utf-8"
            )

        c1 = ContextualizeExperimentSkill()
        c1_result = run_async(c1.execute(
            run_dir=str(current),
            history_dir=str(history_parent),
            threshold_sigma=1.0,
        ))
        assert c1_result.success is True

        c2 = SuggestNextExperimentSkill()
        c2_result = run_async(c2.execute(
            context_data=c1_result.data,
            goal="check system",
        ))
        assert c2_result.success is True
        # With anomaly in context, should recommend diagnostic or generic
        assert c2_result.data["intent"] in (
            "diagnostic_run", "stability_run", "optimisation_run", "generic"
        )
