"""Base agent abstraction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from src.common.config import DEFAULT_MODEL
from src.common.llm_client import chat_completion, load_agent_config


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
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.2
    max_tokens: int | None = None

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        agent_config = load_agent_config(name)
        self.name = name
        self.system_prompt = system_prompt
        self.model = model or str(agent_config["model"])
        self.api_key = api_key or str(agent_config["api_key"])
        self.base_url = base_url or str(agent_config["base_url"])
        self.temperature = (
            float(temperature)
            if temperature is not None
            else float(agent_config["temperature"])
        )
        self.max_tokens = (
            max_tokens
            if max_tokens is not None
            else agent_config["max_tokens"]
        )

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
        temperature = kwargs.pop("temperature", self.temperature)
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        request_kwargs = dict(kwargs)
        request_kwargs["temperature"] = temperature
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens

        response = await chat_completion(
            self.build_messages(task=task, context=context, messages=messages),
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            **request_kwargs,
        )
        return {
            "agent": self.name,
            "model": self.model,
            "content": response,
        }

