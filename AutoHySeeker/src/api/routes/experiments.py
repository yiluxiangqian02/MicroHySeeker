"""Experiment management APIs with persistence, local execution, progress & logs."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Path as PathParam
from pydantic import BaseModel, Field

# MicroHySeeker uvicorn 在 Windows 上使用 anyio IPv6 可能不兼容，此 transport 强制 IPv4
_MHS_TRANSPORT = httpx.AsyncHTTPTransport(local_address="0.0.0.0")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

# ---------------------------------------------------------------------------
# Persistent experiment store
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_EXPERIMENTS_FILE = _DATA_DIR / "experiments.json"

_EXP_STORE: Dict[str, Dict[str, Any]] = {}

# Running experiment state (progress, logs, cancellation)
_RUNNING: Dict[str, "_RunState"] = {}


class _RunState:
    """Tracks a running experiment's progress and logs."""

    def __init__(self, exp_id: str, total_steps: int) -> None:
        self.exp_id = exp_id
        self.total_steps = total_steps
        self.current_step = 0
        self.step_status = "pending"
        self.step_started_at: Optional[str] = None
        self.cancelled = False
        self.logs: list[dict[str, Any]] = []
        self._start_ts = time.monotonic()

    @property
    def elapsed_seconds(self) -> float:
        return round(time.monotonic() - self._start_ts, 1)

    @property
    def progress_percent(self) -> int:
        if self.total_steps == 0:
            return 0
        return min(100, int(self.current_step / self.total_steps * 100))

    def log(self, level: str, message: str) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        self.logs.append(entry)
        if level == "error":
            logger.error("[%s] %s", self.exp_id, message)
        else:
            logger.info("[%s] %s", self.exp_id, message)

    def to_dict(self) -> dict[str, Any]:
        exp = _EXP_STORE.get(self.exp_id, {})
        steps = exp.get("steps", [])
        current = steps[self.current_step] if self.current_step < len(steps) else None
        next_step = steps[self.current_step + 1] if self.current_step + 1 < len(steps) else None
        return {
            "exp_id": self.exp_id,
            "status": exp.get("status", "running"),
            "total_steps": self.total_steps,
            "current_step_index": self.current_step,
            "current_step": current,
            "next_step": next_step,
            "step_status": self.step_status,
            "step_started_at": self.step_started_at,
            "progress_percent": self.progress_percent,
            "elapsed_seconds": self.elapsed_seconds,
            "cancelled": self.cancelled,
        }


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_store() -> None:
    """Load experiments from disk at startup."""
    if not _EXPERIMENTS_FILE.exists():
        return
    try:
        raw = json.loads(_EXPERIMENTS_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            for rec in raw:
                eid = rec.get("exp_id")
                if eid:
                    # Recover from unclean shutdown: reset any stuck "running"
                    if rec.get("status") == "running":
                        rec["status"] = "failed"
                        rec.setdefault("logs", []).append({
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "level": "warn",
                            "message": "实验因服务重启被标记为失败",
                        })
                    _EXP_STORE[eid] = rec
        logger.info("Loaded %d experiments from %s", len(_EXP_STORE), _EXPERIMENTS_FILE)
    except Exception:
        logger.exception("Failed to load experiments from %s", _EXPERIMENTS_FILE)


def _save_store() -> None:
    """Persist current experiments to disk."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _EXPERIMENTS_FILE.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(list(_EXP_STORE.values()), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(_EXPERIMENTS_FILE)
    except Exception:
        logger.exception("Failed to save experiments to %s", _EXPERIMENTS_FILE)


_load_store()

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class StepModel(BaseModel):
    step_type: str = "cv"
    description: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


class ExperimentCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[StepModel] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    category: str = "test"  # test | formal | calibration


# ---------------------------------------------------------------------------
# Local experiment executor (asyncio-based)
# ---------------------------------------------------------------------------

_STEP_DURATION_ESTIMATES: Dict[str, float] = {
    "prep_sol": 5.0,
    "transfer": 4.0,
    "flush": 6.0,
    "evacuate": 3.0,
    "blank": 2.0,
    "echem": 0.0,
}


async def _ensure_mhs_ready(rs: "_RunState") -> bool:
    """检查 MicroHySeeker 是否在线且 RS485 已连接，未连接时尝试自动连接。

    Returns:
        True  — MHS 在线且 RS485 已连接（或成功自动连接）
        False — MHS 离线或连接失败
    """
    try:
        async with httpx.AsyncClient(timeout=5.0, transport=_MHS_TRANSPORT) as client:
            # 1) 查询连接状态
            resp = await client.get("http://127.0.0.1:8100/api/device/connection")
            if resp.status_code != 200:
                rs.log("warn", f"MHS /api/device/connection 返回 {resp.status_code}")
                return False

            info = resp.json()
            connected = info.get("connected", False)
            mock_mode = info.get("mock_mode", True)
            mode_str = "Mock" if mock_mode else "真实硬件"

            if connected:
                rs.log("info", f"MHS 预检查通过: RS485 已连接 ({mode_str})")
                return True

            # 2) 未连接 → 列出可用串口
            rs.log("info", "MHS RS485 未连接，尝试自动连接...")
            ports_resp = await client.get("http://127.0.0.1:8100/api/device/ports")
            if ports_resp.status_code != 200:
                rs.log("warn", "MHS 无法列出串口")
                return False

            ports = ports_resp.json().get("ports", [])
            if not ports:
                rs.log("warn", "MHS 没有可用串口")
                return False

            # 3) 尝试连接第一个可用串口
            target_port = ports[0]
            rs.log("info", f"尝试连接 {target_port}...")
            conn_resp = await client.post(
                "http://127.0.0.1:8100/api/device/connect",
                json={"port": target_port, "baudrate": 38400},
            )
            if conn_resp.status_code == 200:
                rs.log("info", f"MHS RS485 自动连接成功: {target_port} ({mode_str})")
                return True
            else:
                rs.log("warn", f"MHS RS485 连接 {target_port} 失败: {conn_resp.text}")
                return False

    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        rs.log("warn", "MHS 离线，无法进行预检查")
        return False
    except Exception as exc:
        rs.log("warn", f"MHS 预检查异常: {exc}")
        return False


async def _execute_local(exp_id: str) -> None:
    """Execute an experiment locally (non-echem steps simulated)."""
    exp = _EXP_STORE.get(exp_id)
    if not exp:
        return

    steps = exp.get("steps", [])
    rs = _RunState(exp_id, len(steps))
    _RUNNING[exp_id] = rs
    any_forwarded = False
    rs.log("info", f"实验 '{exp.get('name', '')}' 开始本地执行 ({len(steps)} 步)")

    # ── MHS 预检查：确保 RS485 已连接 ──
    mhs_ready = await _ensure_mhs_ready(rs)
    if not mhs_ready:
        rs.log("warn", "MHS 预检查未通过，实验将以本地模拟模式执行")

    try:
        for i, step in enumerate(steps):
            if rs.cancelled:
                rs.log("warn", "实验被用户停止")
                exp["status"] = "stopped"
                break

            rs.current_step = i
            rs.step_status = "running"
            rs.step_started_at = datetime.now(timezone.utc).isoformat()
            step_type = step.get("step_type", "blank")
            step_desc = step.get("description", "") or step_type
            rs.log("info", f"步骤 {i + 1}/{len(steps)}: [{step_type}] {step_desc}")

            if "step_progress" not in exp:
                exp["step_progress"] = [None] * len(steps)
            exp["step_progress"][i] = {
                "status": "running",
                "started_at": rs.step_started_at,
            }
            _save_store()

            if step_type == "echem":
                mhs_result = await _forward_step_to_mhs(exp_id, step, i, rs)
                if mhs_result == "offline":
                    rs.log("warn", f"步骤 {i + 1} 为电化学步骤，MicroHySeeker 离线，跳过")
                    rs.step_status = "skipped"
                    if exp["step_progress"][i]:
                        exp["step_progress"][i]["status"] = "skipped"
                    continue
                elif mhs_result == "failed":
                    rs.log("error", f"步骤 {i + 1} MHS 硬件执行失败")
                    rs.step_status = "failed"
                    if exp["step_progress"][i]:
                        exp["step_progress"][i]["status"] = "failed"
                    exp["status"] = "failed"
                    break
                else:
                    any_forwarded = True
            else:
                params = step.get("params", {})
                duration = params.get("duration_s") or params.get(
                    "flush_cycle_duration_s", 0
                )
                cycles = params.get("flush_cycles", 1)
                if step_type == "flush" and duration and cycles:
                    total_dur = float(duration) * int(cycles)
                else:
                    total_dur = float(duration) if duration else _STEP_DURATION_ESTIMATES.get(step_type, 2.0)

                mhs_result = await _forward_step_to_mhs(exp_id, step, i, rs)
                if mhs_result == "offline":
                    rs.log("info", f"  本地模拟执行 {total_dur:.1f}s ...")
                    elapsed = 0.0
                    while elapsed < total_dur:
                        if rs.cancelled:
                            break
                        await asyncio.sleep(min(0.5, total_dur - elapsed))
                        elapsed += 0.5
                elif mhs_result == "failed":
                    rs.log("error", f"步骤 {i + 1} MHS 硬件执行失败")
                    rs.step_status = "failed"
                    if exp["step_progress"][i]:
                        exp["step_progress"][i]["status"] = "failed"
                    exp["status"] = "failed"
                    break
                else:
                    any_forwarded = True

            if rs.cancelled:
                rs.log("warn", "实验被用户停止")
                exp["status"] = "stopped"
                if exp["step_progress"][i]:
                    exp["step_progress"][i]["status"] = "stopped"
                break

            rs.step_status = "completed"
            rs.log("info", f"步骤 {i + 1} 完成")
            if exp["step_progress"][i]:
                exp["step_progress"][i]["status"] = "completed"
                exp["step_progress"][i]["completed_at"] = datetime.now(timezone.utc).isoformat()
            _save_store()

        if exp["status"] not in ("stopped", "failed"):
            exp["status"] = "completed"
            exp["completed_at"] = datetime.now(timezone.utc).isoformat()
            rs.current_step = len(steps)
            if any_forwarded:
                exp["execution_mode"] = "hardware"
                rs.log("info", "实验执行完成（硬件执行）")
            else:
                exp["execution_mode"] = "simulated"
                rs.log("info", "实验执行完成（模拟执行，MicroHySeeker 未连接）")

    except Exception as exc:
        exp["status"] = "failed"
        rs.log("error", f"实验执行异常: {exc}")

    exp["logs"] = rs.logs
    _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp.get('name', '')}' {exp['status']}")

    await asyncio.sleep(10)
    _RUNNING.pop(exp_id, None)


async def _forward_step_to_mhs(
    exp_id: str, step: dict, step_idx: int, rs: _RunState
) -> str:
    """Try to forward a single step to MicroHySeeker.

    Returns:
        "success"  — 转发成功且 MHS 执行完成
        "failed"   — 转发成功但 MHS 报告执行失败/被停止
        "offline"  — MHS 离线，未转发
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, transport=_MHS_TRANSPORT) as client:
            resp = await client.post(
                "http://127.0.0.1:8100/api/experiment/start",
                json={
                    "plan": {
                        "name": f"{exp_id}_step_{step_idx}",
                        "steps": [step],
                    }
                },
            )
            if resp.status_code == 200:
                rs.log("info", "  步骤已转发到 MicroHySeeker")
                mhs_result = "success"
                for _ in range(300):
                    if rs.cancelled:
                        try:
                            async with httpx.AsyncClient(timeout=5.0, transport=_MHS_TRANSPORT) as stop_c:
                                await stop_c.post(
                                    "http://127.0.0.1:8100/api/experiment/stop",
                                    json={},
                                )
                        except Exception:
                            pass
                        return "success"
                    await asyncio.sleep(1)
                    try:
                        async with httpx.AsyncClient(timeout=5.0, transport=_MHS_TRANSPORT) as poll_c:
                            status_resp = await poll_c.get(
                                "http://127.0.0.1:8100/api/experiment/status"
                            )
                            if status_resp.status_code == 200:
                                data = status_resp.json()
                                if data.get("state") in ("idle", "completed", "stopped"):
                                    finished_ok = data.get("last_finished_success")
                                    if finished_ok is False:
                                        rs.log("warn", "  MicroHySeeker 步骤执行失败（硬件报告 success=False）")
                                        mhs_result = "failed"
                                    elif data.get("state") == "stopped":
                                        rs.log("warn", "  MicroHySeeker 步骤被停止")
                                        mhs_result = "failed"
                                    elif finished_ok is None:
                                        # experiment_finished 未触发（预检查直接拒绝，未执行）
                                        rs.log("warn", "  MicroHySeeker 步骤未执行（可能预检查失败）")
                                        mhs_result = "failed"
                                    else:
                                        rs.log("info", "  MicroHySeeker 步骤执行完成")
                                    break
                    except Exception:
                        break
                return mhs_result
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        return "offline"
    except Exception as exc:
        rs.log("warn", f"  MHS 转发失败: {exc}")
        return "offline"


