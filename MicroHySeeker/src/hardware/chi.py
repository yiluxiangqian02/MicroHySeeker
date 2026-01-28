"""CHI instrument driver."""

from typing import Dict, Optional


class CHIDriver:
    """CHI 电化学仪器驱动（mock）。"""
    
    def __init__(self):
        self.is_connected = False
        self.current_potential = 0.0
        self.current_current = 0.0
    
    def connect(self) -> bool:
        """连接 CHI 仪器。"""
        print("[CHI] Connected")
        self.is_connected = True
        return True
    
    def disconnect(self) -> bool:
        """断开 CHI 仪器。"""
        print("[CHI] Disconnected")
        self.is_connected = False
        return True
    
    def set_potential(self, potential: float) -> bool:
        """设置电位（V）。"""
        if not self.is_connected:
            return False
        self.current_potential = potential
        print(f"[CHI] Potential set to {potential} V")
        return True
    
    def start_measurement(self, duration: float) -> bool:
        """启动测量。"""
        if not self.is_connected:
            return False
        print(f"[CHI] Measurement started for {duration} s")
        return True
    
    def stop_measurement(self) -> bool:
        """停止测量。"""
        print("[CHI] Measurement stopped")
        return True
    
    def get_data(self) -> Optional[Dict]:
        """获取测量数据（mock）。"""
        return {
            "potential": self.current_potential,
            "current": 0.001,
            "timestamp": "2026-01-28 00:00:00"
        }
    
    def enable_ocpt(self, enabled: bool) -> bool:
        """启用/禁用 OCPT（开路电位测量）。"""
        print(f"[CHI] OCPT {'enabled' if enabled else 'disabled'}")
        return True
