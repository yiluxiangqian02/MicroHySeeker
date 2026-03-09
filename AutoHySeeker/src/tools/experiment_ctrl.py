"""MicroHySeeker HTTP API 客户端。

通过 FastAPI（端口 8100）全权控制 MicroHySeeker GUI 前端。
所有函数均为同步调用；AutoHySeeker Agent 在工具节点中直接调用。

MicroHySeeker 未启动时会抛出 MicroHySeekerUnavailableError，
调用方可据此决定是否跳过或重试。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

_logger = logging.getLogger("autohyseeker.experiment_ctrl")

# ── 配置 ──────────────────────────────────────────────────────────────────────

MICROHYSEEKER_BASE_URL: str = os.environ.get(
    "MICROHYSEEKER_API_URL", "http://localhost:8100"
)
_API_BASE = f"{MICROHYSEEKER_BASE_URL}/api"
_DEFAULT_TIMEOUT = 15.0      # 一般操作超时（秒）
_START_TIMEOUT   = 30.0      # 启动操作可能稍慢


# ── 自定义异常 ────────────────────────────────────────────────────────────────

class MicroHySeekerUnavailableError(RuntimeError):
    """MicroHySeeker 服务不可达时抛出。"""


class MicroHySeekerAPIError(RuntimeError):
    """MicroHySeeker 返回错误响应时抛出。"""


# ── ExperimentPlan → plan dict 辅助（透传 AutoHySeeker ProgStep） ─────────────

def _plan_to_payload(plan: Any) -> dict[str, Any]:
    """将 AutoHySeeker ExperimentPlan（Pydantic 模型）转为可 JSON 序列化的 dict。

    MicroHySeeker 端的 bridge.plan_to_experiment() 负责最终字段映射。
    """
    if isinstance(plan, dict):
        return plan
    # Pydantic BaseModel
    if hasattr(plan, "model_dump"):
        return plan.model_dump(mode="json")
    if hasattr(plan, "dict"):
        return plan.dict()
    raise TypeError(f"Unsupported plan type: {type(plan)}")


# ── 内部 HTTP 工具 ─────────────────────────────────────────────────────────────

def _post(path: str, json_body: dict, timeout: float = _DEFAULT_TIMEOUT) -> dict[str, Any]:
    url = f"{_API_BASE}{path}"
    try:
        resp = httpx.post(url, json=json_body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError as exc:
        raise MicroHySeekerUnavailableError(
            f"MicroHySeeker 不可达（{url}）：{exc}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise MicroHySeekerUnavailableError(
            f"MicroHySeeker 请求超时（{url}）：{exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise MicroHySeekerAPIError(
            f"API 错误 {exc.response.status_code}（{url}）：{exc.response.text}"
        ) from exc


def _get(path: str, params: Optional[dict] = None, timeout: float = _DEFAULT_TIMEOUT) -> dict[str, Any]:
    url = f"{_API_BASE}{path}"
    try:
        resp = httpx.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError as exc:
        raise MicroHySeekerUnavailableError(
            f"MicroHySeeker 不可达（{url}）：{exc}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise MicroHySeekerUnavailableError(
            f"MicroHySeeker 请求超时（{url}）：{exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise MicroHySeekerAPIError(
            f"API 错误 {exc.response.status_code}（{url}）：{exc.response.text}"
        ) from exc


# ── 实验控制 ──────────────────────────────────────────────────────────────────

def start_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """启动实验。

    Args:
        payload: 包含 'plan'（ExperimentPlan dict）或 'experiment'（Experiment dict）的字典。
                 也可直接传 ExperimentPlan 对象（自动序列化）。

    Returns:
        {"run_id": "...", "status": "started", "exp_name": "...", "timestamp": "..."}

    Raises:
        MicroHySeekerUnavailableError: MicroHySeeker 未运行
        MicroHySeekerAPIError: API 返回错误
    """
    if payload is None:
        payload = {}

    # 支持直接传 ExperimentPlan 对象
    if "plan" in payload and not isinstance(payload["plan"], dict):
        payload = dict(payload)
        payload["plan"] = _plan_to_payload(payload["plan"])

    _logger.info("start_experiment: sending to MicroHySeeker API")
    result = _post("/experiment/start", payload, timeout=_START_TIMEOUT)
    _logger.info("start_experiment: run_id=%s", result.get("run_id"))
    return result


def stop_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """停止当前实验。

    Args:
        payload: 可选，包含 'run_id' 字段。

    Returns:
        {"status": "stopped", "run_id": "...", "timestamp": "..."}
    """
    body: dict[str, Any] = {}
    if payload and "run_id" in payload:
        body["run_id"] = payload["run_id"]

    _logger.info("stop_experiment: sending stop to MicroHySeeker API")
    return _post("/experiment/stop", body)


def pause_experiment(run_id: Optional[str] = None) -> dict[str, Any]:
    """暂停当前实验。

    Returns:
        {"status": "paused", ...}
    """
    body: dict[str, Any] = {}
    if run_id:
        body["run_id"] = run_id
    _logger.info("pause_experiment: sending pause")
    return _post("/experiment/pause", body)


def resume_experiment(run_id: Optional[str] = None) -> dict[str, Any]:
    """恢复已暂停实验。

    Returns:
        {"status": "resumed", ...}
    """
    body: dict[str, Any] = {}
    if run_id:
        body["run_id"] = run_id
    _logger.info("resume_experiment: sending resume")
    return _post("/experiment/resume", body)


def get_experiment_status() -> dict[str, Any]:
    """查询实验引擎当前状态。

    Returns:
        {
            "state": "idle"|"running"|"paused",
            "run_id": "...",
            "exp_name": "...",
            "is_running": bool,
            "is_paused": bool,
            "total_steps": int,
            "current_step": int|null,
            "timestamp": "...",
        }
    """
    return _get("/experiment/status")


# ── 系统控制 ──────────────────────────────────────────────────────────────────

def health_check() -> dict[str, Any]:
    """检查 MicroHySeeker 是否运行正常。

    Returns:
        {"status": "ok", "uptime_seconds": float, "engine_state": "...", ...}

    Raises:
        MicroHySeekerUnavailableError: 不可达
    """
    return _get("/system/health")


def get_logs(n: int = 100) -> list[str]:
    """获取最近 n 条 MicroHySeeker 运行日志。

    Returns:
        日志字符串列表
    """
    result = _get("/system/logs", params={"n": n})
    return result.get("logs", [])


def restart_microhyseeker() -> dict[str, Any]:
    """重启 MicroHySeeker 进程（危险操作）。

    Returns:
        {"status": "restarting", ...}
    """
    _logger.warning("restart_microhyseeker: sending restart request")
    return _post("/system/restart", {"confirm": True})


# ── 数据查询 ──────────────────────────────────────────────────────────────────

def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    """列出所有实验运行（倒序）。

    Returns:
        [{"run_id": "...", "exp_name": "...", "status": "...", ...}, ...]
    """
    result = _get("/data/runs", params={"limit": limit})
    return result.get("runs", [])


def get_run_detail(run_id: str) -> dict[str, Any]:
    """获取单次运行详情（摘要 + 数据文件列表 + experiment.json）。"""
    return _get(f"/data/runs/{run_id}")


def download_run_file(run_id: str, filename: str) -> bytes:
    """下载运行数据文件（CSV / PNG / JSON）。

    Args:
        run_id:   运行 ID
        filename: 相对路径，如 "echem/step_000_CV.csv"

    Returns:
        文件原始字节内容
    """
    url = f"{_API_BASE}/data/runs/{run_id}/files/{filename}"
    try:
        resp = httpx.get(url, timeout=60.0)
        resp.raise_for_status()
        return resp.content
    except httpx.ConnectError as exc:
        raise MicroHySeekerUnavailableError(str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise MicroHySeekerAPIError(str(exc)) from exc


# ── 可用性检查（Agent 调用前置检查） ─────────────────────────────────────────

def is_microhyseeker_available() -> bool:
    """快速检查 MicroHySeeker API 是否可达。不抛异常。"""
    try:
        health_check()
        return True
    except (MicroHySeekerUnavailableError, MicroHySeekerAPIError):
        return False

