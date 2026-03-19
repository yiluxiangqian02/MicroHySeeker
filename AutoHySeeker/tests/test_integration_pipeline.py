"""Integration test: OptimizationLoop end-to-end with mocked MicroHySeeker API.

Runs a 2-round optimization loop:
  round 1: initial_sampling → execute → analyse → evaluate → continue
  round 2: llm_guided → execute → analyse → evaluate → stop (max_rounds=2)

All external calls (LLM, MicroHySeeker API) are mocked.
"""

from __future__ import annotations

import asyncio
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_ctrl() -> MagicMock:
    """Create a mock experiment_ctrl module."""
    mock = MagicMock()
    mock.health_check.return_value = {"status": "ok"}
    mock.get_connection_info.return_value = {"connected": True, "port": "COM3"}
    mock.instantiate_template.return_value = {
        "status": "started",
        "run_id": "mock_run_001",
    }

    # Status polling: first call = running, second call = idle (done)
    poll_count = {"n": 0}

    def _get_status():
        poll_count["n"] += 1
        if poll_count["n"] <= 1:
            return {"state": "running", "current_step": 1, "total_steps": 3}
        return {"state": "idle", "current_step": 3, "total_steps": 3}

    mock.get_experiment_status.side_effect = _get_status
    mock.get_logs.return_value = {"logs": []}
    mock.get_run_detail.return_value = {
        "run_dir": "data/mock_run_001",
        "files": ["cv.csv"],
    }
    return mock


class TestDesignerExecutorIntegration(unittest.TestCase):
    """Test Designer → Executor handoff."""

    def test_design_then_execute_format(self) -> None:
        """Verify Designer output can be consumed by Executor."""
        from src.agents.exp_designer import ExperimentDesignerAgent

        designer = ExperimentDesignerAgent()
        result = asyncio.run(designer.design_experiment(
            history=[],
            target_metric="overpotential_mV",
            optimization_direction="minimize",
        ))

        # Designer output must have these keys for Executor
        assert "params" in result
        assert "step_overrides" in result
        assert "strategy" in result

        # step_overrides must be in correct format
        overrides = result["step_overrides"]
        assert "0" in overrides
        assert "prep_sol_params" in overrides["0"]
        assert "target_concentrations" in overrides["0"]["prep_sol_params"]

        # Params must sum to 1.0
        assert abs(sum(result["params"].values()) - 1.0) < 1e-6


