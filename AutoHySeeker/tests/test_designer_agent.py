"""Tests for ExperimentDesignerAgent."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any
from unittest.mock import patch


class TestDesignerInitialDesign(unittest.TestCase):
    """Test initial sampling strategy."""

    def test_initial_design_equal_split(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        params = agent._initial_design(
            ["Fe", "Co", "Ni"],
            {"Fe": {"min": 0.05, "max": 0.9},
             "Co": {"min": 0.05, "max": 0.9},
             "Ni": {"min": 0.05, "max": 0.9}},
        )
        assert len(params) == 3
        assert abs(sum(params.values()) - 1.0) < 1e-6
        assert abs(params["Fe"] - 0.3333) < 0.01

    def test_initial_design_two_elements(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        params = agent._initial_design(
            ["Fe", "Co"],
            {"Fe": {"min": 0.1, "max": 0.9},
             "Co": {"min": 0.1, "max": 0.9}},
        )
        assert len(params) == 2
        assert abs(sum(params.values()) - 1.0) < 1e-6


class TestDesignerConstraints(unittest.TestCase):
    """Test constraint application."""

    def test_normalize_to_sum_one(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        space = {
            "Fe": {"min": 0.05, "max": 0.9},
            "Co": {"min": 0.05, "max": 0.9},
            "Ni": {"min": 0.05, "max": 0.9},
        }
        params = {"Fe": 0.6, "Co": 0.3, "Ni": 0.3}  # sum = 1.2
        result = agent._apply_constraints(params, ["Fe", "Co", "Ni"], space)
        assert abs(sum(result.values()) - 1.0) < 1e-6

    def test_clamp_to_bounds(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        space = {
            "Fe": {"min": 0.1, "max": 0.5},
            "Co": {"min": 0.1, "max": 0.5},
        }
        params = {"Fe": 0.01, "Co": 0.99}  # out of bounds
        result = agent._apply_constraints(params, ["Fe", "Co"], space)
        # After clamping: Fe=0.1, Co=0.5, then normalized to sum=1
        assert result["Fe"] >= 0.1
        assert result["Co"] <= 0.9


class TestDesignerStepOverrides(unittest.TestCase):
    """Test step_overrides formatting."""

    def test_format_step_overrides(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        params = {"Fe": 0.5, "Co": 0.3, "Ni": 0.2}
        result = agent._format_step_overrides(params, 1000)
        assert "0" in result
        assert result["0"]["prep_sol_params"]["target_concentrations"] == params
        assert result["0"]["prep_sol_params"]["total_volume_ul"] == 1000


class TestDesignerFullDesign(unittest.TestCase):
    """Test the full design_experiment flow."""

    def test_design_no_history(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        result = asyncio.run(agent.design_experiment(
            history=[],
            target_metric="overpotential_mV",
            optimization_direction="minimize",
        ))
        assert result["strategy"] == "initial_sampling"
        assert "params" in result
        assert "step_overrides" in result
        assert abs(sum(result["params"].values()) - 1.0) < 1e-6

    def test_design_few_history_uses_llm(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        history = [
            {"params": {"Fe": 0.33, "Co": 0.33, "Ni": 0.34},
             "metrics": {"overpotential_mV": 250}},
            {"params": {"Fe": 0.5, "Co": 0.25, "Ni": 0.25},
             "metrics": {"overpotential_mV": 220}},
        ]

        # Mock LLM to avoid network call
        with patch.object(agent, "invoke", side_effect=Exception("no LLM")):
            result = asyncio.run(agent.design_experiment(
                history=history,
                target_metric="overpotential_mV",
                optimization_direction="minimize",
            ))

        assert result["strategy"] == "llm_guided"
        assert abs(sum(result["params"].values()) - 1.0) < 1e-6


class TestDesignerLLMParsing(unittest.TestCase):
    """Test LLM response parsing."""

    def test_parse_json_params(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        content = '```json\n{"params": {"Fe": 0.4, "Co": 0.35, "Ni": 0.25}}\n```'
        space = {"Fe": {"min": 0.05, "max": 0.9}, "Co": {"min": 0.05, "max": 0.9}, "Ni": {"min": 0.05, "max": 0.9}}
        result = agent._parse_params_from_llm(content, ["Co", "Fe", "Ni"], space)
        assert "Fe" in result
        assert "Co" in result
        assert "Ni" in result

    def test_parse_bad_json_fallback(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        content = "I think Fe should be higher"
        space = {"Fe": {"min": 0.05, "max": 0.9}, "Co": {"min": 0.05, "max": 0.9}, "Ni": {"min": 0.05, "max": 0.9}}
        result = agent._parse_params_from_llm(content, ["Co", "Fe", "Ni"], space)
        # Should fall back to center point
        assert len(result) == 3
        assert abs(sum(result.values()) - 1.0) < 1e-6


class TestDesignerImprovement(unittest.TestCase):
    """Test improvement estimation."""

    def test_estimate_minimize(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        history = [
            {"metrics": {"ovp": 300}},
            {"metrics": {"ovp": 250}},
            {"metrics": {"ovp": 200}},
        ]
        result = agent._estimate_improvement(
            {"Fe": 0.5}, history, "ovp", "minimize",
        )
        assert isinstance(result, float)

    def test_estimate_no_values(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        result = agent._estimate_improvement(
            {"Fe": 0.5}, [], "ovp", "minimize",
        )
        assert result == 0.0


class TestDesignerRouting(unittest.TestCase):
    """Test routing to designer agent."""

    def test_optimize_routes_to_designer(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "optimize parameters with optuna"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "exp_designer"

    def test_design_routes_to_designer(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "design next experiment"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "exp_designer"


if __name__ == "__main__":
    unittest.main()