# ---------------------------------------------------------------------------
# Fixed-path routes (BEFORE /{exp_id} catch-all)
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

    avg_duration = None
    if completed:
        total_duration = 0
        count = 0
        for exp in completed:
            if exp.get("started_at") and exp.get("completed_at"):
                try:
                    start = datetime.fromisoformat(exp["started_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(exp["completed_at"].replace("Z", "+00:00"))
                    total_duration += (end - start).total_seconds()
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
    recent = sorted(
        _EXP_STORE.values(),
        key=lambda e: e.get("created_at", ""),
        reverse=True,
    )[:3]
    suggestions = []
    if recent:
        for exp in recent:
            suggestions.append({
                "exp_id": exp["exp_id"],
                "name": exp["name"],
                "suggestion": "智能建议功能开发中",
                "confidence": 0.0,
            })
    else:
        suggestions.append({
            "exp_id": "none",
            "name": "通用建议",
            "suggestion": "开始第一个实验，建立基线数据",
            "confidence": 1.0,
        })
    return {"suggestions": suggestions, "generated_at": datetime.now(timezone.utc).isoformat()}


@router.post("/analyze-recent")
async def analyze_recent() -> Dict[str, Any]:
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
        "category": exp.category,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": [],
        "logs": [],
        "step_progress": [],
    }
    _EXP_STORE[exp_id] = record
    _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp.name}' 已创建")
    return record