class TestOrchestratorAnomalyDispatch(unittest.TestCase):
    """Test Orchestrator → Diagnostics anomaly handling."""

    def test_critical_anomaly_stops(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        result = asyncio.run(orch.handle_anomaly(
            anomaly={"type": "pump_failure", "severity": "critical"},
            optimization={},
            current_round=3,
        ))
        assert result["action"] == "emergency_stop"
        assert result["need_user"] is True

    def test_high_anomaly_diagnoses(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        result = asyncio.run(orch.handle_anomaly(
            anomaly={"type": "pump_error", "severity": "high"},
            optimization={},
            current_round=3,
        ))
        assert result["action"] == "diagnose"

    def test_low_anomaly_continues(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        result = asyncio.run(orch.handle_anomaly(
            anomaly={"type": "warning", "severity": "low"},
            optimization={},
            current_round=3,
        ))
        assert result["action"] == "log_and_continue"


class TestAnalystOutputForOrchestrator(unittest.TestCase):
    """Test DataAnalysisSkill output can be consumed by Orchestrator."""

    def test_analyst_quality_assessment_format(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        quality = skill.assess_quality(
            {"overpotential_mV": 200, "onset_potential_V": -0.15},
            "/data/path",
        )
        # Orchestrator needs these fields
        assert "score" in quality
        assert "reliable" in quality
        assert isinstance(quality["reliable"], bool)

    def test_analyst_comparison_format(self) -> None:
        from src.skills.data_analysis_skill import DataAnalysisSkill

        skill = DataAnalysisSkill()
        result = skill.compare_with_best(
            {"overpotential_mV": 180},
            {"metrics": {"overpotential_mV": 200}},
            "overpotential_mV",
        )
        assert "vs_best" in result
        assert result["vs_best"]["comparable"] is True


class TestOrchestratorBestResult(unittest.TestCase):
    """Test Orchestrator best result tracking across experiments."""

    def test_update_best_minimize(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        history = [
            {"params": {"Fe": 0.3}, "metrics": {"ovp": 250}, "data_quality": {"reliable": True}},
            {"params": {"Fe": 0.5}, "metrics": {"ovp": 180}, "data_quality": {"reliable": True}},
            {"params": {"Fe": 0.7}, "metrics": {"ovp": 220}, "data_quality": {"reliable": True}},
        ]
        optimization = {"target_metric": "ovp", "optimization_direction": "minimize"}
        best = orch.update_best_result(history, optimization)
        assert best is not None
        assert best["metrics"]["ovp"] == 180


class TestKnowledgeArchiveIntegration(unittest.TestCase):
    """Test knowledge archival after experiment completion (now via skill)."""

    def test_archive_and_retrieve(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()

        # Archive 3 experiments
        for i, (fe, ovp) in enumerate([(0.3, 250), (0.5, 200), (0.6, 180)]):
            asyncio.run(skill.archive_experiment(
                run_id=f"exp_{i}",
                params={"Fe": fe, "Co": 0.7 - fe, "Ni": 0.3},
                metrics={"overpotential_mV": ovp},
                round_num=i,
            ))

        # Retrieve best
        best = skill.get_best_experiments("overpotential_mV", "minimize", top_k=1)
        assert best[0]["metrics"]["overpotential_mV"] == 180

        # Search
        results = skill._search_experiments("Fe overpotential", ["Fe", "Co", "Ni"], 5)
        assert len(results) == 3


class TestFullAgentPipeline(unittest.TestCase):
    """Test the full Design→Execute→Analyze pipeline with mocks."""

    def test_design_to_analysis(self) -> None:
        """Full pipeline: design → executor format check → analyst format check."""
        from src.agents.exp_designer import ExperimentDesignerAgent
        from src.skills.data_analysis_skill import DataAnalysisSkill
        from src.agents.orchestrator import OrchestratorAgent

        # Step 1: Design
        designer = ExperimentDesignerAgent()
        design = asyncio.run(designer.design_experiment(history=[]))

        # Verify design output format
        assert "params" in design
        assert "step_overrides" in design

        # Step 2: (Skip actual execution, simulate result)
        exec_result = {
            "status": "completed",
            "run_id": "test_pipeline_001",
            "data_path": "data/test/",
        }

        # Step 3: DataAnalysisSkill quality check on mock metrics
        skill = DataAnalysisSkill()
        mock_metrics = {"overpotential_mV": 195, "onset_potential_V": -0.13}
        quality = skill.assess_quality(mock_metrics, exec_result["data_path"])
        assert quality["reliable"] is True

        # Step 4: Orchestrator evaluates
        orch = OrchestratorAgent()
        history_entry = {
            "params": design["params"],
            "metrics": mock_metrics,
            "data_quality": quality,
            "round": 0,
            "run_id": exec_result["run_id"],
        }
        best = orch.update_best_result(
            [history_entry],
            {"target_metric": "overpotential_mV", "optimization_direction": "minimize"},
        )
        assert best is not None
        assert best["metrics"]["overpotential_mV"] == 195


class TestRunOptimizationBlockingFailures(unittest.TestCase):
    """Blocking setup failures should stop the loop with a clear status."""

    def test_pre_check_failure_returns_blocked(self) -> None:
        from src.run_optimization import run_optimization

        async def fake_execute_experiment(_self: Any, _task: dict[str, Any]) -> dict[str, Any]:
            return {
                "status": "pre_check_failed",
                "error": "RS485 not connected",
            }

        with patch(
            "src.agents.exp_executor.ExperimentExecutorAgent.execute_experiment",
            new=fake_execute_experiment,
        ):
            result = asyncio.run(
                run_optimization(
                    goal="integration smoke",
                    max_rounds=1,
                    dry_run=False,
                )
            )

        assert result["status"] == "blocked"
        assert result["final_decision"] == "blocked"
        assert result["history_count"] == 1


if __name__ == "__main__":
    unittest.main()
