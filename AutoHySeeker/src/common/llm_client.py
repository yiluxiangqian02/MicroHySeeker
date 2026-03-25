"""OpenAI-compatible async client wrapper with retry."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from openai import AsyncOpenAI

import src.common.config as app_config
from src.common.config import load_agent_config
from src.common.logger import get_logger

logger = get_logger(__name__)
_client: AsyncOpenAI | None = None
_custom_clients: dict[tuple[str, str], AsyncOpenAI] = {}
_async_openai_cls: type[AsyncOpenAI] | None = None
_endpoint_backoff_until: dict[str, float] = {}


def _default_agent_config() -> dict[str, Any]:
    return {
        "model": app_config.DEFAULT_MODEL,
        "fallback_model": app_config.FALLBACK_MODEL,
        "api_key": app_config.OPENAI_API_KEY,
        "temperature": 0.2,
        "max_tokens": None,
        "base_url": app_config.OPENAI_BASE_URL,
        "enabled": True,
    }


def _mask_key_prefix(api_key: str) -> str:
    return api_key[:6] if api_key else "empty"


def _get_async_openai_class() -> type[AsyncOpenAI]:
    """Import AsyncOpenAI lazily so non-LLM code paths can still run."""
    global _async_openai_cls
    if _async_openai_cls is None:
        try:
            from openai import AsyncOpenAI as imported_cls
        except ImportError as exc:
            raise RuntimeError(
                "openai package is not installed. Run `pip install -e \".[dev]\"` "
                "inside AutoHySeeker before enabling LLM-backed agents."
            ) from exc
        _async_openai_cls = imported_cls
    return _async_openai_cls


def _build_timeout() -> Any:
    """Use a short connect timeout so unreachable gateways fail fast."""
    try:
        import httpx
    except ImportError:
        return app_config.OPENAI_TIMEOUT_SECONDS
    return httpx.Timeout(
        timeout=app_config.OPENAI_TIMEOUT_SECONDS,
        connect=app_config.OPENAI_CONNECT_TIMEOUT_SECONDS,
    )


def _iter_error_chain(exc: BaseException) -> Sequence[BaseException]:
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def _is_connectivity_error(exc: BaseException) -> bool:
    markers = (
        "connection error",
        "connect error",
        "connecterror",
        "api connection error",
        "all connection attempts failed",
        "connection refused",
        "failed to establish a new connection",
        "temporarily unavailable",
        "winerror 10013",
        "winerror 10061",
        "nodename nor servname provided",
    )
    for item in _iter_error_chain(exc):
        type_name = type(item).__name__.lower()
        message = str(item).lower()
        if "connect" in type_name or "timeout" in type_name:
            return True
        if any(marker in message for marker in markers):
            return True
    return False


def _is_endpoint_backing_off(base_url: str) -> bool:
    return _endpoint_backoff_until.get(base_url, 0.0) > time.monotonic()


def _mark_endpoint_unavailable(base_url: str) -> None:
    _endpoint_backoff_until[base_url] = (
        time.monotonic() + app_config.OPENAI_UNAVAILABLE_COOLDOWN_SECONDS
    )


def _clear_endpoint_backoff(base_url: str) -> None:
    _endpoint_backoff_until.pop(base_url, None)


def get_client(
    api_key: str | None = None,
    base_url: str | None = None,
) -> AsyncOpenAI:
    """Return a singleton AsyncOpenAI client."""
    global _client
    async_openai_cls = _get_async_openai_class()
    default_api_key = app_config.OPENAI_API_KEY
    default_base_url = app_config.OPENAI_BASE_URL
    resolved_api_key = api_key or default_api_key
    resolved_base_url = base_url or default_base_url

    if resolved_api_key == default_api_key and resolved_base_url == default_base_url:
        if _client is None:
            _client = async_openai_cls(
                base_url=resolved_base_url,
                api_key=resolved_api_key,
                timeout=_build_timeout(),
            )
        return _client

    cache_key = (resolved_base_url, resolved_api_key)
    if cache_key not in _custom_clients:
        _custom_clients[cache_key] = async_openai_cls(
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            timeout=_build_timeout(),
        )
    return _custom_clients[cache_key]


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
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    fallback_model: str | None = None,
    **kwargs: Any,
) -> str:
    """Create a chat completion with 2 retries and 2-second backoff."""
    resolved_model = model or app_config.DEFAULT_MODEL
    resolved_fallback_model = fallback_model or app_config.FALLBACK_MODEL
    resolved_api_key = api_key or app_config.OPENAI_API_KEY
    resolved_base_url = base_url or app_config.OPENAI_BASE_URL

    if not resolved_api_key:
        raise RuntimeError("OPENAI_API_KEY is empty. Set it in environment or .env file.")
    if _is_endpoint_backing_off(resolved_base_url):
        raise RuntimeError(
            f"LLM endpoint temporarily unavailable for {resolved_base_url}; "
            "skipping request during cooldown window."
        )

    attempts = 3  # 1 initial + 2 retries
    last_error: Exception | None = None

    for attempt in range(attempts):
        model_name = resolved_model if attempt < attempts - 1 else resolved_fallback_model
        try:
            response = await get_client(
                api_key=resolved_api_key,
                base_url=resolved_base_url,
            ).chat.completions.create(
                model=model_name,
                messages=list(messages),
                **kwargs,
            )
            _clear_endpoint_backoff(resolved_base_url)
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
            if _is_connectivity_error(exc):
                _mark_endpoint_unavailable(resolved_base_url)
                break
            if attempt < attempts - 1:
                await asyncio.sleep(2)

    raise RuntimeError(f"chat completion failed after {attempts} attempts: {last_error}")
