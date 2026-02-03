"""
Diluter - 配液器驱动模块

控制单通道蠕动泵进行精确体积注液。
支持Mock模式和真实硬件模式。
支持两种控制模式：
1. 速度模式（传统）：基于时间估算的注液
2. 位置模式（SR_VFOC）：基于编码器位移的精确控制
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
import threading
import time
import math

from ..utils.constants import (
    ENCODER_DIVISIONS_PER_REV,
    DEFAULT_DILUTION_ACCELERATION,
    DEFAULT_DILUTION_SPEED,
)


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
    tube_diameter_mm: float = 1.0   # 管道内径 (mm)，用于位置模式计算
    
    # 位置模式校准参数 (由校准流程填充)
    ul_per_encoder_count: float = 0.0  # 每编码器计数对应的微升数 (校准值)
    calibration_valid: bool = False    # 校准是否有效


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
            
            # 已知响应不稳定的泵，自动使用fire_and_forget模式
            RESPONSE_UNSTABLE_PUMPS = [1, 11]
            use_fire_and_forget = self.config.address in RESPONSE_UNSTABLE_PUMPS
            
            if use_fire_and_forget and self._logger:
                self._logger.warning(
                    f"{self.config.name} (地址{self.config.address}) 响应不稳定，使用fire_and_forget模式",
                    module="Diluter"
                )
            
            success = self._pump_manager.start_pump(
                self.config.address,
                direction,
                rpm,
                fire_and_forget=use_fire_and_forget
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
            # 已知响应不稳定的泵，自动使用fire_and_forget模式
            RESPONSE_UNSTABLE_PUMPS = [1, 11]
            use_fire_and_forget = self.config.address in RESPONSE_UNSTABLE_PUMPS
            
            success = self._pump_manager.stop_pump(
                self.config.address, 
                fire_and_forget=use_fire_and_forget
            )
            
            if success or use_fire_and_forget:
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
                # 已知响应不稳定的泵，自动使用fire_and_forget模式
                RESPONSE_UNSTABLE_PUMPS = [1, 11]
                use_fire_and_forget = self.config.address in RESPONSE_UNSTABLE_PUMPS
                
                self._pump_manager.stop_pump(
                    self.config.address, 
                    fire_and_forget=use_fire_and_forget
                )
            except:
                pass
        
        # 执行回调
        if self._completion_callback:
            try:
                self._completion_callback()
            except Exception as e:
                if self._logger:
                    self._logger.error(f"回调函数执行失败: {e}", module="Diluter")

    # ==================== SR_VFOC 位置模式方法 ====================

    def calculate_encoder_counts(self, volume_ul: float) -> int:
        """计算指定体积对应的编码器计数
        
        使用校准系数将体积转换为编码器位移。
        如果没有校准，使用默认估算值。
        
        Args:
            volume_ul: 体积 (μL)
            
        Returns:
            int: 编码器计数 (16384 = 1圈)
        """
        if self.config.calibration_valid and self.config.ul_per_encoder_count > 0:
            # 使用校准值
            counts = int(volume_ul / self.config.ul_per_encoder_count)
        else:
            # 使用默认估算: 假设每圈100μL (典型蠕动泵)
            ul_per_rev = 100.0  # 每圈微升数
            revolutions = volume_ul / ul_per_rev
            counts = int(revolutions * ENCODER_DIVISIONS_PER_REV)
        
        if self._logger:
            revolutions = counts / ENCODER_DIVISIONS_PER_REV
            self._logger.debug(
                f"{self.config.name}: {volume_ul:.2f}μL -> {counts} counts ({revolutions:.3f}圈)",
                module="Diluter"
            )
        
        return counts

    def infuse_by_position(
        self,
        volume_ul: Optional[float] = None,
        speed: int = DEFAULT_DILUTION_SPEED,
        acceleration: int = DEFAULT_DILUTION_ACCELERATION,
        forward: bool = True,
        wait_complete: bool = True,
        timeout_s: float = 60.0,
        callback: Optional[Callable] = None,
    ) -> bool:
        """使用位置模式进行精确注液（推荐用于SR_VFOC模式）
        
        使用编码器位置精确控制位移量，不依赖时间估算。
        这是SR_VFOC矢量控制模式下推荐的配液方式。
        
        Args:
            volume_ul: 注液体积 (μL)，默认使用prepare设置的值
            speed: 运行速度 (RPM, 0-3000), 默认100
            acceleration: 加速度参数 (0-255), 默认2(平滑)
            forward: 方向，True=正转(出液), False=反转(吸液)
            wait_complete: 是否等待完成
            timeout_s: 等待超时（秒）
            callback: 完成回调函数
            
        Returns:
            bool: 是否成功
            
        Example:
            >>> diluter.infuse_by_position(volume_ul=100, speed=150)
            True
        """
        if self.is_infusing:
            if self._logger:
                self._logger.warning(
                    f"{self.config.name} 正在注液中，无法重复启动", 
                    module="Diluter"
                )
            return False
        
        # 设置体积
        if volume_ul is not None:
            self.target_volume_ul = volume_ul
        
        if self.target_volume_ul <= 0:
            if self._logger:
                self._logger.warning(
                    f"{self.config.name} 目标体积为0，跳过注液", 
                    module="Diluter"
                )
            return False
        
        # 保存回调
        self._completion_callback = callback
        
        # 计算编码器位移
        encoder_counts = self.calculate_encoder_counts(self.target_volume_ul)
        
        # 方向处理
        if not forward:
            encoder_counts = -encoder_counts
        
        # 更新状态
        self._state = DiluterState.INFUSING
        self.infused_volume_ul = 0.0
        self._start_time = time.time()
        
        if self._logger:
            direction_text = "正转(出液)" if forward else "反转(吸液)"
            self._logger.info(
                f"开始位置模式注液: {self.config.name}, "
                f"体积={self.target_volume_ul:.2f}μL, "
                f"编码器={encoder_counts} counts, "
                f"速度={speed}RPM, {direction_text}",
                module="Diluter"
            )
        
        # Mock模式：模拟注液
        if self._mock_mode:
            # 计算模拟时间
            revolutions = abs(encoder_counts) / ENCODER_DIVISIONS_PER_REV
            minutes = revolutions / speed if speed > 0 else 0
            duration = minutes * 60.0
            
            def mock_complete():
                self.infused_volume_ul = self.target_volume_ul
                self._state = DiluterState.COMPLETED
                if self._logger:
                    self._logger.info(
                        f"{self.config.name} 位置模式注液完成 (Mock): "
                        f"{self.target_volume_ul:.2f}μL",
                        module="Diluter"
                    )
                if self._completion_callback:
                    try:
                        self._completion_callback()
                    except Exception as e:
                        if self._logger:
                            self._logger.error(f"回调函数执行失败: {e}", module="Diluter")
            
            if wait_complete:
                time.sleep(duration)
                mock_complete()
            else:
                self._progress_timer = threading.Timer(duration, mock_complete)
                self._progress_timer.start()
            
            return True
        
        # 真实硬件：使用PumpManager的位置控制
        try:
            success = self._pump_manager.dispense_by_encoder(
                addr=self.config.address,
                encoder_counts=encoder_counts,
                speed=speed,
                acceleration=acceleration,
                wait_complete=wait_complete,
                timeout_s=timeout_s,
            )
            
            if success:
                self.infused_volume_ul = self.target_volume_ul
                self._state = DiluterState.COMPLETED
                
                if self._logger:
                    elapsed = time.time() - self._start_time
                    self._logger.info(
                        f"{self.config.name} 位置模式注液完成: "
                        f"{self.target_volume_ul:.2f}μL, 耗时 {elapsed:.1f}s",
                        module="Diluter"
                    )
                
                # 执行回调
                if self._completion_callback:
                    try:
                        self._completion_callback()
                    except Exception as e:
                        if self._logger:
                            self._logger.error(f"回调函数执行失败: {e}", module="Diluter")
                
                return True
            else:
                self._state = DiluterState.ERROR
                if self._logger:
                    self._logger.error(
                        f"{self.config.name} 位置模式注液失败", 
                        module="Diluter"
                    )
                return False
                
        except Exception as e:
            self._state = DiluterState.ERROR
            if self._logger:
                self._logger.error(
                    f"{self.config.name} 位置模式注液异常: {e}", 
                    module="Diluter"
                )
            return False

    def read_current_position(self) -> Optional[int]:
        """读取当前编码器位置
        
        Returns:
            int | None: 编码器累加值，None表示读取失败
        """
        if self._mock_mode:
            return 0
        
        try:
            return self._pump_manager.read_encoder_accum(self.config.address)
        except Exception as e:
            if self._logger:
                self._logger.debug(f"{self.config.name} 读取编码器失败: {e}", module="Diluter")
            return None

    def set_calibration(self, ul_per_encoder_count: float) -> None:
        """设置校准参数
        
        Args:
            ul_per_encoder_count: 每编码器计数对应的微升数
        """
        self.config.ul_per_encoder_count = ul_per_encoder_count
        self.config.calibration_valid = ul_per_encoder_count > 0
        
        if self._logger:
            if self.config.calibration_valid:
                ul_per_rev = ul_per_encoder_count * ENCODER_DIVISIONS_PER_REV
                self._logger.info(
                    f"{self.config.name} 校准设置: "
                    f"{ul_per_encoder_count:.6f} μL/count, "
                    f"{ul_per_rev:.2f} μL/圈",
                    module="Diluter"
                )
            else:
                self._logger.info(f"{self.config.name} 校准已清除", module="Diluter")
