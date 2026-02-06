"""
LibContext - 依赖注入容器
统一管理系统组件实例，为前端提供后端服务访问入口

这是前端和后端的桥梁模块

泵工作类型定义：
- Inlet: 用于冲洗步骤的进液泵
- Transfer: 用于移液步骤的转移泵
- Outlet: 用于排空步骤的出液泵
- Diluter: 用于配液步骤的稀释泵（从DilutionChannel获取）
"""

from typing import Optional, Callable, Dict, List
from .hardware.rs485_driver import RS485Driver
from .utils.constants import DEFAULT_BAUDRATE


# 泵工作类型枚举
class PumpWorkType:
    """泵工作类型"""
    INLET = "Inlet"       # 冲洗用进液泵
    TRANSFER = "Transfer" # 移液用转移泵  
    OUTLET = "Outlet"     # 排空用出液泵
    DILUTER = "Diluter"   # 配液用稀释泵


class RS485DriverAdapter:
    """RS485Driver适配器，为PumpManager提供期望的接口"""
    
    def __init__(self, driver: RS485Driver):
        self.driver = driver
        self._frame_callback: Optional[Callable] = None
        self._error_callback: Optional[Callable] = None
        
        # 设置回调适配
        self.driver.set_callback(self._on_frame_received)
    
    def on_frame(self, callback: Callable) -> None:
        """设置帧接收回调"""
        self._frame_callback = callback
    
    def on_error(self, callback: Callable) -> None:  
        """设置错误回调"""
        self._error_callback = callback
    
    def _on_frame_received(self, addr: int, cmd: int, payload: bytes):
        """内部帧接收处理"""
        if self._frame_callback:
            # 将参数转换为PumpManager期望的格式
            class ParsedFrame:
                def __init__(self, addr, cmd, payload):
                    self.addr = addr
                    self.cmd = cmd
                    self.payload = payload
            
            frame = ParsedFrame(addr, cmd, payload)
            try:
                self._frame_callback(frame)
            except Exception as e:
                if self._error_callback:
                    self._error_callback(e)
    
    def open(self, port: str, baudrate: int, timeout: float = 0.1):
        """打开连接"""
        # 更新驱动的端口和波特率参数
        self.driver.port = port
        self.driver.baudrate = baudrate
        self.driver.timeout = timeout
        return self.driver.open()
    
    def close(self):
        """关闭连接"""
        return self.driver.close()
    
    def write(self, data: bytes) -> int:
        """写入数据到串口"""
        # PumpManager会调用这个方法发送已构建的帧
        if hasattr(self.driver, '_serial') and self.driver._serial:
            return self.driver._serial.write(data)
        return 0
    
    def send_frame(self, addr: int, cmd: int, payload: bytes = b"") -> bool:
        """发送帧"""
        return self.driver.send_frame(addr, cmd, payload)


