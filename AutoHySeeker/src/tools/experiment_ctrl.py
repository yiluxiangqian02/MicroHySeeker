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
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.post(url, json=json_body)
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
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.get(url, params=params)
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


def get_logs(n: int = 100, level: str | None = None) -> list[str]:
    """获取最近 n 条 MicroHySeeker 运行日志。

    Args:
        n: 返回的日志条数。
        level: 日志级别过滤（"info", "warning", "error"）。

    Returns:
        日志字符串列表
    """
    params: dict[str, Any] = {"n": n}
    if level:
        params["level"] = level
    result = _get("/system/logs", params=params)
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
        with httpx.Client(timeout=60.0, trust_env=False) as client:
            resp = client.get(url)
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


# ── 设备级控制（泵/清洗/配液/紧急停止） ─────────────────────────────────────

def pump_start(address: int, direction: str = "FWD", rpm: int = 100) -> dict[str, Any]:
    """启动单个泵。

    Args:
        address: 泵地址 (1-12)
        direction: 方向 FWD/REV
        rpm: 转速 (0-300)

    Returns:
        {"status": "started", "address": ..., "rpm": ..., ...}
    """
    return _post("/device/pump/start", {
        "address": address, "direction": direction, "rpm": rpm,
    })


def pump_stop(address: int) -> dict[str, Any]:
    """停止单个泵。"""
    return _post("/device/pump/stop", {"address": address})


def pump_stop_all() -> dict[str, Any]:
    """紧急停止所有泵。"""
    return _post("/device/pump/stop-all", {})


def get_pump_status(address: int | None = None) -> dict[str, Any]:
    """查询泵状态。

    Args:
        address: 指定泵地址 (1-12)，为 None 时返回所有泵状态。
    """
    if address is not None:
        return _get(f"/device/pump/{address}")
    return _get("/device/pump/status")


def flusher_start(cycles: int = 3, channel_id: int | None = None) -> dict[str, Any]:
    """启动清洗循环。"""
    body: dict[str, Any] = {"cycles": cycles}
    if channel_id is not None:
        body["channel_id"] = channel_id
    return _post("/device/flusher/start", body)


def flusher_stop() -> dict[str, Any]:
    """停止清洗。"""
    return _post("/device/flusher/stop", {})


def get_flusher_status() -> dict[str, Any]:
    """查询清洗器状态。"""
    return _get("/device/flusher/status")


def diluter_start(channel_id: int, volume_ul: float, rpm: int | None = None) -> dict[str, Any]:
    """启动配液。

    Args:
        channel_id: 配液通道 ID
        volume_ul: 注液体积 (μL)
        rpm: 转速 (可选, 0-300)
    """
    body: dict[str, Any] = {"channel_id": channel_id, "volume_ul": volume_ul}
    if rpm is not None:
        body["rpm"] = rpm
    return _post("/device/diluter/start", body)


def diluter_stop(channel_id: int) -> dict[str, Any]:
    """停止配液。"""
    return _post("/device/diluter/stop", {"channel_id": channel_id})


def get_diluter_status(channel_id: int) -> dict[str, Any]:
    """查询配液通道状态。"""
    return _get(f"/device/diluter/{channel_id}/status")


def emergency_stop() -> dict[str, Any]:
    """紧急停止一切：所有泵 + 清洗 + 配液 + 实验。"""
    _logger.critical("emergency_stop: 紧急停止一切！")
    return _post("/device/emergency-stop", {})


def get_connection_info() -> dict[str, Any]:
    """查询 RS485 连接状态。"""
    return _get("/device/connection")


def list_ports() -> list[str]:
    """列出可用串口。"""
    result = _get("/device/ports")
    return result.get("ports", [])


def connect_port(port: str, baudrate: int = 38400) -> dict[str, Any]:
    """打开串口连接。"""
    return _post("/device/connect", {"port": port, "baudrate": baudrate})


def disconnect_port() -> dict[str, Any]:
    """关闭串口连接。"""
    return _post("/device/disconnect", {})


# ── 模板管理 ─────────────────────────────────────────────────────────────────

def list_templates() -> dict[str, Any]:
    """列出所有实验模板（摘要信息）。

    Returns:
        {"templates": [...], "count": int}
    """
    return _get("/template/list")


def get_template(template_id: str) -> dict[str, Any]:
    """获取模板完整详情（含所有步骤参数）。"""
    return _get(f"/template/{template_id}")


def save_template(
    name: str,
    steps: list[dict[str, Any]],
    description: str = "",
    tags: list[str] | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    """保存或更新实验模板。

    Args:
        name: 模板名称
        steps: 步骤列表 (ProgStep dicts)
        description: 描述
        tags: 标签列表
        template_id: 更新已有模板时提供 ID
    """
    body: dict[str, Any] = {
        "name": name,
        "steps": steps,
        "description": description,
        "tags": tags or [],
    }
    if template_id:
        body["template_id"] = template_id
    return _post("/template/save", body)


def delete_template(template_id: str) -> dict[str, Any]:
    """删除模板。"""
    url = f"{_API_BASE}/template/{template_id}"
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT, trust_env=False) as client:
            resp = client.delete(url)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError as exc:
        raise MicroHySeekerUnavailableError(str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise MicroHySeekerAPIError(str(exc)) from exc


def instantiate_template(
    template_id: str,
    overrides: dict[str, Any] | None = None,
    exp_name: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """从模板实例化并运行实验。

    Args:
        template_id: 模板 ID
        overrides: 参数覆盖，格式:
            - 按步骤: {"step_overrides": {0: {"pump_rpm": 150}}}
            - 全局: {"description": "新描述"}
        exp_name: 实验名称 (默认使用模板名)
        dry_run: 仅验证不运行

    Returns:
        dry_run=True: {"status": "validated", "experiment": {...}, ...}
        dry_run=False: {"status": "started", "run_id": "...", ...}
    """
    body: dict[str, Any] = {
        "overrides": overrides or {},
        "dry_run": dry_run,
    }
    if exp_name:
        body["exp_name"] = exp_name
    return _post(f"/template/{template_id}/instantiate", body, timeout=_START_TIMEOUT)


def validate_experiment(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """验证实验步骤参数是否合法。

    Returns:
        {"valid": bool, "errors": [...], "warnings": [...], "step_count": int}
    """
    return _post("/template/validate", {"steps": steps})


# ── 系统配置查询 ─────────────────────────────────────────────────────────────

def get_system_config() -> dict[str, Any]:
    """查询系统完整配置（泵/通道/端口/校准数据）。"""
    return _get("/template/config/system")


def get_capabilities() -> dict[str, Any]:
    """查询系统能力摘要。

    Agent 设计实验前应先调用此接口了解系统能力。

    Returns:
        {
            "pump_count": int,
            "pump_addresses": [int],
            "dilution_channel_count": int,
            "dilution_solutions": [{"channel_id": ..., "name": ..., "concentration": ...}],
            "flush_channel_count": int,
            "supported_step_types": [str],
            "supported_techniques": [str],
            "max_rpm": 300,
            ...
        }
    """
    return _get("/template/config/capabilities")


def get_dilution_channels() -> list[dict[str, Any]]:
    """查询配液通道列表及配置。"""
    result = _get("/template/config/dilution-channels")
    return result.get("channels", [])


def get_flush_channels() -> list[dict[str, Any]]:
    """查询清洗通道列表及配置。"""
    result = _get("/template/config/flush-channels")
    return result.get("channels", [])


def get_pump_configs() -> list[dict[str, Any]]:
    """查询泵配置列表。"""
    result = _get("/template/config/pumps")
    return result.get("pumps", [])



