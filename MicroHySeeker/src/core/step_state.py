"""
步骤状态模块 - 实现位标志状态机

参考 C# 源项目的 StepState 实现：
- 使用位标志允许状态组合（如 BUSY | NEXT_SOL）
- 支持多批次注入的状态跟踪
- 与 ExperimentEngine 的 tick 循环配合
"""
from enum import IntFlag, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class StepState(IntFlag):
    """步骤状态位标志
    
    位标志允许状态组合：
    - IDLE = 0: 步骤未开始
    - BUSY = 1: 步骤执行中
    - NEXT_SOL = 2: 需要继续下一批次注入
    - END = 4: 步骤完成
    - FAILED = 8: 步骤失败
    - PAUSED = 16: 步骤暂停
    
    组合示例：
    - BUSY | NEXT_SOL (3): 执行中且需要继续下一批注入
    - END | FAILED (12): 完成但失败（异常结束）
    """
    IDLE = 0
    BUSY = 1
    NEXT_SOL = 2  # 多批次注入，需要下一批
    END = 4
    FAILED = 8
    PAUSED = 16
    
    def is_running(self) -> bool:
        """是否运行中"""
        return bool(self & StepState.BUSY)
    
    def is_completed(self) -> bool:
        """是否完成（成功或失败）"""
        return bool(self & (StepState.END | StepState.FAILED))
    
    def needs_next_batch(self) -> bool:
        """是否需要继续下一批次注入"""
        return bool(self & StepState.NEXT_SOL)
    
    def is_success(self) -> bool:
        """是否成功完成"""
        return bool(self & StepState.END) and not bool(self & StepState.FAILED)


class EngineState(IntFlag):
    """引擎状态"""
    IDLE = 0        # 空闲
    LOADING = 1     # 加载程序中
    READY = 2       # 已就绪
    RUNNING = 4     # 运行中
    PAUSED = 8      # 已暂停
    STOPPING = 16   # 停止中
    COMPLETED = 32  # 已完成
    ERROR = 64      # 错误
    
    def can_start(self) -> bool:
        """是否可以启动"""
        return self in [EngineState.IDLE, EngineState.READY, EngineState.COMPLETED]
    
    def is_active(self) -> bool:
        """是否处于活动状态"""
        return bool(self & (EngineState.RUNNING | EngineState.PAUSED))


