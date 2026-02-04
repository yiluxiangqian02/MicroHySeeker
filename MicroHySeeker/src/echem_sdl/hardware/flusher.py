"""
Flusher - 冲洗器驱动模块

管理三泵（Inlet/Outlet/Transfer）的冲洗流程。
支持Mock模式和真实硬件模式。

冲洗循环流程：
1. INLET (进水) → 将溶液抽入反应池
2. TRANSFER (移液) → 在两个池之间转移溶液
3. OUTLET (出水) → 将溶液从反应池排出
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, List, Dict, Any
import threading
import time


class FlusherPhase(Enum):
    """冲洗阶段"""
    IDLE = "idle"           # 空闲
    INLET = "inlet"         # 进水阶段
    TRANSFER = "transfer"   # 移液阶段
    OUTLET = "outlet"       # 出水阶段
    COMPLETED = "completed" # 完成


class FlusherState(Enum):
    """冲洗器整体状态"""
    IDLE = "idle"
    RUNNING = "running"     # 冲洗中
    PAUSED = "paused"       # 暂停
    ERROR = "error"


# 阶段执行顺序
PHASE_SEQUENCE = [
    FlusherPhase.INLET,
    FlusherPhase.TRANSFER,
    FlusherPhase.OUTLET,
]


@dataclass
class FlusherPumpConfig:
    """单个冲洗泵配置"""
    address: int              # RS485 地址 (1-12)
    name: str                 # 泵名称
    rpm: int = 200            # 默认转速
    direction: str = "FWD"    # 默认方向 FWD/REV
    duration_s: float = 10.0  # 默认运行时间（秒）


@dataclass
class FlusherConfig:
    """冲洗器完整配置"""
    inlet: FlusherPumpConfig      # 进水泵
    outlet: FlusherPumpConfig     # 出水泵
    transfer: FlusherPumpConfig   # 移液泵
    default_cycles: int = 3       # 默认冲洗循环数


class FlusherError(Exception):
    """Flusher 错误基类"""
    pass


class PumpCommunicationError(FlusherError):
    """泵通信错误"""
    pass


class InvalidStateError(FlusherError):
    """状态无效"""
    pass


class Flusher:
    """冲洗器控制器
    
    管理三泵（Inlet/Outlet/Transfer）的冲洗流程。
    
    架构说明：
    - 通过 PumpManager 控制泵
    - 支持Mock模式模拟冲洗过程
    - 使用定时器控制阶段切换
    
    Attributes:
        config: 冲洗器配置
        state: 当前状态
        phase: 当前阶段
        current_cycle: 当前循环数 (从1开始)
        total_cycles: 总循环数
        
    Example:
        >>> flusher = Flusher(config, pump_manager, logger)
        >>> flusher.set_cycles(3)
        >>> flusher.start()
        >>> while flusher.is_running:
        ...     print(f"Cycle {flusher.current_cycle}, Phase: {flusher.phase}")
        ...     time.sleep(1)
    """
    
    def __init__(
        self,
        config: FlusherConfig,
        pump_manager: "PumpManager",
        logger: Optional["LoggerService"] = None,
        mock_mode: bool = False
    ) -> None:
        """初始化 Flusher
        
        Args:
            config: 冲洗器配置
            pump_manager: PumpManager 实例
            logger: 日志服务
            mock_mode: Mock模式
        """
        self.config = config
        self._pump_manager = pump_manager
        self._logger = logger
        self._mock_mode = mock_mode
        
        # 状态
        self._state = FlusherState.IDLE
        self._phase = FlusherPhase.IDLE
        self._current_cycle = 0
        self._total_cycles = config.default_cycles
        
        # 线程安全
        self._lock = threading.RLock()
        self._phase_timer: Optional[threading.Timer] = None
        self._phase_start_time = 0.0
        
        # 回调
        self._phase_callbacks: List[Callable[[FlusherPhase], None]] = []
        self._cycle_callbacks: List[Callable[[int], None]] = []
        self._complete_callbacks: List[Callable[[], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []
        
        if self._logger:
            self._logger.info(
                f"Flusher初始化: Inlet={config.inlet.address}, "
                f"Transfer={config.transfer.address}, Outlet={config.outlet.address}",
                module="Flusher"
            )
    
    # ========================
    # 属性
    # ========================
    
    @property
    def state(self) -> FlusherState:
        """获取整体状态"""
        return self._state
    
    @property
    def phase(self) -> FlusherPhase:
        """获取当前阶段"""
        return self._phase
    
    @property
    def current_cycle(self) -> int:
        """获取当前循环数"""
        return self._current_cycle
    
    @property
    def total_cycles(self) -> int:
        """获取总循环数"""
        return self._total_cycles
    
    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._state == FlusherState.RUNNING
    
    @property
    def progress(self) -> float:
        """计算总进度 (0-1)"""
        if self._total_cycles == 0:
            return 0.0
        
        phases_per_cycle = len(PHASE_SEQUENCE)
        total_phases = self._total_cycles * phases_per_cycle
        
        completed_cycles = self._current_cycle - 1
        if completed_cycles < 0:
            completed_cycles = 0
        completed_phases = completed_cycles * phases_per_cycle
        
        if self._phase in PHASE_SEQUENCE:
            current_phase_idx = PHASE_SEQUENCE.index(self._phase)
            completed_phases += current_phase_idx + self.phase_progress
        elif self._phase == FlusherPhase.COMPLETED:
            return 1.0
        
        return min(completed_phases / total_phases, 1.0) if total_phases > 0 else 0.0
    
    @property
    def phase_progress(self) -> float:
        """计算阶段进度 (0-1)"""
        if self._phase_start_time == 0:
            return 0.0
        
        pump_config = self._get_pump_config(self._phase)
        if pump_config is None:
            return 0.0
        
        elapsed = time.time() - self._phase_start_time
        return min(1.0, elapsed / pump_config.duration_s)
    
    # ========================
    # 公开方法
    # ========================
    
    def set_cycles(self, cycles: int) -> None:
        """设置冲洗循环数
        
        Args:
            cycles: 循环次数 (1-99)
        """
        if cycles < 1:
            cycles = 1
        elif cycles > 99:
            cycles = 99
        self._total_cycles = cycles
        
        if self._logger:
            self._logger.info(f"设置冲洗循环数: {cycles}", module="Flusher")
    
    def start(self) -> bool:
        """开始冲洗
        
        Returns:
            bool: 是否成功启动
            
        Note:
            此方法非阻塞，冲洗在后台进行
        """
        with self._lock:
            if self._state == FlusherState.RUNNING:
                if self._logger:
                    self._logger.warning("已在运行中", module="Flusher")
                return False
            
            self._state = FlusherState.RUNNING
            self._current_cycle = 1
            
            if self._logger:
                self._logger.info(
                    f"开始冲洗: {self._total_cycles}个循环",
                    module="Flusher"
                )
            
            # 启动第一阶段
            self._execute_phase(PHASE_SEQUENCE[0])
            return True
    
    def stop(self) -> bool:
        """停止冲洗
        
        Returns:
            bool: 是否成功停止
            
        Note:
            会立即停止所有泵
        """
        with self._lock:
            if self._phase_timer:
                self._phase_timer.cancel()
                self._phase_timer = None
            
            # 停止所有冲洗泵
            self._stop_all_pumps()
            
            self._state = FlusherState.IDLE
            self._phase = FlusherPhase.IDLE
            
            if self._logger:
                self._logger.info("冲洗已停止", module="Flusher")
            
            return True
    
    def pause(self) -> bool:
        """暂停冲洗"""
        with self._lock:
            if self._state != FlusherState.RUNNING:
                return False
            
            if self._phase_timer:
                self._phase_timer.cancel()
                self._phase_timer = None
            
            # 停止当前泵
            pump_config = self._get_pump_config(self._phase)
            if pump_config:
                self._stop_pump(pump_config.address)
            
            self._state = FlusherState.PAUSED
            
            if self._logger:
                self._logger.info("冲洗已暂停", module="Flusher")
            
            return True
    
    def resume(self) -> bool:
        """恢复冲洗"""
        with self._lock:
            if self._state != FlusherState.PAUSED:
                return False
            
            self._state = FlusherState.RUNNING
            
            # 重新启动当前阶段
            if self._phase in PHASE_SEQUENCE:
                self._execute_phase(self._phase)
            
            if self._logger:
                self._logger.info("冲洗已恢复", module="Flusher")
            
            return True
    
    def evacuate(
        self,
        duration_s: Optional[float] = None
    ) -> bool:
        """执行排空操作（仅 Outlet 泵）
        
        Args:
            duration_s: 排空时间，默认使用配置值
            
        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if self._state == FlusherState.RUNNING:
                if self._logger:
                    self._logger.warning("正在运行中，无法执行排空", module="Flusher")
                return False
            
            duration = duration_s if duration_s else self.config.outlet.duration_s
            
            if self._logger:
                self._logger.info(f"开始排空: {duration}秒", module="Flusher")
            
            self._state = FlusherState.RUNNING
            self._phase = FlusherPhase.OUTLET
            self._phase_start_time = time.time()
            
            # 启动 outlet 泵
            success = self._start_pump(
                self.config.outlet.address,
                self.config.outlet.rpm,
                self.config.outlet.direction
            )
            
            if not success:
                self._state = FlusherState.ERROR
                return False
            
            # 设置定时器
            self._phase_timer = threading.Timer(
                duration,
                self._on_evacuate_complete
            )
            self._phase_timer.start()
            
            return True
    
    def transfer(
        self,
        duration_s: Optional[float] = None,
        forward: bool = True
    ) -> bool:
        """执行单次移液
        
        Args:
            duration_s: 持续时间
            forward: 方向
            
        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if self._state == FlusherState.RUNNING:
                if self._logger:
                    self._logger.warning("正在运行中，无法执行移液", module="Flusher")
                return False
            
            duration = duration_s if duration_s else self.config.transfer.duration_s
            direction = "FWD" if forward else "REV"
            
            if self._logger:
                self._logger.info(f"开始移液: {duration}秒, {direction}", module="Flusher")
            
            self._state = FlusherState.RUNNING
            self._phase = FlusherPhase.TRANSFER
            self._phase_start_time = time.time()
            
            # 启动 transfer 泵
            success = self._start_pump(
                self.config.transfer.address,
                self.config.transfer.rpm,
                direction
            )
            
            if not success:
                self._state = FlusherState.ERROR
                return False
            
            # 设置定时器
            self._phase_timer = threading.Timer(
                duration,
                self._on_transfer_complete
            )
            self._phase_timer.start()
            
            return True
    
    def reset(self) -> None:
        """重置状态"""
        with self._lock:
            if self._phase_timer:
                self._phase_timer.cancel()
                self._phase_timer = None
            
            self._stop_all_pumps()
            
            self._state = FlusherState.IDLE
            self._phase = FlusherPhase.IDLE
            self._current_cycle = 0
            self._phase_start_time = 0.0
            
            if self._logger:
                self._logger.info("Flusher已重置", module="Flusher")
    
    # ========================
    # 回调注册
    # ========================
    
    def on_phase_change(self, callback: Callable[[FlusherPhase], None]) -> None:
        """注册阶段变化回调"""
        self._phase_callbacks.append(callback)
    
    def on_cycle_complete(self, callback: Callable[[int], None]) -> None:
        """注册循环完成回调"""
        self._cycle_callbacks.append(callback)
    
    def on_complete(self, callback: Callable[[], None]) -> None:
        """注册全部完成回调"""
        self._complete_callbacks.append(callback)
    
    def on_error(self, callback: Callable[[Exception], None]) -> None:
        """注册错误回调"""
        self._error_callbacks.append(callback)
    
    # ========================
    # 内部方法
    # ========================
    
    def _get_pump_config(self, phase: FlusherPhase) -> Optional[FlusherPumpConfig]:
        """根据阶段获取泵配置"""
        if phase == FlusherPhase.INLET:
            return self.config.inlet
        elif phase == FlusherPhase.TRANSFER:
            return self.config.transfer
        elif phase == FlusherPhase.OUTLET:
            return self.config.outlet
        return None
    
    def _execute_phase(self, phase: FlusherPhase) -> None:
        """执行单个阶段"""
        pump_config = self._get_pump_config(phase)
        if pump_config is None:
            return
        
        self._phase = phase
        self._phase_start_time = time.time()
        
        if self._logger:
            self._logger.info(
                f"执行阶段: {phase.value}, 泵{pump_config.address}, "
                f"{pump_config.rpm}RPM, {pump_config.duration_s}秒",
                module="Flusher"
            )
        
        # 触发阶段变化回调
        for cb in self._phase_callbacks:
            try:
                cb(phase)
            except Exception as e:
                if self._logger:
                    self._logger.error(f"阶段回调异常: {e}", module="Flusher")
        
        # 启动泵
        success = self._start_pump(
            pump_config.address,
            pump_config.rpm,
            pump_config.direction
        )
        
        if not success:
            self._handle_error(PumpCommunicationError(f"无法启动泵 {pump_config.address}"))
            return
        
        # 设置阶段完成定时器
        self._phase_timer = threading.Timer(
            pump_config.duration_s,
            self._on_phase_complete
        )
        self._phase_timer.start()
    
    def _on_phase_complete(self) -> None:
        """阶段完成回调"""
        with self._lock:
            # 停止当前泵
            pump_config = self._get_pump_config(self._phase)
            if pump_config:
                self._stop_pump(pump_config.address)
            
            if self._logger:
                self._logger.info(f"阶段完成: {self._phase.value}", module="Flusher")
            
            # 切换到下一阶段
            self._advance_phase()
    
    def _advance_phase(self) -> None:
        """推进到下一阶段"""
        if self._phase not in PHASE_SEQUENCE:
            return
        
        current_idx = PHASE_SEQUENCE.index(self._phase)
        
        if current_idx < len(PHASE_SEQUENCE) - 1:
            # 切换到下一阶段
            next_phase = PHASE_SEQUENCE[current_idx + 1]
            self._execute_phase(next_phase)
        else:
            # 当前循环完成
            if self._logger:
                self._logger.info(f"循环 {self._current_cycle} 完成", module="Flusher")
            
            # 触发循环完成回调
            for cb in self._cycle_callbacks:
                try:
                    cb(self._current_cycle)
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"循环回调异常: {e}", module="Flusher")
            
            if self._current_cycle < self._total_cycles:
                self._current_cycle += 1
                self._execute_phase(PHASE_SEQUENCE[0])
            else:
                # 全部完成
                self._phase = FlusherPhase.COMPLETED
                self._state = FlusherState.IDLE
                
                if self._logger:
                    self._logger.info(
                        f"冲洗全部完成: 共{self._total_cycles}个循环",
                        module="Flusher"
                    )
                
                # 触发完成回调
                for cb in self._complete_callbacks:
                    try:
                        cb()
                    except Exception as e:
                        if self._logger:
                            self._logger.error(f"完成回调异常: {e}", module="Flusher")
    
    def _on_evacuate_complete(self) -> None:
        """排空完成回调"""
        with self._lock:
            self._stop_pump(self.config.outlet.address)
            self._state = FlusherState.IDLE
            self._phase = FlusherPhase.COMPLETED
            
            if self._logger:
                self._logger.info("排空完成", module="Flusher")
            
            for cb in self._complete_callbacks:
                try:
                    cb()
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"完成回调异常: {e}", module="Flusher")
    
    def _on_transfer_complete(self) -> None:
        """移液完成回调"""
        with self._lock:
            self._stop_pump(self.config.transfer.address)
            self._state = FlusherState.IDLE
            self._phase = FlusherPhase.COMPLETED
            
            if self._logger:
                self._logger.info("移液完成", module="Flusher")
            
            for cb in self._complete_callbacks:
                try:
                    cb()
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"完成回调异常: {e}", module="Flusher")
    
    def _start_pump(self, address: int, rpm: int, direction: str) -> bool:
        """启动泵"""
        if self._mock_mode:
            if self._logger:
                self._logger.debug(
                    f"[MOCK] 启动泵 {address}: {rpm}RPM {direction}",
                    module="Flusher"
                )
            return True
        
        try:
            # 已知响应不稳定的泵
            RESPONSE_UNSTABLE_PUMPS = [1, 11]
            use_fire_and_forget = address in RESPONSE_UNSTABLE_PUMPS
            
            return self._pump_manager.start_pump(
                address,
                direction,
                rpm,
                fire_and_forget=use_fire_and_forget
            )
        except Exception as e:
            if self._logger:
                self._logger.error(f"启动泵 {address} 异常: {e}", module="Flusher")
            return False
    
    def _stop_pump(self, address: int) -> bool:
        """停止泵"""
        if self._mock_mode:
            if self._logger:
                self._logger.debug(f"[MOCK] 停止泵 {address}", module="Flusher")
            return True
        
        try:
            RESPONSE_UNSTABLE_PUMPS = [1, 11]
            use_fire_and_forget = address in RESPONSE_UNSTABLE_PUMPS
            
            return self._pump_manager.stop_pump(
                address,
                fire_and_forget=use_fire_and_forget
            )
        except Exception as e:
            if self._logger:
                self._logger.error(f"停止泵 {address} 异常: {e}", module="Flusher")
            return False
    
    def _stop_all_pumps(self) -> None:
        """停止所有冲洗泵"""
        for pump in [self.config.inlet, self.config.outlet, self.config.transfer]:
            try:
                self._stop_pump(pump.address)
            except Exception:
                pass
    
    def _handle_error(self, error: Exception) -> None:
        """处理错误"""
        self._state = FlusherState.ERROR
        
        if self._logger:
            self._logger.error(f"Flusher错误: {error}", module="Flusher")
        
        # 紧急停止所有泵
        self._stop_all_pumps()
        
        # 触发错误回调
        for cb in self._error_callbacks:
            try:
                cb(error)
            except Exception:
                pass
    
    # ========================
    # 状态查询
    # ========================
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态摘要"""
        return {
            "state": self._state.value,
            "phase": self._phase.value,
            "current_cycle": self._current_cycle,
            "total_cycles": self._total_cycles,
            "progress": self.progress,
            "phase_progress": self.phase_progress,
            "is_running": self.is_running,
        }
