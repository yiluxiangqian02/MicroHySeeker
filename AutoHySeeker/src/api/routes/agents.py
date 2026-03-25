"""Agent invocation and model configuration APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.common.config import (
    get_agent_models_config,
    get_default_llm_config,
    load_agent_config,
    reload_all_configs,
    update_agent_model_config,
)
from src.graph.orchestrator import get_supervisor_graph
from src.graph.state import AutoHySeekerState

router = APIRouter(tags=["agents"])

_AGENT_SECTION_ORDER = (
    "orchestrator",
    "experiment_designer",
    "experiment_executor",
    "diagnostics_expert",
    "chat",
    "heartbeat_inspector",
)
_AVAILABLE_MODEL_OPTIONS = [
    {"value": "anthropic/claude-sonnet-4-6", "label": "Claude Sonnet 4.6"},
    {"value": "anthropic/claude-opus-4-6", "label": "Claude Opus 4.6"},
    {"value": "anthropic/claude-haiku-4-5", "label": "Claude Haiku 4.5"},
    {"value": "ali/qwen3-max-2026-01-23", "label": "Qwen3 Max 2026-01-23"},
    {"value": "google/gemini-3-flash-preview", "label": "Gemini 3 Flash Preview"},
    {"value": "bigmodel/GLM-4.6 Thinking", "label": "GLM-4.6 Thinking"},
]


class AgentInvokeRequest(BaseModel):
    task: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    current_agent: str | None = None


class AgentModelUpdateRequest(BaseModel):
    enabled: bool | None = None
    primary_model: str | None = None
    fallback_model: str | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    base_url: str | None = None


def _serialise_agent_model(agent_name: str) -> dict[str, Any]:
    config = load_agent_config(agent_name, reload=True)
    return {
        "agent_name": agent_name,
        "display_name": str(config.get("name", agent_name)),
        "enabled": bool(config.get("enabled", True)),
        "primary_model": str(config.get("model", "")),
        "fallback_model": str(config.get("fallback_model", "")),
        "api_key": str(config.get("api_key", "")),
        "temperature": float(config.get("temperature", 0.2)),
        "max_tokens": config.get("max_tokens"),
        "base_url": str(config.get("base_url", "")),
    }


@router.post("/agents/invoke")
async def invoke_agent(request: AgentInvokeRequest) -> dict[str, Any]:
    graph = get_supervisor_graph()
    state: AutoHySeekerState = {
        "messages": request.messages,  # type: ignore[assignment]
        "current_agent": request.current_agent or "",
        "task": request.task,
        "context": request.context,
        "error": None,
        "result": None,
    }

    try:
        result_state = await graph.ainvoke(state)
        return {
            "ok": not bool(result_state.get("error")),
            "result": result_state.get("result"),
            "state": result_state,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/agents/models")
async def get_agent_models() -> dict[str, Any]:
    config_sections = get_agent_models_config(reload=True)
    defaults = get_default_llm_config(reload=True)
    agents = {
        agent_name: _serialise_agent_model(agent_name)
        for agent_name in _AGENT_SECTION_ORDER
        if agent_name in config_sections
    }
    return {
        "ok": True,
        "defaults": {
            "model": defaults["model"],
            "fallback_model": defaults["fallback_model"],
            "base_url": defaults["base_url"],
        },
        "available_models": _AVAILABLE_MODEL_OPTIONS,
        "agents": agents,
    }


@router.put("/api/agents/models/{agent_name}")
async def update_agent_model(agent_name: str, request: AgentModelUpdateRequest) -> dict[str, Any]:
    if agent_name not in _AGENT_SECTION_ORDER:
        raise HTTPException(status_code=404, detail=f"Unknown agent model config: {agent_name}")

    updates: dict[str, Any] = {}
    if request.enabled is not None:
        updates["enabled"] = request.enabled
    if request.primary_model is not None:
        updates["model"] = request.primary_model
    if request.fallback_model is not None:
        updates["fallback_model"] = request.fallback_model
    if request.api_key is not None:
        updates["api_key"] = request.api_key
    if request.temperature is not None:
        updates["temperature"] = request.temperature
    if request.max_tokens is not None:
        updates["max_tokens"] = request.max_tokens
    if request.base_url is not None:
        updates["base_url"] = request.base_url

    update_agent_model_config(agent_name, updates)
    reload_all_configs()
    return {
        "ok": True,
        "agent": _serialise_agent_model(agent_name),
    }
