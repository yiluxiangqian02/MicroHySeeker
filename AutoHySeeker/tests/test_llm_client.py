"""Tests for src/common/llm_client.py."""

from __future__ import annotations

import asyncio
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
        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"):
            c1 = llm_client.get_client()
            c2 = llm_client.get_client()
            assert c1 is c2
        llm_client._client = None

    def test_client_has_base_url(self) -> None:
        from src.common import llm_client
        llm_client._client = None
        with patch("src.common.llm_client.OPENAI_API_KEY", "test-key"), \
             patch("src.common.llm_client.OPENAI_BASE_URL", "https://test.example.com"):
            client = llm_client.get_client()
            assert client.base_url is not None
        llm_client._client = None


# ── chat_completion ────────────────────────────────────────────────────────────

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
