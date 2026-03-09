"""
Qt ↔ FastAPI 线程安全桥接层。

APIBridge 必须在 Qt 主线程中创建，其 Signal-Slot 机制保证跨线程
调用安全地在主线程中执行。FastAPI 路由只通过 bridge 公开方法与
ExperimentRunner 交互，不得直接调用 Qt 对象。
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger("microhyseeker.api.bridge")


# ─────────────────────────────────────────────────────────────────────────────
# ExperimentPlan → Experiment 转换
# ─────────────────────────────────────────────────────────────────────────────

def plan_to_experiment(plan: Dict[str, Any]) -> Dict[str, Any]:
    """将 AutoHySeeker ExperimentPlan 转换为 MicroHySeeker Experiment dict。

    AutoHySeeker step_type 映射规则：
      cv / lsv / eis  →  echem（ec_settings.technique 对应设置）
      prep_sol        →  prep_sol
      flush           →  flush
      transfer        →  transfer
      blank           →  blank
      evacuate        →  evacuate
    """
    from src.models import (
        Experiment, ProgStep, ProgramStepType,
        ECSettings, ECTechnique,
    )

    # step_type 映射表
    _TYPE_MAP: Dict[str, ProgramStepType] = {
        "cv":        ProgramStepType.ECHEM,
        "lsv":       ProgramStepType.ECHEM,
        "eis":       ProgramStepType.ECHEM,
        "prep_sol":  ProgramStepType.PREP_SOL,
        "flush":     ProgramStepType.FLUSH,
        "transfer":  ProgramStepType.TRANSFER,
        "blank":     ProgramStepType.BLANK,
        "evacuate":  ProgramStepType.EVACUATE,
    }
    _ECHEM_TECHNIQUE_MAP: Dict[str, ECTechnique] = {
        "cv":  ECTechnique.CV,
        "lsv": ECTechnique.LSV,
        "eis": ECTechnique.EIS,
    }

    exp_id = f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    exp_name = plan.get("name", "API Experiment")
    raw_steps: List[Dict[str, Any]] = plan.get("steps", [])

    steps: List[ProgStep] = []
    for i, raw in enumerate(raw_steps):
        src_type = str(raw.get("step_type", "blank")).lower()
        step_type = _TYPE_MAP.get(src_type, ProgramStepType.BLANK)
        params: Dict[str, Any] = raw.get("params", {})

        step_kwargs: Dict[str, Any] = {
            "step_id": f"step_{i:03d}",
            "step_type": step_type,
            "notes": raw.get("description", ""),
        }

        # 通用参数映射
        for key in ("pump_address", "pump_direction", "pump_rpm",
                    "volume_ul", "duration_s"):
            if key in params:
                step_kwargs[key] = params[key]

        # 电化学步骤：构建 ECSettings
        if step_type == ProgramStepType.ECHEM:
            technique = _ECHEM_TECHNIQUE_MAP.get(src_type, ECTechnique.CV)
            ec_kwargs: Dict[str, Any] = {"technique": technique}
            # 常见 echem 参数透传
            for ec_key in ("scan_rate", "start_potential", "end_potential",
                           "high_potential", "low_potential", "num_cycles",
                           "frequency", "amplitude", "dc_potential",
                           "current_range", "sample_interval_ms"):
                if ec_key in params:
                    ec_kwargs[ec_key] = params[ec_key]
            step_kwargs["ec_settings"] = ECSettings(**{
                k: v for k, v in ec_kwargs.items()
                if k in ECSettings.__dataclass_fields__
            })

        # flush 步骤参数
        if step_type == ProgramStepType.FLUSH:
            for flush_key in ("flush_channel_id", "flush_rpm",
                              "flush_cycle_duration_s", "flush_cycles"):
                if flush_key in params:
                    step_kwargs[flush_key] = params[flush_key]

        # transfer 步骤：支持 transfer_duration
        if step_type == ProgramStepType.TRANSFER:
            for tr_key in ("transfer_duration", "transfer_duration_unit"):
                if tr_key in params:
                    step_kwargs[tr_key] = params[tr_key]

        steps.append(ProgStep(**{
            k: v for k, v in step_kwargs.items()
            if k in ProgStep.__dataclass_fields__
        }))

    exp = Experiment(
        exp_id=exp_id,
        exp_name=exp_name,
        description=plan.get("description", ""),
        steps=steps,
        tags=plan.get("tags", []),
    )
    return exp.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# APIBridge
# ─────────────────────────────────────────────────────────────────────────────

class APIBridge(QObject):
    """Qt ↔ FastAPI 线程安全桥接。

    必须在 Qt 主线程中实例化。FastAPI 路由线程通过 Signal emit 触发
    操作，Qt 信号/槽机制保证 Slot 在主线程的事件循环中执行。

    状态读取（get_status / get_uptime 等）直接读取线程安全属性，无需跨线程调度。
    """

    # ── 信号（FastAPI 线程 emit → 主线程 Slot 执行） ──────────────────────────
    start_experiment_signal = Signal(dict)   # experiment dict
    stop_experiment_signal  = Signal()
    pause_experiment_signal = Signal()
    resume_experiment_signal = Signal()

    def __init__(self, runner, config) -> None:
        """
        Args:
            runner: ExperimentRunner 实例（主线程所有）
            config: SystemConfig 实例
        """
        super().__init__()
        self._runner = runner
        self._config = config
        self._start_time = time.monotonic()

        # 运行中实验追踪（由 Slot 在主线程更新，读取时用锁）
        self._lock = threading.Lock()
        self._current_run_id: Optional[str] = None
        self._current_exp_name: str = ""
        self._last_finished_success: Optional[bool] = None
        self._recent_logs: List[str] = []  # 滚动日志缓冲（最多 500 条）

        # 连接信号
        self.start_experiment_signal.connect(self._slot_start_experiment)
        self.stop_experiment_signal.connect(self._slot_stop)
        self.pause_experiment_signal.connect(self._slot_pause)
        self.resume_experiment_signal.connect(self._slot_resume)

        # 订阅 runner 事件
        runner.experiment_finished.connect(self._on_experiment_finished)
        runner.log_message.connect(self._on_log_message)

    # ── Qt Slots（主线程执行） ─────────────────────────────────────────────

    @Slot(dict)
    def _slot_start_experiment(self, experiment_dict: dict) -> None:
        from src.models import Experiment
        try:
            exp = Experiment.from_dict(experiment_dict)
            with self._lock:
                self._current_run_id = experiment_dict.get("exp_id", "")
                self._current_exp_name = exp.exp_name
                self._last_finished_success = None
            self._runner.run_experiment(exp)
            logger.info("Experiment started via API: %s", exp.exp_name)
        except Exception as exc:
            logger.exception("Failed to start experiment: %s", exc)

    @Slot()
    def _slot_stop(self) -> None:
        self._runner.stop()
        logger.info("Stop requested via API")

    @Slot()
    def _slot_pause(self) -> None:
        self._runner.pause()
        logger.info("Pause requested via API")

    @Slot()
    def _slot_resume(self) -> None:
        self._runner.resume()
        logger.info("Resume requested via API")

    @Slot(bool)
    def _on_experiment_finished(self, success: bool) -> None:
        with self._lock:
            self._last_finished_success = success
        logger.info("Experiment finished (success=%s) via bridge event", success)

    @Slot(str)
    def _on_log_message(self, msg: str) -> None:
        with self._lock:
            self._recent_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
            if len(self._recent_logs) > 500:
                self._recent_logs = self._recent_logs[-500:]

    # ── FastAPI 路由调用的公开方法（任意线程安全） ──────────────────────────

    def start_experiment(self, experiment_dict: dict) -> str:
        """发出信号，在主线程启动实验。返回 run_id。"""
        self.start_experiment_signal.emit(experiment_dict)
        with self._lock:
            return self._current_run_id or experiment_dict.get("exp_id", "")

    def stop_experiment(self) -> None:
        self.stop_experiment_signal.emit()

    def pause_experiment(self) -> None:
        self.pause_experiment_signal.emit()

    def resume_experiment(self) -> None:
        self.resume_experiment_signal.emit()

    def get_status(self) -> Dict[str, Any]:
        """线程安全的状态快照。"""
        is_running = getattr(self._runner, "is_running", False)
        is_paused  = getattr(self._runner, "is_paused",  False)

        if is_paused:
            state = "paused"
        elif is_running:
            state = "running"
        else:
            state = "idle"

        worker = getattr(self._runner, "_worker", None)
        total_steps   = 0
        current_step  = None
        if worker and getattr(worker, "experiment", None):
            total_steps = len(worker.experiment.steps)

        with self._lock:
            run_id   = self._current_run_id
            exp_name = self._current_exp_name

        return {
            "state":       state,
            "run_id":      run_id,
            "exp_name":    exp_name,
            "is_running":  is_running,
            "is_paused":   is_paused,
            "total_steps": total_steps,
            "current_step": current_step,
        }

    def get_data_dir(self) -> str:
        if self._config:
            return getattr(self._config, "data_dir", "./data")
        return "./data"

    def get_uptime(self) -> float:
        return time.monotonic() - self._start_time

    def get_recent_logs(self, n: int = 100) -> List[str]:
        with self._lock:
            return list(self._recent_logs[-n:])
