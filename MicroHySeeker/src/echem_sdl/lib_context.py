"""
LibContext - 依赖注入容器
统一管理系统组件实例，为前端提供后端服务访问入口

这是前端和后端的桥梁模块
"""

from typing import Optional, Callable
from .hardware.rs485_driver import RS485Driver
from .utils.constants import DEFAULT_BAUDRATE


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
    """依赖注入容器 - 系统组件单例管理"""
    
    _pump_manager: Optional['PumpManager'] = None
    _rs485_driver: Optional[RS485Driver] = None
    _logger: Optional['LoggerService'] = None
    _current_mock_mode: Optional[bool] = None  # 跟踪当前的mock模式
    
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