@dataclass
class StepTiming:
    """步骤时间追踪"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_duration_s: float = 0.0
    actual_duration_s: float = 0.0
    
    @property
    def elapsed_seconds(self) -> float:
        """已运行秒数"""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def remaining_seconds(self) -> float:
        """预计剩余秒数"""
        if self.estimated_duration_s <= 0:
            return 0.0
        remaining = self.estimated_duration_s - self.elapsed_seconds
        return max(0.0, remaining)
    
    @property
    def progress(self) -> float:
        """进度 (0-1)"""
        if self.estimated_duration_s <= 0:
            return 0.0
        return min(1.0, self.elapsed_seconds / self.estimated_duration_s)
    
    def start(self):
        """开始计时"""
        self.start_time = datetime.now()
        self.end_time = None
    
    def stop(self):
        """停止计时"""
        self.end_time = datetime.now()
        self.actual_duration_s = self.elapsed_seconds


@dataclass
class BatchInfo:
    """批次信息（用于多批次注入）"""
    batch_index: int = 0  # 当前批次索引
    total_batches: int = 1  # 总批次数
    batch_interval_s: float = 1.0  # 批次间隔（秒）
    components_per_batch: Dict[int, List[str]] = field(default_factory=dict)  # {批次号: [溶液名列表]}
    
    @property
    def current_batch(self) -> int:
        """当前批次（1-based）"""
        return self.batch_index + 1
    
    @property
    def is_last_batch(self) -> bool:
        """是否最后一批"""
        return self.batch_index >= self.total_batches - 1
    
    def advance(self) -> bool:
        """推进到下一批次，返回是否成功"""
        if self.is_last_batch:
            return False
        self.batch_index += 1
        return True
    
    def reset(self):
        """重置批次"""
        self.batch_index = 0


@dataclass 
class StepExecutionContext:
    """步骤执行上下文 - 跟踪执行状态和进度"""
    state: StepState = StepState.IDLE
    timing: StepTiming = field(default_factory=StepTiming)
    batch_info: Optional[BatchInfo] = None
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    # 配液专用
    infusing_channels: List[str] = field(default_factory=list)  # 正在注入的通道
    completed_channels: List[str] = field(default_factory=list)  # 已完成的通道
    
    def start(self, estimated_duration: float = 0.0):
        """开始执行"""
        self.state = StepState.BUSY
        self.timing.estimated_duration_s = estimated_duration
        self.timing.start()
        self.error_message = ""
    
    def complete(self, success: bool = True):
        """完成执行"""
        self.timing.stop()
        if success:
            self.state = StepState.END
        else:
            self.state = StepState.END | StepState.FAILED
    
    def fail(self, error_message: str):
        """失败"""
        self.timing.stop()
        self.state = StepState.FAILED
        self.error_message = error_message
    
    def pause(self):
        """暂停"""
        self.state = self.state | StepState.PAUSED
    
    def resume(self):
        """恢复"""
        self.state = self.state & ~StepState.PAUSED
    
    def request_next_batch(self):
        """请求下一批次注入"""
        self.state = StepState.BUSY | StepState.NEXT_SOL
    
    def reset(self):
        """重置"""
        self.state = StepState.IDLE
        self.timing = StepTiming()
        if self.batch_info:
            self.batch_info.reset()
        self.error_message = ""
        self.retry_count = 0
        self.infusing_channels.clear()
        self.completed_channels.clear()


def estimate_step_duration(step_type: str, params: Dict[str, Any]) -> float:
    """估算步骤时长（秒）
    
    Args:
        step_type: 步骤类型 (prep_sol, transfer, flush, echem, blank, evacuate)
        params: 步骤参数
        
    Returns:
        预估时长（秒）
    """
    if step_type == "prep_sol":
        # 配液：每个通道约 10 秒，多批次需考虑间隔
        channel_count = len(params.get("injection_order", []))
        batch_count = params.get("batch_count", 1)
        batch_interval = params.get("batch_interval_s", 1.0)
        
        base_time = channel_count * 10.0
        interval_time = (batch_count - 1) * batch_interval
        return base_time + interval_time
    
    elif step_type == "transfer":
        # 移液：使用配置的持续时间
        return params.get("duration_s", params.get("transfer_duration", 10.0))
    
    elif step_type == "flush":
        # 冲洗：单次时长 × 循环次数
        cycle_duration = params.get("cycle_duration_s", params.get("flush_cycle_duration_s", 30.0))
        cycles = params.get("cycles", params.get("flush_cycles", 1))
        return cycle_duration * cycles
    
    elif step_type == "echem":
        # 电化学：基于技术类型和参数计算
        technique = params.get("technique", "CV")
        quiet_time = params.get("quiet_time_s", 2.0)
        
        if technique in ["CV", "LSV"]:
            e_high = params.get("eh", params.get("e_high", 0.8))
            e_low = params.get("el", params.get("e_low", -0.2))
            scan_rate = params.get("scan_rate", 0.1)
            segments = params.get("seg_num", params.get("segments", 2))
            
            e_range = abs(e_high - e_low)
            return quiet_time + (e_range * segments / scan_rate)
        
        elif technique in ["i-t", "IT", "CA"]:
            return quiet_time + params.get("run_time_s", params.get("run_time", 60.0))
        
        elif technique == "OCPT":
            return params.get("run_time_s", params.get("run_time", 60.0))
        
        return 60.0  # 默认
    
    elif step_type == "blank":
        return params.get("duration_s", params.get("wait_time", 5.0))
    
    elif step_type == "evacuate":
        # 排空：类似冲洗
        duration = params.get("duration_s", params.get("transfer_duration", 30.0))
        cycles = params.get("cycles", params.get("flush_cycles", 1))
        return duration * cycles
    
    return 0.0


def validate_step_params(step_type: str, params: Dict[str, Any]) -> List[str]:
    """验证步骤参数
    
    Args:
        step_type: 步骤类型
        params: 步骤参数
        
    Returns:
        错误消息列表（空表示验证通过）
    """
    errors = []
    
    if step_type == "prep_sol":
        if not params.get("injection_order") and not params.get("selected_solutions"):
            errors.append("配液步骤缺少溶液配置")
        if params.get("total_volume_ul", 0) <= 0:
            errors.append("总体积必须大于 0")
    
    elif step_type == "transfer":
        if not params.get("pump_address"):
            errors.append("移液步骤缺少泵地址")
        duration = params.get("duration_s", params.get("transfer_duration", 0))
        if duration <= 0:
            errors.append("移液持续时间必须大于 0")
    
    elif step_type == "flush":
        if not params.get("pump_address"):
            errors.append("冲洗步骤缺少泵地址")
        cycles = params.get("cycles", params.get("flush_cycles", 0))
        if cycles <= 0:
            errors.append("冲洗循环次数必须大于 0")
    
    elif step_type == "echem":
        technique = params.get("technique", "")
        if not technique:
            errors.append("电化学步骤缺少技术类型")
        
        if technique in ["CV", "LSV"]:
            e_high = params.get("eh", params.get("e_high", 0))
            e_low = params.get("el", params.get("e_low", 0))
            if e_high <= e_low:
                errors.append("高电位必须大于低电位")
            
            scan_rate = params.get("scan_rate", 0)
            if scan_rate <= 0:
                errors.append("扫描速率必须大于 0")
    
    elif step_type == "evacuate":
        if not params.get("pump_address"):
            errors.append("排空步骤缺少泵地址")
    
    return errors
