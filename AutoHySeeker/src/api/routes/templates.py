"""实验模板管理 API 路由"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.common.config import DATA_ROOT
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api")


# ─────────────────────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────────────────────

class StepTemplate(BaseModel):
    """实验步骤模板"""
    step_type: str = Field(..., description="步骤类型: cv/lsv/eis/prep_sol/flush/transfer/blank/evacuate")
    description: str = Field(default="", description="步骤描述")
    params: dict = Field(default_factory=dict, description="步骤参数")


class ExperimentTemplate(BaseModel):
    """实验模板"""
    template_id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    description: str = Field(default="", description="模板描述")
    steps: List[StepTemplate] = Field(default_factory=list, description="步骤列表")
    tags: List[str] = Field(default_factory=list, description="标签")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CreateTemplateRequest(BaseModel):
    """创建模板请求"""
    name: str
    description: str = ""
    steps: List[StepTemplate]
    tags: List[str] = []


class UpdateTemplateRequest(BaseModel):
    """更新模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[StepTemplate]] = None
    tags: Optional[List[str]] = None


# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def _get_templates_dir() -> Path:
    """获取模板目录"""
    templates_dir = DATA_ROOT.parent / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def _load_template(template_id: str) -> ExperimentTemplate:
    """加载模板"""
    templates_dir = _get_templates_dir()
    template_file = templates_dir / f"{template_id}.json"
    
    if not template_file.exists():
        # 文件名可能不是 template_id（如中文名），扫描目录找匹配的 id 字段
        for candidate in templates_dir.glob("*.json"):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == template_id or data.get("template_id") == template_id:
                    template_file = candidate
                    break
            except Exception:
                continue
        else:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 兼容 MHS 格式 (id → template_id)
        if "template_id" not in data and "id" in data:
            data["template_id"] = data.pop("id")
        if "template_id" not in data:
            data["template_id"] = template_file.stem
        # 兼容 MHS ProgStep 格式 → AHS StepTemplate
        if data.get("steps") and isinstance(data["steps"], list):
            converted: list = []
            for s in data["steps"]:
                if "params" not in s:
                    converted.append({
                        "step_type": s.get("step_type", "blank"),
                        "description": s.get("notes", "") or s.get("step_type", ""),
                        "params": s,
                    })
                else:
                    converted.append(s)
            data["steps"] = converted
        return ExperimentTemplate(**data)
    except Exception as e:
        logger.exception("Failed to load template %s: %s", template_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to load template: {e}")


def _save_template(template: ExperimentTemplate) -> None:
    """保存模板"""
    templates_dir = _get_templates_dir()
    template_file = templates_dir / f"{template.template_id}.json"
    
    try:
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info("Saved template %s to %s", template.template_id, template_file)
    except Exception as e:
        logger.exception("Failed to save template %s: %s", template.template_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to save template: {e}")


def _delete_template_file(template_id: str) -> None:
    """删除模板文件"""
    templates_dir = _get_templates_dir()
    template_file = templates_dir / f"{template_id}.json"
    
    if template_file.exists():
        template_file.unlink()
        logger.info("Deleted template file %s", template_file)


# ─────────────────────────────────────────────────────────────────────────────
# API 路由
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[ExperimentTemplate])
async def list_templates(
    tag: Optional[str] = None,
    limit: int = 100
) -> List[ExperimentTemplate]:
    """列出所有模板（本地 + MHS 远程）。
    
    Args:
        tag: 按标签过滤（可选）
        limit: 返回数量限制
    """
    templates_dir = _get_templates_dir()
    templates = []
    seen_ids: set = set()
    
    for template_file in templates_dir.glob("*.json"):
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 兼容 MHS 格式 (id → template_id)
            if "template_id" not in data and "id" in data:
                data["template_id"] = data.pop("id")
            if "template_id" not in data:
                data["template_id"] = template_file.stem
            # 兼容 MHS ProgStep 格式 → AHS StepTemplate
            if data.get("steps") and isinstance(data["steps"], list):
                converted: list = []
                for s in data["steps"]:
                    if "params" not in s:
                        # MHS flat step → wrap in StepTemplate
                        converted.append({
                            "step_type": s.get("step_type", "blank"),
                            "description": s.get("notes", "") or s.get("step_type", ""),
                            "params": s,
                        })
                    else:
                        converted.append(s)
                data["steps"] = converted
            template = ExperimentTemplate(**data)
            
            # 标签过滤
            if tag and tag not in template.tags:
                continue
            
            templates.append(template)
            seen_ids.add(template.template_id)
            # 将 mhs_ 前缀版本也加入去重集合，避免重复显示 MHS 同名模板
            seen_ids.add(f"mhs_{template.template_id}")
        except Exception as e:
            logger.warning("Failed to load template %s: %s", template_file, e)
            continue
    
    # 按更新时间倒序排序
    templates.sort(key=lambda t: t.updated_at, reverse=True)
    
    return templates[:limit]


@router.get("/templates/{template_id}", response_model=ExperimentTemplate)
async def get_template(template_id: str) -> ExperimentTemplate:
    """获取模板详情"""
    return _load_template(template_id)


@router.post("/templates", response_model=ExperimentTemplate)
async def create_template(request: CreateTemplateRequest) -> ExperimentTemplate:
    """创建新模板"""
    # 生成模板ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    template_id = f"tmpl_{timestamp}"
    
    # 创建模板对象
    template = ExperimentTemplate(
        template_id=template_id,
        name=request.name,
        description=request.description,
        steps=request.steps,
        tags=request.tags,
    )
    
    # 保存
    _save_template(template)
    
    logger.info("Created template %s: %s", template_id, request.name)
    return template


@router.put("/templates/{template_id}", response_model=ExperimentTemplate)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest
) -> ExperimentTemplate:
    """更新模板"""
    # 加载现有模板
    template = _load_template(template_id)
    
    # 更新字段
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.steps is not None:
        template.steps = request.steps
    if request.tags is not None:
        template.tags = request.tags
    
    # 更新时间戳
    template.updated_at = datetime.now().isoformat()
    
    # 保存
    _save_template(template)
    
    logger.info("Updated template %s", template_id)
    return template


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str) -> dict:
    """删除模板"""
    # 检查模板是否存在
    _load_template(template_id)
    
    # 删除文件
    _delete_template_file(template_id)
    
    logger.info("Deleted template %s", template_id)
    return {"status": "ok", "template_id": template_id}


