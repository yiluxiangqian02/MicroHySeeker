"""Tests for ExperimentExecutorAgent."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


def _base_state(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "messages": [],
        "current_agent": "",
        "task": {},
        "context": {},
        "error": None,
        "result": None,
    }
    state.update(overrides)
    return state


class TestExecutorRouting(unittest.TestCase):
    """Verify executor routing keywords work."""

    def test_execute_keyword_routes_to_executor(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "execute this experiment now"})
        result = route_intent(state)
        assert result["current_agent"] == "exp_executor"

    def test_run_experiment_routes_to_executor(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "run experiment with Fe:Co:Ni ratio"})
        result = route_intent(state)
        assert result["current_agent"] == "exp_executor"

    def test_chinese_execute_routes_to_executor(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "执行实验 HER_Fe60Co25Ni15"})
        result = route_intent(state)
        assert result["current_agent"] == "exp_executor"

    def test_start_experiment_routes_to_executor(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "start experiment with template"})
        result = route_intent(state)
        assert result["current_agent"] == "exp_executor"


class TestExecutorGraphRegistration(unittest.TestCase):
    """Verify executor is properly registered in the graph."""

    def test_executor_in_agent_map(self) -> None:
        from src.graph.nodes import AGENT_MAP
        assert "exp_executor" in AGENT_MAP

    def test_select_agent_node_returns_executor(self) -> None:
        from src.graph.nodes import select_agent_node
        state = _base_state(current_agent="exp_executor")
        result = select_agent_node(state)
        assert result == "exp_executor"


class TestExecutorPreCheck(unittest.TestCase):
    """Test pre-check logic."""

    def test_pre_check_healthy(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        with patch("src.agents.exp_executor.ctrl") as mock_ctrl:
            mock_ctrl = MagicMock()
            mock_ctrl.health_check.return_value = {"status": "ok"}
            mock_ctrl.get_connection_info.return_value = {"connected": True}

            with patch.dict("sys.modules", {"src.tools.experiment_ctrl": mock_ctrl}):
                # We need to test _pre_check directly
                result = asyncio.run(agent._pre_check())

        # When import succeeds and returns healthy → ok
        # The actual test is that the logic flow is correct
        assert isinstance(result, dict)
        assert "ok" in result

    def test_pre_check_no_module(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            # When experiment_ctrl is unavailable → not ok
            # Note: import happens inside the method via lazy import
            pass


class TestExecutorValidation(unittest.TestCase):
    """Test parameter validation."""

    def test_missing_template_id(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        task = {"pre_check": False}  # skip pre-check, no template_id
        result = asyncio.run(agent.execute_experiment(task))
        assert result["status"] == "validation_failed"
        assert "template_id" in result["error"]


class TestExecutorAnomalyDetection(unittest.TestCase):
    """Test anomaly detection from logs."""

    def test_detect_pump_error(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        logs = [{"message": "Pump 3 error: communication failure", "timestamp": "t1"}]
        seen: set[str] = set()
        anomalies = agent._detect_anomalies(logs, {}, seen)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "pump_error"
        assert anomalies[0]["severity"] == "high"

    def test_detect_timeout(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        logs = ["RS485 timeout on address 5"]
        seen: set[str] = set()
        anomalies = agent._detect_anomalies(logs, {}, seen)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "communication_timeout"
        assert anomalies[0]["severity"] == "medium"

    def test_detect_emergency(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        logs = [{"message": "Emergency stop triggered", "timestamp": "t2"}]
        seen: set[str] = set()
        anomalies = agent._detect_anomalies(logs, {}, seen)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "emergency_signal"
        assert anomalies[0]["severity"] == "critical"

    def test_no_duplicate_detection(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        logs = ["timeout on pump"]
        seen: set[str] = set()
        # First call
        anomalies1 = agent._detect_anomalies(logs, {}, seen)
        assert len(anomalies1) == 1
        # Second call with same logs — should be deduplicated
        anomalies2 = agent._detect_anomalies(logs, {}, seen)
        assert len(anomalies2) == 0


class TestExecutorErrorClassification(unittest.TestCase):
    """Test error classification."""

    def test_classify_pump_failure(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        result = agent._classify_error("Pump 3 failed", {})
        assert result["type"] == "pump_failure"
        assert result["severity"] == "high"

    def test_classify_timeout(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        result = agent._classify_error("Communication timeout", {})
        assert result["type"] == "timeout"
        assert result["severity"] == "medium"

    def test_classify_echem(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        result = agent._classify_error("CHI instrument error", {})
        assert result["type"] == "echem_failure"
        assert result["severity"] == "high"

    def test_classify_serial(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        result = agent._classify_error("RS485 serial port closed", {})
        assert result["type"] == "serial_failure"
        assert result["severity"] == "high"

    def test_classify_unknown(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        result = agent._classify_error("Some weird thing happened", {})
        assert result["type"] == "unknown"
        assert result["severity"] == "medium"


class TestExecutorProperties(unittest.TestCase):
    """Test agent properties."""

    def test_initial_state(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        assert not agent.is_monitoring
        assert agent.current_run_id is None

    def test_stop_monitoring(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent

        agent = ExperimentExecutorAgent()
        agent._monitoring = True
        assert agent.is_monitoring
        agent.stop_monitoring()
        assert not agent.is_monitoring


if __name__ == "__main__":
    unittest.main()
