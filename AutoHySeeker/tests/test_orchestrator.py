"""Tests for orchestrator graph routing logic (nodes.py + orchestrator.py).

All LLM calls are mocked via ``unittest.mock.patch``.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


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


# ── route_intent ───────────────────────────────────────────────────────────────

class TestRouteIntent:
    def test_cv_keyword_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"intent": "analyze cv data"})
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_eis_keyword_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"goal": "analyze EIS signal"})
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_design_keyword_routes_to_exp_designer(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"prompt": "design next experiment"})
        result = route_intent(state)
        assert result["current_agent"] == "exp_designer"

    def test_optimize_keyword_routes_to_exp_designer(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"intent": "optimize parameters with optuna"})
        result = route_intent(state)
        assert result["current_agent"] == "exp_designer"

    def test_failure_keyword_routes_to_diagnostics(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"query": "diagnose failure"})
        result = route_intent(state)
        assert result["current_agent"] == "diagnostics"

    def test_anomaly_keyword_routes_to_diagnostics(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"intent": "detect anomaly in run"})
        result = route_intent(state)
        assert result["current_agent"] == "diagnostics"

    def test_knowledge_keyword_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"prompt": "search knowledge base"})
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_literature_keyword_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"query": "find paper on HER"})
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_unknown_task_defaults_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"prompt": "run the experiment"})
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_explicit_current_agent_overrides_inference(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(
            task={"intent": "analyze cv"},
            current_agent="orchestrator",
        )
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_route_intent_sets_routed_by_context(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={"intent": "analyze cv"})
        result = route_intent(state)
        assert result["context"]["routed_by"] == "route_intent"

    def test_route_intent_preserves_existing_context(self) -> None:
        from src.graph.nodes import route_intent
        state = _base_state(task={}, context={"my_key": "my_value"})
        result = route_intent(state)
        assert result["context"]["my_key"] == "my_value"


# ── select_agent_node ──────────────────────────────────────────────────────────

class TestSelectAgentNode:
    def test_valid_agent_names_returned_as_is(self) -> None:
        from src.graph.nodes import select_agent_node
        for name in ("orchestrator", "exp_designer", "exp_executor", "diagnostics"):
            state = _base_state(current_agent=name)
            assert select_agent_node(state) == name

    def test_alias_agent_resolves_to_orchestrator(self) -> None:
        from src.graph.nodes import select_agent_node
        for alias in ("data_analyst", "knowledge_mgr", "exp_supervisor"):
            state = _base_state(current_agent=alias)
            assert select_agent_node(state) == "orchestrator"

    def test_unknown_agent_defaults_to_orchestrator(self) -> None:
        from src.graph.nodes import select_agent_node
        state = _base_state(current_agent="nonexistent_agent")
        assert select_agent_node(state) == "orchestrator"

    def test_empty_agent_defaults_to_orchestrator(self) -> None:
        from src.graph.nodes import select_agent_node
        state = _base_state(current_agent="")
        assert select_agent_node(state) == "orchestrator"


# ── format_response ────────────────────────────────────────────────────────────

class TestFormatResponse:
    def test_successful_result_has_ok_true(self) -> None:
        from src.graph.nodes import format_response
        state = _base_state(
            current_agent="orchestrator",
            result={"agent": "orchestrator", "content": "found peaks"},
            error=None,
        )
        result = format_response(state)
        assert result["result"]["ok"] is True

    def test_error_state_has_ok_false(self) -> None:
        from src.graph.nodes import format_response
        state = _base_state(
            current_agent="orchestrator",
            result={"agent": "orchestrator", "content": ""},
            error="something went wrong",
        )
        result = format_response(state)
        assert result["result"]["ok"] is False
        assert result["result"]["error"] == "something went wrong"

    def test_missing_result_gets_default_agent(self) -> None:
        from src.graph.nodes import format_response
        state = _base_state(current_agent="diagnostics", result=None, error=None)
        result = format_response(state)
        assert result["result"]["agent"] == "diagnostics"


# ── run_* node functions ───────────────────────────────────────────────────────

class TestAgentRunnerNodes:
    """Test that run_* coroutines call _invoke_agent and return result/error keys."""

    def test_run_orchestrator_success(self) -> None:
        from src.graph.nodes import run_orchestrator
        state = _base_state(task={"intent": "analyze"}, context={})
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="peaks found")), \
             patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
            result = run_async(run_orchestrator(state))
        assert "result" in result
        assert "error" in result
        assert result["error"] is None
        assert result["result"]["agent"] == "orchestrator"

    def test_run_diagnostics_success(self) -> None:
        from src.graph.nodes import run_diagnostics
        state = _base_state(task={"error": "voltage spike"})
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="no issues")), \
             patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
            result = run_async(run_diagnostics(state))
        assert result["error"] is None
        assert result["result"]["agent"] == "diagnostics"

    def test_run_exp_designer_success(self) -> None:
        from src.graph.nodes import run_exp_designer
        state = _base_state(task={"goal": "design experiment"})
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="plan")), \
             patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
            result = run_async(run_exp_designer(state))
        assert result["error"] is None
        assert result["result"]["agent"] == "exp_designer"

    def test_run_exp_executor_success(self) -> None:
        from src.graph.nodes import run_exp_executor
        state = _base_state(task={"action": "execute"})
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="executed")), \
             patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
            result = run_async(run_exp_executor(state))
        assert result["error"] is None
        assert result["result"]["agent"] == "experiment_executor"

    def test_run_agent_captures_exception(self) -> None:
        """If agent.invoke raises, the runner should return error dict (not raise)."""
        from src.graph.nodes import run_diagnostics
        state = _base_state(task={})
        # Mock chat_completion to raise (simulates LLM failure)
        with patch("src.agents.base.chat_completion",
                   new=AsyncMock(side_effect=RuntimeError("LLM down"))), \
             patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
            result = run_async(run_diagnostics(state))
        assert result["error"] is not None


# ── build_supervisor_graph / _FallbackGraph ────────────────────────────────────

class TestBuildSupervisorGraph:
    def test_build_supervisor_graph_returns_something(self) -> None:
        from src.graph.orchestrator import build_supervisor_graph
        g = build_supervisor_graph()
        assert g is not None

    def test_get_supervisor_graph_cached(self) -> None:
        from src.graph import orchestrator
        orchestrator._SUPERVISOR_GRAPH = None  # reset cache
        g1 = orchestrator.get_supervisor_graph()
        g2 = orchestrator.get_supervisor_graph()
        assert g1 is g2

    def test_fallback_graph_invoke_routes_and_calls_agent(self) -> None:
        """_FallbackGraph should route and call the correct agent (mocked LLM)."""
        from src.graph.orchestrator import _FallbackGraph

        fallback = _FallbackGraph()
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="analysis ok")), \
             patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
            state = _base_state(task={"intent": "analyze cv data"})
            result = run_async(fallback.ainvoke(state))

        assert result is not None
        # format_response wraps result
        assert "result" in result


# ── full orchestrator ainvoke (mocked LLM) ─────────────────────────────────────

class TestOrchestratorAinvoke:
    def test_ainvoke_end_to_end_orchestrator(self) -> None:
        """End-to-end invoke through graph with mocked LLM call."""
        from src.graph.orchestrator import build_supervisor_graph

        fake_llm_response = "Peak current: 0.05 A"

        with patch("src.common.llm_client.chat_completion", new=AsyncMock(return_value=fake_llm_response)):
            # Need to also patch OPENAI_API_KEY
            with patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
                g = build_supervisor_graph()
                state = _base_state(task={"intent": "analyze cv data from run_001"})
                result = run_async(g.ainvoke(state))

        assert result is not None

    def test_ainvoke_returns_ok_field_in_result(self) -> None:
        """The format_response node should inject ok=True when no error."""
        from src.graph.orchestrator import build_supervisor_graph

        with patch("src.common.llm_client.chat_completion", new=AsyncMock(return_value="analysis done")):
            with patch("src.common.llm_client.app_config.OPENAI_API_KEY", "test-key"):
                g = build_supervisor_graph()
                state = _base_state(task={"intent": "analyze cv"})
                out = run_async(g.ainvoke(state))

        result_payload = out.get("result") or {}
        assert result_payload.get("ok") is True
