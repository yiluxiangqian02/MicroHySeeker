"""Approval APIs for human-in-the-loop orchestration decisions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents.orchestrator_shared import get_shared_orchestrator_agent

router = APIRouter(prefix="/api/approval", tags=["approval"])


class ApprovalResponseRequest(BaseModel):
    approval_id: str = Field(..., min_length=1)
    approved: bool
    feedback: str = ""


@router.get("/pending")
async def get_pending_approvals() -> dict[str, Any]:
    orchestrator = get_shared_orchestrator_agent()
    items = orchestrator.get_pending_approvals()
    return {
        "count": len(items),
        "items": items,
    }


@router.post("/respond")
async def respond_pending_approval(req: ApprovalResponseRequest) -> dict[str, Any]:
    orchestrator = get_shared_orchestrator_agent()
    result = orchestrator.respond_human_approval(
        approval_id=req.approval_id,
        approved=req.approved,
        feedback=req.feedback,
    )
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=f"approval not found: {req.approval_id}")

    return {
        "ok": True,
        "approval": result["approval"],
        "pending_count": len(orchestrator.get_pending_approvals()),
    }
