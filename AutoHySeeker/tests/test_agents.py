"""Tests for Agent classes (base.py + all specialist agents).

All LLM calls (``chat_completion``) are mocked.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


MOCK_LLM_RESPONSE = "This is a mock LLM response."


# ── BaseAgent ──────────────────────────────────────────────────────────────────

class TestBaseAgent:
    def test_import_base_agent(self) -> None:
        from src.agents.base import BaseAgent
        assert BaseAgent is not None

    def test_build_messages_includes_system_prompt(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="You are a test agent.")
        messages = agent.build_messages(task={"goal": "run test"})
        assert messages[0]["role"] == "system"
        assert "test agent" in messages[0]["content"]

    def test_build_messages_last_message_is_user(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys")
        messages = agent.build_messages(task={"goal": "test"})
        assert messages[-1]["role"] == "user"

    def test_build_messages_user_content_contains_task_json(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys")
        task = {"goal": "analyze hydrogen evolution", "run_id": "run_42"}
        messages = agent.build_messages(task=task)
        content = messages[-1]["content"]
        parsed = json.loads(content)
        assert parsed["task"]["goal"] == "analyze hydrogen evolution"

    def test_build_messages_includes_context(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys")
        ctx = {"key": "value"}
        messages = agent.build_messages(task={}, context=ctx)
        content = json.loads(messages[-1]["content"])
        assert content["context"]["key"] == "value"

    def test_build_messages_with_prior_messages(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys")
        prior = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        messages = agent.build_messages(task={}, messages=prior)
        # system + 2 prior + final user = 4
        assert len(messages) == 4
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "hello"
        assert messages[2]["role"] == "assistant"

    def test_build_messages_normalizes_ai_role_to_assistant(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys")
        prior = [{"role": "ai", "content": "response"}]
        messages = agent.build_messages(task={}, messages=prior)
        assert messages[1]["role"] == "assistant"

    def test_build_messages_empty_context_defaults_to_empty_dict(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys")
        messages = agent.build_messages(task={"x": 1})
        content = json.loads(messages[-1]["content"])
        assert content["context"] == {}

    def test_invoke_calls_chat_completion(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys")
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value=MOCK_LLM_RESPONSE)):
            result = run_async(agent.invoke(task={"goal": "test"}, context={}))
        assert result["content"] == MOCK_LLM_RESPONSE
        assert result["agent"] == "test"

    def test_invoke_returns_model_field(self) -> None:
        from src.agents.base import BaseAgent
        from src.common.config import DEFAULT_MODEL
        agent = BaseAgent(name="test", system_prompt="sys")
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            result = run_async(agent.invoke(task={}))
        assert result["model"] == DEFAULT_MODEL

    def test_invoke_custom_model_override(self) -> None:
        from src.agents.base import BaseAgent
        agent = BaseAgent(name="test", system_prompt="sys", model="custom-model")
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")) as mock_cc:
            run_async(agent.invoke(task={}))
            mock_cc.assert_called_once()
            call_kwargs = mock_cc.call_args[1]
            assert call_kwargs.get("model") == "custom-model"


# ── Specialist Agents ─────────────────────────────────────────────────────────

class TestDataAnalystAgent:
    def test_import(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent
        assert DataAnalystAgent is not None

    def test_name_is_data_analyst(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        assert agent.name == "data_analyst"

    def test_system_prompt_contains_cv_eis(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        prompt_lower = agent.system_prompt.lower()
        assert "cv" in prompt_lower or "eis" in prompt_lower

    def test_invoke_returns_expected_keys(self) -> None:
        from src.agents.data_analyst import DataAnalystAgent
        agent = DataAnalystAgent()
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="peaks found")):
            result = run_async(agent.invoke(task={"intent": "analyze cv"}))
        assert set(result.keys()) >= {"agent", "model", "content"}
        assert result["content"] == "peaks found"


class TestDiagnosticsExpertAgent:
    def test_import(self) -> None:
        from src.agents.diagnostics import DiagnosticsExpertAgent
        assert DiagnosticsExpertAgent is not None

    def test_name_is_diagnostics(self) -> None:
        from src.agents.diagnostics import DiagnosticsExpertAgent
        agent = DiagnosticsExpertAgent()
        assert agent.name == "diagnostics"

    def test_system_prompt_mentions_failure(self) -> None:
        from src.agents.diagnostics import DiagnosticsExpertAgent
        agent = DiagnosticsExpertAgent()
        assert "failure" in agent.system_prompt.lower() or "diagnos" in agent.system_prompt.lower()

    def test_invoke_mocked(self) -> None:
        from src.agents.diagnostics import DiagnosticsExpertAgent
        agent = DiagnosticsExpertAgent()
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="no failures")):
            result = run_async(agent.invoke(task={"error": "voltage spike"}))
        assert result["agent"] == "diagnostics"
        assert result["content"] == "no failures"


class TestExperimentDesignerAgent:
    def test_import(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent
        assert ExperimentDesignerAgent is not None

    def test_name_is_exp_designer(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent
        agent = ExperimentDesignerAgent()
        assert agent.name == "exp_designer"

    def test_system_prompt_mentions_experiment(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent
        agent = ExperimentDesignerAgent()
        assert "experiment" in agent.system_prompt.lower()

    def test_invoke_mocked(self) -> None:
        from src.agents.exp_designer import ExperimentDesignerAgent
        agent = ExperimentDesignerAgent()
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="design plan")):
            result = run_async(agent.invoke(task={"goal": "optimize HER"}))
        assert result["content"] == "design plan"


class TestExperimentSupervisorAgent:
    def test_import(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        assert ExperimentSupervisorAgent is not None

    def test_name_is_exp_supervisor(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        assert agent.name == "exp_supervisor"

    def test_system_prompt_mentions_coordinate(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        prompt_lower = agent.system_prompt.lower()
        assert "coordinat" in prompt_lower or "supervis" in prompt_lower or "lifecycle" in prompt_lower

    def test_invoke_mocked(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="supervised")):
            result = run_async(agent.invoke(task={"type": "monitor"}))
        assert result["content"] == "supervised"


class TestKnowledgeManagerAgent:
    def test_import(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent
        assert KnowledgeManagerAgent is not None

    def test_name_is_knowledge_mgr(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent
        agent = KnowledgeManagerAgent()
        assert agent.name == "knowledge_mgr"

    def test_system_prompt_mentions_knowledge(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent
        agent = KnowledgeManagerAgent()
        assert "knowledge" in agent.system_prompt.lower()

    def test_invoke_mocked(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent
        agent = KnowledgeManagerAgent()
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="knowledge summary")):
            result = run_async(agent.invoke(task={"query": "HER catalyst"}))
        assert result["agent"] == "knowledge_mgr"
        assert result["content"] == "knowledge summary"


# ── agents __init__ exports ────────────────────────────────────────────────────

class TestAgentsInit:
    def test_all_agents_importable_from_package(self) -> None:
        from src.agents import (
            DataAnalystAgent,
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentSupervisorAgent,
            KnowledgeManagerAgent,
        )
        for cls in (
            DataAnalystAgent,
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentSupervisorAgent,
            KnowledgeManagerAgent,
        ):
            assert cls is not None

    def test_all_agents_are_base_agent_subclasses(self) -> None:
        from src.agents.base import BaseAgent
        from src.agents import (
            DataAnalystAgent,
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentSupervisorAgent,
            KnowledgeManagerAgent,
        )
        for cls in (
            DataAnalystAgent,
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentSupervisorAgent,
            KnowledgeManagerAgent,
        ):
            assert issubclass(cls, BaseAgent)
