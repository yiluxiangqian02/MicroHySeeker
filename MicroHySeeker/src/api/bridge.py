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

def plan_to_experiment(plan: Dict[str, Any], flush_channels: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """将 AutoHySeeker ExperimentPlan 转换为 MicroHySeeker Experiment dict。

    AutoHySeeker step_type 映射规则：
      echem / cv / lsv / eis  →  ECHEM（ec_settings.technique 对应设置）
      prep_sol        →  PREP_SOL
      flush           →  FLUSH
      transfer        →  TRANSFER
      blank           →  BLANK
      evacuate        →  EVACUATE

    AutoHySeeker 从 ExperimentCreateDialog 提交的 params 字段是整个
    ExperimentStep 对象（包含 ec_settings / prep_sol_params 等嵌套字典），
    此函数负责展平并正确映射。
    """
    from src.models import (
        Experiment, ProgStep, ProgramStepType,
        ECSettings, ECTechnique, PrepSolStep,
    )

    # step_type 映射表 —— 兼容 "echem" 和具体 technique 名称
    _TYPE_MAP: Dict[str, ProgramStepType] = {
        "cv":        ProgramStepType.ECHEM,
        "lsv":       ProgramStepType.ECHEM,
        "eis":       ProgramStepType.ECHEM,
        "i-t":       ProgramStepType.ECHEM,
        "adt":       ProgramStepType.ECHEM,
        "echem":     ProgramStepType.ECHEM,   # AutoHySeeker 统一用 "echem"
        "prep_sol":  ProgramStepType.PREP_SOL,
        "flush":     ProgramStepType.FLUSH,
        "transfer":  ProgramStepType.TRANSFER,
        "blank":     ProgramStepType.BLANK,
        "evacuate":  ProgramStepType.EVACUATE,
    }

    exp_id = f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    exp_name = plan.get("name", "API Experiment")
    raw_steps: List[Dict[str, Any]] = plan.get("steps", [])

    steps: List[ProgStep] = []
    for i, raw in enumerate(raw_steps):
        src_type = str(raw.get("step_type", "blank")).lower()
        step_type = _TYPE_MAP.get(src_type, ProgramStepType.BLANK)
        # params 可能是整个 ExperimentStep 对象（AutoHySeeker 格式）
        params: Dict[str, Any] = raw.get("params", {})

        step_kwargs: Dict[str, Any] = {
            "step_id": f"step_{i:03d}",
            "step_type": step_type,
            "notes": raw.get("description", "") or params.get("notes", ""),
        }

        # 通用参数映射（params 顶层字段即为 ExperimentStep 字段）
        for key in ("pump_address", "pump_direction", "pump_rpm",
                    "volume_ul", "duration_s", "transfer_duration",
                    "transfer_duration_unit"):
            if key in params:
                step_kwargs[key] = params[key]

        # 电化学步骤：从嵌套 ec_settings 构建 ECSettings
        if step_type == ProgramStepType.ECHEM:
            # AutoHySeeker 将电化学参数放在 params.ec_settings 嵌套字典中
            ec_src: Dict[str, Any] = {}
            if isinstance(params.get("ec_settings"), dict):
                ec_src = params["ec_settings"].copy()
            elif src_type in ("cv", "lsv", "eis", "i-t", "adt"):
                # 旧格式：technique 即 src_type，参数在 params 顶层
                ec_src = params.copy()
                ec_src.setdefault("technique", src_type.upper())

            # 确保 technique 正确
            if not ec_src.get("technique"):
                ec_src["technique"] = "CV"

            try:
                step_kwargs["ec_settings"] = ECSettings.from_dict(ec_src)
            except Exception:
                logger.warning("ECSettings.from_dict failed for step %d, using default CV", i)
                step_kwargs["ec_settings"] = ECSettings(technique=ECTechnique.CV)

        # 配液步骤：从嵌套 prep_sol_params 构建 PrepSolStep
        if step_type == ProgramStepType.PREP_SOL:
            if isinstance(params.get("prep_sol_params"), dict):
                try:
                    step_kwargs["prep_sol_params"] = PrepSolStep.from_dict(
                        params["prep_sol_params"]
                    )
                except Exception:
                    logger.warning("PrepSolStep.from_dict failed for step %d", i)

        # flush 步骤参数（params 顶层）
        if step_type == ProgramStepType.FLUSH:
            for flush_key in ("flush_channel_id", "flush_rpm",
                              "flush_cycle_duration_s", "flush_cycles"):
                if flush_key in params:
                    step_kwargs[flush_key] = params[flush_key]
            # 从 flush_channels 配置解析 pump_address，供预检查使用
            if "flush_channel_id" in params and not step_kwargs.get("pump_address"):
                ch_id = str(params["flush_channel_id"])
                for fch in (flush_channels or []):
                    if str(fch.get("channel_id")) == ch_id:
                        step_kwargs.setdefault("pump_address", fch.get("pump_address"))
                        step_kwargs.setdefault("pump_rpm", fch.get("rpm", 100))
                        break
            # 从 cycle_duration × cycles 计算 volume_ul（rpm时间模式近似）
            if not step_kwargs.get("volume_ul"):
                dur = float(params.get("flush_cycle_duration_s", 0) or 0)
                cycles = int(params.get("flush_cycles", 1) or 1)
                rpm = step_kwargs.get("pump_rpm") or params.get("flush_rpm") or 100
                # 粗估：calibration 通常 0.5 µL/s at 120 RPM → 按比例
                ul_per_s = 0.5 * rpm / 120.0
                step_kwargs["volume_ul"] = max(0.1, dur * cycles * ul_per_s)

        # transfer / evacuate 步骤参数（params 顶层）
        if step_type in (ProgramStepType.TRANSFER, ProgramStepType.EVACUATE):
            for key in ("pump_address", "pump_direction", "pump_rpm", "volume_ul",
                        "transfer_duration", "transfer_duration_unit"):
                if key in params:
                    step_kwargs[key] = params[key]
            # 若只给了 volume_ul，确保它存在；若只给了 duration，估算 volume
            if not step_kwargs.get("volume_ul"):
                dur = float(params.get("duration_s") or params.get("transfer_duration") or 0)
                rpm = step_kwargs.get("pump_rpm") or 100
                ul_per_s = 0.5 * rpm / 120.0
                if dur > 0:
                    step_kwargs["volume_ul"] = max(0.1, dur * ul_per_s)

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
        import traceback as _tb
        try:
            exp = Experiment.from_dict(experiment_dict)
            with self._lock:
                self._current_run_id = experiment_dict.get("exp_id", "")
                self._current_exp_name = exp.exp_name
                self._last_finished_success = None
            started = self._runner.run_experiment(exp)
            if not started:
                logger.warning("run_experiment returned False (runner busy?)")
            else:
                logger.info("Experiment started via API: %s", exp.exp_name)
        except Exception as exc:
            logger.exception("Failed to start experiment: %s", exc)
            # 确保错误可见：写入文件
            try:
                import pathlib
                pathlib.Path("./logs/bridge_error.log").write_text(
                    f"{_tb.format_exc()}\n", encoding="utf-8"
                )
            except Exception:
                pass

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

    @Slot(str, str, str)
    def _on_log_message(self, msg: str, level: str = "INFO", source: str = "RUNNER") -> None:
        ts = datetime.now().strftime('%H:%M:%S')
        entry = f"[{ts}] [{level}] {msg}"
        with self._lock:
            self._recent_logs.append(entry)
            if len(self._recent_logs) > 500:
                self._recent_logs = self._recent_logs[-500:]
            # 写入调试文件便于排查
            try:
                import pathlib
                with pathlib.Path("./logs/bridge_runner_log.txt").open("a", encoding="utf-8") as f:
                    f.write(f"{entry}\n")
            except Exception:
                pass

    # ── FastAPI 路由调用的公开方法（任意线程安全） ──────────────────────────

    def start_experiment(self, experiment_dict: dict) -> str:
        """发出信号，在主线程启动实验。返回 exp_id。"""
        self.start_experiment_signal.emit(experiment_dict)
        return experiment_dict.get("exp_id", "")

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
            "last_finished_success": self._last_finished_success,
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

    # ── 设备级控制方法（供 /api/device/* 路由调用） ──────────────────────────

    def _get_rs485(self):
        """获取 RS485Wrapper 实例。"""
        rs485 = getattr(self._runner, "rs485", None)
        if rs485 is None:
            raise RuntimeError("RS485Wrapper 未初始化")
        return rs485

    def device_pump_start(self, address: int, direction: str, rpm: int) -> bool:
        """启动单个泵。"""
        rs485 = self._get_rs485()
        return rs485.start_pump(address, direction, rpm)

    def device_pump_stop(self, address: int) -> bool:
        """停止单个泵。"""
        rs485 = self._get_rs485()
        return rs485.stop_pump(address)

    def device_stop_all_pumps(self) -> bool:
        """停止所有泵。"""
        rs485 = self._get_rs485()
        return rs485.stop_all()

    def device_get_pump_status(self, address: int) -> Dict[str, Any]:
        """获取单个泵状态。"""
        rs485 = self._get_rs485()
        return rs485.get_pump_status(address)

    def device_get_all_pump_status(self) -> List[Dict[str, Any]]:
        """获取所有泵状态。"""
        rs485 = self._get_rs485()
        return [rs485.get_pump_status(addr) for addr in range(1, 13)]

    def device_flusher_start(self, cycles: int = 3, channel_id: Optional[int] = None) -> bool:
        """启动清洗循环。"""
        rs485 = self._get_rs485()
        return rs485.start_flush(cycles=cycles, channel_id=channel_id)

    def device_flusher_stop(self) -> bool:
        """停止清洗。"""
        rs485 = self._get_rs485()
        return rs485.stop_flush()

    def device_get_flusher_status(self) -> Dict[str, Any]:
        """获取清洗器状态。"""
        rs485 = self._get_rs485()
        status = rs485.get_flush_status()
        if status is None:
            return {"state": "not_configured", "is_flushing": False}
        return status

    def device_diluter_start(
        self, channel_id: int, volume_ul: float, rpm: Optional[int] = None
    ) -> bool:
        """启动配液。"""
        rs485 = self._get_rs485()
        return rs485.start_dilution(channel_id, volume_ul, rpm=rpm)

    def device_diluter_stop(self, channel_id: int) -> bool:
        """停止配液。"""
        rs485 = self._get_rs485()
        return rs485.stop_dilution(channel_id)

    def device_get_diluter_status(self, channel_id: int) -> Dict[str, Any]:
        """获取配液通道状态。"""
        rs485 = self._get_rs485()
        return rs485.get_dilution_progress(channel_id)

    def device_emergency_stop(self) -> bool:
        """紧急停止一切。"""
        rs485 = self._get_rs485()
        # 1. 停止实验
        try:
            self.stop_experiment()
        except Exception:
            pass
        # 2. 停止清洗
        try:
            rs485.stop_flush()
        except Exception:
            pass
        # 3. 停止所有泵
        try:
            rs485.stop_all()
        except Exception:
            pass
        return True

    def device_get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息。"""
        rs485 = self._get_rs485()
        return {
            "connected": rs485.is_connected(),
            "mock_mode": getattr(rs485, "_mock_mode", True),
            "port": getattr(rs485, "_current_port", ""),
        }

    def device_list_ports(self) -> List[str]:
        """列出可用串口。"""
        from src.services.rs485_wrapper import RS485Wrapper
        return RS485Wrapper.list_available_ports()

    def device_connect(self, port: str, baudrate: int = 38400) -> bool:
        """打开串口。"""
        rs485 = self._get_rs485()
        return rs485.open_port(port, baudrate)

    def device_disconnect(self) -> None:
        """关闭串口。"""
        rs485 = self._get_rs485()
        rs485.close_port()

    # ── 模板管理方法 ─────────────────────────────────────────────────────

    def _get_template_manager(self):
        from src.core.template_manager import get_template_manager
        return get_template_manager()

    def template_list(self) -> List[Dict[str, Any]]:
        return self._get_template_manager().list_templates()

    def template_load(self, template_id: str) -> Optional[Dict[str, Any]]:
        return self._get_template_manager().load(template_id)

    def template_save(
        self, name: str, description: str, tags: List[str],
        steps: List[Dict[str, Any]], template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._get_template_manager().save(
            name=name, description=description, tags=tags,
            steps=steps, template_id=template_id,
        )

    def template_delete(self, template_id: str) -> bool:
        return self._get_template_manager().delete(template_id)

    def template_instantiate(
        self,
        template: Dict[str, Any],
        overrides: Dict[str, Any],
        exp_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """从模板 + 参数覆盖 → 生成可运行的 Experiment dict。"""
        from src.models import (
            Experiment, ProgStep, ProgramStepType, ECSettings,
        )

        steps_raw = list(template.get("steps", []))
        name = exp_name or template.get("name", "模板实验")

        # 应用按步骤覆盖
        step_overrides = overrides.get("step_overrides", {})
        for idx_str, patch in step_overrides.items():
            idx = int(idx_str)
            if 0 <= idx < len(steps_raw):
                step = steps_raw[idx]
                for k, v in patch.items():
                    if k == "ec_settings" and isinstance(v, dict):
                        existing_ec = step.get("ec_settings") or {}
                        existing_ec.update(v)
                        step["ec_settings"] = existing_ec
                    elif k == "prep_sol_params" and isinstance(v, dict):
                        existing_ps = step.get("prep_sol_params") or {}
                        existing_ps.update(v)
                        step["prep_sol_params"] = existing_ps
                    else:
                        step[k] = v

        exp_id = f"tpl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        exp_dict = {
            "_protocol_version": "2.0",
            "_created_at": datetime.now().isoformat(),
            "_modified_at": datetime.now().isoformat(),
            "exp_id": exp_id,
            "exp_name": name,
            "description": overrides.get("description", template.get("description", "")),
            "tags": overrides.get("tags", template.get("tags", [])),
            "operator": overrides.get("operator", ""),
            "steps": steps_raw,
            "notes": overrides.get("notes", ""),
        }

        return exp_dict

    def template_validate(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证步骤参数。"""
        errors: List[str] = []
        warnings: List[str] = []
        valid_types = {"transfer", "prep_sol", "flush", "echem", "blank", "evacuate"}

        for i, step in enumerate(steps):
            prefix = f"步骤 {i}"
            st = step.get("step_type", "")
            if st not in valid_types:
                errors.append(f"{prefix}: step_type='{st}' 无效，有效值: {valid_types}")

            rpm = step.get("pump_rpm")
            if rpm is not None and (rpm < 0 or rpm > 300):
                errors.append(f"{prefix}: pump_rpm={rpm} 超出安全范围 0-300")

            flush_rpm = step.get("flush_rpm")
            if flush_rpm is not None and (flush_rpm < 0 or flush_rpm > 300):
                errors.append(f"{prefix}: flush_rpm={flush_rpm} 超出安全范围 0-300")

            addr = step.get("pump_address")
            if addr is not None and (addr < 1 or addr > 12):
                errors.append(f"{prefix}: pump_address={addr} 无效，有效范围 1-12")

            ec = step.get("ec_settings")
            if st == "echem" and ec is None:
                errors.append(f"{prefix}: echem 步骤必须包含 ec_settings")
            if ec:
                technique = ec.get("technique", "")
                if technique not in ("CV", "LSV", "i-t", "EIS", "ADT"):
                    errors.append(f"{prefix}: technique='{technique}' 无效")
                sr = ec.get("scan_rate")
                if sr is not None and sr <= 0:
                    errors.append(f"{prefix}: scan_rate 必须 > 0")

            if st == "prep_sol":
                ps = step.get("prep_sol_params")
                if ps is None:
                    warnings.append(f"{prefix}: prep_sol 步骤建议包含 prep_sol_params")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "step_count": len(steps),
        }

    # ── 系统配置查询方法 ─────────────────────────────────────────────────

    def config_get_system(self) -> Dict[str, Any]:
        """获取完整系统配置。"""
        cfg = self._config
        if cfg is None:
            return {"error": "系统配置未加载"}
        return cfg.to_dict() if hasattr(cfg, "to_dict") else {}

    def config_get_capabilities(self) -> Dict[str, Any]:
        """获取系统能力摘要。"""
        cfg = self._config
        if cfg is None:
            return {"error": "系统配置未加载"}

        pumps = getattr(cfg, "pumps", [])
        dil_channels = getattr(cfg, "dilution_channels", [])
        flush_channels = getattr(cfg, "flush_channels", [])

        return {
            "pump_count": len(pumps),
            "pump_addresses": [
                p.address if hasattr(p, "address") else p.get("address")
                for p in pumps
            ],
            "dilution_channel_count": len(dil_channels),
            "dilution_solutions": [
                {
                    "channel_id": getattr(ch, "channel_id", None) or ch.get("channel_id"),
                    "name": getattr(ch, "solution_name", None) or ch.get("solution_name"),
                    "concentration": getattr(ch, "stock_concentration", None) or ch.get("stock_concentration"),
                }
                for ch in dil_channels
            ],
            "flush_channel_count": len(flush_channels),
            "supported_step_types": ["echem", "prep_sol", "flush", "transfer", "evacuate", "blank"],
            "supported_techniques": ["CV", "LSV", "EIS", "i-t", "ADT"],
            "max_rpm": 300,
            "rs485_port": getattr(cfg, "rs485_port", ""),
            "mock_mode": getattr(cfg, "mock_mode", True),
            "data_dir": getattr(cfg, "data_dir", "./data"),
        }

    def config_get_dilution_channels(self) -> List[Dict[str, Any]]:
        cfg = self._config
        if cfg is None:
            return []
        channels = getattr(cfg, "dilution_channels", [])
        return [ch.to_dict() if hasattr(ch, "to_dict") else ch for ch in channels]

    def config_get_flush_channels(self) -> List[Dict[str, Any]]:
        cfg = self._config
        if cfg is None:
            return []
        channels = getattr(cfg, "flush_channels", [])
        return [ch.to_dict() if hasattr(ch, "to_dict") else ch for ch in channels]

    def config_get_pumps(self) -> List[Dict[str, Any]]:
        cfg = self._config
        if cfg is None:
            return []
        pumps = getattr(cfg, "pumps", [])
        return [p.to_dict() if hasattr(p, "to_dict") else p for p in pumps]