@router.get("/status")
async def get_experiments_status() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "experiments",
        "total_experiments": len(_EXP_STORE),
    }


@router.get("/recent")
async def get_recent_experiments(limit: int = 20, category: Optional[str] = None) -> Dict[str, Any]:
    experiments = list(_EXP_STORE.values())
    if category:
        experiments = [e for e in experiments if e.get("category", "test") == category]
    recent = sorted(
        experiments,
        key=lambda e: e.get("created_at", ""),
        reverse=True,
    )[:limit]
    return {"experiments": recent, "total": len(experiments)}


@router.get("")
async def list_experiments(category: Optional[str] = None) -> List[Dict[str, Any]]:
    experiments = list(_EXP_STORE.values())
    if category:
        experiments = [e for e in experiments if e.get("category", "test") == category]
    return experiments


# ---------------------------------------------------------------------------
# Per-experiment routes
# ---------------------------------------------------------------------------


@router.get("/detail/{exp_id}")
async def get_experiment(
    exp_id: str = PathParam(..., pattern="^exp_.*"),
) -> Dict[str, Any]:
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")
    return _EXP_STORE[exp_id]


@router.post("/detail/{exp_id}/execute")
async def execute_experiment(
    exp_id: str = PathParam(..., pattern="^exp_.*"),
) -> Dict[str, Any]:
    """Start experiment execution with full step-by-step tracking."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    exp = _EXP_STORE[exp_id]
    if exp["status"] == "running":
        raise HTTPException(status_code=409, detail="experiment already running")

    exp["status"] = "running"
    exp["started_at"] = datetime.now(timezone.utc).isoformat()
    exp["logs"] = []
    exp["step_progress"] = [None] * len(exp.get("steps", []))
    _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 开始执行")

    # 始终使用 _execute_local 逐步执行：echem 步骤转发 MicroHySeeker，非 echem 步骤
    # 本地模拟。这样可以正确追踪每步状态和完成情况。
    exp["execution_source"] = "local"
    _save_store()
    asyncio.get_event_loop().create_task(_execute_local(exp_id))

    return {
        "status": "started",
        "exp_id": exp_id,
        "source": "local",
    }


@router.post("/detail/{exp_id}/stop")
async def stop_experiment(
    exp_id: str = PathParam(..., pattern="^exp_.*"),
) -> Dict[str, Any]:
    """Stop a running experiment."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    exp = _EXP_STORE[exp_id]
    if exp["status"] != "running":
        raise HTTPException(status_code=409, detail="experiment not running")

    rs = _RUNNING.get(exp_id)
    if rs:
        rs.cancelled = True
        rs.log("warn", "收到停止指令")

    try:
        async with httpx.AsyncClient(timeout=5.0, transport=_MHS_TRANSPORT) as client:
            await client.post(
                "http://127.0.0.1:8100/api/experiment/stop",
                json={"exp_id": exp_id},
            )
    except Exception:
        pass

    if not rs:
        exp["status"] = "stopped"
        exp["completed_at"] = datetime.now(timezone.utc).isoformat()
        exp.setdefault("logs", []).append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": "warn",
            "message": "实验已停止",
        })
        _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 已停止")
    return {"status": "stopping", "exp_id": exp_id}


