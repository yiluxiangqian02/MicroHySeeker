"""Tests for Agent classes (base.py + all specialist agents).

All LLM calls (``chat_completion``) are mocked.
"""

from __future__ import annotations

import asyncio
import json
import tomllib
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

    def test_init_loads_agent_config_defaults(self) -> None:
        from src.agents.base import BaseAgent

        with patch(
            "src.agents.base.load_agent_config",
            return_value={
                "model": "agent-model",
                "api_key": "agent-key",
                "temperature": 0.55,
                "max_tokens": 1234,
                "base_url": "https://agent.example.com",
            },
        ) as mock_load:
            agent = BaseAgent(name="agent_a", system_prompt="sys")

        mock_load.assert_called_once_with("agent_a")
        assert agent.model == "agent-model"
        assert agent.api_key == "agent-key"
        assert agent.temperature == pytest.approx(0.55)
        assert agent.max_tokens == 1234
        assert agent.base_url == "https://agent.example.com"

    def test_invoke_passes_agent_credentials_and_limits(self) -> None:
        from src.agents.base import BaseAgent

        agent = BaseAgent(
            name="test",
            system_prompt="sys",
            model="agent-model",
            api_key="agent-key",
            base_url="https://agent.example.com",
            temperature=0.4,
            max_tokens=987,
        )
        with patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")) as mock_cc:
            run_async(agent.invoke(task={}))

        call_kwargs = mock_cc.call_args[1]
        assert call_kwargs["model"] == "agent-model"
        assert call_kwargs["api_key"] == "agent-key"
        assert call_kwargs["base_url"] == "https://agent.example.com"
        assert call_kwargs["temperature"] == pytest.approx(0.4)
        assert call_kwargs["max_tokens"] == 987


# ── Specialist Agents ─────────────────────────────────────────────────────────

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


class TestExperimentExecutorAgent:
    def test_import(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent
        assert ExperimentExecutorAgent is not None

    def test_name_is_exp_executor(self) -> None:
        from src.agents.exp_executor import ExperimentExecutorAgent
        agent = ExperimentExecutorAgent()
        assert agent.name == "exp_executor"


# ── agents __init__ exports ────────────────────────────────────────────────────

class TestAgentConfigLoading:
    def test_all_agents_load_repo_config_and_log_api_key_prefix(self) -> None:
        from src.agents import (
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentExecutorAgent,
            OrchestratorAgent,
        )
        from src.common.config import PROJECT_ROOT

        config_path = PROJECT_ROOT / "configs" / "agent_models.toml"
        with config_path.open("rb") as fh:
            parsed = tomllib.load(fh)

        cases = [
            (OrchestratorAgent, "orchestrator"),
            (DiagnosticsExpertAgent, "diagnostics_expert"),
            (ExperimentDesignerAgent, "experiment_designer"),
            (ExperimentExecutorAgent, "experiment_executor"),
        ]

        for agent_cls, section_name in cases:
            expected = parsed[section_name]
            expected_prefix = expected["api_key"][:6]
            with patch("src.common.llm_client.logger.info") as mock_log:
                agent = agent_cls()

            assert agent.model == expected["model"]
            assert agent.api_key == expected["api_key"]
            assert agent.temperature == pytest.approx(expected["temperature"])
            assert agent.max_tokens == expected["max_tokens"]
            assert agent.base_url == expected["base_url"]
            mock_log.assert_any_call(
                "loaded agent config for %s (resolved=%s): model=%s, api_key_prefix=%s",
                agent.name,
                section_name,
                expected["model"],
                expected_prefix,
            )


class TestAgentsInit:
    def test_all_agents_importable_from_package(self) -> None:
        from src.agents import (
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentExecutorAgent,
            OrchestratorAgent,
        )
        for cls in (
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentExecutorAgent,
            OrchestratorAgent,
        ):
            assert cls is not None

    def test_all_agents_are_base_agent_subclasses(self) -> None:
        from src.agents.base import BaseAgent
        from src.agents import (
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentExecutorAgent,
            OrchestratorAgent,
        )
        for cls in (
            DiagnosticsExpertAgent,
            ExperimentDesignerAgent,
            ExperimentExecutorAgent,
            OrchestratorAgent,
        ):
            assert issubclass(cls, BaseAgent)
