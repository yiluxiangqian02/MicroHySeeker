"""
RS485 通讯封装层 - 复用 485test/通讯 中的实现并适配线程安全
"""
import sys
import threading
import time
from typing import List, Optional, Callable
from pathlib import Path

# 添加 485test/通讯 到 Python 路径
comm_path = Path(__file__).parent.parent.parent / "485test" / "通讯"
if str(comm_path) not in sys.path:
    sys.path.insert(0, str(comm_path))

from comm.serial_comm import SerialComm
from comm.protocol import build_frame, verify_frame, parse_frame, CMD_ENABLE, CMD_SPEED


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
