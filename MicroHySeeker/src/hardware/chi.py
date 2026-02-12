"""CHI instrument driver - 前端适配层

将 echem_sdl.hardware.chi.CHIInstrument 封装为前端友好的接口。
支持 Mock 模式和 libec.dll 硬件模式。
"""

from typing import Dict, Optional, List, Callable
import sys
from pathlib import Path

# 导入后端 CHI 驱动
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from echem_sdl.hardware.chi import (
        CHIInstrument, ECParameters, ECTechnique, ECDataPoint,
        ECDataSet, CHIState, TECHNIQUE_NAMES, TECHNIQUE_FROM_STR
    )
    BACKEND_CHI_AVAILABLE = True
except ImportError as e:
    print(f"[CHI] 后端驱动导入失败: {e}")
    BACKEND_CHI_AVAILABLE = False


class CHIDriver:
    """CHI 电化学仪器驱动（前端适配层）
    
    提供简化的 API 供 UI 和实验引擎调用。
    
    Example:
        >>> driver = CHIDriver(mock_mode=True)
        >>> driver.connect()
        True
        >>> driver.set_potential(0.5)
        True
        >>> driver.start_measurement(duration=60.0)
        True
    """
    
    def __init__(self, dll_path: str = None, mock_mode: bool = True):
        self.is_connected = False
        self.current_potential = 0.0
        self.current_current = 0.0
        self._mock_mode = mock_mode
        
        # 连接状态: "disconnected" | "connected" | "failed"
        self.connection_status = "disconnected"
        
        if BACKEND_CHI_AVAILABLE:
            self._chi = CHIInstrument(
                dll_path=dll_path,
                mock_mode=mock_mode
            )
        else:
            self._chi = None
    
    def connect(self) -> bool:
        """连接 CHI 仪器"""
        if self._chi:
            result = self._chi.connect()
            self.is_connected = result
            self.connection_status = "connected" if result else "failed"
            print(f"[CHI] {'已连接' if result else '连接失败'}")
            return result
        
        # 无后端时使用简单 mock
        self.is_connected = True
        self.connection_status = "connected"
        print("[CHI] Connected (simple mock)")
        return True
    
    def disconnect(self) -> bool:
        """断开 CHI 仪器"""
        if self._chi:
            self._chi.disconnect()
        self.is_connected = False
        self.connection_status = "disconnected"
        print("[CHI] Disconnected")
        return True
    
    def check_connection(self) -> bool:
        """检测仪器是否真实连接（会尝试运行假实验）"""
        if self._chi and hasattr(self._chi, 'check_connection'):
            return self._chi.check_connection()
        return self.is_connected
    
    def set_potential(self, potential: float) -> bool:
        """设置电位（V）"""
        if not self.is_connected:
            return False
        self.current_potential = potential
        print(f"[CHI] Potential set to {potential} V")
        return True
    
    def start_measurement(self, duration: float = 60.0, technique: str = "CV",
                          e_init: float = 0.0, e_high: float = 0.5, e_low: float = -0.5,
                          e_final: float = 0.0, scan_rate: float = 0.1,
                          quiet_time: float = 2.0, segments: int = 2,
                          sample_interval: float = 0.001,
                          data_callback: Callable = None,
                          complete_callback: Callable = None) -> bool:
        """启动测量
        
        Args:
            duration: 运行时间 (s)，用于 i-t 等技术
            technique: 电化学技术 ("CV", "LSV", "i-t", "OCPT" 等)
            data_callback: 实时数据回调 fn(ECDataPoint)
            complete_callback: 测量完成回调 fn()
        """
        if not self.is_connected:
            return False
        
        if self._chi:
            # 构建参数
            tech_enum = TECHNIQUE_FROM_STR.get(technique, ECTechnique.CV)
            params = ECParameters(
                technique=tech_enum,
                e_init=e_init,
                e_high=e_high,
                e_low=e_low,
                e_final=e_final,
                scan_rate=scan_rate,
                sample_interval=sample_interval,
                quiet_time=quiet_time,
                run_time=duration,
                segments=segments,
            )
            self._chi.set_parameters(params)
            if data_callback:
                self._chi.on_data(data_callback)
            if complete_callback:
                self._chi.on_complete(complete_callback)
            return self._chi.run()
        
        print(f"[CHI] Measurement started: {technique} for {duration}s")
        return True
    
    def stop_measurement(self) -> bool:
        """停止测量"""
        if self._chi:
            return self._chi.stop()
        print("[CHI] Measurement stopped")
        return True
    
    def get_data(self) -> Optional[Dict]:
        """获取测量数据"""
        if self._chi:
            data_set = self._chi.get_data_set()
            return {
                "name": data_set.name,
                "technique": data_set.technique,
                "points": [p.to_dict() for p in data_set.points],
                "metadata": data_set.metadata,
            }
        return {
            "potential": self.current_potential,
            "current": 0.001,
            "timestamp": "2026-01-28 00:00:00"
        }
    
    def get_state(self) -> str:
        """获取仪器状态"""
        if self._chi:
            return self._chi.state.value
        return "idle" if self.is_connected else "disconnected"
    
    def is_running(self) -> bool:
        """是否正在测量"""
        if self._chi:
            return self._chi.is_running
        return False
    
    def get_estimated_duration(self, technique: str = "CV", **kwargs) -> float:
        """预估测量时间"""
        if self._chi:
            tech_enum = TECHNIQUE_FROM_STR.get(technique, ECTechnique.CV)
            params = ECParameters(technique=tech_enum, **kwargs)
            return self._chi.get_estimated_duration(params)
        return 60.0
    
    def enable_ocpt(self, enabled: bool) -> bool:
        """启用/禁用 OCPT（开路电位测量）"""
        print(f"[CHI] OCPT {'enabled' if enabled else 'disabled'}")
        return True
