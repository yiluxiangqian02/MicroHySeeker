"""Tests for the supervisor orchestrator — routing logic, node functions, graph build."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


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


# ── route_intent / _infer_agent tests ─────────────────────────────────────────

class TestRouteIntent:
    def test_routes_cv_to_data_analyst(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "analyse CV data"})
        out = route_intent(state)
        assert out["current_agent"] == "data_analyst"

    def test_routes_eis_to_data_analyst(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"goal": "EIS signal interpretation"})
        out = route_intent(state)
        assert out["current_agent"] == "data_analyst"

    def test_routes_design_to_exp_designer(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "design next experiment"})
        out = route_intent(state)
        assert out["current_agent"] == "exp_designer"

    def test_routes_optimize_to_exp_designer(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"goal": "optimize HER activity"})
        out = route_intent(state)
        assert out["current_agent"] == "exp_designer"

    def test_routes_error_to_diagnostics(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "diagnose pump error"})
        out = route_intent(state)
        assert out["current_agent"] == "diagnostics"

    def test_routes_failure_to_diagnostics(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"prompt": "investigate failure in run 42"})
        out = route_intent(state)
        assert out["current_agent"] == "diagnostics"

    def test_routes_knowledge_to_knowledge_mgr(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"query": "find relevant literature"})
        out = route_intent(state)
        assert out["current_agent"] == "knowledge_mgr"

    def test_routes_paper_to_knowledge_mgr(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "paper summary"})
        out = route_intent(state)
        assert out["current_agent"] == "knowledge_mgr"

    def test_default_routes_to_exp_supervisor(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "run the next step"})
        out = route_intent(state)
        assert out["current_agent"] == "exp_supervisor"

    def test_explicit_agent_override(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(
            task={"intent": "analyse CV data"},
            current_agent="diagnostics",
        )
        out = route_intent(state)
        assert out["current_agent"] == "diagnostics"

    def test_context_has_route_metadata(self) -> None:
        from src.graph.nodes import route_intent

        state = _base_state(task={"intent": "analyse data"})
        out = route_intent(state)
        assert out["context"]["routed_by"] == "route_intent"
        assert "route_reason" in out["context"]


# ── select_agent_node tests ───────────────────────────────────────────────────

class TestSelectAgentNode:
    def test_returns_known_agent(self) -> None:
        from src.graph.nodes import select_agent_node

        state = _base_state(current_agent="data_analyst")
        assert select_agent_node(state) == "data_analyst"

    def test_unknown_agent_falls_back(self) -> None:
        from src.graph.nodes import select_agent_node

        state = _base_state(current_agent="nonexistent")
        assert select_agent_node(state) == "exp_supervisor"

    def test_empty_agent_falls_back(self) -> None:
        from src.graph.nodes import select_agent_node

        state = _base_state(current_agent="")
        assert select_agent_node(state) == "exp_supervisor"


# ── format_response tests ─────────────────────────────────────────────────────

class TestFormatResponse:
    def test_ok_true_when_no_error(self) -> None:
        from src.graph.nodes import format_response

        state = _base_state(
            result={"content": "hello"},
            current_agent="data_analyst",
            error=None,
        )
        out = format_response(state)
        assert out["result"]["ok"] is True
        assert out["result"]["agent"] == "data_analyst"

    def test_ok_false_when_error(self) -> None:
        from src.graph.nodes import format_response

        state = _base_state(
            result={"content": ""},
            current_agent="data_analyst",
            error="something broke",
        )
        out = format_response(state)
        assert out["result"]["ok"] is False
        assert out["result"]["error"] == "something broke"

    def test_handles_none_result(self) -> None:
        from src.graph.nodes import format_response

        state = _base_state(result=None, current_agent="exp_supervisor")
        out = format_response(state)
        assert out["result"]["agent"] == "exp_supervisor"


# ── agent node invocation (mocked LLM) ───────────────────────────────────────

class TestAgentNodes:
    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_run_data_analyst(self, mock_llm: AsyncMock) -> None:
        from src.graph.nodes import run_data_analyst

        mock_llm.return_value = "CV analysis complete"
        state = _base_state(task={"intent": "analyse CV"})
        out = run_async(run_data_analyst(state))
        assert out["error"] is None
        assert out["result"]["agent"] == "data_analyst"
        assert "CV analysis complete" in out["result"]["content"]

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_run_exp_designer(self, mock_llm: AsyncMock) -> None:
        from src.graph.nodes import run_exp_designer

        mock_llm.return_value = "Proposed experiment plan"
        state = _base_state(task={"intent": "design experiment"})
        out = run_async(run_exp_designer(state))
        assert out["error"] is None
        assert out["result"]["agent"] == "exp_designer"

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_run_exp_supervisor(self, mock_llm: AsyncMock) -> None:
        from src.graph.nodes import run_exp_supervisor

        mock_llm.return_value = "Execution sequence ready"
        state = _base_state(task={"intent": "run next"})
        out = run_async(run_exp_supervisor(state))
        assert out["error"] is None
        assert out["result"]["agent"] == "exp_supervisor"

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_run_diagnostics(self, mock_llm: AsyncMock) -> None:
        from src.graph.nodes import run_diagnostics

        mock_llm.return_value = "Error diagnosed"
        state = _base_state(task={"intent": "diagnose error"})
        out = run_async(run_diagnostics(state))
        assert out["error"] is None
        assert out["result"]["agent"] == "diagnostics"

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_run_knowledge_mgr(self, mock_llm: AsyncMock) -> None:
        from src.graph.nodes import run_knowledge_mgr

        mock_llm.return_value = "Literature summary"
        state = _base_state(task={"query": "HER literature"})
        out = run_async(run_knowledge_mgr(state))
        assert out["error"] is None
        assert out["result"]["agent"] == "knowledge_mgr"

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_agent_exception_captured(self, mock_llm: AsyncMock) -> None:
        from src.graph.nodes import run_data_analyst

        mock_llm.side_effect = RuntimeError("LLM unavailable")
        state = _base_state(task={"intent": "analyse data"})
        out = run_async(run_data_analyst(state))
        assert out["error"] is not None
        assert "LLM unavailable" in out["error"]


# ── build / cache graph tests ─────────────────────────────────────────────────

class TestBuildSupervisorGraph:
    def test_build_returns_graph(self) -> None:
        from src.graph.orchestrator import build_supervisor_graph

        graph = build_supervisor_graph()
        assert graph is not None
        assert hasattr(graph, "ainvoke") or hasattr(graph, "invoke")

    def test_get_supervisor_graph_cached(self) -> None:
        from src.graph.orchestrator import get_supervisor_graph

        g1 = get_supervisor_graph()
        g2 = get_supervisor_graph()
        assert g1 is g2

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_fallback_graph_end_to_end(self, mock_llm: AsyncMock) -> None:
        from src.graph.orchestrator import _FallbackGraph

        mock_llm.return_value = "analysis done"
        graph = _FallbackGraph()
        state = _base_state(task={"intent": "analyse CV data"})
        result = run_async(graph.ainvoke(state))
        assert result["current_agent"] == "data_analyst"
        assert result["result"]["ok"] is True
