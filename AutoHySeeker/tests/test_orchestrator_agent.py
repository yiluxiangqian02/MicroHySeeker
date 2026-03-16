"""Tests for the OrchestratorAgent and OptimizationLoop.

All LLM and hardware calls are mocked.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# ── OrchestratorAgent tests ────────────────────────────────────────────────────

class TestOrchestratorAgent:
    """Test core decision logic of OrchestratorAgent."""

    def test_max_rounds_forces_stop(self) -> None:
        """When current_round >= max_rounds, action must be 'stop'."""
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        optimization = {
            "goal": "minimize overpotential",
            "target_metric": "overpotential_mV",
            "optimization_direction": "minimize",
            "max_rounds": 5,
            "search_space": {},
        }
        decision = run_async(orch.evaluate_and_decide(
            optimization=optimization,
            experiment_history=[{"round": i, "params": {}, "metrics": {"overpotential_mV": 200 - i * 10}} for i in range(1, 6)],
            current_result={"metrics": {"overpotential_mV": 150}},
            best_result={"metrics": {"overpotential_mV": 150}, "params": {}, "round": 5},
            current_round=5,
        ))
        assert decision["action"] == "stop"
        assert decision["confidence"] == 1.0

    def test_parse_decision_valid_json(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        content = '```json\n{"action": "continue", "reason": "improving", "confidence": 0.8}\n```'
        result = orch._parse_decision(content)
        assert result["action"] == "continue"
        assert result["confidence"] == 0.8

    def test_parse_decision_fallback_text(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        content = "建议停止实验，目标已达成"
        result = orch._parse_decision(content)
        assert result["action"] == "stop"

    def test_parse_decision_retry_detection(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        content = "数据不可靠，建议重试上一组参数"
        result = orch._parse_decision(content)
        assert result["action"] == "retry"

    def test_parse_decision_unknown_defaults_continue(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        content = "看起来还不错，请继续进行下一轮"
        result = orch._parse_decision(content)
        assert result["action"] == "continue"

    def test_handle_anomaly_critical(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        result = run_async(orch.handle_anomaly(
            anomaly={"type": "pump_failure", "severity": "critical"},
            optimization={"goal": "test"},
            current_round=3,
        ))
        assert result["action"] == "emergency_stop"
        assert result["need_user"] is True

    def test_handle_anomaly_high(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        result = run_async(orch.handle_anomaly(
            anomaly={"type": "pump_timeout", "severity": "high"},
            optimization={"goal": "test"},
            current_round=3,
        ))
        assert result["action"] == "diagnose"

    def test_handle_anomaly_low(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        result = run_async(orch.handle_anomaly(
            anomaly={"type": "minor_vibration", "severity": "low"},
            optimization={"goal": "test"},
            current_round=3,
        ))
        assert result["action"] == "log_and_continue"

    def test_update_best_result_minimize(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        history = [
            {"round": 1, "params": {"Fe": 0.3}, "metrics": {"overpotential_mV": 250}, "data_quality": {"reliable": True}},
            {"round": 2, "params": {"Fe": 0.5}, "metrics": {"overpotential_mV": 180}, "data_quality": {"reliable": True}},
            {"round": 3, "params": {"Fe": 0.4}, "metrics": {"overpotential_mV": 210}, "data_quality": {"reliable": True}},
        ]
        optimization = {"target_metric": "overpotential_mV", "optimization_direction": "minimize"}
        best = orch.update_best_result(history, optimization)
        assert best is not None
        assert best["metrics"]["overpotential_mV"] == 180
        assert best["round"] == 2

    def test_update_best_result_maximize(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        history = [
            {"round": 1, "params": {}, "metrics": {"current_density": 5.0}, "data_quality": {"reliable": True}},
            {"round": 2, "params": {}, "metrics": {"current_density": 15.0}, "data_quality": {"reliable": True}},
        ]
        optimization = {"target_metric": "current_density", "optimization_direction": "maximize"}
        best = orch.update_best_result(history, optimization)
        assert best["metrics"]["current_density"] == 15.0

    def test_update_best_result_skips_unreliable(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        history = [
            {"round": 1, "params": {}, "metrics": {"op": 100}, "data_quality": {"reliable": False}},
            {"round": 2, "params": {}, "metrics": {"op": 200}, "data_quality": {"reliable": True}},
        ]
        optimization = {"target_metric": "op", "optimization_direction": "minimize"}
        best = orch.update_best_result(history, optimization)
        assert best["metrics"]["op"] == 200  # 100 was unreliable


# ── OptimizationLoop tests ─────────────────────────────────────────────────────

class TestOptimizationLoop:
    """Test the optimization loop lifecycle."""

    def test_stop_flag(self) -> None:
        from src.graph.optimization_loop import OptimizationLoop

        loop = OptimizationLoop()
        assert not loop.is_running
        loop.stop()  # should be safe when not running

    def test_make_initial_optimization(self) -> None:
        from src.graph.state import make_initial_optimization

        opt = make_initial_optimization(
            goal="minimize HER overpotential",
            target_metric="overpotential_mV",
            optimization_direction="minimize",
            search_space={"Fe": {"min": 0.05, "max": 0.8}},
            max_rounds=10,
        )
        assert opt["goal"] == "minimize HER overpotential"
        assert opt["max_rounds"] == 10
        assert opt["status"] == "idle"
        assert "Fe" in opt["search_space"]


# ── Route intent includes orchestrator ─────────────────────────────────────────

class TestOrchestratorRouting:
    def test_optimization_keyword_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [],
            "current_agent": "",
            "task": {"intent": "开始闭环优化配比"},
            "context": {},
            "error": None,
            "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_loop_keyword_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [],
            "current_agent": "",
            "task": {"prompt": "start optimization loop for closed-loop experiment"},
            "context": {},
            "error": None,
            "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_optimize_routes_to_designer_not_orchestrator(self) -> None:
        """'optimize' alone should go to designer, not orchestrator."""
        from src.graph.nodes import route_intent

        state = {
            "messages": [],
            "current_agent": "",
            "task": {"intent": "optimize parameters with optuna"},
            "context": {},
            "error": None,
            "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "exp_designer"

    def test_orchestrator_in_agent_map(self) -> None:
        from src.graph.nodes import AGENT_MAP

        assert "orchestrator" in AGENT_MAP

    def test_run_orchestrator_node(self) -> None:
        from src.graph.nodes import run_orchestrator

        state = {
            "messages": [],
            "current_agent": "orchestrator",
            "task": {"type": "evaluate_and_decide"},
            "context": {},
            "error": None,
            "result": None,
        }
        with patch("src.agents.base.chat_completion",
                    new=AsyncMock(return_value='{"action": "continue"}')), \
             patch("src.common.llm_client.OPENAI_API_KEY", "test-key"):
            result = run_async(run_orchestrator(state))

        assert result["error"] is None
        assert result["result"]["agent"] == "orchestrator"
