"""End-to-end pipeline tests: A1 → C1 → C2 (SingleExperimentAnalysis → Contextualize → Suggest)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


def _create_run_dir(tmp_path: Path, *, with_cv: bool = True, with_eis: bool = False) -> Path:
    """Create a minimal experiment run directory with CSV data and metadata."""
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()

    # Write run_summary.json with numeric metrics
    summary = {
        "success": True,
        "peak_current_A": 0.0025,
        "onset_potential_V": -0.35,
        "charge_transfer_resistance_ohm": 12.5,
        "elapsed_seconds": 120.0,
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary))

    if with_cv:
        cv_data = pd.DataFrame({
            "Potential(V)": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.4, 0.3, 0.2, 0.1],
            "Current(A)": [0.0, 0.001, 0.002, 0.003, 0.002, 0.001, -0.001, -0.002, -0.003, -0.001],
        })
        cv_data.to_csv(run_dir / "cv_data.csv", index=False)

    if with_eis:
        eis_data = pd.DataFrame({
            "Zre(Ohm)": [10, 15, 20, 25, 20, 15],
            "Zim(Ohm)": [0, 5, 10, 5, 2, 0],
            "Freq(Hz)": [100000, 10000, 1000, 100, 10, 1],
        })
        eis_data.to_csv(run_dir / "eis_data.csv", index=False)

    return run_dir


def _create_history_dirs(tmp_path: Path, n: int = 3) -> list[Path]:
    """Create N historical run directories with incrementing metrics."""
    dirs = []
    for i in range(n):
        d = tmp_path / f"hist_run_{i:03d}"
        d.mkdir()
        summary = {
            "peak_current_A": 0.002 + i * 0.0001,
            "onset_potential_V": -0.35 + i * 0.005,
            "charge_transfer_resistance_ohm": 13.0 - i * 0.2,
        }
        (d / "run_summary.json").write_text(json.dumps(summary))
        dirs.append(d)
    return dirs


# ── A1: SingleExperimentAnalysisSkill ─────────────────────────────────────────

class TestA1SingleExperimentAnalysis:
    def test_analyse_cv_run(self, tmp_path: Path) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        run_dir = _create_run_dir(tmp_path, with_cv=True)
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(run_dir)))
        assert result.success is True
        assert len(result.data) >= 1
        assert result.data[0]["technique"] == "cv"

    def test_analyse_empty_dir(self, tmp_path: Path) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()
        (run_dir / "run_summary.json").write_text("{}")
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(run_dir)))
        assert result.success is True
        assert result.data == []

    def test_analyse_nonexistent_dir(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir="/nonexistent/path"))
        assert result.success is False

    def test_analyse_no_run_dir_param(self) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=""))
        assert result.success is False

    def test_cv_analysis_has_peaks(self, tmp_path: Path) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        run_dir = _create_run_dir(tmp_path, with_cv=True)
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(run_dir)))
        cv_result = result.data[0]
        assert "oxidation_peak" in cv_result or "potential_range" in cv_result

    def test_analyse_eis_run(self, tmp_path: Path) -> None:
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill

        run_dir = _create_run_dir(tmp_path, with_cv=False, with_eis=True)
        skill = SingleExperimentAnalysisSkill()
        result = run_async(skill.execute(run_dir=str(run_dir)))
        assert result.success is True
        assert any(r["technique"] == "eis" for r in result.data)


# ── C1: ContextualizeExperimentSkill ──────────────────────────────────────────

class TestC1ContextualizeExperiment:
    def test_basic_contextualise(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill

        run_dir = _create_run_dir(tmp_path)
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=str(run_dir)))
        assert result.success is True
        assert "comparison" in result.data
        assert "trend" in result.data
        assert "anomalies" in result.data

    def test_with_previous_results(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill

        run_dir = _create_run_dir(tmp_path)
        prev = [
            {"peak_current_A": 0.002, "onset_potential_V": -0.34},
            {"peak_current_A": 0.0021, "onset_potential_V": -0.33},
            {"peak_current_A": 0.0022, "onset_potential_V": -0.32},
        ]
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(run_dir),
            previous_results=prev,
        ))
        assert result.success is True
        assert result.data["n_history"] == 3
        assert len(result.data["comparison"]) > 0

    def test_anomaly_detection(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill

        run_dir = _create_run_dir(tmp_path)
        # Previous results with very consistent values — current run is an outlier
        prev = [{"peak_current_A": 0.001}] * 5
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(run_dir),
            previous_results=prev,
            threshold_sigma=1.0,
        ))
        assert result.success is True
        assert "peak_current_A" in result.data["anomalies"]

    def test_trend_detection(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill

        run_dir = _create_run_dir(tmp_path)
        # Increasing trend in peak_current_A
        prev = [{"peak_current_A": 0.001 + i * 0.0005} for i in range(6)]
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(run_dir),
            previous_results=prev,
        ))
        assert result.success is True
        assert result.data["trend"].get("peak_current_A") in ("increasing", "stable", "declining")

    def test_missing_run_dir(self) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill

        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=""))
        assert result.success is False

    def test_nonexistent_run_dir(self) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill

        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir="/nonexistent"))
        assert result.success is False

    def test_with_history_dir(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill

        run_dir = _create_run_dir(tmp_path)
        history_parent = tmp_path / "history"
        history_parent.mkdir()
        _create_history_dirs(history_parent, n=3)
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(run_dir),
            history_dir=str(history_parent),
        ))
        assert result.success is True
        assert result.data["n_history"] == 3


# ── C2: SuggestNextExperimentSkill ────────────────────────────────────────────

class TestC2SuggestNextExperiment:
    def test_generic_suggestion(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data={}, goal=""))
        assert result.success is True
        assert result.data["intent"] == "generic"
        assert "plan" in result.data

    def test_diagnostic_on_anomalies(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        ctx = {"anomalies": ["peak_current_A"], "trend": {}}
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data=ctx, goal=""))
        assert result.data["intent"] == "diagnostic_run"

    def test_stability_on_declining_trend(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        ctx = {"anomalies": [], "trend": {"peak_current_A": "declining"}}
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data=ctx, goal=""))
        assert result.data["intent"] == "stability_run"

    def test_optimisation_on_goal(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(
            context_data={"anomalies": [], "trend": {}},
            goal="optimize scan rate sweep",
        ))
        assert result.data["intent"] == "optimisation_run"

    def test_plan_is_valid(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data={}, goal="optimize"))
        assert result.data["valid"] is True
        assert "steps" in result.data["plan"]

    def test_plan_has_steps(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(context_data={}, goal=""))
        assert len(result.data["plan"]["steps"]) > 0

    def test_rationale_populated(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(
            context_data={"anomalies": ["x"]},
            goal="",
        ))
        assert len(result.data["rationale"]) > 0


# ── Full A1 → C1 → C2 pipeline ───────────────────────────────────────────────

class TestA1C1C2Pipeline:
    def test_full_pipeline_cv(self, tmp_path: Path) -> None:
        """Run A1 → C1 → C2 with real skill logic, no LLM calls."""
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        run_dir = _create_run_dir(tmp_path, with_cv=True)
        history_parent = tmp_path / "history"
        history_parent.mkdir()
        _create_history_dirs(history_parent, n=4)

        # A1: analyse single experiment
        a1 = SingleExperimentAnalysisSkill()
        a1_result = run_async(a1.execute(run_dir=str(run_dir)))
        assert a1_result.success is True

        # C1: contextualise
        c1 = ContextualizeExperimentSkill()
        c1_result = run_async(c1.execute(
            run_dir=str(run_dir),
            history_dir=str(history_parent),
        ))
        assert c1_result.success is True
        assert "comparison" in c1_result.data

        # C2: suggest next experiment based on C1 output
        c2 = SuggestNextExperimentSkill()
        c2_result = run_async(c2.execute(
            context_data=c1_result.data,
            goal="optimise HER activity",
        ))
        assert c2_result.success is True
        assert "plan" in c2_result.data
        assert c2_result.data["valid"] is True
        assert len(c2_result.data["plan"]["steps"]) > 0

    def test_pipeline_with_anomaly_triggers_diagnostic(self, tmp_path: Path) -> None:
        """Pipeline where C1 detects anomaly → C2 suggests diagnostic run."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        run_dir = _create_run_dir(tmp_path)
        # Feed historical values far from current to trigger anomaly
        prev = [{"peak_current_A": 0.0005}] * 5

        c1 = ContextualizeExperimentSkill()
        c1_result = run_async(c1.execute(
            run_dir=str(run_dir),
            previous_results=prev,
            threshold_sigma=1.0,
        ))
        assert c1_result.success is True
        assert len(c1_result.data["anomalies"]) > 0

        c2 = SuggestNextExperimentSkill()
        c2_result = run_async(c2.execute(
            context_data=c1_result.data,
            goal="",
        ))
        assert c2_result.data["intent"] == "diagnostic_run"

    def test_pipeline_with_eis(self, tmp_path: Path) -> None:
        """A1 → C1 → C2 with EIS data."""
        from src.skills.single_experiment_analysis import SingleExperimentAnalysisSkill
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill

        run_dir = _create_run_dir(tmp_path, with_cv=False, with_eis=True)

        a1 = SingleExperimentAnalysisSkill()
        a1_result = run_async(a1.execute(run_dir=str(run_dir)))
        assert a1_result.success is True

        c1 = ContextualizeExperimentSkill()
        c1_result = run_async(c1.execute(run_dir=str(run_dir)))
        assert c1_result.success is True

        c2 = SuggestNextExperimentSkill()
        c2_result = run_async(c2.execute(
            context_data=c1_result.data,
            goal="",
        ))
        assert c2_result.success is True
        assert c2_result.data["valid"] is True
