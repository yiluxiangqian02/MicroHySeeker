"""实验模板 + 系统配置查询路由。

供 AutoHySeeker agents 使用：
  ── 模板管理 ──────────────────────────────────────────
  GET    /api/template/list              列出所有模板
  GET    /api/template/{id}              获取模板详情
  POST   /api/template/save              保存/更新模板
  DELETE /api/template/{id}              删除模板
  POST   /api/template/{id}/instantiate  从模板实例化并运行实验
  POST   /api/template/validate          验证实验参数

  ── 系统配置查询 ──────────────────────────────────────
  GET    /api/config/system              查询系统配置（泵/通道/端口）
  GET    /api/config/capabilities        查询系统能力摘要
  GET    /api/config/dilution-channels   查询配液通道列表
  GET    /api/config/flush-channels      查询清洗通道列表
  GET    /api/config/pumps               查询泵配置列表
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("microhyseeker.api.routes.template")
router = APIRouter()


def _get_bridge(request: Request):
    bridge = getattr(request.app.state, "bridge", None)
    if bridge is None:
        raise HTTPException(503, "API bridge not available")
    return bridge


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 请求模型 ──────────────────────────────────────────────────────────────────

class TemplateSaveRequest(BaseModel):
    """保存模板请求。"""
    name: str = Field(..., min_length=1, description="模板名称")
    description: str = Field("", description="模板描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    steps: List[Dict[str, Any]] = Field(..., description="步骤列表 (ProgStep dicts)")
    template_id: Optional[str] = Field(None, description="更新已有模板时提供 ID")


class InstantiateRequest(BaseModel):
    """从模板实例化实验的请求，可覆盖部分参数。"""
    overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="参数覆盖: {step_index: {field: value}} 或全局 {field: value}",
    )
    exp_name: Optional[str] = Field(None, description="实验名称 (默认使用模板名)")
    dry_run: bool = Field(False, description="仅验证不运行")


class ValidateRequest(BaseModel):
    """验证实验参数的请求。"""
    steps: List[Dict[str, Any]] = Field(..., description="步骤列表")


# ── 模板管理端点 ──────────────────────────────────────────────────────────────

@router.get("/list")
async def list_templates(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """列出所有实验模板 (按最近更新排序)。"""
    try:
        templates = bridge.template_list()
    except Exception as exc:
        raise HTTPException(500, f"列出模板失败: {exc}") from exc

    # 返回摘要列表（不含完整steps，减少传输量）
    summaries = []
    for t in templates:
        summaries.append({
            "id": t["id"],
            "name": t["name"],
            "description": t.get("description", ""),
            "tags": t.get("tags", []),
            "step_count": len(t.get("steps", [])),
            "step_types": [s.get("step_type", "unknown") for s in t.get("steps", [])],
            "created_at": t.get("created_at"),
            "updated_at": t.get("updated_at"),
        })

    return {"templates": summaries, "count": len(summaries), "timestamp": _ts()}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """获取模板完整详情（含所有步骤参数）。"""
    try:
        template = bridge.template_load(template_id)
    except Exception as exc:
        raise HTTPException(500, f"加载模板失败: {exc}") from exc

    if template is None:
        raise HTTPException(404, f"模板 {template_id} 不存在")

    return {**template, "timestamp": _ts()}


@router.post("/save")
async def save_template(
    body: TemplateSaveRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """保存或更新实验模板。"""
    try:
        template = bridge.template_save(
            name=body.name,
            description=body.description,
            tags=body.tags,
            steps=body.steps,
            template_id=body.template_id,
        )
    except Exception as exc:
        raise HTTPException(500, f"保存模板失败: {exc}") from exc

    return {
        "status": "saved",
        "template_id": template["id"],
        "name": template["name"],
        "timestamp": _ts(),
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """删除模板。"""
    try:
        success = bridge.template_delete(template_id)
    except Exception as exc:
        raise HTTPException(500, f"删除模板失败: {exc}") from exc

    if not success:
        raise HTTPException(404, f"模板 {template_id} 不存在")

    return {"status": "deleted", "template_id": template_id, "timestamp": _ts()}


@router.post("/{template_id}/instantiate")
async def instantiate_template(
    template_id: str,
    body: InstantiateRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """从模板实例化实验。

    流程：加载模板 → 应用参数覆盖 → 验证 → 运行（或仅验证）。
    
    overrides 格式：
    - 全局覆盖: {"exp_name": "新名称"}
    - 按步骤覆盖: {"step_overrides": {0: {"pump_rpm": 150}, 2: {"scan_rate": 0.05}}}
    """
    # 1. 加载模板
    template = bridge.template_load(template_id)
    if template is None:
        raise HTTPException(404, f"模板 {template_id} 不存在")

    # 2. 构建实验 dict
    try:
        exp_dict = bridge.template_instantiate(
            template=template,
            overrides=body.overrides,
            exp_name=body.exp_name,
        )
    except ValueError as exc:
        raise HTTPException(400, f"参数覆盖失败: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"实例化失败: {exc}") from exc

    # 3. 验证
    validation = bridge.template_validate(exp_dict.get("steps", []))
    if not validation["valid"]:
        return {
            "status": "validation_failed",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "experiment": exp_dict,
            "timestamp": _ts(),
        }

    # 4. dry_run 模式只返回实验配置
    if body.dry_run:
        return {
            "status": "validated",
            "experiment": exp_dict,
            "validation": validation,
            "timestamp": _ts(),
        }

    # 5. 运行实验
    try:
        run_id = bridge.start_experiment(exp_dict)
    except Exception as exc:
        raise HTTPException(500, f"启动实验失败: {exc}") from exc

    return {
        "status": "started",
        "run_id": run_id,
        "exp_name": exp_dict.get("exp_name", ""),
        "template_id": template_id,
        "validation": validation,
        "timestamp": _ts(),
    }


@router.post("/validate")
async def validate_experiment(
    body: ValidateRequest,
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """验证实验步骤参数是否合法。

    检查项：RPM范围、泵地址有效性、步骤类型有效性、电化学参数合理性。
    """
    try:
        result = bridge.template_validate(body.steps)
    except Exception as exc:
        raise HTTPException(500, f"验证失败: {exc}") from exc

    return {**result, "timestamp": _ts()}


# ── 系统配置查询端点 ──────────────────────────────────────────────────────────

@router.get("/config/system")
async def get_system_config(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询系统完整配置（泵列表、配液通道、清洗通道等）。

    Agent 在设计实验之前应先调用此接口了解系统能力。
    """
    try:
        config = bridge.config_get_system()
    except Exception as exc:
        raise HTTPException(500, f"查询失败: {exc}") from exc

    return {**config, "timestamp": _ts()}


