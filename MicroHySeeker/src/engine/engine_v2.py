"""
实验引擎 V2 - 基于 QTimer 的精确状态机实现

参考 C# 源项目的 ExperimentEngine 实现：
1. 使用 QTimer (1秒) 替代 threading.sleep 实现精确的状态轮询
2. 实现完整状态机: IDLE → LOADING → READY → RUNNING → STEP_EXECUTING → PAUSED → COMPLETED/ERROR
3. ClockTick 模式: 更新时间 → 检查状态 → 分派 (idle/busy|nextsol/end)
4. 支持多批次注入和 Combo 迭代
"""
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, Signal, QTimer

from src.models import (
    Experiment, ProgStep, ProgramStepType, ECSettings, 
    SystemConfig, PrepSolParams
)
from src.core.step_state import (
    StepState, EngineState, StepExecutionContext,
    estimate_step_duration, validate_step_params
)
from src.core.batch_injection import BatchInjectionManager, InjectionChannel

logger = logging.getLogger(__name__)


class StepExecutor(QObject):
    """步骤执行器基类"""
    
    state_changed = Signal(StepState)  # 状态变更
    progress_updated = Signal(float, str)  # 进度(0-1), 消息
    log_message = Signal(str)
    completed = Signal(bool, str)  # 成功?, 消息
    
    def __init__(self, step: ProgStep, config: Optional[SystemConfig] = None):
        super().__init__()
        self.step = step
        self.config = config
        self.context = StepExecutionContext()
        self._timer: Optional[QTimer] = None
        self._rs485 = None  # 延迟初始化
    
    @property
    def rs485(self):
        if self._rs485 is None:
            from src.services.rs485_wrapper import get_rs485_instance
            self._rs485 = get_rs485_instance()
        return self._rs485
    
    def start(self):
        """启动执行"""
        raise NotImplementedError
    
    def pause(self):
        """暂停"""
        self.context.pause()
        if self._timer:
            self._timer.stop()
        self.state_changed.emit(self.context.state)
    
    def resume(self):
        """恢复"""
        self.context.resume()
        if self._timer:
            self._timer.start()
        self.state_changed.emit(self.context.state)
    
    def stop(self):
        """停止"""
        if self._timer:
            self._timer.stop()
        self._cleanup()
    
    def get_state(self) -> StepState:
        """获取当前状态"""
        return self.context.state
    
    def _cleanup(self):
        """清理资源"""
        pass
    
    def _tick(self):
        """定时回调 - 子类实现"""
        pass


