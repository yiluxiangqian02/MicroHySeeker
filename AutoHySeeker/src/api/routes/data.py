"""Data access APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.tools.echem_reader import list_recent_experiments, read_experiment_dir

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/experiments")
async def get_experiments(limit: int = Query(10, ge=1, le=200)) -> dict[str, object]:
    items = list_recent_experiments(limit)
    return {"count": len(items), "items": items}


@router.get("/latest")
async def get_latest_experiment() -> dict[str, object]:
    items = list_recent_experiments(1)
    if not items:
        raise HTTPException(status_code=404, detail="no experiments found")
    latest = items[0]
    details = read_experiment_dir(latest["run_dir"])
    return {"latest": latest, "details": details}

