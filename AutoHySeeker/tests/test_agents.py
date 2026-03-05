"""Tests for BaseAgent — build_messages, invoke, and concrete agent subclasses."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# ── build_messages tests ──────────────────────────────────────────────────────

class TestBuildMessages:
    def test_system_prompt_is_first(self) -> None:
        from src.agents.base import BaseAgent

        agent = BaseAgent(name="test", system_prompt="You are a test agent.")
        msgs = agent.build_messages(task={"goal": "test"})
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are a test agent."

    def test_task_serialised_as_last_user_message(self) -> None:
        from src.agents.base import BaseAgent

        agent = BaseAgent(name="test", system_prompt="sys")
        msgs = agent.build_messages(task={"goal": "run CV"}, context={"key": "val"})
        last = msgs[-1]
        assert last["role"] == "user"
        payload = json.loads(last["content"])
        assert payload["task"]["goal"] == "run CV"
        assert payload["context"]["key"] == "val"

    def test_history_messages_inserted(self) -> None:
        from src.agents.base import BaseAgent

        agent = BaseAgent(name="test", system_prompt="sys")
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        msgs = agent.build_messages(task={"goal": "x"}, messages=history)
        assert len(msgs) == 4  # system + 2 history + task
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "hello"
        assert msgs[2]["role"] == "assistant"
        assert msgs[2]["content"] == "hi"

    def test_empty_context_defaults_to_empty_dict(self) -> None:
        from src.agents.base import BaseAgent

        agent = BaseAgent(name="test", system_prompt="sys")
        msgs = agent.build_messages(task={"x": 1})
        payload = json.loads(msgs[-1]["content"])
        assert payload["context"] == {}

    def test_no_history_produces_two_messages(self) -> None:
        from src.agents.base import BaseAgent

        agent = BaseAgent(name="test", system_prompt="sys")
        msgs = agent.build_messages(task={"x": 1})
        assert len(msgs) == 2  # system + task


# ── _normalize_role / _convert_message tests ──────────────────────────────────

class TestNormalizeRole:
    def test_ai_becomes_assistant(self) -> None:
        from src.agents.base import _normalize_role

        assert _normalize_role("ai") == "assistant"
        assert _normalize_role("AI") == "assistant"

    def test_system_stays_system(self) -> None:
        from src.agents.base import _normalize_role

        assert _normalize_role("system") == "system"

    def test_unknown_becomes_user(self) -> None:
        from src.agents.base import _normalize_role

        assert _normalize_role("human") == "user"
        assert _normalize_role("") == "user"


class TestConvertMessage:
    def test_dict_message(self) -> None:
        from src.agents.base import _convert_message

        msg = {"role": "assistant", "content": "hi"}
        out = _convert_message(msg)
        assert out == {"role": "assistant", "content": "hi"}

    def test_object_message_with_type_attr(self) -> None:
        from src.agents.base import _convert_message

        class FakeMsg:
            type = "ai"
            content = "response text"

        out = _convert_message(FakeMsg())
        assert out["role"] == "assistant"
        assert out["content"] == "response text"

    def test_missing_role_defaults_to_user(self) -> None:
        from src.agents.base import _convert_message

        out = _convert_message({"content": "test"})
        assert out["role"] == "user"


# ── BaseAgent.invoke tests (mocked LLM) ──────────────────────────────────────

class TestBaseAgentInvoke:
    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_returns_agent_content(self, mock_llm: AsyncMock) -> None:
        from src.agents.base import BaseAgent

        mock_llm.return_value = "mocked response"
        agent = BaseAgent(name="tester", system_prompt="sys")
        result = run_async(agent.invoke(task={"goal": "test"}))
        assert result["agent"] == "tester"
        assert result["content"] == "mocked response"
        assert "model" in result

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_passes_messages_to_llm(self, mock_llm: AsyncMock) -> None:
        from src.agents.base import BaseAgent

        mock_llm.return_value = "ok"
        agent = BaseAgent(name="tester", system_prompt="sys")
        run_async(agent.invoke(
            task={"goal": "test"},
            messages=[{"role": "user", "content": "prior"}],
        ))
        call_args = mock_llm.call_args
        msgs = call_args[0][0]  # first positional arg
        assert any("prior" in m.get("content", "") for m in msgs)

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_default_temperature(self, mock_llm: AsyncMock) -> None:
        from src.agents.base import BaseAgent

        mock_llm.return_value = "ok"
        agent = BaseAgent(name="tester", system_prompt="sys")
        run_async(agent.invoke(task={"goal": "test"}))
        assert mock_llm.call_args[1]["temperature"] == 0.2

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_propagates_exception(self, mock_llm: AsyncMock) -> None:
        from src.agents.base import BaseAgent

        mock_llm.side_effect = RuntimeError("API down")
        agent = BaseAgent(name="tester", system_prompt="sys")
        with pytest.raises(RuntimeError, match="API down"):
            run_async(agent.invoke(task={"goal": "test"}))


# ── Concrete agent subclass tests ─────────────────────────────────────────────

class TestConcreteAgents:
    def test_data_analyst_agent_attrs(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent

        agent = DataAnalystAgent()
        assert agent.name == "data_analyst"
        assert "DataAnalyst" in agent.system_prompt

    def test_exp_designer_agent_attrs(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent

        agent = ExperimentDesignerAgent()
        assert agent.name == "exp_designer"
        assert "ExperimentDesigner" in agent.system_prompt

    def test_exp_supervisor_agent_attrs(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent

        agent = ExperimentSupervisorAgent()
        assert agent.name == "exp_supervisor"
        assert "ExperimentSupervisor" in agent.system_prompt

    def test_diagnostics_agent_attrs(self) -> None:
        from src.agents.diagnostics import DiagnosticsExpertAgent

        agent = DiagnosticsExpertAgent()
        assert agent.name == "diagnostics"

    def test_knowledge_mgr_agent_attrs(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        assert agent.name == "knowledge_mgr"

    def test_all_agents_exported(self) -> None:
        from src.agents import (
            DataAnalystAgent,
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentSupervisorAgent,
            KnowledgeManagerAgent,
        )

        assert all(callable(cls) for cls in [
            DataAnalystAgent,
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentSupervisorAgent,
            KnowledgeManagerAgent,
        ])

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_each_agent_invoke(self, mock_llm: AsyncMock) -> None:
        from src.agents import (
            DataAnalystAgent,
            ExperimentDesignerAgent,
            ExperimentSupervisorAgent,
            KnowledgeManagerAgent,
        )

        mock_llm.return_value = "response"
        for cls in [DataAnalystAgent, ExperimentDesignerAgent,
                     ExperimentSupervisorAgent, KnowledgeManagerAgent]:
            agent = cls()
            result = run_async(agent.invoke(task={"goal": "test"}))
            assert result["content"] == "response"
            assert result["agent"] == agent.name
