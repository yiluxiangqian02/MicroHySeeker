"""
Diluter - 配液器驱动模块

控制单通道蠕动泵进行精确体积注液。
支持Mock模式和真实硬件模式。
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable
import threading
import time


class DiluterState(Enum):
    """Diluter 状态枚举"""
    IDLE = "idle"           # 空闲
    INFUSING = "infusing"   # 注液中
    COMPLETED = "completed" # 已完成
    ERROR = "error"         # 错误


@dataclass
class DiluterConfig:
    """Diluter 配置"""
    address: int                    # RS485 地址 (1-12)
    name: str                       # 溶液名称
    stock_concentration: float      # 储备浓度 (mol/L)
    ul_per_division: float = 0.1    # 每分度对应的微升数（标定因子）
    default_rpm: int = 120          # 默认转速
    default_direction: str = "FWD"  # 默认方向


class Diluter:
    """配液器驱动
    
    控制单通道蠕动泵进行精确体积注液。
    
    架构说明：
    - 通过 PumpManager 获取泵实例进行控制
    - 不直接调用 RS485Driver
    - 支持Mock模式模拟注液过程
    
    Attributes:
        config: 配置参数
        state: 当前状态
        target_volume_ul: 目标体积（微升）
        infused_volume_ul: 已注入体积（微升）
        
    Example:
        >>> from echem_sdl.lib_context import LibContext
        >>> ctx = LibContext(mock_mode=True)
        >>> config = DiluterConfig(address=1, name="H2SO4", stock_concentration=1.0)
        >>> diluter = Diluter(config, ctx.pump_manager, ctx.logger)
        >>> diluter.prepare(target_conc=0.1, total_volume_ul=1000)
        >>> diluter.infuse()
        >>> while diluter.is_infusing:
        ...     time.sleep(0.1)
    """
    
    def __init__(
        self,
        config: DiluterConfig,
        pump_manager: "PumpManager",
        logger: Optional["LoggerService"] = None,
        mock_mode: bool = False
    ) -> None:
        """初始化 Diluter
        
        Args:
            config: 配液器配置
            pump_manager: PumpManager 实例
            logger: 日志服务
            mock_mode: Mock模式（用于模拟注液）
        """
        self.config = config
        self._pump_manager = pump_manager
        self._logger = logger
        self._mock_mode = mock_mode
        
        # 状态
        self._state = DiluterState.IDLE
        self.target_volume_ul = 0.0
        self.infused_volume_ul = 0.0
        
        # 定时器
        self._progress_timer: Optional[threading.Timer] = None
        self._start_time = 0.0
        
        # 回调
        self._completion_callback: Optional[Callable] = None
        
        if self._logger:
            self._logger.info(
                f"Diluter初始化: {config.name} (地址={config.address}, 浓度={config.stock_concentration}M)",
                module="Diluter"
            )
    
    @property
    def state(self) -> DiluterState:
        """获取当前状态"""
        return self._state
    
    @property
    def is_infusing(self) -> bool:
        """是否正在注液"""
        return self._state == DiluterState.INFUSING
    
    @property
    def has_infused(self) -> bool:
        """是否已完成注液"""
        return self._state == DiluterState.COMPLETED
    
    @property
    def progress(self) -> float:
        """注液进度 (0-1)"""
        if self.target_volume_ul <= 0:
            return 0.0
        return min(self.infused_volume_ul / self.target_volume_ul, 1.0)
    
    @property
    def estimated_duration(self) -> float:
        """预计持续时间（秒）"""
        return self.calculate_duration(self.target_volume_ul, self.config.default_rpm)
    
    def prepare(
        self,
        target_conc: float,
        total_volume_ul: float,
        is_solvent: bool = False
    ) -> float:
        """准备注液参数
        
        根据目标浓度计算需要注入的体积。
        
        Args:
            target_conc: 目标浓度 (mol/L)
            total_volume_ul: 总体积 (μL)
            is_solvent: 是否为溶剂（溶剂用于补齐体积）
            
        Returns:
            float: 需要注入的体积 (μL)
            
        Formula:
            V_stock = (target_conc / stock_conc) * total_volume
            V_solvent = total_volume - sum(V_stock_i)
        """
        if is_solvent:
            # 溶剂：补齐总体积
            self.target_volume_ul = total_volume_ul
        else:
            # 储备液：按浓度比计算
            if self.config.stock_concentration <= 0:
                self.target_volume_ul = 0.0
            else:
                ratio = target_conc / self.config.stock_concentration
                self.target_volume_ul = ratio * total_volume_ul
        
        self.infused_volume_ul = 0.0
        self._state = DiluterState.IDLE
        
        if self._logger:
            self._logger.info(
                f"准备注液: {self.config.name}, 目标体积={self.target_volume_ul:.2f}μL",
                module="Diluter"
            )
        
        return self.target_volume_ul
    
    def infuse(
        self,
        volume_ul: Optional[float] = None,
        rpm: Optional[int] = None,
        forward: bool = True,
        callback: Optional[Callable] = None
    ) -> bool:
        """开始注液
        
        Args:
            volume_ul: 注液体积（如果不指定，使用 prepare 设置的值）
            rpm: 转速，默认使用配置值
            forward: 方向，True为正转
            callback: 完成回调函数
            
        Returns:
            bool: 是否成功启动
            
        Note:
            此方法非阻塞，注液在后台进行
            使用 is_infusing 属性检查状态
        """
        if self.is_infusing:
            if self._logger:
                self._logger.warning(f"{self.config.name} 正在注液中，无法重复启动", module="Diluter")
            return False
        
        # 设置体积
        if volume_ul is not None:
            self.target_volume_ul = volume_ul
        
        if self.target_volume_ul <= 0:
            if self._logger:
                self._logger.warning(f"{self.config.name} 目标体积为0，跳过注液", module="Diluter")
            return False
        
        # 设置转速
        if rpm is None:
            rpm = self.config.default_rpm
        
        # 保存回调
        self._completion_callback = callback
        
        # 更新状态
        self._state = DiluterState.INFUSING
        self.infused_volume_ul = 0.0
        self._start_time = time.time()
        
        if self._logger:
            self._logger.info(
                f"开始注液: {self.config.name}, 体积={self.target_volume_ul:.2f}μL, 转速={rpm}RPM",
                module="Diluter"
            )
        
        # Mock模式：模拟注液
        if self._mock_mode:
            duration = self.calculate_duration(self.target_volume_ul, rpm)
            self._start_mock_infusion(duration)
            return True
        
        # 真实硬件：通过 PumpManager 启动泵
        try:
            direction = "FWD" if forward else "REV"
            success = self._pump_manager.start_pump(
                self.config.address,
                direction,
                rpm,
                fire_and_forget=False
            )
            
            if success:
                # 启动进度监控定时器
                self._start_progress_timer()
                return True
            else:
                self._state = DiluterState.ERROR
                if self._logger:
                    self._logger.error(f"{self.config.name} 启动失败", module="Diluter")
                return False
                
        except Exception as e:
            self._state = DiluterState.ERROR
            if self._logger:
                self._logger.error(f"{self.config.name} 注液异常: {e}", module="Diluter")
            return False
    
    def infuse_volume(
        self,
        volume_ul: float,
        callback: Optional[Callable] = None
    ) -> bool:
        """注入指定体积（便捷方法）
        
        Args:
            volume_ul: 体积（微升）
            callback: 完成回调
            
        Returns:
            bool: 是否成功启动
        """
        return self.infuse(volume_ul=volume_ul, callback=callback)
    
    def stop(self) -> bool:
        """停止注液
        
        Returns:
            bool: 是否成功停止
        """
        if not self.is_infusing:
            return True
        
        # 停止定时器
        if self._progress_timer:
            self._progress_timer.cancel()
            self._progress_timer = None
        
        # Mock模式：直接停止
        if self._mock_mode:
            self._state = DiluterState.IDLE
            if self._logger:
                self._logger.info(f"{self.config.name} 注液已停止 (Mock)", module="Diluter")
            return True
        
        # 真实硬件：通过 PumpManager 停止泵
        try:
            success = self._pump_manager.stop_pump(self.config.address)
            if success:
                self._state = DiluterState.IDLE
                if self._logger:
                    self._logger.info(f"{self.config.name} 注液已停止", module="Diluter")
                return True
            else:
                if self._logger:
                    self._logger.error(f"{self.config.name} 停止失败", module="Diluter")
                return False
        except Exception as e:
            if self._logger:
                self._logger.error(f"{self.config.name} 停止异常: {e}", module="Diluter")
            return False
    
    def reset(self) -> None:
        """重置状态
        
        清除目标体积、已注入体积，状态归零
        """
        self.stop()
        self.target_volume_ul = 0.0
        self.infused_volume_ul = 0.0
        self._state = DiluterState.IDLE
        if self._logger:
            self._logger.info(f"{self.config.name} 状态已重置", module="Diluter")
    
    def get_progress(self) -> float:
        """获取进度（0-100%）
        
        Returns:
            float: 进度百分比
        """
        return self.progress * 100.0
    
    @staticmethod
    def calculate_duration(volume_ul: float, rpm: int, ul_per_rev: float = 100.0) -> float:
        """计算注液时间
        
        Args:
            volume_ul: 体积 (μL)
            rpm: 转速
            ul_per_rev: 每转微升数
            
        Returns:
            float: 时间 (秒)
        """
        if rpm <= 0:
            return 0.0
        revolutions = volume_ul / ul_per_rev
        minutes = revolutions / rpm
        return minutes * 60.0
    
    def _start_mock_infusion(self, duration: float) -> None:
        """启动Mock注液模拟
        
        Args:
            duration: 持续时间（秒）
        """
        def mock_complete():
            self.infused_volume_ul = self.target_volume_ul
            self._state = DiluterState.COMPLETED
            if self._logger:
                self._logger.info(
                    f"{self.config.name} 注液完成 (Mock): {self.target_volume_ul:.2f}μL",
                    module="Diluter"
                )
            if self._completion_callback:
                try:
                    self._completion_callback()
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"回调函数执行失败: {e}", module="Diluter")
        
        # 使用定时器模拟注液完成
        self._progress_timer = threading.Timer(duration, mock_complete)
        self._progress_timer.start()
        
        if self._logger:
            self._logger.info(
                f"{self.config.name} 开始Mock注液，预计 {duration:.1f} 秒完成",
                module="Diluter"
            )
    
    def _start_progress_timer(self) -> None:
        """启动进度更新定时器"""
        def update_progress():
            if self._state != DiluterState.INFUSING:
                return
            
            elapsed = time.time() - self._start_time
            if elapsed >= self.estimated_duration:
                self._complete_infusion()
            else:
                # 根据时间估算进度
                progress_ratio = elapsed / self.estimated_duration
                self.infused_volume_ul = self.target_volume_ul * progress_ratio
                
                # 继续定时更新
                self._progress_timer = threading.Timer(0.5, update_progress)
                self._progress_timer.start()
        
        self._progress_timer = threading.Timer(0.5, update_progress)
        self._progress_timer.start()
    
    def _complete_infusion(self) -> None:
        """完成注液"""
        self.infused_volume_ul = self.target_volume_ul
        self._state = DiluterState.COMPLETED
        
        if self._logger:
            self._logger.info(
                f"{self.config.name} 注液完成: {self.target_volume_ul:.2f}μL",
                module="Diluter"
            )
        
        # 停止泵
        if not self._mock_mode:
            try:
                self._pump_manager.stop_pump(self.config.address)
            except:
                pass
        
        # 执行回调
        if self._completion_callback:
            try:
                self._completion_callback()
            except Exception as e:
                if self._logger:
                    self._logger.error(f"回调函数执行失败: {e}", module="Diluter")
