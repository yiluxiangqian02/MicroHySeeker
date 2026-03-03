"""State model for AutoHySeeker supervisor graph."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

try:
    from langchain_core.messages import BaseMessage
except ImportError:  # pragma: no cover - dependency availability dependent
    class BaseMessage:  # type: ignore[no-redef]
        """Fallback type placeholder when langchain-core is unavailable."""

        pass


class AutoHySeekerState(TypedDict):
    messages: list[BaseMessage]
    current_agent: str
    task: dict[str, Any]
    context: dict[str, Any]
    error: Optional[str]
    result: Optional[dict[str, Any]]

