"""
多批次注入管理器

参考 C# 源项目的 InjectOrder 机制：
- 溶液按照注入顺序分批
- 每批次等待所有通道完成后再进行下一批
- 支持暂停、恢复和取消操作
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable, Any
from enum import IntFlag
import logging
from datetime import datetime

from .step_state import StepState, BatchInfo

logger = logging.getLogger(__name__)


@dataclass
class InjectionChannel:
    """注入通道信息"""
    name: str  # 溶液名称
    channel_id: int  # 通道号 (1-6)
    volume_ul: float  # 注入体积 (uL)
    inject_order: int  # 注入顺序号 (用于分批)
    
    # 状态跟踪
    is_infusing: bool = False  # 正在注入
    has_infused: bool = False  # 已完成注入
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: str = ""
    
    def start_infusion(self):
        """开始注入"""
        self.is_infusing = True
        self.has_infused = False
        self.start_time = datetime.now()
        self.error_message = ""
    
    def complete_infusion(self):
        """完成注入"""
        self.is_infusing = False
        self.has_infused = True
        self.end_time = datetime.now()
    
    def fail_infusion(self, error: str):
        """注入失败"""
        self.is_infusing = False
        self.has_infused = False
        self.end_time = datetime.now()
        self.error_message = error
    
    def reset(self):
        """重置状态"""
        self.is_infusing = False
        self.has_infused = False
        self.start_time = None
        self.end_time = None
        self.error_message = ""


@dataclass
class InjectionBatch:
    """注入批次"""
    batch_index: int  # 批次索引 (0-based)
    channels: List[InjectionChannel] = field(default_factory=list)
    
    @property
    def is_infusing(self) -> bool:
        """批次是否正在注入"""
        return any(ch.is_infusing for ch in self.channels)
    
    @property
    def has_infused(self) -> bool:
        """批次是否已完成"""
        return all(ch.has_infused for ch in self.channels)
    
    @property
    def has_errors(self) -> bool:
        """批次是否有错误"""
        return any(ch.error_message for ch in self.channels)
    
    @property
    def infusing_channels(self) -> List[str]:
        """正在注入的通道名称列表"""
        return [ch.name for ch in self.channels if ch.is_infusing]
    
    @property
    def completed_channels(self) -> List[str]:
        """已完成的通道名称列表"""
        return [ch.name for ch in self.channels if ch.has_infused]
    
    @property
    def pending_channels(self) -> List[str]:
        """待注入的通道名称列表"""
        return [ch.name for ch in self.channels 
                if not ch.is_infusing and not ch.has_infused]
    
    def start(self):
        """启动批次注入"""
        for ch in self.channels:
            ch.start_infusion()
    
    def reset(self):
        """重置批次"""
        for ch in self.channels:
            ch.reset()


class BatchInjectionManager:
    """批次注入管理器
    
    负责：
    1. 根据 inject_order 将溶液分批
    2. 跟踪每批次的执行状态
    3. 提供状态查询接口供 ExperimentEngine 使用
    """
    
    def __init__(self):
        self._batches: List[InjectionBatch] = []
        self._current_batch_index: int = 0
        self._is_active: bool = False
        self._is_paused: bool = False
        
        # 回调函数
        self._on_batch_start: Optional[Callable[[int, List[str]], None]] = None
        self._on_batch_complete: Optional[Callable[[int], None]] = None
        self._on_channel_complete: Optional[Callable[[str, int], None]] = None
        self._on_all_complete: Optional[Callable[[], None]] = None
    
    @property
    def total_batches(self) -> int:
        """总批次数"""
        return len(self._batches)
    
    @property
    def current_batch_index(self) -> int:
        """当前批次索引 (0-based)"""
        return self._current_batch_index
    
    @property
    def current_batch(self) -> Optional[InjectionBatch]:
        """当前批次"""
        if 0 <= self._current_batch_index < len(self._batches):
            return self._batches[self._current_batch_index]
        return None
    
    @property
    def is_active(self) -> bool:
        """是否正在运行"""
        return self._is_active
    
    @property
    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._is_paused
    
    @property
    def is_all_complete(self) -> bool:
        """是否全部完成"""
        return all(batch.has_infused for batch in self._batches)
    
    def configure(
        self,
        channels: List[Dict[str, Any]],
        batch_by_inject_order: bool = True
    ) -> int:
        """配置注入批次
        
        Args:
            channels: 通道配置列表
                [{"name": "HCl", "channel_id": 1, "volume_ul": 1000, "inject_order": 1}, ...]
            batch_by_inject_order: 是否按 inject_order 分批
            
        Returns:
            总批次数
        """
        self._batches.clear()
        self._current_batch_index = 0
        
        # 创建通道对象
        injection_channels = []
        for ch in channels:
            if ch.get("volume_ul", 0) > 0:  # 只添加有体积的通道
                injection_channels.append(InjectionChannel(
                    name=ch["name"],
                    channel_id=ch.get("channel_id", 0),
                    volume_ul=ch["volume_ul"],
                    inject_order=ch.get("inject_order", 1)
                ))
        
        if not injection_channels:
            return 0
        
        if batch_by_inject_order:
            # 按 inject_order 分批
            order_groups: Dict[int, List[InjectionChannel]] = {}
            for ch in injection_channels:
                order = ch.inject_order
                if order not in order_groups:
                    order_groups[order] = []
                order_groups[order].append(ch)
            
            # 按顺序号排序创建批次
            for idx, order in enumerate(sorted(order_groups.keys())):
                batch = InjectionBatch(
                    batch_index=idx,
                    channels=order_groups[order]
                )
                self._batches.append(batch)
        else:
            # 所有通道作为单一批次
            self._batches.append(InjectionBatch(
                batch_index=0,
                channels=injection_channels
            ))
        
        logger.info(f"配置了 {len(self._batches)} 个注入批次，共 {len(injection_channels)} 个通道")
        return len(self._batches)
    
    def start(self) -> bool:
        """启动注入流程
        
        Returns:
            是否成功启动
        """
        if not self._batches:
            logger.warning("没有配置注入批次")
            return False
        
        self._is_active = True
        self._is_paused = False
        self._current_batch_index = 0
        
        # 启动第一批
        return self._start_current_batch()
    
    def _start_current_batch(self) -> bool:
        """启动当前批次"""
        batch = self.current_batch
        if not batch:
            return False
        
        batch.start()
        channel_names = [ch.name for ch in batch.channels]
        
        logger.info(f"启动批次 {self._current_batch_index + 1}/{len(self._batches)}: {channel_names}")
        
        if self._on_batch_start:
            self._on_batch_start(self._current_batch_index, channel_names)
        
        return True
    
    def get_state(self) -> StepState:
        """获取当前状态
        
        返回 C# 风格的位标志状态：
        - IDLE: 未开始
        - BUSY: 正在注入
        - BUSY | NEXT_SOL: 当前批次完成，需要下一批
        - END: 全部完成
        """
        if not self._is_active:
            return StepState.IDLE
        
        if self._is_paused:
            return StepState.BUSY | StepState.PAUSED
        
        batch = self.current_batch
        if not batch:
            return StepState.END
        
        # 检查当前批次状态
        if batch.is_infusing:
            # 仍在注入
            return StepState.BUSY
        
        if batch.has_infused:
            # 当前批次完成
            if self._current_batch_index < len(self._batches) - 1:
                # 还有下一批
                return StepState.BUSY | StepState.NEXT_SOL
            else:
                # 全部完成
                return StepState.END
        
        # 批次尚未开始
        return StepState.BUSY
    
    def update(self) -> StepState:
        """更新状态（由 tick 调用）
        
        检查当前批次是否完成，自动推进到下一批次
        
        Returns:
            当前状态
        """
        state = self.get_state()
        
        if state.needs_next_batch():
            # 当前批次完成，推进到下一批
            self._current_batch_index += 1
            
            if self._on_batch_complete:
                self._on_batch_complete(self._current_batch_index - 1)
            
            if self._current_batch_index < len(self._batches):
                self._start_current_batch()
                return StepState.BUSY
            else:
                # 全部完成
                self._is_active = False
                if self._on_all_complete:
                    self._on_all_complete()
                return StepState.END
        
        return state
    
    def mark_channel_complete(self, channel_name: str) -> bool:
        """标记通道完成
        
        Args:
            channel_name: 通道名称
            
        Returns:
            是否成功
        """
        batch = self.current_batch
        if not batch:
            return False
        
        for ch in batch.channels:
            if ch.name == channel_name and ch.is_infusing:
                ch.complete_infusion()
                logger.info(f"通道 {channel_name} 注入完成")
                
                if self._on_channel_complete:
                    self._on_channel_complete(channel_name, self._current_batch_index)
                
                return True
        
        return False
    
    def mark_channel_failed(self, channel_name: str, error: str) -> bool:
        """标记通道失败"""
        batch = self.current_batch
        if not batch:
            return False
        
        for ch in batch.channels:
            if ch.name == channel_name:
                ch.fail_infusion(error)
                logger.error(f"通道 {channel_name} 注入失败: {error}")
                return True
        
        return False
    
    def pause(self):
        """暂停注入"""
        self._is_paused = True
    
    def resume(self):
        """恢复注入"""
        self._is_paused = False
    
    def stop(self):
        """停止注入"""
        self._is_active = False
        self._is_paused = False
        for batch in self._batches:
            batch.reset()
        self._current_batch_index = 0
    
    def reset(self):
        """重置管理器"""
        self._batches.clear()
        self._current_batch_index = 0
        self._is_active = False
        self._is_paused = False
    
    # 回调设置方法
    def on_batch_start(self, callback: Callable[[int, List[str]], None]):
        """设置批次开始回调"""
        self._on_batch_start = callback
    
    def on_batch_complete(self, callback: Callable[[int], None]):
        """设置批次完成回调"""
        self._on_batch_complete = callback
    
    def on_channel_complete(self, callback: Callable[[str, int], None]):
        """设置通道完成回调"""
        self._on_channel_complete = callback
    
    def on_all_complete(self, callback: Callable[[], None]):
        """设置全部完成回调"""
        self._on_all_complete = callback
    
    # 状态查询方法
    def get_progress_info(self) -> Dict[str, Any]:
        """获取进度信息"""
        total_channels = sum(len(b.channels) for b in self._batches)
        completed_channels = sum(
            len([ch for ch in b.channels if ch.has_infused])
            for b in self._batches
        )
        
        current_infusing = []
        current_completed = []
        current_pending = []
        
        if self.current_batch:
            current_infusing = self.current_batch.infusing_channels
            current_completed = self.current_batch.completed_channels
            current_pending = self.current_batch.pending_channels
        
        return {
            "total_batches": len(self._batches),
            "current_batch": self._current_batch_index + 1,
            "total_channels": total_channels,
            "completed_channels": completed_channels,
            "progress": completed_channels / total_channels if total_channels > 0 else 0.0,
            "is_active": self._is_active,
            "is_paused": self._is_paused,
            "current_infusing": current_infusing,
            "current_completed": current_completed,
            "current_pending": current_pending,
        }
    
    def get_batch_summary(self) -> List[Dict[str, Any]]:
        """获取批次摘要"""
        summary = []
        for batch in self._batches:
            summary.append({
                "batch_index": batch.batch_index,
                "channels": [ch.name for ch in batch.channels],
                "is_infusing": batch.is_infusing,
                "has_infused": batch.has_infused,
                "has_errors": batch.has_errors,
                "infusing_channels": batch.infusing_channels,
                "completed_channels": batch.completed_channels,
                "pending_channels": batch.pending_channels,
            })
        return summary
