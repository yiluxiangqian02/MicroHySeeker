"""
RS485 通讯封装层 - 前端和后端的桥梁
将前端的调用适配到新的后端架构（通过LibContext和PumpManager）
"""
import sys
import threading
import time
from typing import List, Optional, Callable, Dict
from pathlib import Path

# 导入后端模块
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from echem_sdl.lib_context import LibContext
    from echem_sdl.hardware.pump_manager import PumpManager, PumpState
    from echem_sdl.hardware.rs485_driver import RS485Driver
    from echem_sdl.hardware.diluter import Diluter, DiluterConfig
    from echem_sdl.services.logger_service import get_logger
    from models import DilutionChannel
    BACKEND_AVAILABLE = True
except Exception as e:
    print(f"❌ 后端模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    BACKEND_AVAILABLE = False


class RS485Wrapper:
    """RS485 前端适配器
    
    统一前端和后端的桥梁，通过LibContext获取PumpManager实例。
    支持Mock模式和真实硬件模式。
    """
    
    def __init__(self):
        self._pump_manager: Optional[PumpManager] = None
        self._connected = False
        self._mock_mode = True  # 默认使用Mock模式
        self._pump_states: Dict[int, dict] = {}  # 泵状态缓存
        self._state_callback: Optional[Callable] = None  # 状态变化回调
        
        # 配液功能
        self._diluters: Dict[int, Diluter] = {}  # 地址 -> Diluter实例
        self._logger = get_logger()  # 获取日志实例
        
    def set_mock_mode(self, mock_mode: bool):
        """设置模拟模式
        
        如果模式改变，将在下次open_port时重新创建PumpManager
        """
        if self._mock_mode != mock_mode:
            # 模式改变，需要关闭现有连接并重置
            if self._connected:
                self.close_port()
            # LibContext会在get_pump_manager时检测到模式改变并重新创建
        self._mock_mode = mock_mode
        print(f"🔧 RS485Wrapper: Mock模式 {'开启' if mock_mode else '关闭'}")
    
    @staticmethod
    def list_available_ports() -> List[str]:
        """列出可用串口（实际检测到的端口）"""
        if not BACKEND_AVAILABLE:
            return ['COM1', 'COM2', 'COM3']  # 默认端口
        try:
            return RS485Driver.list_ports()
        except Exception as e:
            print(f"❌ 端口枚举失败: {e}")
            return ['COM1', 'COM2', 'COM3']
        
    def open_port(self, port: str, baudrate: int = 38400) -> bool:
        """打开串口连接
        
        通过LibContext获取PumpManager并连接。
        """
        if not BACKEND_AVAILABLE:
            print("❌ RS485Wrapper: 后端不可用")
            return False
        
        # 关闭已有连接
        if self._pump_manager and self._connected:
            self.close_port()
            
        try:
            # 通过LibContext获取PumpManager
            self._pump_manager = LibContext.get_pump_manager(mock_mode=self._mock_mode)
            
            # 设置状态变化回调
            self._pump_manager.on_state(self._on_pump_state_changed)
            
            # 连接串口
            self._pump_manager.connect(port, baudrate, timeout=0.1)
            self._connected = True
            
            print(f"✅ RS485Wrapper: 连接成功 {port}@{baudrate} (Mock={self._mock_mode})")
            return True
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 连接异常 {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _on_pump_state_changed(self, state: PumpState):
        """泵状态变化回调"""
        # 更新缓存
        self._pump_states[state.address] = {
            "address": state.address,
            "online": state.online,
            "enabled": state.enabled if state.enabled is not None else False,
            "speed": state.speed if state.speed is not None else 0,
            "fault": state.fault,
            "last_seen": state.last_seen
        }
        
        # 如果有外部回调，通知前端
        if self._state_callback:
            try:
                self._state_callback(state.address, self._pump_states[state.address])
            except:
                pass
    
    def close_port(self) -> None:
        """关闭串口连接"""
        if self._pump_manager:
            try:
                self._pump_manager.disconnect()
            except:
                pass
            self._pump_manager = None
        self._connected = False
        self._pump_states.clear()
        print("✅ RS485Wrapper: 连接已关闭")
        
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._pump_manager is not None
        
    def scan_pumps(self) -> List[int]:
        """扫描可用泵（地址1-12）
        
        使用PumpManager的scan_devices方法。
        """
        if not self.is_connected():
            print("❌ RS485Wrapper: 未连接，无法扫描")
            return []
            
        try:
            # 使用 PumpManager 的扫描功能
            online_pumps = self._pump_manager.scan_devices(
                addresses=list(range(1, 13)),
                timeout_per_addr=0.2
            )
                    
            print(f"✅ RS485Wrapper: 扫描到泵 {online_pumps}")
            
            # 保存在线泵列表用于后续判断
            self._online_pumps = online_pumps
            
            return online_pumps
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 扫描失败 {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def start_pump(self, address: int, direction: str, rpm: int) -> bool:
        """启动泵
        
        使用PumpManager的start_pump便捷方法。
        对于响应不稳定的泵（泵1、泵11），始终使用fire_and_forget模式。
        """
        if not self.is_connected():
            print(f"❌ RS485Wrapper: 未连接，无法启动泵 {address}")
            return False
        
        # 已知响应不稳定的泵，始终使用fire_and_forget模式
        RESPONSE_UNSTABLE_PUMPS = [1, 11]
        use_fire_and_forget = address in RESPONSE_UNSTABLE_PUMPS
        
        if use_fire_and_forget:
            print(f"⚠️ RS485Wrapper: 泵 {address} 响应不稳定，使用fire_and_forget模式")
            
        try:
            # 使用 PumpManager 的便捷方法
            success = self._pump_manager.start_pump(
                address, direction, rpm, 
                fire_and_forget=use_fire_and_forget
            )
            
            # 更新状态缓存
            self._pump_states[address] = {
                "address": address,
                "online": True,
                "enabled": True,
                "speed": rpm,
                "direction": direction
            }
            
            if success:
                print(f"✅ RS485Wrapper: 泵 {address} 启动成功 {direction} {rpm}RPM")
            else:
                print(f"❌ RS485Wrapper: 泵 {address} 启动失败")
            
            return success
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 启动泵 {address} 异常 {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_pump(self, address: int) -> bool:
        """停止泵
        
        使用PumpManager的stop_pump便捷方法。
        对于响应不稳定的泵（泵1、泵11），始终使用fire_and_forget模式。
        """
        if not self.is_connected():
            return False
        
        # 已知响应不稳定的泵，始终使用fire_and_forget模式
        RESPONSE_UNSTABLE_PUMPS = [1, 11]
        use_fire_and_forget = address in RESPONSE_UNSTABLE_PUMPS
        
        if use_fire_and_forget:
            print(f"⚠️ RS485Wrapper: 泵 {address} 响应不稳定，使用fire_and_forget模式")
            
        try:
            # 使用 PumpManager 的便捷方法
            success = self._pump_manager.stop_pump(address, fire_and_forget=use_fire_and_forget)
            
            # 更新状态
            if address in self._pump_states:
                self._pump_states[address]["enabled"] = False
                self._pump_states[address]["speed"] = 0
            
            if success or use_fire_and_forget:
                print(f"✅ RS485Wrapper: 泵 {address} 停止{'命令已发送' if use_fire_and_forget else '成功'}")
                return True
            else:
                print(f"❌ RS485Wrapper: 泵 {address} 停止失败")
                return False
                
        except Exception as e:
            print(f"❌ RS485Wrapper: 停止泵 {address} 异常 {e}")
            return False
    
    def stop_pump_fast(self, address: int) -> bool:
        """快速停止泵（不等待响应确认）
        
        用于窗口关闭等需要快速响应的场景。
        """
        if not self.is_connected():
            return False
            
        try:
            self._pump_manager.stop_pump(address, fire_and_forget=True)
            # 更新状态
            if address in self._pump_states:
                self._pump_states[address]["enabled"] = False
                self._pump_states[address]["speed"] = 0
            return True
        except Exception:
            return True  # 即使失败也返回True，不阻塞UI
    
    def stop_pumps_fast(self, addresses: list) -> bool:
        """快速停止多个泵（不等待响应确认）
        
        用于窗口关闭等需要快速响应的场景。
        """
        if not self.is_connected():
            return False
            
        for addr in addresses:
            self.stop_pump_fast(addr)
        return True
    
    def stop_all(self) -> bool:
        """停止所有泵
        
        使用PumpManager的stop_all方法（快速模式）。
        """
        if not self.is_connected():
            return False
            
        print("⏹️ RS485Wrapper: 停止所有泵")
        
        try:
            success_count = self._pump_manager.stop_all(addresses=list(range(1, 13)), fire_and_forget=True)
            print(f"✅ RS485Wrapper: 已发送停止命令给 {success_count} 个泵")
            return True
        except Exception as e:
            print(f"❌ RS485Wrapper: 停止所有泵失败 {e}")
            return False
        
    def get_pump_status(self, address: int) -> dict:
        """获取泵状态
        
        从PumpManager获取最新状态。
        """
        if not self.is_connected():
            return {"online": False, "enabled": False, "speed": 0, "address": address}
        
        try:
            # 从 PumpManager 获取状态
            state = self._pump_manager.get_state(address)
            return {
                "address": address,
                "online": state.online,
                "enabled": state.enabled if state.enabled is not None else False,
                "speed": state.speed if state.speed is not None else 0,
                "fault": state.fault
            }
        except:
            # 从缓存返回状态
            if address in self._pump_states:
                return self._pump_states[address]
            else:
                return {"online": False, "enabled": False, "speed": 0, "address": address}
    
    def set_state_callback(self, callback: Callable):
        """设置状态变化回调
        
        Args:
            callback: 回调函数 callback(address: int, state: dict)
        """
        self._state_callback = callback
    
    def start_monitoring(self):
        """启动后台状态监控
        
        启动PumpManager的后台扫描，实时更新泵状态。
        """
        if not self.is_connected():
            print("❌ RS485Wrapper: 未连接，无法启动监控")
            return False
        
        try:
            self._pump_manager.start_scan(
                addresses=list(range(1, 13)),
                poll_interval_s=0.5  # 每0.5秒轮询一次
            )
            print("✅ RS485Wrapper: 启动状态监控")
            return True
        except Exception as e:
            print(f"❌ RS485Wrapper: 启动监控失败 {e}")
            return False
    
    def stop_monitoring(self):
        """停止后台状态监控"""
        if self._pump_manager:
            try:
                self._pump_manager.stop_scan()
                print("✅ RS485Wrapper: 停止状态监控")
            except:
                pass
    
    # ========== 配液功能接口 ==========
    
    def configure_dilution_channels(self, channels: List[DilutionChannel]) -> bool:
        """配置配液通道
        
        Args:
            channels: 配液通道列表（来自前端配置对话框）
            
        Returns:
            bool: 是否配置成功
            
        Example:
            >>> from models import DilutionChannel
            >>> channels = [
            ...     DilutionChannel(
            ...         channel_id="1",
            ...         solution_name="H2SO4",
            ...         stock_concentration=1.0,
            ...         pump_address=1,
            ...         direction="FWD",
            ...         default_rpm=120,
            ...         color="#FF0000"
            ...     )
            ... ]
            >>> wrapper.configure_dilution_channels(channels)
        """
        if not self.is_connected():
            print("❌ RS485Wrapper: 未连接，无法配置配液通道")
            return False
        
        try:
            # 清空现有配置
            self._diluters.clear()
            
            # 为每个通道创建Diluter实例
            for channel in channels:
                config = DiluterConfig(
                    address=channel.pump_address,
                    name=channel.solution_name,
                    stock_concentration=channel.stock_concentration,
                    default_rpm=channel.default_rpm,
                    default_direction=channel.direction
                )
                
                diluter = Diluter(
                    config=config,
                    pump_manager=self._pump_manager,
                    logger=self._logger,
                    mock_mode=self._mock_mode
                )
                
                self._diluters[channel.pump_address] = diluter
                
                print(f"✅ RS485Wrapper: 配置通道 {channel.solution_name} (地址={channel.pump_address})")
            
            print(f"✅ RS485Wrapper: 配液通道配置完成，共 {len(channels)} 个通道")
            return True
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 配置配液通道失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_dilution(self, channel_id: int, volume_ul: float, callback: Optional[Callable] = None) -> bool:
        """开始配液
        
        Args:
            channel_id: 通道ID（即泵地址）
            volume_ul: 体积（微升）
            callback: 完成回调函数
            
        Returns:
            bool: 是否成功启动
        """
        if not self.is_connected():
            print(f"❌ RS485Wrapper: 未连接，无法启动配液")
            return False
        
        if channel_id not in self._diluters:
            print(f"❌ RS485Wrapper: 通道 {channel_id} 未配置")
            return False
        
        try:
            diluter = self._diluters[channel_id]
            success = diluter.infuse_volume(volume_ul, callback)
            
            if success:
                print(f"✅ RS485Wrapper: 通道 {channel_id} 开始配液 {volume_ul}μL")
            else:
                print(f"❌ RS485Wrapper: 通道 {channel_id} 启动配液失败")
            
            return success
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 启动配液异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_dilution(self, channel_id: int) -> bool:
        """停止配液
        
        Args:
            channel_id: 通道ID（即泵地址）
            
        Returns:
            bool: 是否成功停止
        """
        if channel_id not in self._diluters:
            print(f"❌ RS485Wrapper: 通道 {channel_id} 未配置")
            return False
        
        try:
            diluter = self._diluters[channel_id]
            success = diluter.stop()
            
            if success:
                print(f"✅ RS485Wrapper: 通道 {channel_id} 配液已停止")
            
            return success
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 停止配液异常: {e}")
            return False
    
    def get_dilution_progress(self, channel_id: int) -> dict:
        """获取配液进度
        
        Args:
            channel_id: 通道ID（即泵地址）
            
        Returns:
            dict: 进度信息
                {
                    "state": "idle" | "infusing" | "completed" | "error",
                    "progress": 0-100,
                    "target_volume_ul": float,
                    "infused_volume_ul": float
                }
        """
        if channel_id not in self._diluters:
            return {
                "state": "error",
                "progress": 0.0,
                "target_volume_ul": 0.0,
                "infused_volume_ul": 0.0,
                "error": "通道未配置"
            }
        
        try:
            diluter = self._diluters[channel_id]
            return {
                "state": diluter.state.value,
                "progress": diluter.get_progress(),
                "target_volume_ul": diluter.target_volume_ul,
                "infused_volume_ul": diluter.infused_volume_ul
            }
        except Exception as e:
            return {
                "state": "error",
                "progress": 0.0,
                "target_volume_ul": 0.0,
                "infused_volume_ul": 0.0,
                "error": str(e)
            }
    
    def prepare_dilution(self, channel_id: int, target_conc: float, total_volume_ul: float) -> float:
        """准备配液（计算需要的体积）
        
        Args:
            channel_id: 通道ID（即泵地址）
            target_conc: 目标浓度 (mol/L)
            total_volume_ul: 总体积 (μL)
            
        Returns:
            float: 需要注入的体积 (μL)
        """
        if channel_id not in self._diluters:
            print(f"❌ RS485Wrapper: 通道 {channel_id} 未配置")
            return 0.0
        
        try:
            diluter = self._diluters[channel_id]
            volume = diluter.prepare(target_conc, total_volume_ul)
            print(f"✅ RS485Wrapper: 通道 {channel_id} 需要注入 {volume:.2f}μL")
            return volume
        except Exception as e:
            print(f"❌ RS485Wrapper: 准备配液异常: {e}")
            return 0.0


# 全局单例
_rs485_instance: Optional[RS485Wrapper] = None

def get_rs485_instance() -> RS485Wrapper:
    """获取RS485实例单例"""
    global _rs485_instance
    if _rs485_instance is None:
        _rs485_instance = RS485Wrapper()
        _rs485_instance.set_mock_mode(True)
    return _rs485_instance