class LibContext:
    """依赖注入容器 - 系统组件单例管理
    
    管理系统中各硬件组件的实例，提供泵工作类型映射。
    
    泵工作类型映射：
    - 移液(transfer): 使用 work_type="Transfer" 的泵
    - 冲洗(flush): 使用 work_type="Inlet" 的泵
    - 排空(evacuate): 使用 work_type="Outlet" 的泵
    - 配液(prep_sol): 使用 DilutionChannel 中配置的泵
    """
    
    _pump_manager: Optional['PumpManager'] = None
    _rs485_driver: Optional[RS485Driver] = None
    _logger: Optional['LoggerService'] = None
    _current_mock_mode: Optional[bool] = None  # 跟踪当前的mock模式
    
    # 泵工作类型到地址的映射（从配置加载）
    _pump_type_map: Dict[str, int] = {}
    
    # 稀释通道映射（channel_id -> pump_address）
    _diluter_channels: Dict[str, int] = {}
    
    @classmethod
    def configure_pumps_from_config(cls, system_config) -> None:
        """从系统配置加载泵映射
        
        Args:
            system_config: SystemConfig 对象（来自前端 models.py）
        """
        cls._pump_type_map.clear()
        cls._diluter_channels.clear()
        
        # 从 flush_channels 获取工作类型映射
        if hasattr(system_config, 'flush_channels'):
            for ch in system_config.flush_channels:
                work_type = getattr(ch, 'work_type', 'Transfer')
                pump_addr = getattr(ch, 'pump_address', 0)
                if work_type and pump_addr > 0:
                    cls._pump_type_map[work_type] = pump_addr
                    print(f"  泵映射: {work_type} -> 泵{pump_addr}")
        
        # 从 dilution_channels 获取稀释泵映射
        if hasattr(system_config, 'dilution_channels'):
            for ch in system_config.dilution_channels:
                channel_id = getattr(ch, 'channel_id', '')
                pump_addr = getattr(ch, 'pump_address', 0)
                if channel_id and pump_addr > 0:
                    cls._diluter_channels[channel_id] = pump_addr
                    print(f"  稀释通道: {channel_id} -> 泵{pump_addr}")
    
    @classmethod
    def get_pump_for_work_type(cls, work_type: str) -> int:
        """根据工作类型获取泵地址
        
        Args:
            work_type: 工作类型 (Inlet/Transfer/Outlet)
            
        Returns:
            int: 泵地址，未找到返回0
        """
        return cls._pump_type_map.get(work_type, 0)
    
    @classmethod
    def get_inlet_pump(cls) -> int:
        """获取进液泵地址（用于冲洗）"""
        return cls._pump_type_map.get(PumpWorkType.INLET, 1)
    
    @classmethod
    def get_transfer_pump(cls) -> int:
        """获取转移泵地址（用于移液）"""
        return cls._pump_type_map.get(PumpWorkType.TRANSFER, 2)
    
    @classmethod
    def get_outlet_pump(cls) -> int:
        """获取出液泵地址（用于排空）"""
        return cls._pump_type_map.get(PumpWorkType.OUTLET, 3)
    
    @classmethod
    def get_diluter_pump(cls, channel_id: str) -> int:
        """获取稀释泵地址
        
        Args:
            channel_id: 稀释通道ID (如 "D1", "D2")
            
        Returns:
            int: 泵地址，未找到返回0
        """
        return cls._diluter_channels.get(channel_id, 0)
    
    @classmethod
    def get_pump_manager(cls, mock_mode: bool = True) -> 'PumpManager':
        """获取泵管理器实例
        
        Args:
            mock_mode: 是否使用模拟模式
            
        Returns:
            PumpManager: 泵管理器实例
            
        Note:
            如果mock_mode与当前模式不同，会重新创建PumpManager
        """
        # 如果mock_mode改变了，需要重新创建
        if cls._pump_manager is not None and cls._current_mock_mode != mock_mode:
            print(f"⚠️ LibContext: mock_mode 已改变 ({cls._current_mock_mode} -> {mock_mode})，重新创建 PumpManager")
            cls.reset()
        
        if cls._pump_manager is None:
            # 创建RS485驱动（使用宽松校验和模式以兼容校验和有问题的设备）
            driver = RS485Driver(mock_mode=mock_mode, strict_checksum=False)
            cls._rs485_driver = driver
            
            # 创建适配器
            adapter = RS485DriverAdapter(driver)
            
            # 创建泵管理器
            from .hardware.pump_manager import PumpManager
            cls._pump_manager = PumpManager(
                driver=adapter,
                logger=cls.get_logger(),
                timeout_s=1.0
            )
            
            cls._current_mock_mode = mock_mode
            print(f"✅ LibContext: 创建 PumpManager (mock_mode={mock_mode})")
        
        return cls._pump_manager
    
    @classmethod
    def get_logger(cls) -> 'LoggerService':
        """获取日志服务实例"""
        if cls._logger is None:
            try:
                from .services.logger import LoggerService
                cls._logger = LoggerService()
            except:
                # 如果还没实现LoggerService，先用None
                cls._logger = None
        return cls._logger
    
    @classmethod
    def reset(cls):
        """重置所有单例（测试用或模式切换时）"""
        if cls._pump_manager:
            try:
                cls._pump_manager.disconnect()
            except:
                pass
        cls._pump_manager = None
        cls._rs485_driver = None
        cls._current_mock_mode = None
        # 注意：不重置 _logger，日志服务可以复用