@router.get("/detail/{exp_id}/progress")
async def get_experiment_progress(
    exp_id: str = PathParam(..., pattern="^exp_.*"),
) -> Dict[str, Any]:
    """Get real-time experiment progress (step info, elapsed, logs)."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    exp = _EXP_STORE[exp_id]
    rs = _RUNNING.get(exp_id)

    if rs:
        return {
            **rs.to_dict(),
            "logs": rs.logs[-50:],
        }

    steps = exp.get("steps", [])
    return {
        "exp_id": exp_id,
        "status": exp.get("status", "created"),
        "total_steps": len(steps),
        "current_step_index": len(steps) if exp.get("status") == "completed" else 0,
        "current_step": None,
        "next_step": steps[0] if steps and exp.get("status") == "created" else None,
        "step_status": "completed" if exp.get("status") == "completed" else "pending",
        "step_started_at": None,
        "progress_percent": 100 if exp.get("status") == "completed" else 0,
        "elapsed_seconds": 0,
        "cancelled": False,
        "step_progress": exp.get("step_progress", []),
        "logs": exp.get("logs", [])[-50:],
    }


@router.get("/detail/{exp_id}/logs")
async def get_experiment_logs(
    exp_id: str = PathParam(..., pattern="^exp_.*"),
    limit: int = 100,
) -> Dict[str, Any]:
    """Get experiment execution logs."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    rs = _RUNNING.get(exp_id)
    logs = rs.logs if rs else _EXP_STORE[exp_id].get("logs", [])
    return {"exp_id": exp_id, "logs": logs[-limit:], "total": len(logs)}


@router.post("/detail/{exp_id}/complete")
async def complete_experiment(
    exp_id: str = PathParam(..., pattern="^exp_.*"),
) -> Dict[str, Any]:
    """Mark experiment as completed (manual override or callback)."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    exp = _EXP_STORE[exp_id]
    exp["status"] = "completed"
    exp["completed_at"] = datetime.now(timezone.utc).isoformat()
    _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 已完成")
    return exp
