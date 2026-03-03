"""OpenAI-compatible async client wrapper with retry."""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Sequence

from openai import AsyncOpenAI

from src.common.config import (
    DEFAULT_MODEL,
    FALLBACK_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_TIMEOUT_SECONDS,
)
from src.common.logger import get_logger

logger = get_logger(__name__)
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Return a singleton AsyncOpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
    return _client


def _extract_text(message_content: Any) -> str:
    if isinstance(message_content, str):
        return message_content.strip()
    if isinstance(message_content, list):
        chunks: list[str] = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
        return "".join(chunks).strip()
    if message_content is None:
        return ""
    return str(message_content).strip()


async def chat_completion(
    messages: Sequence[Mapping[str, Any]],
    model: str = DEFAULT_MODEL,
    **kwargs: Any,
) -> str:
    """Create a chat completion with 2 retries and 2-second backoff."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is empty. Set it in environment or .env file.")

    attempts = 3  # 1 initial + 2 retries
    last_error: Exception | None = None

    for attempt in range(attempts):
        model_name = model if attempt < attempts - 1 else FALLBACK_MODEL
        try:
            response = await get_client().chat.completions.create(
                model=model_name,
                messages=list(messages),
                **kwargs,
            )
            content = response.choices[0].message.content if response.choices else ""
            return _extract_text(content)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            last_error = exc
            logger.warning(
                "chat completion failed (attempt %s/%s, model=%s): %s",
                attempt + 1,
                attempts,
                model_name,
                exc,
            )
            if attempt < attempts - 1:
                await asyncio.sleep(2)

    raise RuntimeError(f"chat completion failed after {attempts} attempts: {last_error}")

