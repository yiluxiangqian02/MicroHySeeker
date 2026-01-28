"""Pump drivers (mock and real)."""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import time


class PumpInterface(ABC):
    """泵接口（抽象）。"""
    
    @abstractmethod
    def start(self) -> bool:
        """启动泵。"""
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """停止泵。"""
        pass
    
    @abstractmethod
    def set_speed(self, speed: float) -> bool:
        """设置转速。"""
        pass
    
    @abstractmethod
    def move_volume(self, volume: float) -> bool:
        """移动指定体积。"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, any]:
        """获取状态。"""
        pass


class SyringePumpDriver(PumpInterface):
    """注射泵驱动（当前为 mock）。"""
    
    def __init__(self, pump_id: int = 1, port: str = "COM1"):
        self.pump_id = pump_id
        self.port = port
        self.is_running = False
        self.current_speed = 0.0
        self.current_position = 0.0
        self.total_volume = 10.0  # mL
    
    def start(self) -> bool:
        """启动泵。"""
        self.is_running = True
        print(f"[SyringePump {self.pump_id}] Started")
        return True
    
    def stop(self) -> bool:
        """停止泵。"""
        self.is_running = False
        print(f"[SyringePump {self.pump_id}] Stopped")
        return True
    
    def set_speed(self, speed: float) -> bool:
        """设置转速（mL/min）。"""
        self.current_speed = speed
        print(f"[SyringePump {self.pump_id}] Speed set to {speed} mL/min")
        return True
    
    def move_volume(self, volume: float) -> bool:
        """移动指定体积（mL）。"""
        if self.current_position + volume > self.total_volume:
            print(f"[SyringePump {self.pump_id}] Error: exceeds max volume")
            return False
        self.current_position += volume
        print(f"[SyringePump {self.pump_id}] Moved {volume} mL, position: {self.current_position}")
        return True
    
    def get_status(self) -> Dict[str, any]:
        """获取状态。"""
        return {
            "pump_id": self.pump_id,
            "running": self.is_running,
            "speed": self.current_speed,
            "position": self.current_position,
            "total_volume": self.total_volume
        }


class RS485PeristalticDriver(PumpInterface):
    """RS485 蠕动泵驱动（当前为 mock）。"""
    
    def __init__(self, device_address: int = 1, port: str = "COM1"):
        self.device_address = device_address
        self.port = port
        self.is_running = False
        self.current_speed = 0.0
        self.total_cycles = 0.0
        self.direction = "forward"
    
    def start(self) -> bool:
        """启动泵。"""
        self.is_running = True
        print(f"[RS485Peristaltic addr:{self.device_address}] Started")
        return True
    
    def stop(self) -> bool:
        """停止泵。"""
        self.is_running = False
        print(f"[RS485Peristaltic addr:{self.device_address}] Stopped")
        return True
    
    def set_speed(self, speed: float) -> bool:
        """设置转速（RPM）。"""
        self.current_speed = speed
        print(f"[RS485Peristaltic addr:{self.device_address}] Speed set to {speed} RPM")
        return True
    
    def move_volume(self, volume: float) -> bool:
        """移动指定体积（毫升数据转换为周期）。"""
        cycles = volume * 10  # 简化转换：1mL = 10 cycles
        self.total_cycles += cycles
        print(f"[RS485Peristaltic addr:{self.device_address}] Moved {volume} mL ({cycles} cycles)")
        return True
    
    def set_direction(self, direction: str) -> bool:
        """设置方向（forward/backward）。"""
        self.direction = direction
        print(f"[RS485Peristaltic addr:{self.device_address}] Direction set to {direction}")
        return True
    
    def get_status(self) -> Dict[str, any]:
        """获取状态。"""
        return {
            "device_address": self.device_address,
            "running": self.is_running,
            "speed": self.current_speed,
            "total_cycles": self.total_cycles,
            "direction": self.direction
        }


class PumpManager:
    """泵管理器。"""
    
    def __init__(self):
        self.syringe_pumps: Dict[int, SyringePumpDriver] = {}
        self.peristaltic_pumps: Dict[int, RS485PeristalticDriver] = {}
    
    def add_syringe_pump(self, pump_id: int, port: str = "COM1") -> SyringePumpDriver:
        """添加注射泵。"""
        pump = SyringePumpDriver(pump_id, port)
        self.syringe_pumps[pump_id] = pump
        return pump
    
    def add_peristaltic_pump(self, address: int, port: str = "COM1") -> RS485PeristalticDriver:
        """添加蠕动泵。"""
        pump = RS485PeristalticDriver(address, port)
        self.peristaltic_pumps[address] = pump
        return pump
    
    def get_syringe_pump(self, pump_id: int) -> Optional[SyringePumpDriver]:
        """获取注射泵。"""
        return self.syringe_pumps.get(pump_id)
    
    def get_peristaltic_pump(self, address: int) -> Optional[RS485PeristalticDriver]:
        """获取蠕动泵。"""
        return self.peristaltic_pumps.get(address)
    
    def list_all_pumps(self) -> Dict[str, list]:
        """列出所有泵。"""
        return {
            "syringe_pumps": list(self.syringe_pumps.keys()),
            "peristaltic_pumps": list(self.peristaltic_pumps.keys())
        }
