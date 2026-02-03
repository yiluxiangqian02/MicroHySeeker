"""
RS485 通讯封装层 - 前端和后端的桥梁
将前端的调用适配到新的后端架构
"""
import sys
import threading
import time
from typing import List, Optional, Callable
from pathlib import Path

# 导入新的后端
try:
    sys.path.append(str(Path(__file__).parent.parent / "echem_sdl"))
    from echem_sdl.lib_context import LibContext
    from echem_sdl.hardware.pump_manager import PumpManager, PumpState
    BACKEND_AVAILABLE = True
except Exception as e:
    print(f"❌ 后端模块导入失败: {e}")
    BACKEND_AVAILABLE = False


class RS485Wrapper:
    """RS485 前端适配器
    
    将前端的RS485调用适配到新的PumpManager后端
    """
    
    def __init__(self):
        self._pump_manager: Optional[PumpManager] = None
        self._connected = False
        self._mock_mode = True  # 默认使用Mock模式
        
    def set_mock_mode(self, mock_mode: bool):
        """设置模拟模式"""
        self._mock_mode = mock_mode
        
    def open_port(self, port: str, baudrate: int = 38400) -> bool:
        """打开串口连接
        
        Args:
            port: 端口名称
            baudrate: 波特率
            
        Returns:
            bool: 连接是否成功
        """
        if not BACKEND_AVAILABLE:
            print("❌ RS485Wrapper: 后端不可用")
            return False
            
        try:
            # 获取PumpManager实例
            self._pump_manager = LibContext.get_pump_manager(mock_mode=self._mock_mode)
            
            # 连接
            self._pump_manager.connect(port, baudrate, timeout=0.5)
            self._connected = True
            
            print(f"✅ RS485Wrapper: 连接成功 {port}@{baudrate}")
            return True
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 连接失败 {e}")
            return False
    
    def close_port(self) -> None:
        """关闭串口连接"""
        if self._pump_manager:
            self._pump_manager.disconnect()
        self._connected = False
        print("✅ RS485Wrapper: 连接已关闭")
        
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._pump_manager is not None
        
    def scan_pumps(self) -> List[int]:
        """扫描可用泵
        
        Returns:
            List[int]: 可用泵地址列表
        """
        if not self.is_connected():
            return []
            
        try:
            # 启动扫描
            self._pump_manager.start_scan(
                addresses=list(range(1, 13)),
                poll_interval_s=0.2
            )
            
            # 等待扫描完成
            time.sleep(2.0)
            
            # 停止扫描
            self._pump_manager.stop_scan()
            
            # 获取在线设备
            online_pumps = []
            for addr in range(1, 13):
                state = self._pump_manager.get_state(addr)
                if state.online:
                    online_pumps.append(addr)
                    
            print(f"✅ RS485Wrapper: 扫描到泵 {online_pumps}")
            return online_pumps
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 扫描失败 {e}")
            return []
    
    def start_pump(self, address: int, direction: str, rpm: int) -> bool:
        """启动泵
        
        Args:
            address: 泵地址 (1-12)
            direction: 方向 "FWD" 或 "REV"  
            rpm: 转速
            
        Returns:
            bool: 启动是否成功
        """
        if not self.is_connected():
            print(f"❌ RS485Wrapper: 未连接，无法启动泵 {address}")
            return False
            
        try:
            # 1. 使能泵
            enable_result = self._pump_manager.set_enable(address, True)
            if enable_result is None:
                print(f"❌ RS485Wrapper: 泵 {address} 使能失败")
                return False
                
            # 2. 设置速度（根据方向）
            speed = rpm if direction.upper() == "FWD" else -rpm
            speed_result = self._pump_manager.set_speed(address, speed)
            
            if speed_result is None:
                print(f"❌ RS485Wrapper: 泵 {address} 设置速度失败")
                return False
                
            print(f"✅ RS485Wrapper: 泵 {address} 启动成功 {direction} {rpm}RPM")
            return True
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 启动泵 {address} 异常 {e}")
            return False
    
    def stop_pump(self, address: int) -> bool:
        """停止泵
        
        Args:
            address: 泵地址
            
        Returns:
            bool: 停止是否成功
        """
        if not self.is_connected():
            return False
            
        try:
            # 1. 停止旋转（速度设为0）
            speed_result = self._pump_manager.set_speed(address, 0)
            
            # 2. 禁用泵
            disable_result = self._pump_manager.set_enable(address, False)
            
            success = (speed_result is not None) and (disable_result is not None)
            if success:
                print(f"✅ RS485Wrapper: 泵 {address} 停止成功")
            else:
                print(f"❌ RS485Wrapper: 泵 {address} 停止失败")
                
            return success
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 停止泵 {address} 异常 {e}")
            return False
    
    def stop_all(self) -> bool:
        """停止所有泵"""
        if not self.is_connected():
            return False
            
        print("⏹️ RS485Wrapper: 停止所有泵")
        success_count = 0
        
        for address in range(1, 13):
            if self.stop_pump(address):
                success_count += 1
                
        print(f"✅ RS485Wrapper: 停止了 {success_count} 个泵")
        return True
        
    def get_pump_status(self, address: int) -> dict:
        """获取泵状态
        
        Args:
            address: 泵地址
            
        Returns:
            dict: 泵状态信息
        """
        if not self.is_connected():
            return {"online": False, "enabled": False, "speed": 0}
            
        try:
            state = self._pump_manager.get_state(address)
            return {
                "online": state.online,
                "enabled": state.enabled or False,
                "speed": state.speed or 0,
                "address": address
            }
        except:
            return {"online": False, "enabled": False, "speed": 0}


