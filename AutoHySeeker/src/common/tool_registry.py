"""Tool registry for AutoHySeeker agents."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Optional

from pydantic import BaseModel


class ToolDef(BaseModel):
    name: str
    description: str
    parameters_schema: dict
    func: Any  # Callable, excluded from serialization

    model_config = {"arbitrary_types_allowed": True}


class ToolRegistry:
    """Registry for agent tools with OpenAI function-calling support."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters_schema: Optional[dict] = None,
    ) -> None:
        """Register a tool function."""
        self._tools[name] = ToolDef(
            name=name,
            description=description,
            parameters_schema=parameters_schema or {},
            func=func,
        )

    def get(self, name: str) -> ToolDef:
        """Get a tool definition by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        return self._tools[name]

    def list_tools(self) -> list[ToolDef]:
        """List all registered tools."""
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        """Convert registry to OpenAI function calling format."""
        result = []
        for tool in self._tools.values():
            result.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema,
                    },
                }
            )
        return result

    async def call(self, name: str, **kwargs: Any) -> Any:
        """Call a registered tool by name (supports sync and async functions)."""
        tool = self.get(name)
        func = tool.func
        if inspect.iscoroutinefunction(func):
            return await func(**kwargs)
        return await asyncio.get_event_loop().run_in_executor(None, lambda: func(**kwargs))


# Global registry instance
registry = ToolRegistry()
