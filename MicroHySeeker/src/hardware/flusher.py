"""Flusher driver."""

from typing import Dict, Optional


class FlusherDriver:
    """冲洗设备驱动（mock）。"""
    
    def __init__(self, rs485_driver=None):
        self.rs485_driver = rs485_driver
        self.is_running = False
        self.current_cycle = 0
    
    def start_flush(self, pump_address: int, volume: float, direction: str = "forward") -> bool:
        """启动冲洗。"""
        print(f"[Flusher] Starting flush: pump={pump_address}, volume={volume}, dir={direction}")
        self.is_running = True
        return True
    
    def stop_flush(self) -> bool:
        """停止冲洗。"""
        print(f"[Flusher] Stopped at cycle {self.current_cycle}")
        self.is_running = False
        return True
    
    def get_status(self) -> Dict[str, any]:
        """获取冲洗状态。"""
        return {
            "running": self.is_running,
            "current_cycle": self.current_cycle
        }
