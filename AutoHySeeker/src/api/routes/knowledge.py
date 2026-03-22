"""Knowledge-base query APIs backed by KnowledgeQuerySkill."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.skills.knowledge_query_skill import KnowledgeQuerySkill

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _parse_partitions(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return items or None


def _parse_params_json(raw: str) -> dict[str, float]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="params must be valid JSON") from exc

    if not isinstance(parsed, dict) or not parsed:
        raise HTTPException(status_code=400, detail="params must be a non-empty object")

    result: dict[str, float] = {}
    for key, value in parsed.items():
        if not str(key).strip():
            raise HTTPException(status_code=400, detail="params keys must be non-empty")
        if isinstance(value, bool) or value is None:
            raise HTTPException(status_code=400, detail=f"params.{key} must be numeric")
        try:
            result[str(key)] = float(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"params.{key} must be numeric") from exc
    return result


@router.get("/search")
async def search_knowledge(
    query: str = Query(..., min_length=1),
    partitions: str | None = Query(default=None, description="Comma-separated partition names"),
    top_k: int = Query(default=5, ge=1, le=50),
) -> dict[str, Any]:
    skill = KnowledgeQuerySkill()
    items = await skill.search(
        query=query,
        partitions=_parse_partitions(partitions),
        top_k=top_k,
    )
    return {
        "query": query,
        "partitions": _parse_partitions(partitions),
        "count": len(items),
        "items": items,
    }


@router.get("/experiments")
async def get_similar_experiments(
    params: str = Query(..., description="JSON object of target composition, e.g. {\"Fe\":0.3}"),
    threshold: float = Query(default=0.8, ge=0.0, le=1.0),
    top_k: int = Query(default=5, ge=1, le=50),
    project_id: str | None = Query(default=None),
) -> dict[str, Any]:
    skill = KnowledgeQuerySkill()
    parsed_params = _parse_params_json(params)
    items = await skill.get_similar_experiments(
        params=parsed_params,
        threshold=threshold,
        top_k=top_k,
    )
    if project_id:
        items = [item for item in items if item.get("project_id") == project_id]

    return {
        "params": parsed_params,
        "threshold": threshold,
        "project_id": project_id,
        "count": len(items),
        "items": items,
    }


@router.get("/faults")
async def get_fault_history(
    fault_type: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=50),
) -> dict[str, Any]:
    skill = KnowledgeQuerySkill()
    items = await skill.get_fault_history(fault_type=fault_type, top_k=top_k)
    return {
        "fault_type": fault_type,
        "count": len(items),
        "items": items,
    }
