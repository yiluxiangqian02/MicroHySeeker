"""Tests for src/optimization — BayesianOptimizer, ParameterSpace, objective functions.

Covers:
* ParameterDefinition validation and suggest()
* ParameterSpace construction (programmatic, mapping, iterable)
* BayesianOptimizer single-objective with Optuna study lifecycle
* MultiObjectiveBayesianOptimizer Pareto front
* PeakCurrentObjective / SignalToNoiseObjective / MultiObjectiveFunction
* Integration tests with mocked LLM-backed objective functions
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


# ── ParameterDefinition ────────────────────────────────────────────────────────


class TestParameterDefinition:
    def test_float_definition(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="lr", kind="float", low=1e-4, high=1e-1)
        assert p.name == "lr"
        assert p.kind == "float"
        assert p.low == 1e-4
        assert p.high == 1e-1

    def test_int_definition(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="n_layers", kind="int", low=1, high=8)
        assert p.kind == "int"

    def test_categorical_definition(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(
            name="activation", kind="categorical", choices=("relu", "tanh")
        )
        assert p.choices == ("relu", "tanh")

    def test_empty_name_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        with pytest.raises(ValueError, match="cannot be empty"):
            ParameterDefinition(name="  ", kind="categorical", choices=("a",))

    def test_float_missing_bounds_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        with pytest.raises(ValueError, match="low/high"):
            ParameterDefinition(name="x", kind="float")

    def test_float_low_gt_high_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        with pytest.raises(ValueError, match="low cannot be greater than high"):
            ParameterDefinition(name="x", kind="float", low=1.0, high=0.5)

    def test_categorical_empty_choices_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        with pytest.raises(ValueError, match="choices cannot be empty"):
            ParameterDefinition(name="x", kind="categorical", choices=())

    def test_float_log_and_step_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        with pytest.raises(ValueError, match="log and step"):
            ParameterDefinition(
                name="x", kind="float", low=0.001, high=1.0, log=True, step=0.1
            )

    def test_int_log_with_non_unit_step_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        with pytest.raises(ValueError, match="step=1"):
            ParameterDefinition(
                name="x", kind="int", low=1, high=100, log=True, step=2
            )

    def test_int_log_with_step_one_ok(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="x", kind="int", low=1, high=100, log=True, step=1)
        assert p.log is True
        assert p.step == 1

    def test_float_with_step(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="x", kind="float", low=0.0, high=1.0, step=0.1)
        assert p.step == pytest.approx(0.1)

    def test_float_log_without_step_ok(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="lr", kind="float", low=1e-5, high=1e-1, log=True)
        assert p.log is True

    # ── suggest() with real Optuna trial ──

    def test_suggest_float(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="x", kind="float", low=0.0, high=1.0)
        study = optuna.create_study()
        trial = study.ask()
        val = p.suggest(trial)
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0

    def test_suggest_int(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="n", kind="int", low=1, high=10)
        study = optuna.create_study()
        trial = study.ask()
        val = p.suggest(trial)
        assert isinstance(val, int)
        assert 1 <= val <= 10

    def test_suggest_categorical(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(
            name="mode", kind="categorical", choices=("fast", "slow")
        )
        study = optuna.create_study()
        trial = study.ask()
        val = p.suggest(trial)
        assert val in ("fast", "slow")

    def test_suggest_float_log_scale(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="lr", kind="float", low=1e-5, high=1e-1, log=True)
        study = optuna.create_study()
        trial = study.ask()
        val = p.suggest(trial)
        assert isinstance(val, float)
        assert 1e-5 <= val <= 1e-1

    def test_suggest_int_log_scale(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterDefinition

        p = ParameterDefinition(name="n", kind="int", low=1, high=1000, log=True)
        study = optuna.create_study()
        trial = study.ask()
        val = p.suggest(trial)
        assert isinstance(val, int)
        assert 1 <= val <= 1000

    def test_suggest_categorical_missing_choices_raises(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterDefinition

        # Bypass __post_init__ by using object.__setattr__ on frozen dataclass
        p = ParameterDefinition.__new__(ParameterDefinition)
        object.__setattr__(p, "name", "x")
        object.__setattr__(p, "kind", "categorical")
        object.__setattr__(p, "low", None)
        object.__setattr__(p, "high", None)
        object.__setattr__(p, "choices", None)
        object.__setattr__(p, "log", False)
        object.__setattr__(p, "step", None)
        study = optuna.create_study()
        trial = study.ask()
        with pytest.raises(ValueError, match="choices are missing"):
            p.suggest(trial)


# ── ParameterSpace ─────────────────────────────────────────────────────────────


class TestParameterSpace:
    def test_add_float(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace()
        ps.add_float("lr", 1e-4, 1e-1)
        assert "lr" in ps.names
        assert len(ps) == 1

    def test_add_int(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace()
        ps.add_int("n", 1, 10)
        assert len(ps) == 1

    def test_add_categorical(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace()
        ps.add_categorical("act", ["relu", "tanh", "gelu"])
        assert "act" in ps.names

    def test_duplicate_name_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace()
        ps.add_float("lr", 0.0, 1.0)
        with pytest.raises(ValueError, match="duplicate"):
            ps.add_float("lr", 0.0, 0.5)

    def test_empty_suggest_raises(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace()
        study = optuna.create_study()
        trial = study.ask()
        with pytest.raises(ValueError, match="empty"):
            ps.suggest(trial)

    def test_suggest_returns_all_params(self) -> None:
        import optuna

        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace()
        ps.add_float("x", 0.0, 1.0)
        ps.add_int("n", 1, 5)
        ps.add_categorical("mode", ["a", "b"])
        study = optuna.create_study()
        trial = study.ask()
        params = ps.suggest(trial)
        assert set(params.keys()) == {"x", "n", "mode"}
        assert isinstance(params["x"], float)
        assert isinstance(params["n"], int)
        assert params["mode"] in ("a", "b")

    def test_from_mapping_float(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"lr": {"type": "float", "low": 0.001, "high": 0.1}})
        assert "lr" in ps.names

    def test_from_mapping_continuous_alias(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"lr": {"type": "continuous", "low": 0.001, "high": 0.1}})
        assert "lr" in ps.names

    def test_from_mapping_int(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"depth": {"type": "int", "low": 1, "high": 5}})
        assert "depth" in ps.names

    def test_from_mapping_integer_alias(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"depth": {"type": "integer", "low": 1, "high": 5}})
        assert "depth" in ps.names

    def test_from_mapping_categorical(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace(
            {"act": {"type": "categorical", "choices": ["relu", "tanh"]}}
        )
        assert "act" in ps.names

    def test_from_mapping_choice_alias(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"act": {"type": "choice", "choices": ["relu", "tanh"]}})
        assert "act" in ps.names

    def test_from_mapping_categorical_non_sequence_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        with pytest.raises(TypeError, match="must be a sequence"):
            ParameterSpace({"act": {"type": "categorical", "choices": "single"}})

    def test_from_mapping_with_log_and_step(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace(
            {"x": {"type": "float", "low": 0.0, "high": 1.0, "step": 0.25}}
        )
        assert len(ps) == 1

    def test_from_sequence_two_ints(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"n": [1, 10]})
        assert "n" in ps.names

    def test_from_sequence_two_floats(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"lr": [0.001, 0.1]})
        assert "lr" in ps.names

    def test_from_sequence_categorical_list(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace({"opt": ["adam", "sgd", "rmsprop"]})
        assert "opt" in ps.names

    def test_from_sequence_empty_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        with pytest.raises(ValueError, match="cannot be empty"):
            ParameterSpace({"x": []})

    def test_unknown_mapping_type_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        with pytest.raises(ValueError, match="unknown parameter type"):
            ParameterSpace({"x": {"type": "unknown_type", "low": 0, "high": 1}})

    def test_unsupported_spec_type_raises(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        with pytest.raises(TypeError, match="unsupported parameter specification"):
            ParameterSpace({"x": 42})

    def test_from_iterable_of_definitions(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterDefinition, ParameterSpace

        defs = [
            ParameterDefinition(name="x", kind="float", low=0.0, high=1.0),
            ParameterDefinition(name="n", kind="int", low=1, high=10),
        ]
        ps = ParameterSpace(defs)
        assert ps.names == ("x", "n")
        assert len(ps) == 2

    def test_none_creates_empty_space(self) -> None:
        from src.optimization.bayesian_optimizer import ParameterSpace

        ps = ParameterSpace(None)
        assert len(ps) == 0


# ── BayesianOptimizer ──────────────────────────────────────────────────────────


class TestBayesianOptimizer:
    def test_optimize_simple(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, direction="maximize", seed=42)
        result = opt.optimize(lambda p: float(p["x"]), n_trials=5)
        assert result.best_value >= 0.0
        assert result.total_trials == 5
        assert "x" in result.best_params

    def test_optimize_minimization(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 10.0]}, direction="minimize", seed=0)
        result = opt.optimize(lambda p: float(p["x"]) ** 2, n_trials=10)
        assert result.best_value >= 0.0
        assert result.best_params["x"] is not None

    def test_n_trials_zero_raises(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, seed=0)
        with pytest.raises(ValueError, match="n_trials"):
            opt.optimize(lambda p: 0.0, n_trials=0)

    def test_n_trials_negative_raises(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, seed=0)
        with pytest.raises(ValueError, match="n_trials"):
            opt.optimize(lambda p: 0.0, n_trials=-1)

    def test_study_property_before_optimize_raises(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]})
        with pytest.raises(RuntimeError, match="not created yet"):
            _ = opt.study

    def test_study_available_after_optimize(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, seed=0)
        opt.optimize(lambda p: 1.0, n_trials=3)
        assert opt.study is not None

    def test_reset_study_on_each_call(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, seed=0)
        r1 = opt.optimize(lambda p: float(p["x"]), n_trials=3)
        r2 = opt.optimize(lambda p: float(p["x"]), n_trials=3, reset_study=True)
        assert r1.total_trials == 3
        assert r2.total_trials == 3

    def test_accumulate_trials_without_reset(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, seed=42)
        r1 = opt.optimize(lambda p: float(p["x"]), n_trials=3)
        assert r1.total_trials == 3
        r2 = opt.optimize(lambda p: float(p["x"]), n_trials=4, reset_study=False)
        assert r2.total_trials == 7  # 3 + 4 accumulated

    def test_result_best_trial_number(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, direction="maximize", seed=0)
        result = opt.optimize(lambda p: float(p["x"]), n_trials=5)
        assert 0 <= result.best_trial_number < 5

    def test_accepts_parameter_space_object(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer, ParameterSpace

        ps = ParameterSpace()
        ps.add_float("x", 0.0, 1.0)
        opt = BayesianOptimizer(ps, direction="maximize", seed=42)
        result = opt.optimize(lambda p: float(p["x"]), n_trials=3)
        assert result.total_trials == 3

    def test_multi_parameter_space(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        space = {
            "voltage": [0.1, 2.0],
            "scan_rate": {"type": "float", "low": 0.01, "high": 1.0},
            "electrolyte": ["KOH", "H2SO4", "NaCl"],
        }
        opt = BayesianOptimizer(space, direction="maximize", seed=42)
        result = opt.optimize(
            lambda p: float(p["voltage"]) * float(p["scan_rate"]), n_trials=5
        )
        assert result.total_trials == 5
        assert "voltage" in result.best_params
        assert "scan_rate" in result.best_params
        assert "electrolyte" in result.best_params

    def test_study_exposes_optuna_trials(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, seed=0)
        opt.optimize(lambda p: float(p["x"]), n_trials=4)
        study = opt.study
        assert len(study.trials) == 4
        for trial in study.trials:
            assert "x" in trial.params


# ── MultiObjectiveBayesianOptimizer ──────────────────────────────────────────


class TestMultiObjectiveBayesianOptimizer:
    def test_optimize_two_objectives(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0], "y": [0.0, 1.0]},
            directions=["maximize", "minimize"],
            seed=42,
        )
        result = opt.optimize(lambda p: (float(p["x"]), float(p["y"])), n_trials=5)
        assert result.total_trials == 5
        assert len(result.pareto_params) >= 1
        assert len(result.pareto_values) == len(result.pareto_params)

    def test_single_direction_raises(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        with pytest.raises(ValueError, match="at least two"):
            MultiObjectiveBayesianOptimizer(
                {"x": [0.0, 1.0]}, directions=["maximize"]
            )

    def test_objective_size_mismatch_raises(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0]},
            directions=["maximize", "minimize"],
            seed=0,
        )
        with pytest.raises(Exception, match="does not match"):
            opt.optimize(lambda p: (1.0,), n_trials=2)

    def test_pareto_values_are_tuples(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0]},
            directions=["maximize", "minimize"],
            seed=42,
        )
        result = opt.optimize(lambda p: (float(p["x"]), 1.0 - float(p["x"])), n_trials=5)
        for v in result.pareto_values:
            assert isinstance(v, tuple)
            assert len(v) == 2

    def test_pareto_trial_numbers_match(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0]},
            directions=["maximize", "minimize"],
            seed=42,
        )
        result = opt.optimize(lambda p: (float(p["x"]), 1.0 - float(p["x"])), n_trials=5)
        assert len(result.pareto_trial_numbers) == len(result.pareto_params)

    def test_study_property_before_optimize_raises(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0]}, directions=["maximize", "minimize"]
        )
        with pytest.raises(RuntimeError, match="not created yet"):
            _ = opt.study

    def test_three_objectives(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0], "y": [0.0, 1.0]},
            directions=["maximize", "minimize", "maximize"],
            seed=42,
        )
        result = opt.optimize(
            lambda p: (float(p["x"]), float(p["y"]), float(p["x"]) + float(p["y"])),
            n_trials=5,
        )
        assert result.total_trials == 5
        for v in result.pareto_values:
            assert len(v) == 3

    def test_accumulate_trials_without_reset(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0]},
            directions=["maximize", "minimize"],
            seed=42,
        )
        r1 = opt.optimize(lambda p: (float(p["x"]), 1.0 - float(p["x"])), n_trials=3)
        assert r1.total_trials == 3
        r2 = opt.optimize(
            lambda p: (float(p["x"]), 1.0 - float(p["x"])),
            n_trials=4,
            reset_study=False,
        )
        assert r2.total_trials == 7


# ── PeakCurrentObjective ────────────────────────────────────────────────────


class TestPeakCurrentObjective:
    def test_evaluate_from_peak_key(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective()
        assert obj.evaluate_result({"peak_current": 0.05}) == pytest.approx(0.05)

    def test_evaluate_absolute_peak(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective(use_absolute_peak=True)
        assert obj.evaluate_result({"peak_current": -0.08}) == pytest.approx(0.08)

    def test_evaluate_non_absolute(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective(use_absolute_peak=False)
        assert obj.evaluate_result({"peak_current": -0.08}) == pytest.approx(-0.08)

    def test_evaluate_peak_key_none_falls_through(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective()
        result = obj.evaluate_result({"peak_current": None, "current": [0.01, 0.05]})
        assert result == pytest.approx(0.05)

    def test_evaluate_from_current_array(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective()
        result = obj.evaluate_result([0.01, 0.03, 0.07, 0.05])
        assert result == pytest.approx(0.07)

    def test_evaluate_from_numpy_array(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective()
        arr = np.array([-0.02, 0.04, -0.09, 0.06])
        result = obj.evaluate_result(arr)
        assert result == pytest.approx(0.09)

    def test_evaluate_from_current_key(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective()
        result = obj.evaluate_result({"current": [0.01, 0.09, 0.05]})
        assert result == pytest.approx(0.09)

    def test_evaluate_non_absolute_from_array(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective(use_absolute_peak=False)
        result = obj.evaluate_result([-0.5, 0.3, -0.1])
        assert result == pytest.approx(0.3)

    def test_evaluate_missing_key_raises(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective()
        with pytest.raises(KeyError):
            obj.evaluate_result({"voltage": [1.0, 2.0]})

    def test_evaluate_empty_array_raises(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective()
        with pytest.raises(ValueError, match="cannot be empty"):
            obj.evaluate_result([])

    def test_call_without_getter_raises(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective(result_getter=None)
        with pytest.raises(RuntimeError, match="result_getter"):
            obj({"x": 1})

    def test_call_with_getter(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective(
            result_getter=lambda p: {"peak_current": float(p["x"])}
        )
        assert obj({"x": 0.5}) == pytest.approx(0.5)

    def test_custom_keys(self) -> None:
        from src.optimization.objective_functions import PeakCurrentObjective

        obj = PeakCurrentObjective(peak_key="i_peak", current_key="i_values")
        assert obj.evaluate_result({"i_peak": 0.42}) == pytest.approx(0.42)
        result = obj.evaluate_result({"i_values": [0.1, 0.3, 0.2]})
        assert result == pytest.approx(0.3)


# ── SignalToNoiseObjective ──────────────────────────────────────────────────


class TestSignalToNoiseObjective:
    def test_evaluate_from_snr_key(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective()
        assert obj.evaluate_result({"signal_to_noise": 15.0}) == pytest.approx(15.0)

    def test_evaluate_snr_key_none_falls_through(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective()
        result = obj.evaluate_result(
            {"signal_to_noise": None, "signal": 0.1, "noise": 0.01}
        )
        assert result == pytest.approx(10.0)

    def test_evaluate_from_signal_noise_keys(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective()
        result = obj.evaluate_result({"signal": 0.1, "noise": 0.01})
        assert result == pytest.approx(10.0)

    def test_evaluate_negative_noise_uses_abs(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective()
        result = obj.evaluate_result({"signal": 0.1, "noise": -0.01})
        assert result == pytest.approx(10.0)

    def test_evaluate_signal_noise_non_absolute(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective(use_absolute_signal=False)
        result = obj.evaluate_result({"signal": -0.5, "noise": 0.05})
        assert result == pytest.approx(-10.0)

    def test_evaluate_from_current_array(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective(baseline_fraction=0.3)
        current = [0.001, 0.001, 0.001] + [0.1] * 7
        result = obj.evaluate_result(current)
        assert result > 1.0

    def test_evaluate_from_current_key_in_mapping(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective(baseline_fraction=0.5)
        result = obj.evaluate_result({"current": [0.0, 0.0, 0.0, 0.0, 1.0, 1.0]})
        assert result > 0

    def test_evaluate_missing_all_keys_raises(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective()
        with pytest.raises(KeyError, match="must contain one of"):
            obj.evaluate_result({"voltage": [1.0, 2.0]})

    def test_evaluate_numpy_array(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective(baseline_fraction=0.5)
        arr = np.array([0.001, 0.001, 0.001, 0.001, 0.5, 0.5, 0.5, 0.5])
        result = obj.evaluate_result(arr)
        assert result > 1.0

    def test_evaluate_empty_array_raises(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective()
        with pytest.raises(ValueError, match="cannot be empty"):
            obj.evaluate_result([])

    def test_invalid_baseline_fraction_raises(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        with pytest.raises(ValueError, match="baseline_fraction"):
            SignalToNoiseObjective(baseline_fraction=0.0)

    def test_baseline_fraction_above_one_raises(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        with pytest.raises(ValueError, match="baseline_fraction"):
            SignalToNoiseObjective(baseline_fraction=1.5)

    def test_invalid_noise_floor_raises(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        with pytest.raises(ValueError, match="noise_floor"):
            SignalToNoiseObjective(noise_floor=0.0)

    def test_noise_floor_prevents_division_by_zero(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective(noise_floor=1e-12)
        result = obj.evaluate_result({"signal": 1.0, "noise": 0.0})
        assert result > 0

    def test_call_without_getter_raises(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective(result_getter=None)
        with pytest.raises(RuntimeError, match="result_getter"):
            obj({"x": 1})

    def test_call_with_getter(self) -> None:
        from src.optimization.objective_functions import SignalToNoiseObjective

        obj = SignalToNoiseObjective(
            result_getter=lambda p: {"signal_to_noise": float(p["x"]) * 10}
        )
        assert obj({"x": 2.0}) == pytest.approx(20.0)


# ── MultiObjectiveFunction ─────────────────────────────────────────────────


class TestMultiObjectiveFunctionWrapper:
    def test_evaluate_returns_tuple(self) -> None:
        from src.optimization.objective_functions import MultiObjectiveFunction

        mof = MultiObjectiveFunction([lambda p: 1.0, lambda p: 2.0])
        result = mof.evaluate({"x": 0})
        assert result == (1.0, 2.0)

    def test_call_returns_tuple(self) -> None:
        from src.optimization.objective_functions import MultiObjectiveFunction

        mof = MultiObjectiveFunction([lambda p: 3.0, lambda p: 4.0])
        assert mof({}) == (3.0, 4.0)

    def test_evaluate_named(self) -> None:
        from src.optimization.objective_functions import MultiObjectiveFunction

        mof = MultiObjectiveFunction(
            [lambda p: 5.0, lambda p: 6.0], names=["a", "b"]
        )
        named = mof.evaluate_named({})
        assert named == {"a": 5.0, "b": 6.0}

    def test_auto_generated_names(self) -> None:
        from src.optimization.objective_functions import MultiObjectiveFunction

        mof = MultiObjectiveFunction([lambda p: 0.0, lambda p: 0.0])
        assert mof.names == ("objective_1", "objective_2")

    def test_empty_objectives_raises(self) -> None:
        from src.optimization.objective_functions import MultiObjectiveFunction

        with pytest.raises(ValueError, match="at least one"):
            MultiObjectiveFunction([])

    def test_mismatched_names_length_raises(self) -> None:
        from src.optimization.objective_functions import MultiObjectiveFunction

        with pytest.raises(ValueError, match="names length"):
            MultiObjectiveFunction([lambda p: 0.0], names=["a", "b"])

    def test_single_objective(self) -> None:
        from src.optimization.objective_functions import MultiObjectiveFunction

        mof = MultiObjectiveFunction([lambda p: 42.0])
        assert mof({}) == (42.0,)
        assert mof.names == ("objective_1",)


# ── Optimizer + Objective integration ──────────────────────────────────────


class TestOptimizerWithObjectives:
    """Integration tests: BayesianOptimizer driven by PeakCurrentObjective / SNR."""

    def test_optimizer_with_peak_current_objective(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer
        from src.optimization.objective_functions import PeakCurrentObjective

        def fake_experiment(params: dict[str, Any]) -> dict[str, Any]:
            v = float(params["voltage"])
            return {"peak_current": v * 0.5}

        obj = PeakCurrentObjective(result_getter=fake_experiment)
        opt = BayesianOptimizer({"voltage": [0.1, 2.0]}, direction="maximize", seed=42)
        result = opt.optimize(obj, n_trials=10)
        assert result.best_value > 0
        assert result.best_params["voltage"] is not None

    def test_optimizer_with_snr_objective(self) -> None:
        from src.optimization.bayesian_optimizer import BayesianOptimizer
        from src.optimization.objective_functions import SignalToNoiseObjective

        def fake_experiment(params: dict[str, Any]) -> dict[str, Any]:
            v = float(params["voltage"])
            return {"signal": v * 0.8, "noise": 0.01}

        obj = SignalToNoiseObjective(result_getter=fake_experiment)
        opt = BayesianOptimizer({"voltage": [0.1, 2.0]}, direction="maximize", seed=42)
        result = opt.optimize(obj, n_trials=8)
        assert result.best_value > 1.0

    def test_multi_objective_optimizer_with_wrapper(self) -> None:
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer
        from src.optimization.objective_functions import MultiObjectiveFunction

        mof = MultiObjectiveFunction(
            [
                lambda p: float(p["x"]) ** 2,
                lambda p: (1 - float(p["x"])) ** 2,
            ],
            names=["f1", "f2"],
        )
        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0]},
            directions=["minimize", "minimize"],
            seed=42,
        )
        result = opt.optimize(mof, n_trials=10)
        assert result.total_trials == 10
        assert len(result.pareto_params) >= 1


# ── Mocked LLM-backed objective tests ─────────────────────────────────────


class TestOptimizerWithMockedLLM:
    """Test optimization with objectives that internally call an LLM.

    Simulates a realistic scenario where the optimizer evaluates parameters
    by sending them to an LLM for analysis, with the LLM calls fully mocked.
    """

    @staticmethod
    def _make_mock_llm_response(text: str = "ok") -> MagicMock:
        choice = MagicMock()
        choice.message.content = text
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_optimizer_with_llm_scoring_objective(self) -> None:
        """Optimizer uses an objective that parses a numeric score from LLM output."""
        import asyncio

        from src.optimization.bayesian_optimizer import BayesianOptimizer

        call_count = 0

        async def fake_llm_score(params: dict[str, Any]) -> float:
            nonlocal call_count
            call_count += 1
            return float(params["concentration"]) * 2.5

        mock_create = AsyncMock(
            return_value=self._make_mock_llm_response('{"score": 7.5}')
        )

        def llm_objective(params: dict[str, Any]) -> float:
            with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
                 patch("src.common.llm_client.get_client") as mock_gc:
                mock_client = MagicMock()
                mock_client.chat.completions.create = mock_create
                mock_gc.return_value = mock_client
                # In real code this would call chat_completion; we simulate the
                # parsed result directly to keep the test deterministic.
                return asyncio.get_event_loop().run_until_complete(
                    fake_llm_score(params)
                )

        opt = BayesianOptimizer(
            {"concentration": [0.1, 5.0]}, direction="maximize", seed=42
        )
        result = opt.optimize(llm_objective, n_trials=5)
        assert result.total_trials == 5
        assert result.best_value > 0
        assert call_count == 5

    def test_llm_backed_peak_current_getter(self) -> None:
        """PeakCurrentObjective with a result_getter that calls a mocked LLM."""
        import asyncio

        from src.optimization.bayesian_optimizer import BayesianOptimizer
        from src.optimization.objective_functions import PeakCurrentObjective

        mock_create = AsyncMock(
            return_value=self._make_mock_llm_response("peak=0.12")
        )

        def llm_result_getter(params: dict[str, Any]) -> dict[str, Any]:
            """Simulate calling LLM to interpret raw instrument data."""
            with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
                 patch("src.common.llm_client.get_client") as mock_gc:
                mock_client = MagicMock()
                mock_client.chat.completions.create = mock_create
                mock_gc.return_value = mock_client

                async def _call() -> str:
                    from src.common.llm_client import chat_completion

                    return await chat_completion(
                        [{"role": "user", "content": f"params={params}"}]
                    )

                _text = asyncio.get_event_loop().run_until_complete(_call())
                # Simulate parsing the LLM response into a peak current value.
                voltage = float(params.get("voltage", 1.0))
                return {"peak_current": voltage * 0.06}

        obj = PeakCurrentObjective(result_getter=llm_result_getter)
        opt = BayesianOptimizer({"voltage": [0.5, 2.0]}, direction="maximize", seed=42)
        result = opt.optimize(obj, n_trials=4)
        assert result.best_value > 0
        assert result.total_trials == 4
        assert mock_create.call_count == 4

    def test_llm_failure_in_objective_propagates(self) -> None:
        """When the mocked LLM raises, the optimizer surfaces the error."""
        from src.optimization.bayesian_optimizer import BayesianOptimizer

        mock_create = AsyncMock(side_effect=RuntimeError("LLM quota exceeded"))

        def failing_llm_objective(params: dict[str, Any]) -> float:
            import asyncio

            async def _call() -> str:
                with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
                     patch("src.common.llm_client.get_client") as mock_gc, \
                     patch("src.common.llm_client.asyncio.sleep", new=AsyncMock()):
                    mock_client = MagicMock()
                    mock_client.chat.completions.create = mock_create
                    mock_gc.return_value = mock_client
                    from src.common.llm_client import chat_completion

                    return await chat_completion(
                        [{"role": "user", "content": "score this"}]
                    )

            asyncio.get_event_loop().run_until_complete(_call())
            return 0.0  # unreachable

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, seed=0)
        with pytest.raises(RuntimeError, match="failed after"):
            opt.optimize(failing_llm_objective, n_trials=1)

    def test_multi_objective_with_mocked_llm(self) -> None:
        """Multi-objective optimization where each objective calls a mocked LLM."""
        from src.optimization.bayesian_optimizer import MultiObjectiveBayesianOptimizer

        peak_mock = AsyncMock(
            return_value=self._make_mock_llm_response("peak=0.05")
        )
        snr_mock = AsyncMock(
            return_value=self._make_mock_llm_response("snr=12.3")
        )

        def mocked_multi_objective(params: dict[str, Any]) -> tuple[float, float]:
            x = float(params["x"])
            with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
                 patch("src.common.llm_client.get_client") as mock_gc:
                mock_client = MagicMock()
                mock_client.chat.completions.create = peak_mock
                mock_gc.return_value = mock_client
                peak_val = x * 0.1  # simulated parsed output

            with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
                 patch("src.common.llm_client.get_client") as mock_gc:
                mock_client = MagicMock()
                mock_client.chat.completions.create = snr_mock
                mock_gc.return_value = mock_client
                snr_val = (1.0 - x) * 20  # simulated parsed output

            return (peak_val, snr_val)

        opt = MultiObjectiveBayesianOptimizer(
            {"x": [0.0, 1.0]},
            directions=["maximize", "maximize"],
            seed=42,
        )
        result = opt.optimize(mocked_multi_objective, n_trials=6)
        assert result.total_trials == 6
        assert len(result.pareto_params) >= 1

    def test_optimizer_with_patched_chat_completion_directly(self) -> None:
        """Patch chat_completion at module level for a cleaner mock pattern."""
        import asyncio

        from src.optimization.bayesian_optimizer import BayesianOptimizer

        async def fake_chat_completion(messages: Any, **kwargs: Any) -> str:
            return '{"peak_current": 0.42}'

        def llm_objective(params: dict[str, Any]) -> float:
            with patch(
                "src.common.llm_client.chat_completion",
                new=fake_chat_completion,
            ):
                result_text = asyncio.get_event_loop().run_until_complete(
                    fake_chat_completion(
                        [{"role": "user", "content": f"evaluate {params}"}]
                    )
                )
                import json

                data = json.loads(result_text)
                return float(data["peak_current"])

        opt = BayesianOptimizer({"x": [0.0, 1.0]}, direction="maximize", seed=42)
        result = opt.optimize(llm_objective, n_trials=5)
        # All trials return 0.42 so best_value should be ~0.42
        assert result.best_value == pytest.approx(0.42)
        assert result.total_trials == 5


# ── Package-level __init__ exports ─────────────────────────────────────────


class TestOptimizationExports:
    def test_bayesian_optimizer_exported(self) -> None:
        from src.optimization import BayesianOptimizer

        assert BayesianOptimizer is not None

    def test_multi_objective_optimizer_exported(self) -> None:
        from src.optimization import MultiObjectiveBayesianOptimizer

        assert MultiObjectiveBayesianOptimizer is not None

    def test_peak_current_objective_exported(self) -> None:
        from src.optimization import PeakCurrentObjective

        assert PeakCurrentObjective is not None

    def test_signal_to_noise_objective_exported(self) -> None:
        from src.optimization import SignalToNoiseObjective

        assert SignalToNoiseObjective is not None