class PrepSolExecutor(StepExecutor):
    """配液执行器 - 支持多批次注入"""
    
    def __init__(self, step: ProgStep, config: Optional[SystemConfig] = None):
        super().__init__(step, config)
        self.batch_manager = BatchInjectionManager()
        self._dilution_channels: Dict[str, dict] = {}
        self._setup_channels()
    
    def _setup_channels(self):
        """设置通道信息"""
        if self.config:
            for ch in self.config.dilution_channels:
                self._dilution_channels[ch.solution_name] = {
                    "pump_address": ch.pump_address,
                    "direction": ch.direction,
                    "stock_concentration": ch.stock_concentration,
                    "default_rpm": ch.default_rpm,
                    "channel_id": ch.pump_address,
                }
    
    def start(self):
        """启动配液"""
        if not self.step.prep_sol_params:
            self.context.fail("配液参数缺失")
            self.completed.emit(False, "配液参数缺失")
            return
        
        params = self.step.prep_sol_params
        
        # 计算各溶液体积
        volumes = self._calculate_volumes(params)
        if not volumes:
            self.context.fail("无有效溶液配置")
            self.completed.emit(False, "无有效溶液配置")
            return
        
        # 构建注入通道配置
        channels = []
        for sol_name, vol in volumes.items():
            if vol > 0:
                ch_info = self._dilution_channels.get(sol_name, {})
                inject_order = params.inject_orders.get(sol_name, 1) if hasattr(params, 'inject_orders') else 1
                channels.append({
                    "name": sol_name,
                    "channel_id": ch_info.get("channel_id", 0),
                    "volume_ul": vol,
                    "inject_order": inject_order,
                })
        
        # 配置批次管理器
        batch_count = self.batch_manager.configure(channels, batch_by_inject_order=True)
        if batch_count == 0:
            self.context.fail("配置批次失败")
            self.completed.emit(False, "配置批次失败")
            return
        
        # 设置回调
        self.batch_manager.on_batch_start(self._on_batch_start)
        self.batch_manager.on_batch_complete(self._on_batch_complete)
        self.batch_manager.on_channel_complete(self._on_channel_complete)
        self.batch_manager.on_all_complete(self._on_all_complete)
        
        # 估算时长
        estimated = estimate_step_duration("prep_sol", {
            "injection_order": list(volumes.keys()),
            "batch_count": batch_count,
        })
        
        # 启动
        self.context.start(estimated)
        self.context.batch_info = self.batch_manager.get_progress_info()
        self.state_changed.emit(self.context.state)
        
        self.log_message.emit(f"配液开始: {batch_count} 批次, 预计 {estimated:.1f}s")
        
        # 启动批次注入
        self.batch_manager.start()
        
        # 启动定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)  # 1秒间隔
    
    def _calculate_volumes(self, params: PrepSolParams) -> Dict[str, float]:
        """计算各溶液体积 (C1*V1 = C2*V2)"""
        volumes = {}
        total_volume_ul = params.total_volume_ul
        remaining_volume = total_volume_ul
        
        for sol_name in params.injection_order:
            if not params.selected_solutions.get(sol_name, False):
                continue
            
            is_solvent = params.solvent_flags.get(sol_name, False)
            
            if is_solvent:
                volumes[sol_name] = remaining_volume  # 溶剂填充剩余
            else:
                target_conc = params.target_concentrations.get(sol_name, 0.0)
                if target_conc <= 0:
                    continue
                
                ch_info = self._dilution_channels.get(sol_name, {})
                stock_conc = ch_info.get("stock_concentration", target_conc)
                
                if stock_conc > 0:
                    vol_needed = (target_conc * total_volume_ul) / stock_conc
                    volumes[sol_name] = vol_needed
                    remaining_volume -= vol_needed
        
        return volumes
    
    def _tick(self):
        """定时回调 - 更新状态"""
        state = self.batch_manager.update()
        self.context.state = state
        
        # 更新进度
        progress_info = self.batch_manager.get_progress_info()
        progress = progress_info["progress"]
        msg = f"批次 {progress_info['current_batch']}/{progress_info['total_batches']}"
        self.progress_updated.emit(progress, msg)
        
        self.state_changed.emit(state)
        
        # 检查完成
        if state.is_completed():
            self._timer.stop()
            if state.is_success():
                self.context.complete(True)
                self.log_message.emit("配液完成")
                self.completed.emit(True, "配液完成")
            else:
                self.log_message.emit("配液失败")
                self.completed.emit(False, self.context.error_message)
    
    def _on_batch_start(self, batch_idx: int, channels: List[str]):
        """批次开始回调"""
        self.log_message.emit(f"  批次 {batch_idx + 1} 开始: {', '.join(channels)}")
        
        # 启动对应泵
        for ch_name in channels:
            ch_info = self._dilution_channels.get(ch_name, {})
            pump_addr = ch_info.get("pump_address", 0)
            direction = ch_info.get("direction", "FWD")
            rpm = ch_info.get("default_rpm", 100)
            
            if pump_addr > 0:
                self.rs485.start_pump(pump_addr, direction, rpm)
    
    def _on_batch_complete(self, batch_idx: int):
        """批次完成回调"""
        self.log_message.emit(f"  批次 {batch_idx + 1} 完成")
        
        # 停止对应泵（通过批次信息获取）
        batch_summary = self.batch_manager.get_batch_summary()
        if batch_idx < len(batch_summary):
            for ch_name in batch_summary[batch_idx]["channels"]:
                ch_info = self._dilution_channels.get(ch_name, {})
                pump_addr = ch_info.get("pump_address", 0)
                if pump_addr > 0:
                    self.rs485.stop_pump(pump_addr)
    
    def _on_channel_complete(self, channel_name: str, batch_idx: int):
        """通道完成回调"""
        self.log_message.emit(f"    {channel_name} 注入完成")
    
    def _on_all_complete(self):
        """全部完成回调"""
        pass
    
    def _cleanup(self):
        """清理 - 停止所有泵"""
        for ch_info in self._dilution_channels.values():
            pump_addr = ch_info.get("pump_address", 0)
            if pump_addr > 0:
                try:
                    self.rs485.stop_pump(pump_addr)
                except:
                    pass