@router.get("/config/capabilities")
async def get_capabilities(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询系统能力摘要。

    返回精简的系统能力描述，供 agent 快速了解可以做什么。
    """
    try:
        caps = bridge.config_get_capabilities()
    except Exception as exc:
        raise HTTPException(500, f"查询失败: {exc}") from exc

    return {**caps, "timestamp": _ts()}


@router.get("/config/dilution-channels")
async def get_dilution_channels(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询配液通道列表及其配置详情。"""
    try:
        channels = bridge.config_get_dilution_channels()
    except Exception as exc:
        raise HTTPException(500, f"查询失败: {exc}") from exc

    return {"channels": channels, "timestamp": _ts()}


@router.get("/config/flush-channels")
async def get_flush_channels(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询清洗通道列表及其配置详情。"""
    try:
        channels = bridge.config_get_flush_channels()
    except Exception as exc:
        raise HTTPException(500, f"查询失败: {exc}") from exc

    return {"channels": channels, "timestamp": _ts()}


@router.get("/config/pumps")
async def get_pumps(bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """查询泵配置列表。"""
    try:
        pumps = bridge.config_get_pumps()
    except Exception as exc:
        raise HTTPException(500, f"查询失败: {exc}") from exc

    return {"pumps": pumps, "timestamp": _ts()}
