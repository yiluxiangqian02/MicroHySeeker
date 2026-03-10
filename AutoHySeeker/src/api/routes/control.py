"""Experiment control API — start, pause, resume, stop, status."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MICROHYSEEKER_BASE = "http://localhost:8100"

router = APIRouter(prefix="/experiments", tags=["control"])


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ExperimentPlan(BaseModel):
    name: str
    description: str = ""
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class ExperimentStatus(BaseModel):
    exp_id: str
    status: str  # running/paused/stopped/completed/failed
    progress: float = Field(0.0, ge=0.0, le=1.0)
    current_step: int = 0
    total_steps: int = 0
    start_time: str = ""
    elapsed_time: float = 0.0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _call_microhyseeker(
    method: str,
    path: str,
    json: Dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Forward a request to MicroHySeeker and return the JSON response.

    Falls back gracefully when MicroHySeeker is not reachable so that the API
    remains testable without a live MicroHySeeker instance.
    """
    url = f"{MICROHYSEEKER_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                resp = await client.get(url)
            else:
                resp = await client.post(url, json=json or {})
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        logger.warning("MicroHySeeker unreachable at %s — returning offline stub", url)
        return {"status": "offline", "message": "MicroHySeeker not reachable"}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"MicroHySeeker error: {exc.response.text}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{exp_id}/start")
async def start_experiment(exp_id: str, plan: ExperimentPlan) -> Dict[str, Any]:
    """Start an experiment via MicroHySeeker."""
    experiment_dict = {
        "exp_id": exp_id,
        "name": plan.name,
        "description": plan.description,
        "steps": plan.steps,
        "tags": plan.tags,
    }
    logger.info("starting experiment %s", exp_id)
    result = await _call_microhyseeker("POST", "/api/experiment/start", json=experiment_dict)
    return {"exp_id": exp_id, **result}


@router.post("/{exp_id}/pause")
async def pause_experiment(exp_id: str) -> Dict[str, Any]:
    """Pause a running experiment."""
    logger.info("pausing experiment %s", exp_id)
    result = await _call_microhyseeker("POST", "/api/experiment/pause", json={"exp_id": exp_id})
    return {"exp_id": exp_id, "status": "paused", **result}


@router.post("/{exp_id}/resume")
async def resume_experiment(exp_id: str) -> Dict[str, Any]:
    """Resume a paused experiment."""
    logger.info("resuming experiment %s", exp_id)
    result = await _call_microhyseeker("POST", "/api/experiment/resume", json={"exp_id": exp_id})
    return {"exp_id": exp_id, "status": "running", **result}


@router.post("/{exp_id}/stop")
async def stop_experiment(exp_id: str) -> Dict[str, Any]:
    """Stop an experiment."""
    logger.info("stopping experiment %s", exp_id)
    result = await _call_microhyseeker("POST", "/api/experiment/stop", json={"exp_id": exp_id})
    return {"exp_id": exp_id, "status": "stopped", **result}


@router.get("/{exp_id}/status")
async def get_experiment_status(exp_id: str) -> Dict[str, Any]:
    """Get the current status of an experiment from MicroHySeeker."""
    result = await _call_microhyseeker("GET", "/api/system/status")
    return {"exp_id": exp_id, **result}
