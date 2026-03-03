"""Task APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/tasks", tags=["tasks"])
TASK_STORE: dict[str, dict[str, Any]] = {}


class TaskCreateRequest(BaseModel):
    task_type: str = "general"
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/create")
async def create_task(request: TaskCreateRequest) -> dict[str, Any]:
    task_id = f"task_{uuid4().hex[:12]}"
    record = {
        "task_id": task_id,
        "status": "queued",
        "task_type": request.task_type,
        "payload": request.payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    TASK_STORE[task_id] = record
    return record


@router.get("/{task_id}/status")
async def get_task_status(task_id: str) -> dict[str, Any]:
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    return TASK_STORE[task_id]

