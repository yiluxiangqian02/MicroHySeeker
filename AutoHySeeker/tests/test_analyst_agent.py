"""Tests for DataAnalystAgent."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any
from unittest.mock import patch


class TestAnalystQualityAssessment(unittest.TestCase):
    """Test data quality assessment."""

    def test_full_metrics_high_quality(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {
            "overpotential_mV": 200,
            "onset_potential_V": -0.15,
            "tafel_slope_mV_dec": 68,
        }
        quality = agent._assess_quality(metrics, "/some/path")
        assert quality["score"] >= 0.8
        assert quality["reliable"] is True
        assert len(quality["issues"]) == 0

    def test_missing_metrics_lowers_quality(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {"tafel_slope_mV_dec": 68}
        quality = agent._assess_quality(metrics, "/some/path")
        assert quality["score"] < 1.0
        assert len(quality["issues"]) > 0

    def test_no_metrics_zero_quality(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        quality = agent._assess_quality({}, "")
        assert quality["score"] == 0.0
        assert quality["reliable"] is False

    def test_negative_overpotential_is_issue(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {"overpotential_mV": -50, "onset_potential_V": -0.1}
        quality = agent._assess_quality(metrics, "/path")
        assert any("负值" in issue for issue in quality["issues"])

    def test_very_high_overpotential_is_issue(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {"overpotential_mV": 1500, "onset_potential_V": -0.5}
        quality = agent._assess_quality(metrics, "/path")
        assert any("过大" in issue for issue in quality["issues"])

    def test_high_tafel_slope_is_issue(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {
            "overpotential_mV": 200,
            "onset_potential_V": -0.15,
            "tafel_slope_mV_dec": 250,
        }
        quality = agent._assess_quality(metrics, "/path")
        assert any("Tafel" in issue for issue in quality["issues"])


class TestAnalystComparison(unittest.TestCase):
    """Test metric comparison."""

    def test_compare_improvement(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {"overpotential_mV": 180}
        best = {"metrics": {"overpotential_mV": 200}}
        result = agent._compare_with_best(metrics, best, "overpotential_mV")
        assert result["vs_best"]["comparable"] is True
        assert result["vs_best"]["overpotential_mV_change"] == -20  # improved
        assert result["vs_best"]["is_improvement"] is True

    def test_compare_worse(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {"overpotential_mV": 250}
        best = {"metrics": {"overpotential_mV": 200}}
        result = agent._compare_with_best(metrics, best, "overpotential_mV")
        assert result["vs_best"]["is_improvement"] is False

    def test_compare_missing_metric(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = {}
        best = {"metrics": {"overpotential_mV": 200}}
        result = agent._compare_with_best(metrics, best, "overpotential_mV")
        assert result["vs_best"]["comparable"] is False


class TestAnalystSkillExtraction(unittest.TestCase):
    """Test metric extraction from skill results."""

    def test_extract_lsv_metrics(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        skill_data = [
            {
                "technique": "LSV",
                "analysis": {
                    "onset_potential_V": -0.12,
                    "overpotential_mV": 195.5,
                },
            }
        ]
        metrics = agent._extract_from_skill_result(skill_data)
        assert metrics["onset_potential_V"] == -0.12
        assert metrics["overpotential_mV"] == 195.5

    def test_extract_cv_metrics(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        skill_data = [
            {
                "technique": "CV",
                "analysis": {
                    "peak_current_A": 0.005,
                    "ecsa_cm2": 12.8,
                },
            }
        ]
        metrics = agent._extract_from_skill_result(skill_data)
        assert metrics["peak_current_A"] == 0.005
        assert metrics["ecsa_cm2"] == 12.8

    def test_extract_empty_data(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        metrics = agent._extract_from_skill_result([])
        assert metrics == {}


class TestAnalystFullAnalysis(unittest.TestCase):
    """Test full analyze_experiment flow."""

    def test_analyze_no_data(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        with patch.object(agent, "invoke", side_effect=Exception("no LLM")):
            result = asyncio.run(agent.analyze_experiment(
                run_id="test_001",
                data_path="",
                params={"Fe": 0.5, "Co": 0.3, "Ni": 0.2},
            ))

        assert result["status"] == "analyzed"
        assert result["data_quality"]["reliable"] is False


class TestAnalystRouting(unittest.TestCase):
    """Test routing to analyst."""

    def test_cv_routes_to_analyst(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "analyze cv data"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "data_analyst"


if __name__ == "__main__":
    unittest.main()