# 全局单例
_rs485_instance: Optional[RS485Wrapper] = None

def get_rs485_instance() -> RS485Wrapper:
    """获取RS485实例单例"""
    global _rs485_instance
    if _rs485_instance is None:
        _rs485_instance = RS485Wrapper()
        # 默认开启Mock模式用于开发
        _rs485_instance.set_mock_mode(True)
    return _rs485_instance
                    return False
            return False

except ImportError:
    # 轻量模拟类
    class SerialComm:
        def __init__(self, *args, **kwargs):
            self._is_open = False
            class _Sig:
                def connect(self, *a, **k):
                    pass
            self.data_received = _Sig()
            self.error = _Sig()
            self.state_changed = _Sig()

        def open(self, *args, **kwargs):
            self._is_open = True

        def close(self):
            self._is_open = False

        def is_open(self):
            return self._is_open

        def send(self, data: bytes):
            # 不做任何实际发送，仅模拟成功
            return True

    def build_frame(address, cmd, payload=b""):
        return b""

    def verify_frame(data):
        return True

    def parse_frame(data):
        return {}

    CMD_ENABLE = 0x10
    CMD_SPEED = 0x11


class RS485Wrapper:
    """RS485 通讯包装器 - 线程安全地包装 SerialComm 和协议层"""
    
    def __init__(self):
        self.serial_comm = SerialComm()
        self._response_cache = {}
        self._response_lock = threading.Lock()
        self._pump_states = {}  # 缓存泵状态
        self._scan_result = []  # 扫描结果
        self._is_scanning = False
        
        # 连接信号
        self.serial_comm.data_received.connect(self._on_data_received)
        self.serial_comm.error.connect(self._on_error)
        self.serial_comm.state_changed.connect(self._on_state_changed)
        
        self._callbacks = []
    
    def on_response(self, callback: Callable[[int, int, bytes], None]):
        """注册数据响应回调"""
        self._callbacks.append(callback)
    
    def _on_data_received(self, data: bytes):
        """处理串口数据"""
        # 简化处理：缓存响应供查询
        if len(data) >= 4:
            with self._response_lock:
                self._response_cache['last_response'] = data
            # 调用回调
            for cb in self._callbacks:
                try:
                    cb(data)
                except Exception as e:
                    print(f"Callback error: {e}")
    
    def _on_error(self, error_msg: str):
        """处理错误"""
        print(f"Serial error: {error_msg}")
    
    def _on_state_changed(self, is_open: bool):
        """处理连接状态变化"""
        print(f"Serial state: {'opened' if is_open else 'closed'}")
    
    def open_port(self, port_name: str, baudrate: int = 9600) -> bool:
        """打开串口"""
        try:
            self.serial_comm.open(port_name, baudrate, timeout=0.1)
            time.sleep(0.2)  # 稳定
            return self.serial_comm.is_open()
        except Exception as e:
            print(f"Failed to open port: {e}")
            return False
    
    def close_port(self):
        """关闭串口"""
        self.serial_comm.close()
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.serial_comm.is_open()
    
    def send_command(self, address: int, cmd: int, payload: bytes = b"") -> bool:
        """发送命令"""
        if not self.is_connected():
            return False
        try:
            frame = build_frame(address, cmd, payload)
            self.serial_comm.send(frame)
            return True
        except Exception as e:
            print(f"Send command failed: {e}")
            return False
    
    def scan_pumps(self) -> List[int]:
        """
        扫描可用泵地址（1..12）
        返回可用泵的地址列表
        """
        if not self.is_connected():
            print("Serial port not connected")
            return []
        
        available = []
        print("Scanning pump addresses (1-12)...")
        
        for addr in range(1, 13):
            # 尝试使能泵以检测是否存在
            try:
                if self.enable_pump(addr):
                    available.append(addr)
                    print(f"  Pump {addr}: OK")
                    time.sleep(0.1)
                else:
                    print(f"  Pump {addr}: No response")
            except Exception as e:
                print(f"  Pump {addr}: Error - {e}")
            
            time.sleep(0.05)
        
        self._scan_result = available
        print(f"Scan completed. Found pumps: {available}")
        return available
    
    def enable_pump(self, address: int) -> bool:
        """使能泵"""
        return self.send_command(address, CMD_ENABLE, b"\x01")
    
    def disable_pump(self, address: int) -> bool:
        """禁能泵"""
        return self.send_command(address, CMD_ENABLE, b"\x00")
    
    def set_pump_speed(self, address: int, direction: int, rpm: int) -> bool:
        """
        设置泵转速
        direction: 0x01=正转, 0x02=反转
        rpm: 转速（可能需要编码，具体格式根据协议）
        """
        # 简化实现：将 rpm 编码为两字节
        payload = bytes([direction, (rpm >> 8) & 0xFF, rpm & 0xFF])
        return self.send_command(address, CMD_SPEED, payload)
    
    def start_pump(self, address: int, direction: str = "FWD", rpm: int = 100) -> bool:
        """启动泵"""
        dir_byte = 0x01 if direction.upper() == "FWD" else 0x02
        return self.set_pump_speed(address, dir_byte, rpm)
    
    def stop_pump(self, address: int) -> bool:
        """停止泵"""
        return self.set_pump_speed(address, 0x00, 0)
    
    def stop_all(self) -> bool:
        """停止所有泵（1-12）"""
        success = True
        for addr in range(1, 13):
            if not self.stop_pump(addr):
                success = False
        return success
    
    def get_pump_speed(self, address: int) -> Optional[int]:
        """读取泵当前转速（模拟实现，实际需根据协议）"""
        # 这里仅返回缓存数据或模拟值
        return self._pump_states.get(address, None)
    
    def dispose(self):
        """清理资源"""
        self.close_port()


# 全局实例
_rs485_instance: Optional[RS485Wrapper] = None


def get_rs485_instance() -> RS485Wrapper:
    """获取全局 RS485 实例"""
    global _rs485_instance
    if _rs485_instance is None:
        _rs485_instance = RS485Wrapper()
    return _rs485_instance
