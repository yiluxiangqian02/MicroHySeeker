"""Knowledge-base query APIs backed by KnowledgeQuerySkill."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from src.skills.knowledge_query_skill import KnowledgeQuerySkill

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# ── In-memory ingest task store ───────────────────────────────────────────────
_ingest_tasks: dict[str, dict[str, Any]] = {}

_AUTOHYSEEKER_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MINERU_OUTPUT = _AUTOHYSEEKER_ROOT / "MinerU" / "output"
_DEFAULT_OPENVIKING_WORKSPACE = _AUTOHYSEEKER_ROOT / "OpenViking"


class IngestRequest(BaseModel):
    mineru_output_dir: str | None = None
    target_uri: str = "viking://resources/literature/mineru_pipeline/"
    batch_name: str = ""


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


# ── MinerU → OpenViking ingest pipeline ──────────────────────────────────────

def _run_mineru_pipeline(task_id: str, mineru_dir: Path, target_uri: str, batch_name: str) -> None:
    """Blocking worker executed inside asyncio.to_thread.

    Spawns a subprocess using the Python 3.11 venv that has engine.pyd compatible
    dependencies, instead of doing an in-process import (engine.pyd requires python311.dll).
    """
    import subprocess

    openviking_src = _DEFAULT_OPENVIKING_WORKSPACE
    venv311_python = openviking_src / ".venv311" / "Scripts" / "python.exe"
    run_script = _AUTOHYSEEKER_ROOT.parent / "run_mineru_import.py"

    # Fallback: try sys.executable if venv311 not found (non-Windows or already 3.11)
    python_exe = str(venv311_python) if venv311_python.exists() else __import__("sys").executable

    cmd = [
        python_exe,
        str(run_script),
        str(mineru_dir),
        "--workspace", str(openviking_src),
        "--target", target_uri,
    ]
    if batch_name:
        cmd += ["--batch-name", batch_name]

    _ingest_tasks[task_id]["status"] = "running"
    _ingest_tasks[task_id]["started_at"] = time.time()

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0:
            # Parse last JSON block from stdout
            output = proc.stdout
            import re
            m = re.search(r"\{.*\}", output, re.DOTALL)
            result = __import__("json").loads(m.group()) if m else {"raw": output}
            _ingest_tasks[task_id]["status"] = "completed"
            _ingest_tasks[task_id]["result"] = result
        else:
            _ingest_tasks[task_id]["status"] = "failed"
            _ingest_tasks[task_id]["error"] = proc.stderr or proc.stdout
    except Exception as exc:  # pragma: no cover
        _ingest_tasks[task_id]["status"] = "failed"
        _ingest_tasks[task_id]["error"] = str(exc)
    finally:
        _ingest_tasks[task_id]["finished_at"] = time.time()


@router.post("/ingest-mineru")
async def ingest_mineru(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Start a background MinerU → OpenViking import job."""
    raw_dir = request.mineru_output_dir
    mineru_dir = Path(raw_dir) if raw_dir else _DEFAULT_MINERU_OUTPUT

    if not mineru_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"MinerU output directory not found: {mineru_dir}",
        )

    # Reject if another import is already running
    running = [t for t in _ingest_tasks.values() if t.get("status") == "running"]
    if running:
        raise HTTPException(
            status_code=409,
            detail="An ingest job is already running. Please wait for it to finish.",
        )

    task_id = uuid.uuid4().hex[:12]
    _ingest_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "mineru_dir": str(mineru_dir),
        "target": request.target_uri,
        "created_at": time.time(),
    }

    # Run in a thread pool to avoid blocking the event loop
    background_tasks.add_task(
        _run_mineru_pipeline,
        task_id,
        mineru_dir,
        request.target_uri,
        request.batch_name,
    )

    return {"task_id": task_id, "status": "pending", "mineru_dir": str(mineru_dir)}


@router.get("/ingest-status")
async def get_ingest_status(task_id: str | None = Query(default=None)) -> dict[str, Any]:
    """Return status of an ingest task, or the most recent one."""
    if task_id:
        task = _ingest_tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task

    if not _ingest_tasks:
        return {"status": "idle", "tasks": []}

    tasks_list = sorted(_ingest_tasks.values(), key=lambda t: t.get("created_at", 0), reverse=True)
    latest = tasks_list[0]
    return {
        "latest": latest,
        "tasks": tasks_list[:10],
        "total": len(_ingest_tasks),
    }


@router.get("/ingest-default-dir")
async def get_default_ingest_dir() -> dict[str, Any]:
    """Return the resolved default MinerU output directory."""
    exists = _DEFAULT_MINERU_OUTPUT.exists()
    doc_count = 0
    if exists:
        doc_count = sum(1 for item in _DEFAULT_MINERU_OUTPUT.iterdir() if item.is_dir())
    return {
        "default_mineru_output": str(_DEFAULT_MINERU_OUTPUT),
        "exists": exists,
        "document_count": doc_count,
    }
