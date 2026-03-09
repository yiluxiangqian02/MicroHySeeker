"""Tests for src/common/llm_client.py."""

from __future__ import annotations

import asyncio
from pathlib import Path
import tomllib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# ── _extract_text ──────────────────────────────────────────────────────────────

class TestExtractText:
    def test_string_input(self) -> None:
        from src.common.llm_client import _extract_text
        assert _extract_text("  hello  ") == "hello"

    def test_none_input(self) -> None:
        from src.common.llm_client import _extract_text
        assert _extract_text(None) == ""

    def test_list_with_text_parts(self) -> None:
        from src.common.llm_client import _extract_text
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": " World"},
        ]
        assert _extract_text(content) == "Hello World"

    def test_list_ignores_non_text_parts(self) -> None:
        from src.common.llm_client import _extract_text
        content = [
            {"type": "image_url", "url": "http://example.com/img.png"},
            {"type": "text", "text": "caption"},
        ]
        assert _extract_text(content) == "caption"

    def test_empty_list(self) -> None:
        from src.common.llm_client import _extract_text
        assert _extract_text([]) == ""

    def test_numeric_input_converted_to_str(self) -> None:
        from src.common.llm_client import _extract_text
        assert _extract_text(42) == "42"

    def test_strips_whitespace(self) -> None:
        from src.common.llm_client import _extract_text
        assert _extract_text("  \n  trimmed  \n  ") == "trimmed"


# ── get_client ─────────────────────────────────────────────────────────────────

class TestGetClient:
    def test_returns_singleton(self) -> None:
        from src.common import llm_client
        # Reset singleton so test is isolated
        llm_client._client = None
        llm_client._custom_clients.clear()
        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"):
            c1 = llm_client.get_client()
            c2 = llm_client.get_client()
            assert c1 is c2
        llm_client._client = None
        llm_client._custom_clients.clear()

    def test_client_has_base_url(self) -> None:
        from src.common import llm_client
        llm_client._client = None
        llm_client._custom_clients.clear()
        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
             patch("src.common.llm_client.OPENAI_BASE_URL", "https://test.example.com"):
            client = llm_client.get_client()
            assert client.base_url is not None
        llm_client._client = None
        llm_client._custom_clients.clear()

    def test_returns_cached_custom_client_for_same_credentials(self) -> None:
        from src.common import llm_client

        llm_client._client = None
        llm_client._custom_clients.clear()
        c1 = llm_client.get_client(
            api_key="agent-key",
            base_url="https://agent.example.com",
        )
        c2 = llm_client.get_client(
            api_key="agent-key",
            base_url="https://agent.example.com",
        )
        assert c1 is c2
        llm_client._client = None
        llm_client._custom_clients.clear()


# ── chat_completion ────────────────────────────────────────────────────────────

class TestLoadAgentConfig:
    def test_returns_defaults_when_file_missing(self) -> None:
        from src.common.llm_client import load_agent_config

        missing_path = Path(".pytest_tmp") / "missing-agent-models.toml"
        with patch("src.common.llm_client.AGENT_CONFIG_PATH", missing_path), \
             patch("src.common.llm_client.DEFAULT_MODEL", "default-model"), \
             patch("src.common.llm_client.OPENAI_API_KEY", "default-key"), \
             patch("src.common.llm_client.OPENAI_BASE_URL", "https://default.example.com"):
            config = load_agent_config("ghost_agent")

        assert config == {
            "model": "default-model",
            "api_key": "default-key",
            "temperature": 0.2,
            "max_tokens": None,
            "base_url": "https://default.example.com",
        }

    def test_returns_defaults_when_agent_missing(self) -> None:
        from src.common.llm_client import load_agent_config

        temp_root = Path(".pytest_tmp")
        temp_root.mkdir(exist_ok=True)
        config_path = temp_root / "agent_models.toml"
        config_path.write_text(
            "[known_agent]\nmodel='known-model'\napi_key='known-key'\n",
            encoding="utf-8",
        )
        with patch("src.common.llm_client.AGENT_CONFIG_PATH", config_path), \
             patch("src.common.llm_client.DEFAULT_MODEL", "default-model"), \
             patch("src.common.llm_client.OPENAI_API_KEY", "default-key"), \
             patch("src.common.llm_client.OPENAI_BASE_URL", "https://default.example.com"):
            config = load_agent_config("unknown_agent")

        assert config["model"] == "default-model"
        assert config["api_key"] == "default-key"
        assert config["temperature"] == 0.2
        assert config["max_tokens"] is None
        assert config["base_url"] == "https://default.example.com"

    def test_resolves_agent_aliases_from_repo_config(self) -> None:
        from src.common.config import PROJECT_ROOT
        from src.common.llm_client import load_agent_config

        config_path = PROJECT_ROOT / "configs" / "agent_models.toml"
        with config_path.open("rb") as fh:
            parsed = tomllib.load(fh)

        config = load_agent_config("exp_designer")
        expected = parsed["experiment_designer"]

        assert config["model"] == expected["model"]
        assert config["api_key"] == expected["api_key"]
        assert config["temperature"] == expected["temperature"]
        assert config["max_tokens"] == expected["max_tokens"]
        assert config["base_url"] == expected["base_url"]