class TransferExecutor(StepExecutor):
    """移液执行器"""
    
    def start(self):
        pump_addr = self.step.pump_address
        if not pump_addr:
            self.context.fail("未指定泵地址")
            self.completed.emit(False, "未指定泵地址")
            return
        
        duration = self.step.transfer_duration or 10.0
        direction = self.step.pump_direction or "FWD"
        rpm = self.step.pump_rpm or 100
        
        self.context.start(duration)
        self.state_changed.emit(self.context.state)
        
        self.log_message.emit(f"移液: 泵{pump_addr} {direction} {rpm}RPM, 持续{duration}s")
        
        # 启动泵
        self.rs485.start_pump(pump_addr, direction, rpm)
        
        # 启动定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
    
    def _tick(self):
        elapsed = self.context.timing.elapsed_seconds
        progress = self.context.timing.progress
        remaining = self.context.timing.remaining_seconds
        
        self.progress_updated.emit(progress, f"剩余 {remaining:.0f}s")
        
        if progress >= 1.0:
            self._timer.stop()
            pump_addr = self.step.pump_address
            self.rs485.stop_pump(pump_addr)
            self.context.complete(True)
            self.completed.emit(True, "移液完成")
    
    def _cleanup(self):
        if self.step.pump_address:
            try:
                self.rs485.stop_pump(self.step.pump_address)
            except:
                pass


class FlushExecutor(StepExecutor):
    """冲洗执行器"""
    
    def __init__(self, step: ProgStep, config: Optional[SystemConfig] = None):
        super().__init__(step, config)
        self._current_cycle = 0
        self._cycles_total = 1
        self._cycle_duration = 30.0
        self._in_cycle = False
        self._cycle_start_time: Optional[datetime] = None
    
    def start(self):
        pump_addr = self.step.pump_address
        if not pump_addr:
            self.context.fail("未指定泵地址")
            self.completed.emit(False, "未指定泵地址")
            return
        
        self._cycles_total = self.step.flush_cycles or 1
        self._cycle_duration = self.step.flush_cycle_duration_s or 30.0
        total_duration = self._cycles_total * self._cycle_duration
        
        self.context.start(total_duration)
        self.state_changed.emit(self.context.state)
        
        rpm = self.step.flush_rpm or 100
        direction = self.step.pump_direction or "FWD"
        self.log_message.emit(
            f"冲洗: 泵{pump_addr} {direction} {rpm}RPM, "
            f"{self._cycles_total}次, 每次{self._cycle_duration}s"
        )
        
        # 开始第一个周期
        self._start_cycle()
        
        # 启动定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
    
    def _start_cycle(self):
        """开始一个冲洗周期"""
        self._in_cycle = True
        self._cycle_start_time = datetime.now()
        pump_addr = self.step.pump_address
        direction = self.step.pump_direction or "FWD"
        rpm = self.step.flush_rpm or 100
        
        self.log_message.emit(f"  冲洗第 {self._current_cycle + 1}/{self._cycles_total} 次...")
        self.rs485.start_pump(pump_addr, direction, rpm)
    
    def _end_cycle(self):
        """结束当前冲洗周期"""
        self._in_cycle = False
        pump_addr = self.step.pump_address
        self.rs485.stop_pump(pump_addr)
        self._current_cycle += 1
    
    def _tick(self):
        # 检查当前周期
        if self._in_cycle and self._cycle_start_time:
            cycle_elapsed = (datetime.now() - self._cycle_start_time).total_seconds()
            if cycle_elapsed >= self._cycle_duration:
                self._end_cycle()
                
                if self._current_cycle < self._cycles_total:
                    # 开始下一个周期
                    self._start_cycle()
                else:
                    # 全部完成
                    self._timer.stop()
                    self.context.complete(True)
                    self.log_message.emit("冲洗完成")
                    self.completed.emit(True, "冲洗完成")
                    return
        
        # 更新进度
        progress = self.context.timing.progress
        remaining = self.context.timing.remaining_seconds
        self.progress_updated.emit(
            progress, 
            f"第 {self._current_cycle + 1}/{self._cycles_total} 次, 剩余 {remaining:.0f}s"
        )
    
    def _cleanup(self):
        if self.step.pump_address:
            try:
                self.rs485.stop_pump(self.step.pump_address)
            except:
                pass


