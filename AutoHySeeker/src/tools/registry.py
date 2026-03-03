"""Simple runtime registry for tools."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from src.tools.echem_reader import (
    list_recent_experiments,
    read_cv_csv,
    read_eis_csv,
    read_experiment_dir,
)
from src.tools.experiment_ctrl import start_experiment, stop_experiment
from src.tools.file_watcher import watch_data_dir

ToolHandler = Callable[..., Any]


@dataclass(slots=True)
class RegisteredTool:
    name: str
    handler: ToolHandler
    description: str = ""


class ToolRegistry:
    """Store and invoke tools by name."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, name: str, handler: ToolHandler, description: str = "") -> None:
        if not name:
            raise ValueError("tool name cannot be empty")
        self._tools[name] = RegisteredTool(name=name, handler=handler, description=description)

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> ToolHandler:
        if name not in self._tools:
            raise KeyError(f"tool not found: {name}")
        return self._tools[name].handler

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    async def invoke(self, name: str, *args: Any, **kwargs: Any) -> Any:
        handler = self.get(name)
        result = handler(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("read_cv_csv", read_cv_csv, "Read and validate CV CSV data.")
    registry.register("read_eis_csv", read_eis_csv, "Read EIS CSV data.")
    registry.register("read_experiment_dir", read_experiment_dir, "Load a run directory summary.")
    registry.register(
        "list_recent_experiments",
        list_recent_experiments,
        "List recent run directories from data root.",
    )
    registry.register("start_experiment", start_experiment, "Stub: start experiment.")
    registry.register("stop_experiment", stop_experiment, "Stub: stop experiment.")
    registry.register("watch_data_dir", watch_data_dir, "Poll data root for new run directories.")
    return registry

