"""Tests for DataAnalysisSkill (formerly DataAnalystAgent).

After the 7→4 agent consolidation, data analysis is a skill of the
Orchestrator.  These tests verify the skill directly.
"""

from __future__ import annotations

import asyncio
import unittest
from typing import Any


class TestAnalysisQualityAssessment(unittest.TestCase):
    """Test data quality assessment."""

    def test_full_metrics_high_quality(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {
            "overpotential_mV": 200,
            "onset_potential_V": -0.15,
            "tafel_slope_mV_dec": 68,
        }
        quality = skill.assess_quality(metrics, "/some/path")
        assert quality["score"] >= 0.8
        assert quality["reliable"] is True
        assert len(quality["issues"]) == 0

    def test_missing_metrics_lowers_quality(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {"tafel_slope_mV_dec": 68}
        quality = skill.assess_quality(metrics, "/some/path")
        assert quality["score"] < 1.0
        assert len(quality["issues"]) > 0

    def test_no_metrics_zero_quality(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        quality = skill.assess_quality({}, "")
        assert quality["score"] == 0.0
        assert quality["reliable"] is False

    def test_negative_overpotential_is_issue(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {"overpotential_mV": -50, "onset_potential_V": -0.1}
        quality = skill.assess_quality(metrics, "/path")
        assert any("\u8d1f\u503c" in issue for issue in quality["issues"])

    def test_very_high_overpotential_is_issue(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {"overpotential_mV": 1500, "onset_potential_V": -0.5}
        quality = skill.assess_quality(metrics, "/path")
        assert any("\u8fc7\u5927" in issue for issue in quality["issues"])

    def test_high_tafel_slope_is_issue(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {
            "overpotential_mV": 200,
            "onset_potential_V": -0.15,
            "tafel_slope_mV_dec": 250,
        }
        quality = skill.assess_quality(metrics, "/path")
        assert any("Tafel" in issue for issue in quality["issues"])


class TestAnalysisComparison(unittest.TestCase):
    """Test metric comparison."""

    def test_compare_improvement(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {"overpotential_mV": 180}
        best = {"metrics": {"overpotential_mV": 200}}
        result = skill.compare_with_best(metrics, best, "overpotential_mV")
        assert result["vs_best"]["comparable"] is True
        assert result["vs_best"]["overpotential_mV_change"] == -20  # improved
        assert result["vs_best"]["is_improvement"] is True

    def test_compare_worse(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {"overpotential_mV": 250}
        best = {"metrics": {"overpotential_mV": 200}}
        result = skill.compare_with_best(metrics, best, "overpotential_mV")
        assert result["vs_best"]["is_improvement"] is False

    def test_compare_missing_metric(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = {}
        best = {"metrics": {"overpotential_mV": 200}}
        result = skill.compare_with_best(metrics, best, "overpotential_mV")
        assert result["vs_best"]["comparable"] is False


class TestAnalysisSkillExtraction(unittest.TestCase):
    """Test metric extraction from skill results."""

    def test_extract_lsv_metrics(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        skill_data = [
            {
                "technique": "LSV",
                "analysis": {
                    "onset_potential_V": -0.12,
                    "overpotential_mV": 195.5,
                },
            }
        ]
        metrics = skill._extract_from_skill_result(skill_data)
        assert metrics["onset_potential_V"] == -0.12
        assert metrics["overpotential_mV"] == 195.5

    def test_extract_cv_metrics(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        skill_data = [
            {
                "technique": "CV",
                "analysis": {
                    "peak_current_A": 0.005,
                    "ecsa_cm2": 12.8,
                },
            }
        ]
        metrics = skill._extract_from_skill_result(skill_data)
        assert metrics["peak_current_A"] == 0.005
        assert metrics["ecsa_cm2"] == 12.8

    def test_extract_empty_data(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        metrics = skill._extract_from_skill_result([])
        assert metrics == {}


class TestAnalysisRouting(unittest.TestCase):
    """Test routing: CV/data keywords now go to orchestrator (not data_analyst)."""

    def test_cv_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "analyze cv data"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"


if __name__ == "__main__":
    unittest.main()