@router.post("/templates/{template_id}/instantiate")
async def instantiate_template(
    template_id: str,
    exp_name: Optional[str] = None,
    params_override: Optional[dict] = None
) -> dict:
    """从模板实例化实验 — 在实验存储中创建并返回实验。

    Args:
        template_id: 模板ID
        exp_name: 实验名称（可选，默认使用模板名称）
        params_override: 参数覆盖（可选）

    Returns:
        包含 experiment_id 和完整实验记录的 dict
    """
    # 加载模板
    template = _load_template(template_id)

    # 构建步骤列表
    steps_raw = [step.model_dump() for step in template.steps]
    if params_override:
        for i, step in enumerate(steps_raw):
            if str(i) in params_override:
                step.setdefault("params", {}).update(params_override[str(i)])

    # 通过实验路由创建实验（复用实验存储逻辑）
    from src.api.routes.experiments import _EXP_STORE, _save_store

    exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    record = {
        "exp_id": exp_id,
        "name": exp_name or template.name,
        "description": template.description,
        "steps": steps_raw,
        "tags": template.tags,
        "category": "test",
        "status": "created",
        "created_at": datetime.now().isoformat(),
        "data": [],
        "logs": [],
        "step_progress": [],
        "source_template": template_id,
    }
    _EXP_STORE[exp_id] = record
    _save_store()

    logger.info("Instantiated experiment %s from template %s", exp_id, template_id)
    return {"experiment_id": exp_id, **record}
