"""Phase 2 tests — Tool layer: data_reader, echem_analysis, experiment_builder."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def _cv_df() -> pd.DataFrame:
    """Minimal synthetic CV dataset."""
    import numpy as np

    n = 200
    t = np.linspace(0, 2 * np.pi, n)
    potential = np.sin(t)          # -1 V → +1 V → -1 V
    current = np.cos(t) * 1e-3    # ±1 mA, already in A after *1e-3
    return pd.DataFrame({"Potential(V)": potential, "Current(A)": current})


def _lsv_df() -> pd.DataFrame:
    import numpy as np

    potential = np.linspace(0, -0.6, 100)
    current = -np.abs(potential) * 0.01   # simple cathodic
    return pd.DataFrame({"Potential(V)": potential, "Current(A)": current})


def _eis_df() -> pd.DataFrame:
    import numpy as np

    freq = np.logspace(5, -1, 50)[::-1]
    zre = 10 + 50 * np.exp(-((np.log10(freq) - 2) ** 2))
    zim = 40 * np.exp(-((np.log10(freq) - 2) ** 2))
    return pd.DataFrame({"Freq(Hz)": freq, "Zre(Ohm)": zre, "Zim(Ohm)": zim})


# ── echem_analysis tests ───────────────────────────────────────────────────────

class TestAnalyzeCV:
    def test_basic_cv(self) -> None:
        from src.tools.echem_analysis import analyze_cv

        result = analyze_cv(_cv_df())
        assert "potential_range" in result
        assert "oxidation_peak" in result
        assert "reduction_peak" in result
        assert result["n_points"] == 200

    def test_returns_delta_ep(self) -> None:
        from src.tools.echem_analysis import analyze_cv

        result = analyze_cv(_cv_df())
        assert result["delta_Ep_V"] is not None
        assert result["delta_Ep_V"] >= 0

    def test_missing_columns(self) -> None:
        from src.tools.echem_analysis import analyze_cv

        bad_df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = analyze_cv(bad_df)
        assert "error" in result

    def test_scan_rate_echoed(self) -> None:
        from src.tools.echem_analysis import analyze_cv

        result = analyze_cv(_cv_df(), scan_rate_mv_s=50.0)
        assert result["scan_rate_mv_s"] == 50.0


class TestAnalyzeLSV:
    def test_basic_lsv(self) -> None:
        from src.tools.echem_analysis import analyze_lsv

        result = analyze_lsv(_lsv_df(), direction="cathodic")
        assert "onset_potential_V" in result
        assert "limiting_current_A" in result
        assert result["n_points"] == 100

    def test_direction_echoed(self) -> None:
        from src.tools.echem_analysis import analyze_lsv

        result = analyze_lsv(_lsv_df(), direction="cathodic")
        assert result["direction"] == "cathodic"

    def test_missing_columns(self) -> None:
        from src.tools.echem_analysis import analyze_lsv

        result = analyze_lsv(pd.DataFrame({"X": [1]}))
        assert "error" in result


class TestAnalyzeEIS:
    def test_basic_eis(self) -> None:
        from src.tools.echem_analysis import analyze_eis

        result = analyze_eis(_eis_df())
        assert "Rs_ohm" in result
        assert "Rct_ohm" in result
        assert result["n_points"] == 50
        assert result["Rs_ohm"] >= 0

    def test_frequency_range(self) -> None:
        from src.tools.echem_analysis import analyze_eis

        result = analyze_eis(_eis_df())
        assert result["frequency_range_Hz"] is not None
        assert len(result["frequency_range_Hz"]) == 2

    def test_missing_columns(self) -> None:
        from src.tools.echem_analysis import analyze_eis

        result = analyze_eis(pd.DataFrame({"A": [1]}))
        assert "error" in result


class TestAnalyzeEchemFiles:
    def test_batch_with_mixed_files(self, tmp_path: Path) -> None:
        from src.tools.echem_analysis import analyze_echem_files

        cv_file = tmp_path / "cv_001.csv"
        cv_file.write_text("Potential(V),Current(A)\n0.0,0.001\n0.5,0.002\n1.0,0.003\n")

        results = analyze_echem_files([str(cv_file)])
        assert len(results) == 1
        assert results[0]["technique"] == "cv"

    def test_bad_file_returns_error_entry(self) -> None:
        from src.tools.echem_analysis import analyze_echem_files

        results = analyze_echem_files(["/nonexistent/path/cv.csv"])
        assert len(results) == 1
        assert "error" in results[0]


# ── data_reader tests ──────────────────────────────────────────────────────────

class TestLoadEchemFile:
    def test_load_csv(self, tmp_path: Path) -> None:
        from src.tools.data_reader import load_echem_file

        f = tmp_path / "cv_test.csv"
        f.write_text("Potential(V),Current(A)\n0.1,0.001\n0.2,0.002\n")
        echem = load_echem_file(str(f))
        assert echem.technique == "cv"
        assert echem.points == 2

    def test_not_found_raises(self) -> None:
        from src.tools.data_reader import load_echem_file

        with pytest.raises(FileNotFoundError):
            load_echem_file("/no/such/file.csv")

    def test_technique_detection(self, tmp_path: Path) -> None:
        from src.tools.data_reader import load_echem_file

        for tech in ("cv", "lsv", "eis"):
            f = tmp_path / f"{tech}_data.csv"
            f.write_text("A,B\n1,2\n")
            echem = load_echem_file(str(f))
            assert echem.technique == tech


class TestLoadRunEchemFiles:
    def test_loads_all_csvs(self, tmp_path: Path) -> None:
        from src.tools.data_reader import load_run_echem_files

        for i in range(3):
            (tmp_path / f"cv_{i}.csv").write_text("Potential(V),Current(A)\n0,0\n")
        items = load_run_echem_files(str(tmp_path))
        assert len(items) == 3

    def test_missing_dir_raises(self) -> None:
        from src.tools.data_reader import load_run_echem_files

        with pytest.raises(FileNotFoundError):
            load_run_echem_files("/no/such/dir")


class TestReadRunMetadata:
    def test_returns_dict_with_keys(self, tmp_path: Path) -> None:
        from src.tools.data_reader import read_run_metadata

        meta = read_run_metadata(str(tmp_path))
        assert "run_dir" in meta
        assert "run_summary" in meta
        assert "experiment" in meta
        assert "params" in meta

    def test_reads_json_files(self, tmp_path: Path) -> None:
        import json
        from src.tools.data_reader import read_run_metadata

        (tmp_path / "run_summary.json").write_text(json.dumps({"success": True}))
        meta = read_run_metadata(str(tmp_path))
        assert meta["run_summary"]["success"] is True


class TestListRunFiles:
    def test_groups_by_extension(self, tmp_path: Path) -> None:
        from src.tools.data_reader import list_run_files

        (tmp_path / "a.csv").write_text("x")
        (tmp_path / "b.csv").write_text("x")
        (tmp_path / "c.json").write_text("{}")
        grouped = list_run_files(str(tmp_path))
        assert "csv" in grouped
        assert len(grouped["csv"]) == 2
        assert "json" in grouped


# ── experiment_builder tests ───────────────────────────────────────────────────

class TestBuildStep:
    def test_defaults_applied(self) -> None:
        from src.tools.experiment_builder import build_step

        step = build_step(0, "cv")
        assert step.step_index == 0
        assert step.step_type == "cv"
        assert "scan_rate" in step.params

    def test_params_override_defaults(self) -> None:
        from src.tools.experiment_builder import build_step

        step = build_step(1, "cv", params={"scan_rate": 0.1})
        assert step.params["scan_rate"] == 0.1

    def test_unknown_type_accepted(self) -> None:
        from src.tools.experiment_builder import build_step

        step = build_step(0, "custom_step", params={"foo": 42})
        assert step.params["foo"] == 42


class TestBuildExperimentPlan:
    def test_basic_plan(self) -> None:
        from src.tools.experiment_builder import build_experiment_plan

        plan = build_experiment_plan(
            "test_plan",
            [{"step_type": "cv"}, {"step_type": "eis"}],
        )
        assert plan.name == "test_plan"
        assert len(plan.steps) == 2
        assert plan.steps[0].step_type == "cv"

    def test_empty_specs_raises(self) -> None:
        from src.tools.experiment_builder import build_experiment_plan

        with pytest.raises(ValueError):
            build_experiment_plan("fail", [])

    def test_missing_step_type_raises(self) -> None:
        from src.tools.experiment_builder import build_experiment_plan

        with pytest.raises(ValueError):
            build_experiment_plan("fail", [{"params": {}}])


class TestGenerateParamGrid:
    def test_grid_size(self) -> None:
        from src.tools.experiment_builder import generate_param_grid

        grid = generate_param_grid({"a": [1, 2], "b": [3, 4, 5]})
        assert len(grid) == 6

    def test_empty_raises(self) -> None:
        from src.tools.experiment_builder import generate_param_grid

        with pytest.raises(ValueError):
            generate_param_grid({})


class TestBuildPlansFromGrid:
    def test_produces_correct_count(self) -> None:
        from src.tools.experiment_builder import build_plans_from_grid

        plans = build_plans_from_grid(
            "her",
            [{"step_type": "cv"}, {"step_type": "lsv"}],
            {"scan_rate": [0.005, 0.01, 0.02]},
            target_step_index=1,
        )
        assert len(plans) == 3
        for i, plan in enumerate(plans):
            assert plan.name == f"her_{i + 1}"

    def test_combo_params_applied(self) -> None:
        from src.tools.experiment_builder import build_plans_from_grid

        plans = build_plans_from_grid(
            "test",
            [{"step_type": "cv"}],
            {"scan_rate": [0.01, 0.05]},
            target_step_index=0,
        )
        rates = {p.steps[0].params["scan_rate"] for p in plans}
        assert rates == {0.01, 0.05}


class TestValidatePlan:
    def test_valid_plan(self) -> None:
        from src.tools.experiment_builder import build_experiment_plan, validate_plan

        plan = build_experiment_plan("ok", [{"step_type": "cv"}])
        report = validate_plan(plan)
        assert report["valid"] is True
        assert report["errors"] == []

    def test_missing_required_param(self) -> None:
        from src.tools.experiment_builder import build_experiment_plan, validate_plan
        from src.common.types import ProgStep

        plan = build_experiment_plan("bad", [{"step_type": "cv"}])
        # Remove a required param
        plan.steps[0].params.pop("scan_rate", None)
        report = validate_plan(plan)
        assert report["valid"] is False
        assert any("scan_rate" in e for e in report["errors"])


class TestPlanToDict:
    def test_serialisable(self) -> None:
        import json
        from src.tools.experiment_builder import build_experiment_plan, plan_to_dict

        plan = build_experiment_plan("ser_test", [{"step_type": "cv"}])
        d = plan_to_dict(plan)
        # Should be JSON-serialisable without errors
        dumped = json.dumps(d)
        assert "ser_test" in dumped
