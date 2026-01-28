"""RS485 driver for device communication."""

import serial
from typing import List, Optional, Dict, Tuple
import time


class RS485Driver:
    """RS485 通讯驱动（mock 与实现兼容）。"""
    
    def __init__(self, port: str = "COM1", baudrate: int = 9600, use_mock: bool = True):
        self.port = port
        self.baudrate = baudrate
        self.use_mock = use_mock
        self.ser = None
        self.connected = False
        self.last_response = None
        
        if not use_mock:
            try:
                self.ser = serial.Serial(port, baudrate, timeout=1)
                self.connected = True
            except Exception as e:
                print(f"Failed to connect RS485 on {port}: {e}")
    
    def connect(self) -> bool:
        """连接设备。"""
        if self.use_mock:
            self.connected = True
            print(f"[RS485 Mock] Connected to {self.port}")
            return True
        
        try:
            if self.ser is None or not self.ser.is_open:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connected = True
            print(f"[RS485] Connected to {self.port}")
            return True
        except Exception as e:
            print(f"[RS485] Connection error: {e}")
            return False
    
    def disconnect(self) -> bool:
        """断开连接。"""
        if not self.use_mock and self.ser and self.ser.is_open:
            self.ser.close()
        self.connected = False
        print(f"[RS485] Disconnected")
        return True
    
    def send(self, data: bytes) -> bool:
        """发送数据。"""
        if not self.connected:
            print("[RS485] Not connected")
            return False
        
        try:
            if self.use_mock:
                print(f"[RS485 Mock] Sent: {data.hex()}")
                self.last_response = self._mock_response(data)
                return True
            else:
                self.ser.write(data)
                return True
        except Exception as e:
            print(f"[RS485] Send error: {e}")
            return False
    
    def read(self, timeout: float = 1.0) -> Optional[bytes]:
        """接收数据。"""
        if not self.connected:
            return None
        
        try:
            if self.use_mock:
                if self.last_response:
                    resp = self.last_response
                    self.last_response = None
                    return resp
                return None
            else:
                data = self.ser.read(256)
                return data if data else None
        except Exception as e:
            print(f"[RS485] Read error: {e}")
            return None
    
    def _mock_response(self, request: bytes) -> bytes:
        """生成 mock 回复（简化实现）。"""
        # 简单的 Modbus RTU 模拟回复
        if len(request) > 2:
            slave_id = request[0]
            function_code = request[1]
            # 返回简单的 ACK
            return bytes([slave_id, function_code, 0x00, 0x01])
        return b'\x01\x03\x00\x00'
    
    def scan_devices(self) -> List[int]:
        """扫描 RS485 设备地址（模拟）。"""
        if not self.connected:
            self.connect()
        
        # Mock: 返回模拟设备地址
        mock_addresses = [1, 2, 3, 4, 5]
        print(f"[RS485] Scanned devices: {mock_addresses}")
        return mock_addresses
    
    def send_command(self, device_address: int, command: str, params: Dict = None) -> bool:
        """发送高级命令。"""
        print(f"[RS485] Command to addr {device_address}: {command} {params or ''}")
        return True
    
    def get_device_status(self, device_address: int) -> Optional[Dict]:
        """获取设备状态（mock）。"""
        return {
            "address": device_address,
            "status": "OK",
            "speed": 100,
            "running": False
        }
