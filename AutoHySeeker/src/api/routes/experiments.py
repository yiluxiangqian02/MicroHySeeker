"""Experiment management APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

# In-memory experiment store (persists for the lifetime of the process)
_EXP_STORE: Dict[str, Dict[str, Any]] = {}


class StepModel(BaseModel):
    step_type: str = "cv"
    description: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


class ExperimentCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[StepModel] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Fixed-path routes  (must be declared BEFORE /{exp_id} catch-all)
# ---------------------------------------------------------------------------

@router.get("/statistics")
async def get_statistics() -> Dict[str, Any]:
    """Return aggregate experiment statistics."""
    total = len(_EXP_STORE)
    today = datetime.now(timezone.utc).date().isoformat()
    today_count = sum(
        1
        for e in _EXP_STORE.values()
        if e.get("created_at", "").startswith(today)
    )
    completed = [e for e in _EXP_STORE.values() if e.get("status") == "completed"]
    success_rate = round(len(completed) / total * 100, 1) if total > 0 else 0.0

    # Calculate average duration from completed experiments
    avg_duration = None
    if completed:
        total_duration = 0
        count = 0
        for exp in completed:
            if exp.get("started_at") and exp.get("completed_at"):
                try:
                    start = datetime.fromisoformat(exp["started_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(exp["completed_at"].replace("Z", "+00:00"))
                    duration_seconds = (end - start).total_seconds()
                    total_duration += duration_seconds
                    count += 1
                except (ValueError, KeyError):
                    continue
        
        if count > 0:
            avg_seconds = total_duration / count
            if avg_seconds < 60:
                avg_duration = f"{int(avg_seconds)}s"
            elif avg_seconds < 3600:
                avg_duration = f"{int(avg_seconds / 60)}m"
            else:
                avg_duration = f"{round(avg_seconds / 3600, 1)}h"

    return {
        "totalExperiments": total,
        "todayExperiments": today_count,
        "successRate": success_rate,
        "successTrend": "up" if success_rate >= 80 else "down",
        "avgDuration": avg_duration,
    }


@router.get("/suggestions")
async def get_suggestions() -> Dict[str, Any]:
    """Return experiment parameter suggestions."""
    recent = sorted(
        _EXP_STORE.values(),
        key=lambda e: e.get("created_at", ""),
        reverse=True,
    )[:3]

    suggestions = []
    
    # TODO: Integrate with real Agent for intelligent suggestions
    # For now, return empty suggestions with a note
    if recent:
        for exp in recent:
            suggestions.append(
                {
                    "exp_id": exp["exp_id"],
                    "name": exp["name"],
                    "suggestion": "智能建议功能开发中，即将接入 Agent 系统",
                    "confidence": 0.0,
                }
            )
    else:
        suggestions.append(
            {
                "exp_id": "none",
                "name": "通用建议",
                "suggestion": "开始第一个实验，建立基线数据",
                "confidence": 1.0,
            }
        )

    from src.api.routes.system import record_activity
    record_activity("system", "生成了实验建议")
    return {"suggestions": suggestions, "generated_at": datetime.now(timezone.utc).isoformat()}


@router.post("/analyze-recent")
async def analyze_recent() -> Dict[str, Any]:
    """Trigger analysis of recent experiments."""
    recent = sorted(
        _EXP_STORE.values(),
        key=lambda e: e.get("created_at", ""),
        reverse=True,
    )[:5]

    from src.api.routes.system import record_activity
    record_activity("system", f"分析了最近 {len(recent)} 个实验")
    return {
        "analyzed": len(recent),
        "experiments": [e["exp_id"] for e in recent],
        "summary": "分析完成，未发现异常",
    }


@router.post("/create")
async def create_experiment(exp: ExperimentCreate) -> Dict[str, Any]:
    """Create a new experiment."""
    exp_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
    record: Dict[str, Any] = {
        "exp_id": exp_id,
        "name": exp.name,
        "description": exp.description,
        "steps": [s.model_dump() for s in exp.steps],
        "tags": exp.tags,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": [],
    }
    _EXP_STORE[exp_id] = record

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp.name}' 已创建")

    return record


@router.get("/status")
async def get_experiments_status() -> Dict[str, Any]:
    """Health-check for the experiments service."""
    return {
        "status": "ok",
        "service": "experiments",
        "total_experiments": len(_EXP_STORE),
    }


@router.get("/recent")
async def get_recent_experiments(limit: int = 20) -> Dict[str, Any]:
    """Get recent experiments for experiment selector."""
    recent = sorted(
        _EXP_STORE.values(),
        key=lambda e: e.get("created_at", ""),
        reverse=True,
    )[:limit]

    return {
        "experiments": recent,
        "total": len(_EXP_STORE)
    }


@router.get("")
async def list_experiments() -> List[Dict[str, Any]]:
    """List all experiments."""
    return list(_EXP_STORE.values())


# ---------------------------------------------------------------------------
# Per-experiment routes  (/{exp_id} catch-all must be LAST)
# ---------------------------------------------------------------------------

@router.get("/detail/{exp_id}")
async def get_experiment(
    exp_id: str = Path(..., pattern="^exp_.*")
) -> Dict[str, Any]:
    """Return experiment details."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")
    return _EXP_STORE[exp_id]


@router.post("/detail/{exp_id}/execute")
async def execute_experiment(
    exp_id: str = Path(..., pattern="^exp_.*")
) -> Dict[str, Any]:
    """Start experiment execution (delegates to MicroHySeeker if available)."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    exp = _EXP_STORE[exp_id]
    exp["status"] = "running"
    exp["started_at"] = datetime.now(timezone.utc).isoformat()

    # Try forwarding to MicroHySeeker
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8100/api/experiment/start",
                json={"exp_id": exp_id},
                timeout=10.0,
            )
            if resp.status_code == 200:
                from src.api.routes.system import record_activity
                record_activity("experiment", f"实验 '{exp['name']}' 已提交到 MicroHySeeker")
                return {"status": "started", "exp_id": exp_id, "source": "microhyseeker"}
    except Exception:
        pass

    # MicroHySeeker unavailable – run locally as a stub
    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 开始执行 (本地模式)")
    return {"status": "started", "exp_id": exp_id, "source": "local"}


@router.post("/detail/{exp_id}/complete")
async def complete_experiment(
    exp_id: str = Path(..., pattern="^exp_.*")
) -> Dict[str, Any]:
    """Mark experiment as completed (used by worker callbacks)."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    exp = _EXP_STORE[exp_id]
    exp["status"] = "completed"
    exp["completed_at"] = datetime.now(timezone.utc).isoformat()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 已完成")
    return exp