class EchemExecutor(StepExecutor):
    """电化学测量执行器"""
    
    def __init__(self, step: ProgStep, config: Optional[SystemConfig] = None):
        super().__init__(step, config)
        self._in_quiet_time = False
        self._quiet_start: Optional[datetime] = None
        self._measure_start: Optional[datetime] = None
        self._data_points: List[tuple] = []
    
    def start(self):
        if not self.step.ec_settings:
            self.context.fail("电化学参数缺失")
            self.completed.emit(False, "电化学参数缺失")
            return
        
        ec = self.step.ec_settings
        technique = ec.technique.value if hasattr(ec.technique, 'value') else str(ec.technique)
        
        # 估算时长
        estimated = estimate_step_duration("echem", {
            "technique": technique,
            "quiet_time_s": ec.quiet_time_s or 0,
            "eh": ec.eh,
            "el": ec.el,
            "scan_rate": ec.scan_rate or 0.1,
            "seg_num": ec.seg_num or 2,
            "run_time_s": ec.run_time_s or 60,
        })
        
        self.context.start(estimated)
        self.state_changed.emit(self.context.state)
        
        # 记录参数
        if technique in ["CV", "LSV"]:
            params_str = (
                f"E0={ec.e0:.2f}V, Eh={ec.eh:.2f}V, El={ec.el:.2f}V, "
                f"扫描速率={ec.scan_rate}V/s, 段数={ec.seg_num}"
            )
        elif technique in ["i-t", "IT"]:
            params_str = f"E0={ec.e0:.2f}V, 运行时间={ec.run_time_s}s"
        elif technique == "OCPT":
            params_str = f"运行时间={ec.run_time_s}s"
        else:
            params_str = f"采样间隔={ec.sample_interval_ms}ms"
        
        self.log_message.emit(f"电化学: {technique.upper()}, {params_str}")
        
        # 开始静置时间（如果有）
        quiet_time = ec.quiet_time_s or 0
        if quiet_time > 0:
            self._in_quiet_time = True
            self._quiet_start = datetime.now()
            self.log_message.emit(f"  静置时间: {quiet_time}s")
        else:
            self._start_measurement()
        
        # 启动定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
    
    def _start_measurement(self):
        """开始测量"""
        self._in_quiet_time = False
        self._measure_start = datetime.now()
        self.log_message.emit("  开始测量...")
    
    def _tick(self):
        ec = self.step.ec_settings
        
        # 检查静置时间
        if self._in_quiet_time and self._quiet_start:
            quiet_elapsed = (datetime.now() - self._quiet_start).total_seconds()
            quiet_time = ec.quiet_time_s or 0
            if quiet_elapsed >= quiet_time:
                self._start_measurement()
        
        # 测量阶段
        if not self._in_quiet_time and self._measure_start:
            measure_elapsed = (datetime.now() - self._measure_start).total_seconds()
            
            # 计算测量时长
            technique = ec.technique.value if hasattr(ec.technique, 'value') else str(ec.technique)
            if technique in ["CV", "LSV"]:
                e_range = abs(ec.eh - ec.el) if ec.eh and ec.el else 1.0
                measure_duration = (e_range * (ec.seg_num or 2)) / (ec.scan_rate or 0.1)
            else:
                measure_duration = ec.run_time_s or 60
            
            # 限制模拟时间
            actual_duration = min(measure_duration, 10)
            
            if measure_elapsed >= actual_duration:
                self._timer.stop()
                self.context.complete(True)
                self.log_message.emit(f"电化学完成: 采集 {len(self._data_points)} 个数据点")
                self.completed.emit(True, "电化学测量完成")
                return
            
            # 模拟数据采集
            self._collect_data_point(measure_elapsed, technique)
        
        # 更新进度
        progress = self.context.timing.progress
        remaining = self.context.timing.remaining_seconds
        phase = "静置中" if self._in_quiet_time else "测量中"
        self.progress_updated.emit(progress, f"{phase}, 剩余 {remaining:.0f}s")
    
    def _collect_data_point(self, elapsed: float, technique: str):
        """采集数据点（模拟）"""
        ec = self.step.ec_settings
        
        if technique == "CV":
            e_range = abs(ec.eh - ec.el) if ec.eh and ec.el else 1.0
            cycle_time = e_range / (ec.scan_rate or 0.1)
            t_in_cycle = elapsed % cycle_time
            segment = int(elapsed / cycle_time) % 2
            if segment == 0:
                potential = (ec.el or -0.2) + (t_in_cycle / cycle_time) * e_range
            else:
                potential = (ec.eh or 0.8) - (t_in_cycle / cycle_time) * e_range
            current = 1e-6 * (potential - 0.3) + 1e-7
        elif technique == "OCPT":
            potential = 0.2 + 0.01 * elapsed
            current = 0
        else:
            potential = ec.e0 or 0
            current = 1e-6 * (1 - 2.718 ** (-elapsed / 5))
        
        self._data_points.append((elapsed, potential, current))


