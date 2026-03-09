"""数据查询路由。

端点：
  GET /api/data/runs                              列出所有实验运行
  GET /api/data/runs/{run_id}                     获取单次运行详情
  GET /api/data/runs/{run_id}/files/{filename}    下载数据文件（CSV 等）
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

logger = logging.getLogger("microhyseeker.api.routes.data")
router = APIRouter()


def _get_bridge(request: Request):
    bridge = getattr(request.app.state, "bridge", None)
    if bridge is None:
        raise HTTPException(503, "API bridge not available")
    return bridge


def _get_data_dir(bridge) -> Path:
    return Path(bridge.get_data_dir())


# ── 辅助：遍历 data 目录，构建 run 列表 ─────────────────────────────────────

def _list_runs(data_dir: Path) -> List[Dict[str, Any]]:
    """扫描 data_dir/YYYY-MM-DD/TIMESTAMP_NAME/ 结构，返回 run 摘要列表。"""
    runs: List[Dict[str, Any]] = []
    if not data_dir.exists():
        return runs

    for date_dir in sorted(data_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for run_dir in sorted(date_dir.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            summary = _load_run_summary(run_dir)
            runs.append(summary)
    return runs


def _load_run_summary(run_dir: Path) -> Dict[str, Any]:
    """从运行目录加载或构造摘要。"""
    run_id = run_dir.name

    # 尝试读 summary.json
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        try:
            with open(summary_path, encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("run_id", run_id)
            data.setdefault("run_dir", str(run_dir))
            return data
        except Exception:
            pass

    # 尝试读 experiment.json 获取名称
    exp_name = run_id
    exp_path = run_dir / "experiment.json"
    if exp_path.exists():
        try:
            with open(exp_path, encoding="utf-8") as f:
                exp_data = json.load(f)
            exp_name = exp_data.get("exp_name", run_id)
        except Exception:
            pass

    # 推断完成状态
    status = "unknown"
    if (run_dir / "summary.json").exists():
        status = "completed"
    elif any(run_dir.rglob("*.csv")):
        status = "has_data"

    return {
        "run_id": run_id,
        "exp_name": exp_name,
        "status": status,
        "run_dir": str(run_dir),
        "date": run_dir.parent.name,
    }


def _get_run_dir(data_dir: Path, run_id: str) -> Optional[Path]:
    """在 data_dir 中查找 run_id 对应的目录。"""
    if not data_dir.exists():
        return None
    for date_dir in data_dir.iterdir():
        if not date_dir.is_dir():
            continue
        candidate = date_dir / run_id
        if candidate.is_dir():
            return candidate
    return None


def _list_data_files(run_dir: Path) -> List[str]:
    """列出运行目录中所有数据文件（CSV/JSON/PNG），返回相对路径列表。"""
    files = []
    for p in run_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".csv", ".json", ".png", ".txt"}:
            files.append(p.relative_to(run_dir).as_posix())
    return sorted(files)


# ── 端点 ──────────────────────────────────────────────────────────────────────

@router.get("/runs")
async def list_runs(
    limit: int = Query(default=50, ge=1, le=500),
    bridge=Depends(_get_bridge),
) -> Dict[str, Any]:
    """列出所有实验运行（按时间倒序）。"""
    data_dir = _get_data_dir(bridge)
    try:
        runs = _list_runs(data_dir)[:limit]
    except Exception as exc:
        logger.exception("list_runs failed")
        raise HTTPException(500, f"数据目录扫描失败: {exc}") from exc

    return {
        "total": len(runs),
        "runs": runs,
        "data_dir": str(data_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str, bridge=Depends(_get_bridge)) -> Dict[str, Any]:
    """获取单次运行详情。"""
    data_dir = _get_data_dir(bridge)
    run_dir = _get_run_dir(data_dir, run_id)
    if run_dir is None:
        raise HTTPException(404, f"运行 '{run_id}' 未找到")

    summary = _load_run_summary(run_dir)
    data_files = _list_data_files(run_dir)

    # 附加 experiment.json 内容（若存在）
    exp_dict: Dict[str, Any] = {}
    exp_path = run_dir / "experiment.json"
    if exp_path.exists():
        try:
            with open(exp_path, encoding="utf-8") as f:
                exp_dict = json.load(f)
        except Exception:
            pass

    return {
        "run_id": run_id,
        "summary": summary,
        "experiment": exp_dict,
        "data_files": data_files,
        "run_dir": str(run_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/runs/{run_id}/files/{filename:path}")
async def download_file(
    run_id: str,
    filename: str,
    bridge=Depends(_get_bridge),
) -> FileResponse:
    """下载运行数据文件（CSV / PNG / JSON）。

    `filename` 为相对于运行目录的路径，例如 `echem/step_000_CV.csv`。
    """
    data_dir = _get_data_dir(bridge)
    run_dir = _get_run_dir(data_dir, run_id)
    if run_dir is None:
        raise HTTPException(404, f"运行 '{run_id}' 未找到")

    # 路径穿越防护
    file_path = (run_dir / filename).resolve()
    if not str(file_path).startswith(str(run_dir.resolve())):
        raise HTTPException(400, "非法文件路径")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"文件 '{filename}' 不存在")

    # 根据扩展名设置 media_type
    media_types = {
        ".csv":  "text/csv",
        ".json": "application/json",
        ".png":  "image/png",
        ".txt":  "text/plain",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )
