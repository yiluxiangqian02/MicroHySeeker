"""Tests for the OrchestratorAgent and OptimizationLoop.

All LLM and hardware calls are mocked.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


# ── OrchestratorAgent tests ────────────────────────────────────────────────────

class TestOrchestratorAgent:
    """Test core decision logic of OrchestratorAgent."""

    def test_max_rounds_forces_stop(self) -> None:
        """When current_round >= max_rounds, action must be 'stop'."""
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        orch._work_mode = "full_auto"
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
        assert result["action"] in ("diagnose", "pause_for_human")

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

    def test_semi_auto_first_round_requires_approval(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        orch._work_mode = "semi_auto"

        with patch.object(orch, "invoke", new=AsyncMock(return_value={"content": '{"action": "continue"}'})):
            result = run_async(
                orch.evaluate_and_decide(
                    optimization={
                        "goal": "test",
                        "target_metric": "overpotential_mV",
                        "optimization_direction": "minimize",
                        "max_rounds": 10,
                        "search_space": {},
                    },
                    experiment_history=[],
                    current_result={"metrics": {"overpotential_mV": 250}},
                    best_result=None,
                    current_round=1,
                )
            )

        assert result["action"] == "pause_for_human"
        assert result["pending_approval"]["decision"]["decision_type"] == "initial_round_confirmation"

    def test_manual_mode_always_requires_approval(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        orch._work_mode = "manual"

        with patch.object(orch, "invoke", new=AsyncMock(return_value={"content": '{"action": "continue"}'})):
            result = run_async(
                orch.evaluate_and_decide(
                    optimization={
                        "goal": "test",
                        "target_metric": "overpotential_mV",
                        "optimization_direction": "minimize",
                        "max_rounds": 10,
                        "search_space": {},
                    },
                    experiment_history=[{"metrics": {"overpotential_mV": 250}}],
                    current_result={"metrics": {"overpotential_mV": 240}},
                    best_result={"metrics": {"overpotential_mV": 240}},
                    current_round=2,
                )
            )

        assert result["action"] == "pause_for_human"
        assert result["pending_approval"]["decision"]["decision_type"] == "manual_round_confirmation"

    def test_request_and_respond_human_approval(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        request = run_async(
            orch.request_human_approval(
                decision={"action": "stop"},
                context={"current_round": 3},
            )
        )

        approval_id = request["approval_id"]
        pending = orch.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["approval_id"] == approval_id

        resolved = orch.respond_human_approval(approval_id, approved=True, feedback="ok")
        assert resolved["found"] is True
        assert resolved["approval"]["approved"] is True
        assert orch.get_pending_approvals() == []

    def test_retrieve_knowledge_uses_query_skill(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        with patch.object(
            orch._knowledge_query_skill,
            "search",
            new=AsyncMock(return_value=[{"partition": "experiments"}]),
        ):
            result = run_async(orch.retrieve_knowledge("Fe-Co-Ni", search_type="both", top_k=3))

        assert result["status"] == "retrieved"
        assert result["results"][0]["partition"] == "experiments"

    def test_update_ml_training_data_returns_fit_status(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orch = OrchestratorAgent()
        result = run_async(
            orch.update_ml_training_data(
                {
                    "history": [
                        {
                            "params": {"Fe": 0.3, "Co": 0.5, "Ni": 0.2},
                            "metrics": {"overpotential_mV": 200},
                        }
                    ]
                }
            )
        )
        assert result["ready"] is False


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

    def test_pause_for_human_waits_for_approval_and_resumes(self) -> None:
        from src.agents.orchestrator import OrchestratorAgent
        from src.graph.optimization_loop import OptimizationLoop

        async def scenario() -> dict[str, Any]:
            loop = OptimizationLoop()
            orchestrator = OrchestratorAgent()
            loop._orchestrator = orchestrator
            approval_id: dict[str, str] = {}

            async def fake_decide(**_: Any) -> dict[str, Any]:
                request = await orchestrator.request_human_approval(
                    decision={"action": "continue", "decision_type": "initial_round_confirmation"},
                    context={"current_round": 1},
                )
                approval_id["value"] = request["approval_id"]
                return {
                    "action": "pause_for_human",
                    "reason": "initial_round_confirmation",
                    "pending_approval": request["pending_approval"],
                    "original_decision": {"action": "continue"},
                }

            async def approve_later() -> None:
                while "value" not in approval_id:
                    await asyncio.sleep(0.01)
                orchestrator.respond_human_approval(approval_id["value"], approved=True, feedback="ok")

            with patch.object(
                loop,
                "_step_design",
                new=AsyncMock(return_value={"params": {"Fe": 0.5}, "step_overrides": {}, "template_id": ""}),
            ), patch.object(
                loop,
                "_step_execute",
                new=AsyncMock(return_value={"status": "completed", "run_id": "run_001", "data_path": ""}),
            ), patch.object(
                loop,
                "_step_analyse",
                new=AsyncMock(return_value={"metrics": {"overpotential_mV": 180}, "data_quality": {"reliable": True}}),
            ), patch.object(
                orchestrator,
                "evaluate_and_decide",
                new=AsyncMock(side_effect=fake_decide),
            ):
                approval_task = asyncio.create_task(approve_later())
                result = await loop.run(
                    goal="test",
                    target_metric="overpotential_mV",
                    search_space={"Fe": {"min": 0.1, "max": 0.9}},
                    max_rounds=1,
                )
                await approval_task

            assert result["status"] == "completed"
            assert loop.current_state is not None
            assert loop.current_state["last_approval"]["approved"] is True
            assert loop.current_state.get("pending_approval") is None
            return result

        result = run_async(scenario())
        assert result["current_round"] == 1


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
             patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
            result = run_async(run_orchestrator(state))

        assert result["error"] is None
        assert result["result"]["agent"] == "orchestrator"
