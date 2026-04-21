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
# transport 不可跨 AsyncClient 复用，每次调用创建新实例
def _mhs_transport() -> httpx.AsyncHTTPTransport:
    return httpx.AsyncHTTPTransport(local_address="0.0.0.0")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

# ---------------------------------------------------------------------------
# Persistent experiment store
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_EXPERIMENTS_FILE = _DATA_DIR / "experiments.json"
# 共享数据目录（与 MHS 相同的 data/ 根），用于保存实验运行日志
_SHARED_DATA_DIR = Path(__file__).resolve().parents[4] / "data"

_EXP_STORE: Dict[str, Dict[str, Any]] = {}

# Running experiment state (progress, logs, cancellation)
_RUNNING: Dict[str, "_RunState"] = {}


class _RunState:
    """Tracks a running experiment's progress and logs."""

    def __init__(self, exp_id: str, total_steps: int, exp_name: str = "") -> None:
        self.exp_id = exp_id
        self.total_steps = total_steps
        self.current_step = 0
        self.step_status = "pending"
        self.step_started_at: Optional[str] = None
        self.cancelled = False
        self.logs: list[dict[str, Any]] = []
        self._start_ts = time.monotonic()
        self._start_dt = datetime.now()  # 本地时间
        # 创建运行数据文件夹: data/{date}/{date}_{time}_{name}_AHS/
        self.run_dir = self._create_run_dir(exp_name)
        self._log_file: Optional[Path] = None
        if self.run_dir:
            self._log_file = self.run_dir / "run_log.log"

    def _create_run_dir(self, exp_name: str) -> Optional[Path]:
        try:
            dt = self._start_dt
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H-%M-%S")
            safe_name = (exp_name or "unnamed").replace("/", "_").replace("\\", "_")[:60]
            folder_name = f"{date_str}_{time_str}_{safe_name}_AHS"
            run_dir = _SHARED_DATA_DIR / date_str / folder_name
            run_dir.mkdir(parents=True, exist_ok=True)
            return run_dir
        except Exception:
            logger.exception("Failed to create AHS run directory")
            return None

    @property
    def elapsed_seconds(self) -> float:
        return round(time.monotonic() - self._start_ts, 1)

    @property
    def progress_percent(self) -> int:
        if self.total_steps == 0:
            return 0
        return min(100, int(self.current_step / self.total_steps * 100))

    def log(self, level: str, message: str) -> None:
        now = datetime.now()
        entry = {
            "ts": now.isoformat(),
            "level": level,
            "message": message,
        }
        self.logs.append(entry)
        if level == "error":
            logger.error("[%s] %s", self.exp_id, message)
        else:
            logger.info("[%s] %s", self.exp_id, message)
        # 同步写入日志文件
        if self._log_file:
            try:
                ts_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                lvl = level.upper().ljust(7)
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{ts_str}] [{lvl}] {message}\n")
            except Exception:
                pass

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
                            "ts": datetime.now().isoformat(),
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

    优先使用 system.json 中配置的 rs485_port，而不是盲目连接第一个可用串口。

    Returns:
        True  — MHS 在线且 RS485 已连接（或成功自动连接）
        False — MHS 离线或连接失败
    """
    try:
        async with httpx.AsyncClient(timeout=5.0, transport=_mhs_transport()) as client:
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

            # 3) 从系统配置读取首选端口
            from src.api.routes.system import _load_system_config
            sys_cfg = _load_system_config()
            preferred_port = sys_cfg.get("rs485_port", "")
            baudrate = sys_cfg.get("rs485_baudrate", 38400)

            if preferred_port and preferred_port in ports:
                target_port = preferred_port
            else:
                if preferred_port:
                    rs.log("warn", f"配置的端口 {preferred_port} 不可用，使用第一个可用端口")
                target_port = ports[0]

            rs.log("info", f"尝试连接 {target_port} (波特率 {baudrate})...")
            conn_resp = await client.post(
                "http://127.0.0.1:8100/api/device/connect",
                json={"port": target_port, "baudrate": baudrate},
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


def _save_run_summary(rs: "_RunState", exp: dict, steps: list) -> None:
    """Save run_summary.json to the AHS run directory."""
    if not rs.run_dir:
        return
    try:
        summary = {
            "run_id": f"ahs_{rs._start_dt.strftime('%Y%m%d_%H%M%S')}",
            "exp_id": rs.exp_id,
            "exp_name": exp.get("name", ""),
            "started_at": rs._start_dt.isoformat(),
            "finished_at": datetime.now().isoformat(),
            "elapsed_seconds": rs.elapsed_seconds,
            "success": exp.get("status") == "completed",
            "status": exp.get("status", "unknown"),
            "total_steps": len(steps),
            "step_progress": exp.get("step_progress", []),
            "source": "AutoHySeeker",
        }
        (rs.run_dir / "run_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        logger.exception("Failed to save AHS run_summary.json")


async def _execute_local(exp_id: str) -> None:
    """Execute an experiment locally (non-echem steps simulated)."""
    exp = _EXP_STORE.get(exp_id)
    if not exp:
        return

    steps = exp.get("steps", [])
    rs = _RunState(exp_id, len(steps), exp.get("name", ""))
    _RUNNING[exp_id] = rs
    rs.log("info", f"实验 '{exp.get('name', '')}' 开始本地执行 ({len(steps)} 步)")
    if rs.run_dir:
        rs.log("info", f"运行数据目录: {rs.run_dir}")
        # 保存实验定义快照
        try:
            (rs.run_dir / "experiment.json").write_text(
                json.dumps(exp, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    # ── MHS 预检查：确保 RS485 已连接 ──
    mhs_ready = await _ensure_mhs_ready(rs)
    if not mhs_ready:
        rs.log("error", "MHS 预检查未通过，无法执行实验（MicroHySeeker 离线或 RS485 未连接）")
        exp["status"] = "failed"
        exp["logs"] = rs.logs
        if rs.run_dir:
            exp["run_dir"] = str(rs.run_dir)
        _save_store()
        _save_run_summary(rs, exp, steps)
        from src.api.routes.system import record_activity
        record_activity("experiment", f"实验 '{exp.get('name', '')}' 失败：MHS 离线")
        await asyncio.sleep(10)
        _RUNNING.pop(exp_id, None)
        return

    try:
        for i, step in enumerate(steps):
            if rs.cancelled:
                rs.log("warn", "实验被用户停止")
                exp["status"] = "stopped"
                break

            rs.current_step = i
            rs.step_status = "running"
            rs.step_started_at = datetime.now().isoformat()
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

            # 所有步骤统一转发 MHS
            mhs_result = await _forward_step_to_mhs(exp_id, step, i, rs)
            if mhs_result == "offline":
                detail_msg = f"步骤 {i + 1} [{step_type}] MicroHySeeker 离线，无法执行"
                rs.log("error", detail_msg)
                rs.step_status = "failed"
                if exp["step_progress"][i]:
                    exp["step_progress"][i]["status"] = "failed"
                exp["status"] = "failed"
                exp["error_detail"] = detail_msg
                break
            elif mhs_result == "failed":
                detail_msg = f"步骤 {i + 1} [{step_type}] MHS 硬件执行失败"
                rs.log("error", detail_msg)
                rs.step_status = "failed"
                if exp["step_progress"][i]:
                    exp["step_progress"][i]["status"] = "failed"
                exp["status"] = "failed"
                exp["error_detail"] = detail_msg
                break

            if rs.cancelled:
                rs.log("warn", "实验被用户停止")
                exp["status"] = "stopped"
                if exp["step_progress"][i]:
                    exp["step_progress"][i]["status"] = "stopped"
                break

            rs.step_status = "completed"
            rs.log("info", f"步骤 {i + 1} 完成 ✓")
            if exp["step_progress"][i]:
                exp["step_progress"][i]["status"] = "completed"
                exp["step_progress"][i]["completed_at"] = datetime.now().isoformat()
            _save_store()

        if exp["status"] not in ("stopped", "failed"):
            exp["status"] = "completed"
            exp["completed_at"] = datetime.now().isoformat()
            rs.current_step = len(steps)
            exp["execution_mode"] = "hardware"
            rs.log("info", f"实验执行完成 ✓ 共 {len(steps)} 步")

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        exp["status"] = "failed"
        exp["error_detail"] = f"{type(exc).__name__}: {exc}"
        rs.log("error", f"实验执行异常: {type(exc).__name__}: {exc}")
        rs.log("error", f"堆栈: {tb[-500:]}")

    exp["logs"] = rs.logs
    if rs.run_dir:
        exp["run_dir"] = str(rs.run_dir)
    _save_store()
    _save_run_summary(rs, exp, steps)

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
    # 构造符合 ProgStepPayload 格式的 step
    mhs_step = {
        "step_index": step_idx,
        "step_type": step.get("step_type", "blank"),
        "params": step.get("params", {}),
        "description": step.get("description", ""),
        "parallel_group": step.get("parallel_group", 0),
    }
    rs.log("info", f"  正在转发步骤到 MHS (step_type={mhs_step['step_type']})...")
    try:
        async with httpx.AsyncClient(timeout=15.0, transport=_mhs_transport()) as client:
            resp = await client.post(
                "http://127.0.0.1:8100/api/experiment/start",
                json={
                    "plan": {
                        "name": f"{exp_id}_step_{step_idx}",
                        "steps": [mhs_step],
                    }
                },
            )
            if resp.status_code == 200:
                rs.log("info", "  步骤已转发到 MicroHySeeker，等待执行...")
                mhs_result = "success"
                # 快照 MHS 已有日志，避免拉取历史日志
                _seen_log_hashes: set[str] = set()
                try:
                    async with httpx.AsyncClient(timeout=3.0, transport=_mhs_transport()) as snap_c:
                        snap_resp = await snap_c.get(
                            "http://127.0.0.1:8100/api/experiment/logs?n=500"
                        )
                        if snap_resp.status_code == 200:
                            for lg in snap_resp.json().get("logs", []):
                                _seen_log_hashes.add(str(lg))
                except Exception:
                    pass
                # 等待 Qt 信号处理 + 实验启动
                await asyncio.sleep(2)
                idle_none_count = 0
                ever_seen_running = False
                poll_error_count = 0
                for tick in range(600):  # 最多等待 600 秒
                    if rs.cancelled:
                        try:
                            async with httpx.AsyncClient(timeout=5.0, transport=_mhs_transport()) as stop_c:
                                await stop_c.post(
                                    "http://127.0.0.1:8100/api/experiment/stop",
                                    json={},
                                )
                        except Exception:
                            pass
                        return "success"
                    await asyncio.sleep(1)
                    try:
                        async with httpx.AsyncClient(timeout=5.0, transport=_mhs_transport()) as poll_c:
                            status_resp = await poll_c.get(
                                "http://127.0.0.1:8100/api/experiment/status"
                            )
                            if status_resp.status_code != 200:
                                poll_error_count += 1
                                if poll_error_count > 5:
                                    rs.log("error", f"  MHS 状态查询连续失败 {poll_error_count} 次")
                                continue
                            poll_error_count = 0
                            data = status_resp.json()
                            state = data.get("state", "idle")

                            # 每 5 秒拉取 MHS runner 日志
                            if tick % 5 == 0:
                                try:
                                    log_resp = await poll_c.get(
                                        "http://127.0.0.1:8100/api/experiment/logs?n=500"
                                    )
                                    if log_resp.status_code == 200:
                                        all_logs = log_resp.json().get("logs", [])
                                        for lg in all_logs:
                                            lg_hash = str(lg)
                                            if lg_hash not in _seen_log_hashes:
                                                _seen_log_hashes.add(lg_hash)
                                                rs.log("info", f"  [MHS] {lg}")
                                except Exception:
                                    pass

                            if state == "running":
                                idle_none_count = 0
                                ever_seen_running = True
                                continue
                            if state in ("idle", "completed", "stopped"):
                                finished_ok = data.get("last_finished_success")
                                # Qt 信号尚未处理或实验未启动，多等几秒
                                if finished_ok is None and idle_none_count < 10:
                                    idle_none_count += 1
                                    continue
                                if finished_ok is False:
                                    rs.log("warn", "  MHS 步骤执行失败（硬件报告 success=False）")
                                    mhs_result = "failed"
                                elif state == "stopped":
                                    rs.log("warn", "  MHS 步骤被用户停止")
                                    mhs_result = "failed"
                                elif finished_ok is None:
                                    if ever_seen_running:
                                        rs.log("warn", "  MHS 步骤状态异常：曾运行但未获得完成信号")
                                    else:
                                        rs.log("warn", "  MHS 步骤未执行（可能预检查失败或参数转换出错）")
                                    mhs_result = "failed"
                                else:
                                    rs.log("info", "  MHS 步骤执行完成 ✓")
                                # 拉取最终日志
                                try:
                                    final_log_resp = await poll_c.get(
                                        "http://127.0.0.1:8100/api/experiment/logs?n=500"
                                    )
                                    if final_log_resp.status_code == 200:
                                        all_logs = final_log_resp.json().get("logs", [])
                                        for lg in all_logs:
                                            lg_hash = str(lg)
                                            if lg_hash not in _seen_log_hashes:
                                                _seen_log_hashes.add(lg_hash)
                                                rs.log("info", f"  [MHS] {lg}")
                                except Exception:
                                    pass
                                break
                    except (httpx.ConnectError, httpx.TimeoutException, OSError) as poll_exc:
                        poll_error_count += 1
                        if poll_error_count >= 3:
                            rs.log("error", f"  MHS 轮询连接失败: {poll_exc}")
                            mhs_result = "failed"
                            break
                    except Exception as poll_exc:
                        rs.log("error", f"  MHS 轮询异常: {poll_exc}")
                        mhs_result = "failed"
                        break
                else:
                    # for-else: 600 秒超时
                    rs.log("error", "  MHS 步骤执行超时（600 秒）")
                    mhs_result = "failed"
                return mhs_result
            else:
                # MHS 返回错误（如 400 转换失败、500 内部错误）
                error_text = resp.text[:500]
                rs.log("error", f"  MHS 拒绝执行 (HTTP {resp.status_code}): {error_text}")
                return "failed"
    except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
        rs.log("error", f"  无法连接 MHS (127.0.0.1:8100): {type(exc).__name__}: {exc}")
        return "offline"
    except Exception as exc:
        rs.log("error", f"  MHS 转发异常: {type(exc).__name__}: {exc}")
        return "offline"


# ---------------------------------------------------------------------------
# Fixed-path routes (BEFORE /{exp_id} catch-all)
# ---------------------------------------------------------------------------


@router.get("/statistics")
async def get_statistics() -> Dict[str, Any]:
    """Return aggregate experiment statistics."""
    total = len(_EXP_STORE)
    today = datetime.now().date().isoformat()
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
    return {"suggestions": suggestions, "generated_at": datetime.now().isoformat()}


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


def _get_volume_warnings(steps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """检查 prep_sol 步骤使用的溶液剩余量，返回低量警告列表。"""
    warnings: List[Dict[str, str]] = []
    try:
        from src.api.routes.system import _load_system_config
        cfg = _load_system_config()
        channels = {ch["solution_name"]: ch for ch in cfg.get("dilution_channels", [])}
        # 收集本实验用到的溶液
        used: set[str] = set()
        for step in steps:
            if step.get("step_type") == "prep_sol":
                params = step.get("prep_sol_params") or {}
                for sol, selected in params.get("selected_solutions", {}).items():
                    if selected and params.get("solvent_flags", {}).get(sol) is not True:
                        used.add(sol)
        # 检查剩余量
        LOW_ML = 50.0      # 警告阈值
        CRITICAL_ML = 20.0  # 严重阈值
        for sol in used:
            ch = channels.get(sol)
            if not ch:
                continue
            remaining = ch.get("remaining_volume_ml", 0.0)
            total = ch.get("total_volume_ml", 0.0)
            if total > 0 and remaining <= CRITICAL_ML:
                warnings.append({
                    "level": "critical",
                    "solution": sol,
                    "message": f"{sol} 溶液严重不足：剩余 {remaining:.0f}mL，建议立即补充",
                })
            elif total > 0 and remaining <= LOW_ML:
                warnings.append({
                    "level": "warning",
                    "solution": sol,
                    "message": f"{sol} 溶液偏低：剩余 {remaining:.0f}mL（阈值 {LOW_ML:.0f}mL）",
                })
    except Exception:
        pass
    return warnings


@router.post("/create")
async def create_experiment(exp: ExperimentCreate) -> Dict[str, Any]:
    """Create a new experiment."""
    exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    record: Dict[str, Any] = {
        "exp_id": exp_id,
        "name": exp.name,
        "description": exp.description,
        "steps": [s.model_dump() for s in exp.steps],
        "tags": exp.tags,
        "category": exp.category,
        "status": "created",
        "created_at": datetime.now().isoformat(),
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
        raise HTTPException(status_code=404, detail=f"实验不存在: {exp_id}")

    exp = _EXP_STORE[exp_id]

    # 仅阻止「正在运行」的实验，其他状态均可重新执行
    if exp["status"] == "running":
        raise HTTPException(status_code=409, detail="实验正在运行中，请先停止后重试")

    steps = exp.get("steps", [])
    if not steps:
        raise HTTPException(status_code=422, detail="实验没有步骤，无法执行。请先添加至少一个步骤。")

    # 重置状态（支持重新执行已失败/已完成的实验）
    exp["status"] = "running"
    exp["started_at"] = datetime.now().isoformat()
    exp.pop("completed_at", None)
    exp["logs"] = []
    exp["step_progress"] = [None] * len(steps)
    exp["error_detail"] = None
    _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 开始执行")

    exp["execution_source"] = "local"
    _save_store()

    # 用安全包装启动后台任务，确保异常不会静默丢失
    async def _safe_execute(eid: str) -> None:
        try:
            await _execute_local(eid)
        except Exception as exc:
            logger.exception("[%s] _execute_local 未捕获异常", eid)
            e = _EXP_STORE.get(eid)
            if e and e.get("status") == "running":
                e["status"] = "failed"
                e["error_detail"] = f"执行器内部错误: {exc}"
                e.setdefault("logs", []).append({
                    "ts": datetime.now().isoformat(),
                    "level": "error",
                    "message": f"执行器崩溃: {exc}",
                })
                _save_store()

    asyncio.create_task(_safe_execute(exp_id))

    volume_warnings = _get_volume_warnings(steps)

    return {
        "status": "started",
        "exp_id": exp_id,
        "source": "local",
        "total_steps": len(steps),
        "warnings": volume_warnings,
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
        async with httpx.AsyncClient(timeout=5.0, transport=_mhs_transport()) as client:
            await client.post(
                "http://127.0.0.1:8100/api/experiment/stop",
                json={"exp_id": exp_id},
            )
    except Exception:
        pass

    if not rs:
        exp["status"] = "stopped"
        exp["completed_at"] = datetime.now().isoformat()
        exp.setdefault("logs", []).append({
            "ts": datetime.now().isoformat(),
            "level": "warn",
            "message": "实验已停止",
        })
        _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 已停止")
    return {"status": "stopping", "exp_id": exp_id}


def _parse_pump_batch_status(logs: list) -> Dict[str, Any]:
    """从最近日志中解析泵批次状态（用于前端指示灯）。

    扫描最近日志，提取当前批次中正在运行、等待和已完成的泵/溶液信息。
    """
    result: Dict[str, Any] = {
        "active": False,
        "batch_id": None,
        "running": [],    # [{"name": str, "pump_addr": int, "volume_ul": float}]
        "waiting": [],    # [{"name": str}]
        "completed": [],  # [{"name": str}]
    }
    import re
    # 扫描最近 60 条日志
    recent = [lg.get("message", "") for lg in (logs[-60:] if logs else [])]
    batch_start = False
    batch_done = False
    running_set: set = set()
    done_set: set = set()
    for msg in recent:
        # 检测批次开始（等待批次 N 完成）
        m = re.search(r"等待批次 (\d+) 完成", msg)
        if m:
            batch_start = True
            batch_done = False
            result["batch_id"] = int(m.group(1))
            running_set.clear()
            done_set.clear()
        # 检测批次完成
        if "全部泵已完成" in msg or "批次" in msg and "全部泵已完成" in msg:
            batch_done = True
        # 检测泵注入开始（注入 Ni: 16,000.00uL）
        m = re.search(r"注入 ([^:：]+)[：:] ([\d,.]+)uL.*泵(\d+)", msg)
        if m:
            sol = m.group(1).strip()
            pump_addr = int(m.group(3))
            running_set.add((sol, pump_addr))
        # 检测注入完成（✓ Ni 注入完成）
        m = re.search(r"✓ (.+?) 注入完成", msg)
        if m:
            sol = m.group(1).strip()
            done_set.add(sol)
    # 组合结果
    if batch_start and not batch_done:
        result["active"] = True
        for sol, addr in running_set:
            if sol not in done_set:
                result["running"].append({"name": sol, "pump_addr": addr})
            else:
                result["completed"].append({"name": sol, "pump_addr": addr})
    return result


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
        logs = rs.logs[-50:]
        return {
            **rs.to_dict(),
            "error_detail": exp.get("error_detail"),
            "logs": logs,
            "pump_batch": _parse_pump_batch_status(logs),
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
        "error_detail": exp.get("error_detail"),
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


@router.get("/active-progress")
async def get_active_experiment_progress() -> Dict[str, Any]:
    """Return the currently running experiment's progress + logs (for Dashboard).

    If no experiment is running, returns ``{"active": false}``.
    """
    if not _RUNNING:
        return {"active": False}

    # Pick the first (and usually only) running experiment
    exp_id, rs = next(iter(_RUNNING.items()))
    exp = _EXP_STORE.get(exp_id, {})
    return {
        "active": True,
        "exp_id": exp_id,
        "exp_name": exp.get("name", exp_id),
        **rs.to_dict(),
        "step_progress": exp.get("step_progress", []),
        "logs": rs.logs[-30:],
    }


@router.post("/detail/{exp_id}/complete")
async def complete_experiment(
    exp_id: str = PathParam(..., pattern="^exp_.*"),
) -> Dict[str, Any]:
    """Mark experiment as completed (manual override or callback)."""
    if exp_id not in _EXP_STORE:
        raise HTTPException(status_code=404, detail=f"experiment not found: {exp_id}")

    exp = _EXP_STORE[exp_id]
    exp["status"] = "completed"
    exp["completed_at"] = datetime.now().isoformat()
    _save_store()

    from src.api.routes.system import record_activity
    record_activity("experiment", f"实验 '{exp['name']}' 已完成")
    return exp
