"""Base agent abstraction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from src.common.config import DEFAULT_MODEL
from src.common.llm_client import chat_completion


def _normalize_role(role: str) -> str:
    role_value = role.lower().strip()
    if role_value in {"assistant", "ai"}:
        return "assistant"
    if role_value in {"system"}:
        return "system"
    return "user"


def _convert_message(message: Any) -> dict[str, str]:
    if isinstance(message, dict):
        role = _normalize_role(str(message.get("role", "user")))
        return {"role": role, "content": str(message.get("content", ""))}

    role = _normalize_role(str(getattr(message, "type", "user")))
    content = str(getattr(message, "content", ""))
    return {"role": role, "content": content}


@dataclass(slots=True)
class BaseAgent:
    name: str
    system_prompt: str
    model: str = DEFAULT_MODEL

    def build_messages(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
        messages: Iterable[Any] | None = None,
    ) -> list[dict[str, str]]:
        chat_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        if messages:
            chat_messages.extend(_convert_message(item) for item in messages)

        payload = {"task": task, "context": context or {}}
        chat_messages.append(
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        )
        return chat_messages

    async def invoke(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
        messages: Iterable[Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = await chat_completion(
            self.build_messages(task=task, context=context, messages=messages),
            model=self.model,
            temperature=kwargs.pop("temperature", 0.2),
            **kwargs,
        )
        return {
            "agent": self.name,
            "model": self.model,
            "content": response,
        }

