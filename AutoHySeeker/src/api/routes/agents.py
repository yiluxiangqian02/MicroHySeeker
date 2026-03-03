"""Agent invocation APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.graph.orchestrator import get_supervisor_graph
from src.graph.state import AutoHySeekerState

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentInvokeRequest(BaseModel):
    task: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    current_agent: str | None = None


@router.post("/invoke")
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