class TestChatCompletion:
    def _make_mock_response(self, text: str = "ok") -> MagicMock:
        choice = MagicMock()
        choice.message.content = text
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_raises_when_api_key_empty(self) -> None:
        from src.common.llm_client import chat_completion
        with patch("src.common.llm_client.OPENAI_API_KEY", ""):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                run_async(chat_completion([{"role": "user", "content": "hi"}]))

    def test_returns_string_on_success(self) -> None:
        from src.common.llm_client import chat_completion
        mock_response = self._make_mock_response("Hello from LLM")
        mock_create = AsyncMock(return_value=mock_response)
        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
             patch("src.common.llm_client.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client
            result = run_async(chat_completion([{"role": "user", "content": "hi"}]))
        assert result == "Hello from LLM"

    def test_retries_on_failure_then_raises(self) -> None:
        from src.common.llm_client import chat_completion
        mock_create = AsyncMock(side_effect=RuntimeError("network error"))
        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
             patch("src.common.llm_client.get_client") as mock_get_client, \
             patch("src.common.llm_client.asyncio.sleep", new=AsyncMock()):
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client
            with pytest.raises(RuntimeError, match="failed after"):
                run_async(chat_completion([{"role": "user", "content": "hi"}]))
        assert mock_create.call_count == 3  # 1 initial + 2 retries

    def test_uses_fallback_model_on_last_retry(self) -> None:
        from src.common.llm_client import chat_completion
        called_models: list[str] = []

        async def fake_create(**kwargs: Any) -> Any:
            called_models.append(kwargs.get("model", ""))
            raise RuntimeError("fail")

        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
             patch("src.common.llm_client.FALLBACK_MODEL", "fallback-model"), \
             patch("src.common.llm_client.DEFAULT_MODEL", "default-model"), \
             patch("src.common.llm_client.get_client") as mock_get_client, \
             patch("src.common.llm_client.asyncio.sleep", new=AsyncMock()):
            mock_client = MagicMock()
            mock_client.chat.completions.create = fake_create
            mock_get_client.return_value = mock_client
            with pytest.raises(RuntimeError):
                run_async(chat_completion([{"role": "user", "content": "hi"}]))
        # Last attempt should use fallback model
        assert called_models[-1] == "fallback-model"

    def test_custom_model_used(self) -> None:
        from src.common.llm_client import chat_completion
        mock_response = self._make_mock_response("response")
        called_models: list[str] = []

        async def fake_create(**kwargs: Any) -> Any:
            called_models.append(kwargs.get("model", ""))
            return mock_response

        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
             patch("src.common.llm_client.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = fake_create
            mock_get_client.return_value = mock_client
            run_async(chat_completion([{"role": "user", "content": "hi"}], model="gpt-custom"))
        assert called_models[0] == "gpt-custom"

    def test_custom_api_key_and_base_url_are_used(self) -> None:
        from src.common.llm_client import chat_completion

        mock_response = self._make_mock_response("response")
        with patch("src.common.llm_client.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = run_async(
                chat_completion(
                    [{"role": "user", "content": "hi"}],
                    api_key="agent-key",
                    base_url="https://agent.example.com",
                )
            )

        assert result == "response"
        mock_get_client.assert_called_once_with(
            api_key="agent-key",
            base_url="https://agent.example.com",
        )

    def test_empty_choices_returns_empty_string(self) -> None:
        from src.common.llm_client import chat_completion
        mock_response = MagicMock()
        mock_response.choices = []
        mock_create = AsyncMock(return_value=mock_response)
        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
             patch("src.common.llm_client.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create = mock_create
            mock_get_client.return_value = mock_client
            result = run_async(chat_completion([{"role": "user", "content": "hi"}]))
        assert result == ""
