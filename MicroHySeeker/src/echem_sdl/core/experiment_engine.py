"""
ExperimentEngine - 实验执行引擎

驱动实验程序执行，协调硬件操作，管理组合实验迭代。
采用状态机 + 线程驱动模式。
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any, TYPE_CHECKING
import threading
import time
from datetime import datetime

from .prog_step import ProgStep, StepType
from .exp_program import ExpProgram

if TYPE_CHECKING:
    from ..lib_context import LibContext
    from ..hardware.chi import CHIInstrument, ECParameters, ECDataPoint
    from ..hardware.pump_manager import PumpManager
    from ..hardware.diluter import Diluter
    from ..hardware.flusher import Flusher


class EngineState(Enum):
    """引擎状态"""
    IDLE = "idle"                    # 空闲
    LOADING = "loading"              # 加载程序中
    READY = "ready"                  # 已就绪
    RUNNING = "running"              # 运行中
    STEP_EXECUTING = "step_executing"  # 步骤执行中
    PAUSED = "paused"                # 已暂停
    STOPPING = "stopping"            # 停止中
    COMPLETED = "completed"          # 已完成
    ERROR = "error"                  # 错误


# ========================
# 事件类型
# ========================

EVENT_EXPERIMENT_STARTED = "experiment_started"
EVENT_EXPERIMENT_COMPLETED = "experiment_completed"
EVENT_EXPERIMENT_STOPPED = "experiment_stopped"
EVENT_EXPERIMENT_ERROR = "experiment_error"
EVENT_STEP_STARTED = "step_started"
EVENT_STEP_COMPLETED = "step_completed"
EVENT_STEP_PROGRESS = "step_progress"
EVENT_COMBO_ADVANCED = "combo_advanced"
EVENT_ECHEM_DATA = "echem_data"
EVENT_STATE_CHANGED = "state_changed"


@dataclass
class EngineStatus:
    """引擎状态信息"""
    state: EngineState = EngineState.IDLE
    current_step_index: int = 0
    current_step_name: str = ""
    current_combo_index: int = 0
    total_combos: int = 1
    elapsed_time: float = 0.0
    step_elapsed_time: float = 0.0
    progress: float = 0.0
    step_progress: float = 0.0
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "current_step_index": self.current_step_index,
            "current_step_name": self.current_step_name,
            "current_combo_index": self.current_combo_index,
            "total_combos": self.total_combos,
            "elapsed_time": self.elapsed_time,
            "step_elapsed_time": self.step_elapsed_time,
            "progress": self.progress,
            "step_progress": self.step_progress,
            "error_message": self.error_message,
        }


@dataclass
class ExperimentResult:
    """实验结果"""
    experiment_name: str = ""
    program_name: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    combo_index: int = 0
    combo_params: Dict[str, Any] = field(default_factory=dict)
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    ec_data_sets: List[Any] = field(default_factory=list)
    success: bool = False
    error_message: str = ""
    
    @property
    def duration(self) -> float:
        if self.start_time is None or self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()


class ExperimentEngine:
    """实验执行引擎
    
    驱动实验程序执行，协调硬件操作，管理组合实验迭代。
    
    Attributes:
        state: 当前引擎状态
        program: 当前加载的实验程序
        current_step_index: 当前步骤索引
        current_combo_index: 当前组合索引
        elapsed_time: 实验已运行时间（秒）
        
    Example:
        >>> engine = ExperimentEngine(context)
        >>> engine.load_program(program)
        >>> engine.start()
        >>> while engine.is_running:
        ...     print(f"Step {engine.current_step_index}, Progress: {engine.progress}")
        ...     time.sleep(1)
    """
    
    def __init__(
        self,
        context: Optional["LibContext"] = None,
        mock_mode: bool = True,
        tick_interval: float = 0.5
    ) -> None:
        """初始化实验引擎
        
        Args:
            context: 全局上下文（包含硬件和服务实例）
            mock_mode: Mock模式
            tick_interval: 心跳间隔（秒）
        """
        self._context = context
        self._mock_mode = mock_mode
        self._tick_interval = tick_interval
        
        # 状态
        self._state = EngineState.IDLE
        self._program: Optional[ExpProgram] = None
        self._current_step_index = 0
        self._current_combo_index = 0
        self._total_combos = 1
        self._combo_mode = False
        
        # 时间跟踪
        self._start_time = 0.0
        self._step_start_time = 0.0
        self._elapsed_time = 0.0
        self._step_elapsed_time = 0.0
        
        # 控制标志
        self._stop_requested = False
        self._pause_requested = False
        
        # 线程
        self._lock = threading.RLock()
        self._run_thread: Optional[threading.Thread] = None
        self._ticker_thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # 初始非暂停
        
        # 事件回调
        self._event_callbacks: List[Callable[[str, Dict], None]] = []
        self._specific_callbacks: Dict[str, List[Callable]] = {}
        
        # 结果
        self._current_result: Optional[ExperimentResult] = None
        self._results: List[ExperimentResult] = []
        
        # 硬件引用（延迟获取）
        self._pump_manager: Optional["PumpManager"] = None
        self._chi: Optional["CHIInstrument"] = None
        self._diluters: Dict[str, "Diluter"] = {}
        self._flusher: Optional["Flusher"] = None
        
        # 日志
        self._logger = None
        if context:
            self._logger = context.get_logger()
    
    # ========================
    # 属性
    # ========================
    
    @property
    def state(self) -> EngineState:
        """当前状态"""
        return self._state
    
    @property
    def program(self) -> Optional[ExpProgram]:
        """当前程序"""
        return self._program
    
    @property
    def current_step_index(self) -> int:
        """当前步骤索引"""
        return self._current_step_index
    
    @property
    def current_step(self) -> Optional[ProgStep]:
        """当前步骤"""
        if self._program and 0 <= self._current_step_index < len(self._program.steps):
            return self._program.steps[self._current_step_index]
        return None
    
    @property
    def current_combo_index(self) -> int:
        """当前组合索引"""
        return self._current_combo_index
    
    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._state in [EngineState.RUNNING, EngineState.STEP_EXECUTING]
    
    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._state == EngineState.PAUSED
    
    @property
    def elapsed_time(self) -> float:
        """已运行时间（秒）"""
        if self._start_time > 0 and self.is_running:
            return time.time() - self._start_time
        return self._elapsed_time
    
    @property
    def step_elapsed_time(self) -> float:
        """当前步骤已运行时间"""
        if self._step_start_time > 0 and self.is_running:
            return time.time() - self._step_start_time
        return self._step_elapsed_time
    
    @property
    def progress(self) -> float:
        """计算总进度 (0-1)"""
        if not self._program or not self._program.steps:
            return 0.0
        
        total_steps = len(self._program.steps)
        
        if self._combo_mode and self._total_combos > 1:
            combo_progress = self._current_combo_index / self._total_combos
            step_progress = self._current_step_index / total_steps
            return combo_progress + step_progress / self._total_combos
        else:
            base = self._current_step_index / total_steps
            step_contrib = self.step_progress / total_steps
            return base + step_contrib
    
    @property
    def step_progress(self) -> float:
        """计算步骤进度 (0-1)"""
        current = self.current_step
        if current is None:
            return 0.0
        
        duration = current.get_duration()
        if duration <= 0:
            return 0.0
        
        return min(self.step_elapsed_time / duration, 1.0)
    
    def get_status(self) -> EngineStatus:
        """获取引擎状态"""
        return EngineStatus(
            state=self._state,
            current_step_index=self._current_step_index,
            current_step_name=self.current_step.name if self.current_step else "",
            current_combo_index=self._current_combo_index,
            total_combos=self._total_combos,
            elapsed_time=self.elapsed_time,
            step_elapsed_time=self.step_elapsed_time,
            progress=self.progress,
            step_progress=self.step_progress,
        )
    
    # ========================
    # 公开方法
    # ========================
    
    def load_program(self, program: ExpProgram) -> bool:
        """加载实验程序
        
        Args:
            program: 实验程序
            
        Returns:
            bool: 加载是否成功
        """
        with self._lock:
            if self._state not in [EngineState.IDLE, EngineState.COMPLETED, EngineState.ERROR]:
                self._log("无法加载程序：引擎正在运行", "warning")
                return False
            
            self._state = EngineState.LOADING
            
            # 验证程序
            errors = program.validate()
            if errors:
                self._log(f"程序验证失败: {errors}", "error")
                self._state = EngineState.ERROR
                return False
            
            self._program = program
            self._current_step_index = 0
            self._current_combo_index = 0
            self._total_combos = program.combo_count
            
            self._state = EngineState.READY
            self._log(f"程序已加载: {program.name}, {program.step_count} 步骤, {self._total_combos} 组合")
            
            return True
    
    def prepare_hardware(self) -> bool:
        """准备硬件（连接设备）"""
        if self._context is None:
            self._log("无上下文，使用Mock模式", "warning")
            return True
        
        try:
            # 获取泵管理器
            self._pump_manager = self._context.get_pump_manager(self._mock_mode)
            
            # 获取CHI（如果需要电化学步骤）
            if self._program:
                for step in self._program.steps:
                    if step.step_type == StepType.ECHEM:
                        self._chi = self._get_or_create_chi()
                        break
            
            return True
        except Exception as e:
            self._log(f"硬件准备失败: {e}", "error")
            return False
    
    def start(self, combo_mode: bool = False) -> bool:
        """启动实验
        
        Args:
            combo_mode: 是否启用组合实验模式
            
        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if self._state not in [EngineState.READY, EngineState.IDLE]:
                self._log(f"无法启动：当前状态 {self._state.value}", "warning")
                return False
            
            if not self._program:
                self._log("无程序加载", "error")
                return False
            
            self._combo_mode = combo_mode
            self._stop_requested = False
            self._pause_requested = False
            self._pause_event.set()
            
            if combo_mode:
                # 生成组合参数矩阵
                self._program.fill_param_matrix()
                self._total_combos = self._program.combo_count
                self._current_combo_index = 0
                
                # 加载第一组参数
                self._program.load_param_values(0)
            
            self._current_step_index = 0
            self._start_time = time.time()
            self._state = EngineState.RUNNING
            
            # 初始化结果
            self._current_result = ExperimentResult(
                experiment_name=f"Experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                program_name=self._program.name,
                start_time=datetime.now(),
                combo_index=self._current_combo_index,
                combo_params=self._program.get_current_params() if combo_mode else {},
            )
            
            self._emit_event(EVENT_EXPERIMENT_STARTED, {
                "program_name": self._program.name,
                "combo_mode": combo_mode,
                "total_combos": self._total_combos,
            })
            
            # 启动执行线程
            self._run_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._run_thread.start()
            
            self._log(f"实验已启动: {self._program.name}, combo_mode={combo_mode}")
            return True
    
    def stop(self) -> bool:
        """停止实验"""
        with self._lock:
            if self._state not in [EngineState.RUNNING, EngineState.STEP_EXECUTING, EngineState.PAUSED]:
                return True
            
            self._stop_requested = True
            self._pause_event.set()  # 取消暂停以允许线程退出
            self._state = EngineState.STOPPING
            
            self._log("停止请求已发送")
            return True
    
    def pause(self) -> bool:
        """暂停实验"""
        with self._lock:
            if self._state not in [EngineState.RUNNING, EngineState.STEP_EXECUTING]:
                return False
            
            self._pause_requested = True
            self._pause_event.clear()
            self._state = EngineState.PAUSED
            self._elapsed_time = self.elapsed_time
            
            self._log("实验已暂停")
            return True
    
    def resume(self) -> bool:
        """恢复实验"""
        with self._lock:
            if self._state != EngineState.PAUSED:
                return False
            
            self._pause_requested = False
            self._pause_event.set()
            self._state = EngineState.RUNNING
            self._start_time = time.time() - self._elapsed_time
            
            self._log("实验已恢复")
            return True
    
    def reset(self) -> None:
        """重置引擎状态"""
        with self._lock:
            if self.is_running:
                self.stop()
            
            self._state = EngineState.IDLE
            self._program = None
            self._current_step_index = 0
            self._current_combo_index = 0
            self._elapsed_time = 0.0
            self._step_elapsed_time = 0.0
            self._results.clear()
            
            self._log("引擎已重置")
    
    # ========================
    # 事件系统
    # ========================
    
    def on_event(self, callback: Callable[[str, Dict], None]) -> None:
        """订阅所有事件"""
        self._event_callbacks.append(callback)
    
    def on(self, event_type: str, callback: Callable) -> None:
        """订阅特定事件"""
        if event_type not in self._specific_callbacks:
            self._specific_callbacks[event_type] = []
        self._specific_callbacks[event_type].append(callback)
    
    def off(self, event_type: str, callback: Callable) -> None:
        """取消订阅"""
        if event_type in self._specific_callbacks:
            if callback in self._specific_callbacks[event_type]:
                self._specific_callbacks[event_type].remove(callback)
    
    def _emit_event(self, event_type: str, data: Dict = None) -> None:
        """发出事件"""
        data = data or {}
        data["timestamp"] = time.time()
        data["state"] = self._state.value
        
        # 通用回调
        for cb in self._event_callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                self._log(f"事件回调错误: {e}", "error")
        
        # 特定回调
        for cb in self._specific_callbacks.get(event_type, []):
            try:
                cb(data)
            except Exception as e:
                self._log(f"事件回调错误: {e}", "error")
    
    # ========================
    # 执行循环
    # ========================
    
    def _run_loop(self) -> None:
        """主执行循环"""
        try:
            while not self._stop_requested:
                # 等待暂停结束
                self._pause_event.wait()
                
                if self._stop_requested:
                    break
                
                # 获取当前步骤
                if self._current_step_index >= len(self._program.steps):
                    # 当前组合完成
                    if self._combo_mode and self._advance_combo():
                        # 继续下一组合
                        continue
                    else:
                        # 全部完成
                        self._complete()
                        break
                
                step = self._program.steps[self._current_step_index]
                
                if not step.enabled:
                    # 跳过禁用的步骤
                    self._current_step_index += 1
                    continue
                
                # 执行步骤
                self._execute_step(step)
                
                if self._stop_requested:
                    break
                
                # 推进到下一步
                self._advance_step()
                
        except Exception as e:
            self._log(f"执行错误: {e}", "error")
            self._state = EngineState.ERROR
            self._emit_event(EVENT_EXPERIMENT_ERROR, {"error": str(e)})
        
        finally:
            if self._stop_requested:
                self._state = EngineState.IDLE
                self._emit_event(EVENT_EXPERIMENT_STOPPED, {})
                self._log("实验已停止")
    
    def _execute_step(self, step: ProgStep) -> None:
        """执行单个步骤"""
        self._state = EngineState.STEP_EXECUTING
        self._step_start_time = time.time()
        
        self._emit_event(EVENT_STEP_STARTED, {
            "index": self._current_step_index,
            "step_type": step.step_type.value,
            "step_name": step.name,
        })
        
        self._log(f"执行步骤 {self._current_step_index}: {step.name} ({step.step_type.value})")
        
        step_type = step.step_type
        success = False
        
        try:
            if step_type == StepType.PREP_SOL:
                success = self._execute_prep_sol(step)
            elif step_type == StepType.TRANSFER:
                success = self._execute_transfer(step)
            elif step_type == StepType.FLUSH:
                success = self._execute_flush(step)
            elif step_type == StepType.ECHEM:
                success = self._execute_echem(step)
            elif step_type == StepType.BLANK:
                success = self._execute_blank(step)
            elif step_type == StepType.EVACUATE:
                success = self._execute_evacuate(step)
            else:
                self._log(f"未知步骤类型: {step_type}", "warning")
                success = True
            
        except Exception as e:
            self._log(f"步骤执行错误: {e}", "error")
            success = False
        
        self._step_elapsed_time = time.time() - self._step_start_time
        
        self._emit_event(EVENT_STEP_COMPLETED, {
            "index": self._current_step_index,
            "success": success,
            "duration": self._step_elapsed_time,
        })
        
        # 记录步骤结果
        if self._current_result:
            self._current_result.step_results.append({
                "index": self._current_step_index,
                "name": step.name,
                "type": step.step_type.value,
                "success": success,
                "duration": self._step_elapsed_time,
            })
    
    def _advance_step(self) -> None:
        """推进到下一步骤"""
        self._current_step_index += 1
        self._state = EngineState.RUNNING
    
    def _advance_combo(self) -> bool:
        """推进到下一个组合
        
        Returns:
            bool: 是否有下一个组合
        """
        # 保存当前结果
        if self._current_result:
            self._current_result.end_time = datetime.now()
            self._current_result.success = True
            self._results.append(self._current_result)
        
        next_index = self._current_combo_index + 1
        
        if next_index >= self._total_combos:
            return False
        
        self._current_combo_index = next_index
        self._program.load_param_values(next_index)
        self._current_step_index = 0
        
        # 新建结果
        self._current_result = ExperimentResult(
            experiment_name=f"Experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            program_name=self._program.name,
            start_time=datetime.now(),
            combo_index=self._current_combo_index,
            combo_params=self._program.get_current_params(),
        )
        
        self._emit_event(EVENT_COMBO_ADVANCED, {
            "index": next_index,
            "total": self._total_combos,
            "params": self._program.get_current_params(),
        })
        
        self._log(f"切换到组合 {next_index + 1}/{self._total_combos}")
        return True
    
    def _complete(self) -> None:
        """完成实验"""
        # 保存最后结果
        if self._current_result:
            self._current_result.end_time = datetime.now()
            self._current_result.success = True
            self._results.append(self._current_result)
        
        self._elapsed_time = time.time() - self._start_time
        self._state = EngineState.COMPLETED
        
        self._emit_event(EVENT_EXPERIMENT_COMPLETED, {
            "total_duration": self._elapsed_time,
            "combo_count": self._current_combo_index + 1 if self._combo_mode else 1,
        })
        
        self._log(f"实验完成，总时长 {self._elapsed_time:.1f} 秒")
    
    # ========================
    # 步骤执行器
    # ========================
    
    def _execute_prep_sol(self, step: ProgStep) -> bool:
        """执行配液步骤
        
        配液使用 DilutionChannel 中配置的稀释泵
        支持多批次注入模式（类似C# InjectOrder）:
        - 单批次: 一次性完成配液
        - 多批次: 分批注入，每批次之间可设置间隔
        """
        config = step.prep_sol_config
        if not config:
            return False
        
        # 获取注入顺序
        injection_order = config.get_injection_order()
        
        if config.multi_batch and config.batch_count > 1:
            # 多批次注入模式
            batch_volumes = config.get_batch_volumes_ul()
            
            self._log(f"配液(多批次): {config.concentrations}, "
                     f"总体积 {config.total_volume_ul} uL, "
                     f"{config.batch_count} 批次")
            
            for batch_idx in range(config.batch_count):
                if self._stop_requested:
                    return False
                
                batch_vol = batch_volumes[batch_idx]
                self._log(f"  批次 {batch_idx + 1}/{config.batch_count}: {batch_vol:.1f} uL")
                
                # 计算该批次各通道体积
                for channel_id in injection_order:
                    if self._stop_requested:
                        return False
                    
                    conc = config.get_concentration(channel_id)
                    channel_vol = batch_vol * conc
                    
                    if channel_vol > 0:
                        # 获取该通道的泵地址
                        pump_addr = self._get_diluter_pump(channel_id)
                        self._log(f"    {channel_id}: {channel_vol:.2f} uL (泵{pump_addr})")
                        
                        # Mock或真实硬件执行
                        if self._mock_mode:
                            # 模拟单个通道注液时间
                            self._simulate_duration(channel_vol / 50.0)  # 假设 50 uL/s
                        else:
                            # 真实硬件: 调用Diluter
                            if self._pump_manager and pump_addr > 0:
                                try:
                                    # 计算运行时间（假设 50 uL/s）
                                    duration = channel_vol / 50.0
                                    self._pump_manager.start_pump(pump_addr, "FWD", 100)
                                    self._wait_with_stop_check(duration)
                                    self._pump_manager.stop_pump(pump_addr)
                                except Exception as e:
                                    self._log(f"通道 {channel_id} 配液失败: {e}", "error")
                
                # 批次间间隔
                if batch_idx < config.batch_count - 1:
                    if config.batch_interval_s > 0:
                        self._log(f"  等待 {config.batch_interval_s}s")
                        self._simulate_duration(config.batch_interval_s)
            
            # 混合（如果配置了）
            if config.mix_count > 0:
                self._log(f"  混合 {config.mix_count} 次")
                self._simulate_duration(config.mix_count * 0.5)  # 假设每次混合 0.5s
            
            return True
        else:
            # 单批次模式
            self._log(f"配液: {config.concentrations}, 总体积 {config.total_volume_ul} uL")
            
            if self._mock_mode:
                # Mock模式: 使用基于体积的快速模拟（50 uL/s）
                for channel_id in injection_order:
                    if self._stop_requested:
                        return False
                    conc = config.get_concentration(channel_id)
                    channel_vol = config.total_volume_ul * conc
                    if channel_vol > 0:
                        pump_addr = self._get_diluter_pump(channel_id)
                        self._log(f"  {channel_id}: {channel_vol:.2f} uL (泵{pump_addr})")
                        self._simulate_duration(channel_vol / 50.0)
                return True
            
            # 真实硬件配液 - 按通道顺序逐个配制
            for channel_id in injection_order:
                if self._stop_requested:
                    return False
                
                conc = config.get_concentration(channel_id)
                channel_vol = config.total_volume_ul * conc
                
                if channel_vol > 0:
                    pump_addr = self._get_diluter_pump(channel_id)
                    self._log(f"  {channel_id}: {channel_vol:.2f} uL (泵{pump_addr})")
                    
                    if self._pump_manager and pump_addr > 0:
                        try:
                            duration = channel_vol / 50.0
                            self._pump_manager.start_pump(pump_addr, "FWD", 100)
                            self._wait_with_stop_check(duration)
                            self._pump_manager.stop_pump(pump_addr)
                        except Exception as e:
                            self._log(f"通道 {channel_id} 配液失败: {e}", "error")
            
            return True
    
    def _get_diluter_pump(self, channel_id: str) -> int:
        """获取稀释通道对应的泵地址
        
        Args:
            channel_id: 通道ID (如 "D1", "D2")
            
        Returns:
            int: 泵地址
        """
        if self._context:
            from ..lib_context import LibContext
            addr = LibContext.get_diluter_pump(channel_id)
            if addr > 0:
                return addr
        
        # 默认映射: D1->4, D2->5, D3->6, ...
        try:
            num = int(channel_id[1:])
            return num + 3
        except:
            return 4  # 默认
    
    def _execute_transfer(self, step: ProgStep) -> bool:
        """执行移液步骤
        
        移液使用 work_type="Transfer" 的泵
        如果步骤未指定泵地址，从LibContext获取Transfer泵地址
        """
        config = step.transfer_config
        if not config:
            return False
        
        # 获取泵地址：优先使用步骤配置，否则从LibContext获取Transfer泵
        pump_address = config.pump_address
        if pump_address <= 0 and self._context:
            from ..lib_context import LibContext
            pump_address = LibContext.get_transfer_pump()
        if pump_address <= 0:
            pump_address = 2  # 默认Transfer泵地址
        
        self._log(f"移液: 泵{pump_address}, {config.volume_ul} uL, {config.direction}")
        
        if self._mock_mode:
            # Mock模式: 使用基于体积的快速模拟（50 uL/s）
            if config.duration_s:
                duration = config.duration_s
            else:
                duration = config.volume_ul / 50.0  # 假设 50 uL/s
            self._simulate_duration(duration)
            return True
        
        # 真实硬件移液
        if self._pump_manager:
            try:
                # 计算运行时间
                duration = config.duration_s or step.get_duration()
                
                # 启动泵
                self._pump_manager.start_pump(
                    pump_address,
                    config.direction,
                    config.speed_rpm
                )
                
                # 等待完成
                self._wait_with_stop_check(duration)
                
                # 停止泵
                self._pump_manager.stop_pump(pump_address)
                
                return True
            except Exception as e:
                self._log(f"移液失败: {e}", "error")
                return False
        
        return True
    
    def _execute_flush(self, step: ProgStep) -> bool:
        """执行冲洗步骤
        
        冲洗使用 work_type="Inlet" 的泵
        Flusher会协调Inlet/Transfer/Outlet三个泵的工作
        """
        config = step.flush_config
        if not config:
            return False
        
        self._log(f"冲洗: {config.cycles} 轮, 每阶段 {config.phase_duration_s} 秒")
        
        if self._mock_mode:
            duration = step.get_duration()
            self._simulate_duration(duration)
            return True
        
        # 真实硬件冲洗
        if self._flusher:
            try:
                self._flusher.set_cycles(config.cycles)
                self._flusher.start()
                
                while self._flusher.is_running and not self._stop_requested:
                    self._pause_event.wait()
                    time.sleep(0.1)
                
                return not self._stop_requested
            except Exception as e:
                self._log(f"冲洗失败: {e}", "error")
                return False
        
        return True
    
    def _execute_echem(self, step: ProgStep) -> bool:
        """执行电化学步骤"""
        config = step.ec_config
        if not config:
            return False
        
        self._log(f"电化学: {config.technique}, 扫描速率 {config.scan_rate} V/s")
        
        # 获取或创建CHI
        chi = self._get_or_create_chi()
        if not chi:
            self._log("CHI 仪器不可用", "error")
            return False
        
        try:
            # 连接
            if not chi.is_connected:
                chi.connect()
            
            # 设置参数
            from ..hardware.chi import ECParameters
            params = ECParameters.from_ec_config(config)
            chi.set_parameters(params)
            
            # 设置数据回调
            ec_data_points = []
            
            def on_data(point):
                ec_data_points.append(point)
                self._emit_event(EVENT_ECHEM_DATA, {"point": point.to_dict()})
            
            chi.on_data(on_data)
            
            # 运行
            chi.run()
            
            # 等待完成
            while chi.is_running and not self._stop_requested:
                self._pause_event.wait()
                if self._pause_requested:
                    chi.pause()
                    self._pause_event.wait()
                    chi.resume()
                time.sleep(0.1)
            
            if self._stop_requested:
                chi.stop()
                return False
            
            # 保存数据
            data_set = chi.get_data_set()
            if self._current_result:
                self._current_result.ec_data_sets.append(data_set)
            
            return True
            
        except Exception as e:
            self._log(f"电化学测量失败: {e}", "error")
            return False
    
    def _execute_blank(self, step: ProgStep) -> bool:
        """执行空白/等待步骤"""
        config = step.blank_config
        wait_time = config.wait_time if config else 5.0
        
        self._log(f"等待: {wait_time} 秒")
        
        self._simulate_duration(wait_time)
        return True
    
    def _execute_evacuate(self, step: ProgStep) -> bool:
        """执行抽空步骤
        
        排空使用 work_type="Outlet" 的泵
        如果步骤未指定泵地址，从LibContext获取Outlet泵地址
        """
        config = step.evacuate_config
        if not config:
            return False
        
        # 获取泵地址：优先使用步骤配置，否则从LibContext获取Outlet泵
        pump_address = config.pump_address
        if pump_address <= 0 and self._context:
            from ..lib_context import LibContext
            pump_address = LibContext.get_outlet_pump()
        if pump_address <= 0:
            pump_address = 3  # 默认Outlet泵地址
        
        self._log(f"抽空: 泵{pump_address}, {config.evacuate_time} 秒")
        
        if self._mock_mode:
            self._simulate_duration(config.evacuate_time)
            return True
        
        # 真实硬件抽空 - 使用Outlet泵
        if self._pump_manager:
            try:
                self._pump_manager.start_pump(
                    pump_address,
                    "FWD",
                    config.speed_rpm
                )
                
                self._wait_with_stop_check(config.evacuate_time)
                
                self._pump_manager.stop_pump(pump_address)
                return True
            except Exception as e:
                self._log(f"抽空失败: {e}", "error")
                return False
        
        return True
    
    # ========================
    # 辅助方法
    # ========================
    
    def _simulate_duration(self, duration: float) -> None:
        """模拟等待时间（支持暂停和停止）"""
        start = time.time()
        while time.time() - start < duration:
            if self._stop_requested:
                break
            self._pause_event.wait()
            time.sleep(0.1)
    
    def _wait_with_stop_check(self, duration: float) -> None:
        """等待指定时间，支持停止检查"""
        start = time.time()
        while time.time() - start < duration:
            if self._stop_requested:
                break
            self._pause_event.wait()
            time.sleep(0.05)
    
    def _get_or_create_chi(self) -> Optional["CHIInstrument"]:
        """获取或创建CHI实例"""
        if self._chi is None:
            from ..hardware.chi import CHIInstrument
            self._chi = CHIInstrument(mock_mode=self._mock_mode, logger=self._logger)
        return self._chi
    
    def _log(self, message: str, level: str = "info") -> None:
        """记录日志"""
        if self._logger:
            log_func = getattr(self._logger, level, self._logger.info)
            log_func(f"[Engine] {message}")
        else:
            print(f"[Engine] [{level.upper()}] {message}")
    
    # ========================
    # 结果获取
    # ========================
    
    def get_results(self) -> List[ExperimentResult]:
        """获取所有实验结果"""
        return self._results.copy()
    
    def get_last_result(self) -> Optional[ExperimentResult]:
        """获取最后一个实验结果"""
        if self._results:
            return self._results[-1]
        return self._current_result
