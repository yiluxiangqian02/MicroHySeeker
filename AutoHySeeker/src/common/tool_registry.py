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

    def tool(
        self,
        name: Optional[str] = None,
        description: str = "",
        parameters_schema: Optional[dict] = None,
    ) -> Callable:
        """Decorator to register a function as a tool.

        Usage::

            @registry.tool(description="Read a CV CSV file")
            def read_cv(path: str) -> dict: ...
        """

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip().splitlines()[0]
            self.register(tool_name, func, tool_desc, parameters_schema)
            return func

        return decorator

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


def _register_log_analysis_tools() -> None:
    """Register log-analysis tools into the global registry."""
    try:
        from src.tools.log_analysis import (
            classify_errors,
            detect_pump_anomalies,
            extract_step_timeline,
            parse_run_log,
            summarize_run,
        )

        registry.register(
            "parse_run_log",
            parse_run_log,
            "Parse run_log.log into structured LogEntry objects",
            {
                "type": "object",
                "properties": {
                    "log_path": {"type": "string", "description": "Path to the log file"}
                },
                "required": ["log_path"],
            },
        )
        registry.register(
            "classify_errors",
            classify_errors,
            "Group ERROR-level log entries by source component",
            {
                "type": "object",
                "properties": {
                    "entries": {"type": "array", "description": "List of LogEntry objects"}
                },
                "required": ["entries"],
            },
        )
        registry.register(
            "detect_pump_anomalies",
            detect_pump_anomalies,
            "Detect pump-related anomalies (timeout, failure, abnormal stop) from log entries",
            {
                "type": "object",
                "properties": {
                    "entries": {"type": "array", "description": "List of LogEntry objects"}
                },
                "required": ["entries"],
            },
        )
        registry.register(
            "summarize_run",
            summarize_run,
            "Build a RunSummary from run_log.log + run_summary.json in a run directory",
            {
                "type": "object",
                "properties": {
                    "run_dir": {"type": "string", "description": "Path to the experiment run directory"}
                },
                "required": ["run_dir"],
            },
        )
        registry.register(
            "extract_step_timeline",
            extract_step_timeline,
            "Extract step start/end events and compute per-step durations from log entries",
            {
                "type": "object",
                "properties": {
                    "entries": {"type": "array", "description": "List of LogEntry objects"}
                },
                "required": ["entries"],
            },
        )
    except ImportError:
        pass  # tools not yet available; registry remains empty for these tools


# Auto-register log analysis tools when the module is imported
_register_log_analysis_tools()
