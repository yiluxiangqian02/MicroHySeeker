"""Agent status monitoring and control API."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from src.common.agent_manager import agent_manager

router = APIRouter(prefix="/agents", tags=["agent-control"])


@router.get("/status")
async def get_all_agents_status() -> Dict[str, Any]:
    """Return the status snapshot for all known agents."""
    return agent_manager.get_all_status()


@router.post("/{agent_id}/start")
async def start_agent(agent_id: str) -> Dict[str, Any]:
    """Mark an agent as running."""
    if agent_id not in agent_manager.agents:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    agent_manager.start_agent(agent_id)
    return {"status": "ok", "agent_id": agent_id, "agent_status": "running"}


@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: str) -> Dict[str, Any]:
    """Mark an agent as idle."""
    if agent_id not in agent_manager.agents:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    agent_manager.stop_agent(agent_id)
    return {"status": "ok", "agent_id": agent_id, "agent_status": "idle"}


@router.get("/{agent_id}/logs")
async def get_agent_logs(agent_id: str, limit: int = 50) -> Dict[str, Any]:
    """Retrieve the most recent log entries for an agent."""
    if agent_id not in agent_manager.agents:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    logs: List[Dict[str, str]] = agent_manager.get_logs(agent_id, limit)
    return {"agent_id": agent_id, "logs": logs}


@router.get("/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str) -> Dict[str, Any]:
    """Retrieve performance metrics for an agent."""
    if agent_id not in agent_manager.agents:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    metrics = agent_manager.get_metrics(agent_id)
    return {"agent_id": agent_id, "metrics": metrics}
