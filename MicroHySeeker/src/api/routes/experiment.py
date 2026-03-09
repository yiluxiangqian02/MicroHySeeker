"""实验控制路由。

端点：
  POST /api/experiment/start    启动实验
  POST /api/experiment/stop     停止实验
  POST /api/experiment/pause    暂停实验
  POST /api/experiment/resume   恢复实验
  GET  /api/experiment/status   查询状态
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("microhyseeker.api.routes.experiment")
router = APIRouter()


def _get_bridge(request: Request):
    bridge = getattr(request.app.state, "bridge", None)
    if bridge is None:
        raise HTTPException(503, "API bridge not available")
    return bridge


# ── 请求/响应模型 ─────────────────────────────────────────────────────────────

class ProgStepPayload(BaseModel):
    step_index: int = 0
    step_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    expected_duration_s: Optional[float] = None


class ExperimentPlanPayload(BaseModel):
    """AutoHySeeker ExperimentPlan 格式（直接传入）。"""
    name: str
    description: str = ""
    steps: list[ProgStepPayload] = Field(default_factory=list)
    combo_params: Optional[Dict[str, Any]] = None
    tags: list[str] = Field(default_factory=list)


class StartRequest(BaseModel):
    """可接受两种格式：
    1. plan: ExperimentPlanPayload  — AutoHySeeker ExperimentPlan（自动转换）
    2. experiment: dict             — 已经是 MicroHySeeker Experiment dict
    """
    plan: Optional[ExperimentPlanPayload] = None
    experiment: Optional[Dict[str, Any]] = None


class RunIdRequest(BaseModel):
    run_id: Optional[str] = None


# ── 端点 ──────────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_experiment(
    body: StartRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """启动实验。

    - 若提供 `plan`（ExperimentPlan 格式），自动转换为 MicroHySeeker Experiment
    - 若提供 `experiment`（Experiment dict），直接使用
    """
    from src.api.bridge import plan_to_experiment

    if body.plan is not None:
        try:
            exp_dict = plan_to_experiment(body.plan.model_dump())
        except Exception as exc:
            logger.exception("plan_to_experiment failed")
            raise HTTPException(400, f"计划转换失败: {exc}") from exc
    elif body.experiment is not None:
        exp_dict = body.experiment
        # 补充缺失的 exp_id
        if not exp_dict.get("exp_id"):
            exp_dict["exp_id"] = f"api_{uuid.uuid4().hex[:8]}"
    else:
        raise HTTPException(422, "必须提供 'plan' 或 'experiment' 字段")

    try:
        run_id = bridge.start_experiment(exp_dict)
    except Exception as exc:
        logger.exception("start_experiment failed")
        raise HTTPException(500, f"启动失败: {exc}") from exc

    return {
        "run_id": run_id,
        "status": "started",
        "exp_name": exp_dict.get("exp_name", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/stop")
async def stop_experiment(
    body: RunIdRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """停止当前实验。"""
    try:
        bridge.stop_experiment()
    except Exception as exc:
        raise HTTPException(500, f"停止失败: {exc}") from exc

    return {
        "status": "stopped",
        "run_id": body.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/pause")
async def pause_experiment(
    body: RunIdRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """暂停当前实验。"""
    try:
        bridge.pause_experiment()
    except Exception as exc:
        raise HTTPException(500, f"暂停失败: {exc}") from exc

    return {
        "status": "paused",
        "run_id": body.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/resume")
async def resume_experiment(
    body: RunIdRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """恢复已暂停实验。"""
    try:
        bridge.resume_experiment()
    except Exception as exc:
        raise HTTPException(500, f"恢复失败: {exc}") from exc

    return {
        "status": "resumed",
        "run_id": body.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def get_status(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询实验引擎当前状态。"""
    try:
        status = bridge.get_status()
    except Exception as exc:
        raise HTTPException(500, f"状态查询失败: {exc}") from exc

    return {
        **status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