class BlankExecutor(StepExecutor):
    """空白步骤执行器"""
    
    def start(self):
        duration = self.step.duration_s or 5.0
        self.context.start(duration)
        self.state_changed.emit(self.context.state)
        
        self.log_message.emit(f"空白: 等待 {duration}s")
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
    
    def _tick(self):
        progress = self.context.timing.progress
        remaining = self.context.timing.remaining_seconds
        
        self.progress_updated.emit(progress, f"等待中, 剩余 {remaining:.0f}s")
        
        if progress >= 1.0:
            self._timer.stop()
            self.context.complete(True)
            self.log_message.emit("空白步骤完成")
            self.completed.emit(True, "空白步骤完成")


class EvacuateExecutor(StepExecutor):
    """排空执行器"""
    
    def __init__(self, step: ProgStep, config: Optional[SystemConfig] = None):
        super().__init__(step, config)
        self._current_cycle = 0
        self._cycles_total = 1
        self._cycle_duration = 30.0
        self._in_cycle = False
        self._cycle_start_time: Optional[datetime] = None
    
    def start(self):
        pump_addr = self.step.pump_address
        if not pump_addr:
            self.context.fail("未指定泵地址")
            self.completed.emit(False, "未指定泵地址")
            return
        
        self._cycles_total = self.step.flush_cycles or 1
        self._cycle_duration = self.step.transfer_duration or 30.0
        total_duration = self._cycles_total * self._cycle_duration
        
        self.context.start(total_duration)
        self.state_changed.emit(self.context.state)
        
        rpm = self.step.pump_rpm or 100
        direction = self.step.pump_direction or "FWD"
        self.log_message.emit(
            f"排空: 泵{pump_addr} {direction} {rpm}RPM, "
            f"{self._cycles_total}次, 每次{self._cycle_duration}s"
        )
        
        self._start_cycle()
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
    
    def _start_cycle(self):
        self._in_cycle = True
        self._cycle_start_time = datetime.now()
        pump_addr = self.step.pump_address
        direction = self.step.pump_direction or "FWD"
        rpm = self.step.pump_rpm or 100
        
        self.log_message.emit(f"  排空第 {self._current_cycle + 1}/{self._cycles_total} 次...")
        self.rs485.start_pump(pump_addr, direction, rpm)
    
    def _end_cycle(self):
        self._in_cycle = False
        pump_addr = self.step.pump_address
        self.rs485.stop_pump(pump_addr)
        self._current_cycle += 1
    
    def _tick(self):
        if self._in_cycle and self._cycle_start_time:
            cycle_elapsed = (datetime.now() - self._cycle_start_time).total_seconds()
            if cycle_elapsed >= self._cycle_duration:
                self._end_cycle()
                
                if self._current_cycle < self._cycles_total:
                    self._start_cycle()
                else:
                    self._timer.stop()
                    self.context.complete(True)
                    self.log_message.emit("排空完成")
                    self.completed.emit(True, "排空完成")
                    return
        
        progress = self.context.timing.progress
        remaining = self.context.timing.remaining_seconds
        self.progress_updated.emit(
            progress, 
            f"第 {self._current_cycle + 1}/{self._cycles_total} 次, 剩余 {remaining:.0f}s"
        )
    
    def _cleanup(self):
        if self.step.pump_address:
            try:
                self.rs485.stop_pump(self.step.pump_address)
            except:
                pass


