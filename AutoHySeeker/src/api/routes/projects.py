"""Project management APIs backed by configs/projects/*.toml."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.common.config import (
    PROJECT_ROOT,
    get_project_config,
    load_project_configs,
    reload_all_configs,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])

_current_project_id: str | None = None
_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ProjectCreateRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=500)
    target_metric: str = Field(default="overpotential_mV", min_length=1, max_length=100)
    direction: Literal["minimize", "maximize"] = "minimize"
    elements: list[str] = Field(default_factory=list)
    template_id: str = Field(default="tpl_her_standard", min_length=1, max_length=100)
    max_rounds: int = Field(default=20, ge=1, le=500)
    total_volume_ul: float = Field(default=1000.0, gt=0.0)
    search_space: dict[str, dict[str, float]]
    constraints: dict[str, Any] = Field(default_factory=dict)


def _projects_dir() -> Path:
    return PROJECT_ROOT / "configs" / "projects"


def _reload_configs() -> None:
    reload_all_configs()


def _load_projects(*, reload: bool = False) -> dict[str, dict[str, Any]]:
    return load_project_configs(reload=reload)


def _load_project(project_id: str, *, reload: bool = False) -> dict[str, Any] | None:
    return get_project_config(project_id, reload=reload)


def _ensure_valid_project_id(project_id: str) -> str:
    candidate = project_id.strip()
    if not candidate or not _PROJECT_ID_PATTERN.fullmatch(candidate):
        raise HTTPException(
            status_code=400,
            detail="project_id must match [A-Za-z0-9_-]+",
        )
    return candidate


def _normalise_elements(
    elements: list[str],
    search_space: dict[str, dict[str, float]],
) -> list[str]:
    keys = [key.strip() for key in elements if key.strip()] if elements else list(search_space.keys())
    deduped: list[str] = []
    for key in keys:
        if key not in deduped:
            deduped.append(key)

    if not deduped:
        raise HTTPException(status_code=400, detail="at least one element is required")

    missing = [item for item in deduped if item not in search_space]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"missing search_space entries for: {', '.join(missing)}",
        )
    return deduped


def _normalise_search_space(
    search_space: dict[str, dict[str, float]],
    elements: list[str],
) -> dict[str, dict[str, float]]:
    if not search_space:
        raise HTTPException(status_code=400, detail="search_space must not be empty")

    normalised: dict[str, dict[str, float]] = {}
    for element in elements:
        bounds = search_space.get(element)
        if not isinstance(bounds, dict):
            raise HTTPException(status_code=400, detail=f"search_space.{element} must be an object")

        minimum = _coerce_number(bounds.get("min"), field=f"search_space.{element}.min")
        maximum = _coerce_number(bounds.get("max"), field=f"search_space.{element}.max")
        if minimum >= maximum:
            raise HTTPException(
                status_code=400,
                detail=f"search_space.{element} requires min < max",
            )
        normalised[element] = {"min": minimum, "max": maximum}
    return normalised


def _coerce_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or value is None:
        raise HTTPException(status_code=400, detail=f"{field} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field} must be a number") from exc


def _coerce_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.12g}"
        return text if "." in text or "e" in text.lower() else f"{text}.0"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_project_toml(
    project_id: str,
    payload: ProjectCreateRequest,
    elements: list[str],
    search_space: dict[str, dict[str, float]],
) -> str:
    constraints = {
        "sum_equals": 1.0,
        "min_component": 0.05,
        "max_rpm": 300,
        "sum_tolerance": 0.001,
        **payload.constraints,
    }

    lines = [
        f'# 项目配置: {payload.name}',
        f'# 由 /api/projects 于 2026-03-19 创建',
        "",
        "[project]",
        f'id = {_coerce_scalar(project_id)}',
        f'name = {_coerce_scalar(payload.name)}',
        f'goal = {_coerce_scalar(payload.goal)}',
        "",
        "[optimization]",
        f"max_rounds = {payload.max_rounds}",
        f"target_metric = {_coerce_scalar(payload.target_metric)}",
        f"direction = {_coerce_scalar(payload.direction)}",
        f"template_id = {_coerce_scalar(payload.template_id)}",
        f"total_volume_ul = {_coerce_scalar(payload.total_volume_ul)}",
        "",
    ]

    for element in elements:
        bounds = search_space[element]
        lines.extend(
            [
                f"[search_space.{element}]",
                f"min = {_coerce_scalar(bounds['min'])}",
                f"max = {_coerce_scalar(bounds['max'])}",
                "",
            ]
        )

    lines.append("[constraints]")
    for key, value in constraints.items():
        lines.append(f"{key} = {_coerce_scalar(value)}")
    lines.append("")

    return "\n".join(lines)


def _pick_current_project_id(projects: dict[str, dict[str, Any]]) -> str | None:
    global _current_project_id
    if _current_project_id in projects:
        return _current_project_id
    if not projects:
        _current_project_id = None
        return None
    _current_project_id = next(iter(sorted(projects)))
    return _current_project_id


def _summarise_project(project_id: str, config: dict[str, Any], *, current_project_id: str | None) -> dict[str, Any]:
    project = config.get("project", {})
    optimization = config.get("optimization", {})
    search_space = config.get("search_space", {})
    constraints = config.get("constraints", {})
    return {
        "project_id": project_id,
        "name": project.get("name", project_id),
        "goal": project.get("goal", ""),
        "target_metric": optimization.get("target_metric", "overpotential_mV"),
        "direction": optimization.get("direction", "minimize"),
        "template_id": optimization.get("template_id", ""),
        "max_rounds": optimization.get("max_rounds"),
        "total_volume_ul": optimization.get("total_volume_ul"),
        "elements": list(search_space.keys()),
        "constraints": constraints,
        "is_current": project_id == current_project_id,
    }


@router.get("")
async def list_projects() -> dict[str, Any]:
    projects = _load_projects()
    current_project_id = _pick_current_project_id(projects)
    items = [
        _summarise_project(project_id, config, current_project_id=current_project_id)
        for project_id, config in sorted(projects.items())
    ]
    return {
        "count": len(items),
        "current_project_id": current_project_id,
        "items": items,
    }


@router.get("/current")
async def get_current_project() -> dict[str, Any]:
    projects = _load_projects()
    current_project_id = _pick_current_project_id(projects)
    if current_project_id is None:
        raise HTTPException(status_code=404, detail="no projects configured")
    config = projects[current_project_id]
    return {
        "current_project_id": current_project_id,
        "project": _summarise_project(
            current_project_id,
            config,
            current_project_id=current_project_id,
        ),
        "config": config,
    }


@router.post("", status_code=201)
async def create_project(req: ProjectCreateRequest) -> dict[str, Any]:
    project_id = _ensure_valid_project_id(req.project_id)
    existing = _load_project(project_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"project already exists: {project_id}")

    elements = _normalise_elements(req.elements, req.search_space)
    search_space = _normalise_search_space(req.search_space, elements)
    project_file = _projects_dir() / f"{project_id}.toml"
    project_file.parent.mkdir(parents=True, exist_ok=True)
    project_file.write_text(
        _render_project_toml(project_id, req, elements, search_space),
        encoding="utf-8",
    )

    _reload_configs()
    projects = _load_projects(reload=True)

    global _current_project_id
    if _current_project_id is None:
        _current_project_id = project_id

    config = projects.get(project_id)
    if config is None:
        raise HTTPException(status_code=500, detail="failed to load created project config")

    return {
        "status": "created",
        "current_project_id": _pick_current_project_id(projects),
        "project": _summarise_project(
            project_id,
            config,
            current_project_id=_current_project_id,
        ),
        "config_path": str(project_file),
    }


@router.post("/{project_id}/select")
async def select_project(project_id: str) -> dict[str, Any]:
    project_id = _ensure_valid_project_id(project_id)
    config = _load_project(project_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"unknown project: {project_id}")

    global _current_project_id
    _current_project_id = project_id

    return {
        "status": "selected",
        "current_project_id": project_id,
        "project": _summarise_project(
            project_id,
            config,
            current_project_id=project_id,
        ),
    }


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    project_id = _ensure_valid_project_id(project_id)
    config = _load_project(project_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"unknown project: {project_id}")

    projects = _load_projects()
    current_project_id = _pick_current_project_id(projects)
    return {
        "project": _summarise_project(
            project_id,
            config,
            current_project_id=current_project_id,
        ),
        "config": config,
    }