@dataclass
class ExperimentProgress:
    """实验进度信息"""
    state: EngineState = EngineState.IDLE
    current_step_index: int = -1
    total_steps: int = 0
    current_step_name: str = ""
    current_step_state: StepState = StepState.IDLE
    step_progress: float = 0.0  # 当前步骤进度 (0-1)
    step_message: str = ""
    overall_progress: float = 0.0  # 总体进度 (0-1)
    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0
    
    # Combo 信息
    current_combo_index: int = 0
    total_combos: int = 1
    
    # 批次信息（配液用）
    current_batch: int = 0
    total_batches: int = 0


class ExperimentEngineV2(QObject):
    """实验引擎 V2 - 基于 QTimer 的精确状态机实现"""
    
    # 信号
    state_changed = Signal(EngineState)
    step_started = Signal(int, str)  # step_index, step_id
    step_finished = Signal(int, str, bool)  # step_index, step_id, success
    step_progress = Signal(int, float, str)  # step_index, progress(0-1), message
    log_message = Signal(str)
    experiment_finished = Signal(bool)  # success
    progress_updated = Signal(ExperimentProgress)
    
    def __init__(self, config: Optional[SystemConfig] = None):
        super().__init__()
        self.config = config
        self._state = EngineState.IDLE
        self._experiment: Optional[Experiment] = None
        self._current_step_index = -1
        self._current_executor: Optional[StepExecutor] = None
        self._progress = ExperimentProgress()
        
        # 主定时器 (1秒间隔，类似 C# ClockTick)
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._clock_tick)
        
        # 启动时间
        self._start_time: Optional[datetime] = None
    
    @property
    def state(self) -> EngineState:
        return self._state
    
    @state.setter
    def state(self, value: EngineState):
        if self._state != value:
            self._state = value
            self.state_changed.emit(value)
    
    def set_config(self, config: SystemConfig):
        """设置系统配置"""
        self.config = config
    
    def load_experiment(self, experiment: Experiment) -> bool:
        """加载实验"""
        if self.state.is_active():
            logger.warning("实验正在运行，无法加载新实验")
            return False
        
        self.state = EngineState.LOADING
        self.log_message.emit(f"[引擎] 加载实验: {experiment.name}")
        
        # 验证步骤
        for i, step in enumerate(experiment.steps):
            errors = self._validate_step(step)
            if errors:
                for err in errors:
                    self.log_message.emit(f"[警告] 步骤 {i+1}: {err}")
        
        self._experiment = experiment
        self._current_step_index = -1
        
        # 更新进度信息
        self._progress.total_steps = len(experiment.steps)
        self._progress.current_step_index = -1
        
        self.state = EngineState.READY
        self.log_message.emit(f"[引擎] 实验已加载，共 {len(experiment.steps)} 步")
        return True
    
    def start(self) -> bool:
        """启动实验"""
        if not self._experiment:
            logger.error("没有加载实验")
            return False
        
        if not self.state.can_start():
            logger.warning(f"当前状态 {self.state} 无法启动")
            return False
        
        self.state = EngineState.RUNNING
        self._start_time = datetime.now()
        self.log_message.emit(f"[引擎] 开始执行实验")
        
        # 启动主定时器
        self._tick_timer.start(1000)
        
        # 开始第一步
        self._advance_to_next_step()
        
        return True
    
    def pause(self):
        """暂停"""
        if self.state & EngineState.RUNNING:
            self.state = EngineState.PAUSED
            if self._current_executor:
                self._current_executor.pause()
            self.log_message.emit("[引擎] 已暂停")
    
    def resume(self):
        """恢复"""
        if self.state & EngineState.PAUSED:
            self.state = EngineState.RUNNING
            if self._current_executor:
                self._current_executor.resume()
            self.log_message.emit("[引擎] 已恢复")
    
    def stop(self):
        """停止"""
        self._tick_timer.stop()
        if self._current_executor:
            self._current_executor.stop()
            self._current_executor = None
        
        self.state = EngineState.IDLE
        self.log_message.emit("[引擎] 已停止")
        self.experiment_finished.emit(False)
    
    def _clock_tick(self):
        """主定时回调 (类似 C# ClockTick)
        
        执行逻辑：
        1. 更新时间
        2. 检查当前步骤状态
        3. 根据状态分派 (idle/busy/nextsol/end)
        """
        # 更新已运行时间
        if self._start_time:
            self._progress.elapsed_seconds = (datetime.now() - self._start_time).total_seconds()
        
        # 检查当前执行器状态
        if self._current_executor:
            step_state = self._current_executor.get_state()
            self._progress.current_step_state = step_state
            
            if step_state.is_completed():
                # 步骤完成
                success = step_state.is_success()
                self._on_step_completed(success)
            elif step_state.needs_next_batch():
                # 需要下一批次（由执行器内部处理）
                pass
        
        # 广播进度
        self._update_progress()
        self.progress_updated.emit(self._progress)
    
    def _advance_to_next_step(self):
        """推进到下一步"""
        self._current_step_index += 1
        
        if self._current_step_index >= len(self._experiment.steps):
            # 全部完成
            self._on_experiment_completed(True)
            return
        
        step = self._experiment.steps[self._current_step_index]
        self._execute_step(step)
    
    def _execute_step(self, step: ProgStep):
        """执行步骤"""
        self._progress.current_step_index = self._current_step_index
        self._progress.current_step_name = step.step_type.value
        
        self.step_started.emit(self._current_step_index, step.step_id)
        self.log_message.emit(f"[步骤 {self._current_step_index + 1}] 开始: {step.step_type.value}")
        
        # 创建对应的执行器
        executor = self._create_executor(step)
        if not executor:
            self.log_message.emit(f"[错误] 不支持的步骤类型: {step.step_type.value}")
            self._on_step_completed(False)
            return
        
        self._current_executor = executor
        
        # 连接信号
        executor.state_changed.connect(self._on_executor_state_changed)
        executor.progress_updated.connect(self._on_executor_progress)
        executor.log_message.connect(self._on_executor_log)
        executor.completed.connect(self._on_executor_completed)
        
        # 启动执行
        executor.start()
    
    def _create_executor(self, step: ProgStep) -> Optional[StepExecutor]:
        """创建步骤执行器"""
        executors = {
            ProgramStepType.PREP_SOL: PrepSolExecutor,
            ProgramStepType.TRANSFER: TransferExecutor,
            ProgramStepType.FLUSH: FlushExecutor,
            ProgramStepType.ECHEM: EchemExecutor,
            ProgramStepType.BLANK: BlankExecutor,
            ProgramStepType.EVACUATE: EvacuateExecutor,
        }
        
        executor_class = executors.get(step.step_type)
        if executor_class:
            return executor_class(step, self.config)
        return None
    
    def _validate_step(self, step: ProgStep) -> List[str]:
        """验证步骤"""
        params = {}
        
        if step.step_type == ProgramStepType.PREP_SOL and step.prep_sol_params:
            params = {
                "injection_order": step.prep_sol_params.injection_order,
                "selected_solutions": step.prep_sol_params.selected_solutions,
                "total_volume_ul": step.prep_sol_params.total_volume_ul,
            }
        elif step.step_type == ProgramStepType.TRANSFER:
            params = {
                "pump_address": step.pump_address,
                "duration_s": step.transfer_duration,
            }
        elif step.step_type == ProgramStepType.FLUSH:
            params = {
                "pump_address": step.pump_address,
                "cycles": step.flush_cycles,
            }
        elif step.step_type == ProgramStepType.ECHEM and step.ec_settings:
            ec = step.ec_settings
            params = {
                "technique": ec.technique.value if hasattr(ec.technique, 'value') else str(ec.technique),
                "eh": ec.eh,
                "el": ec.el,
                "scan_rate": ec.scan_rate,
            }
        elif step.step_type == ProgramStepType.EVACUATE:
            params = {
                "pump_address": step.pump_address,
            }
        
        return validate_step_params(step.step_type.value, params)
    
    def _on_executor_state_changed(self, state: StepState):
        """执行器状态变更"""
        self._progress.current_step_state = state
    
    def _on_executor_progress(self, progress: float, message: str):
        """执行器进度更新"""
        self._progress.step_progress = progress
        self._progress.step_message = message
        self.step_progress.emit(self._current_step_index, progress, message)
    
    def _on_executor_log(self, message: str):
        """执行器日志"""
        self.log_message.emit(message)
    
    def _on_executor_completed(self, success: bool, message: str):
        """执行器完成"""
        pass  # 由 _clock_tick 处理
    
    def _on_step_completed(self, success: bool):
        """步骤完成"""
        step_id = ""
        if self._experiment and 0 <= self._current_step_index < len(self._experiment.steps):
            step_id = self._experiment.steps[self._current_step_index].step_id
        
        self.step_finished.emit(self._current_step_index, step_id, success)
        
        if success:
            self.log_message.emit(f"[步骤 {self._current_step_index + 1}] 完成")
            # 继续下一步
            self._advance_to_next_step()
        else:
            self.log_message.emit(f"[步骤 {self._current_step_index + 1}] 失败")
            self._on_experiment_completed(False)
    
    def _on_experiment_completed(self, success: bool):
        """实验完成"""
        self._tick_timer.stop()
        self._current_executor = None
        
        if success:
            self.state = EngineState.COMPLETED
            self.log_message.emit("[引擎] 实验成功完成")
        else:
            self.state = EngineState.ERROR
            self.log_message.emit("[引擎] 实验执行失败")
        
        self.experiment_finished.emit(success)
    
    def _update_progress(self):
        """更新进度信息"""
        self._progress.state = self._state
        
        # 计算总体进度
        if self._progress.total_steps > 0:
            step_weight = 1.0 / self._progress.total_steps
            completed_steps = max(0, self._current_step_index)
            self._progress.overall_progress = (
                completed_steps * step_weight + 
                self._progress.step_progress * step_weight
            )
