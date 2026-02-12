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
        self._current_port: str = ""  # 当前连接的端口名
        
        # 配液功能
        self._diluters: Dict[int, Diluter] = {}  # 地址 -> Diluter实例
        self._logger = get_logger()  # 获取日志实例
        
        # 冲洗功能
        self._flusher: Optional["Flusher"] = None  # Flusher实例
        
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
            self._current_port = port  # 保存当前端口名以供状态显示
            
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
    
    def run_position_rel(self, address: int, encoder_counts: int, speed: int, 
                         acceleration: int = 2, direction: int = 0) -> bool:
        """位置模式运行 - 相对位移
        
        使用SR_VFOC位置模式，通过编码器计数精确控制泵位移。
        
        Args:
            address: 泵地址 (1-12)
            encoder_counts: 编码器计数（正数正转，负数反转）。16384 counts = 1圈
            speed: 运行速度 RPM (0-1000)
            acceleration: 加速度等级 (0-255, 默认2)
            direction: 0=使用encoder_counts符号判断, 1=强制正转, -1=强制反转
            
        Returns:
            bool: 命令发送是否成功
        """
        if not self.is_connected():
            print(f"❌ RS485Wrapper: 未连接，无法执行位置运动 泵{address}")
            return False
        
        # 已知响应不稳定的泵，始终使用fire_and_forget模式
        RESPONSE_UNSTABLE_PUMPS = [1, 11]
        use_fire_and_forget = address in RESPONSE_UNSTABLE_PUMPS
        
        if use_fire_and_forget:
            print(f"⚠️ RS485Wrapper: 泵 {address} 响应不稳定，使用fire_and_forget模式")
        
        try:
            # 使用 PumpManager 的位置模式方法
            success = self._pump_manager.move_position_rel(
                address, 
                encoder_counts,
                speed,
                acceleration,
                fire_and_forget=use_fire_and_forget
            )
            
            # 更新状态缓存
            dir_str = "正向" if encoder_counts >= 0 else "反向"
            self._pump_states[address] = {
                "address": address,
                "online": True,
                "enabled": True,
                "speed": speed,
                "direction": dir_str,
                "position_mode": True,
                "target_counts": encoder_counts
            }
            
            if success or use_fire_and_forget:
                revs = abs(encoder_counts) / 16384.0
                print(f"✅ RS485Wrapper: 泵 {address} 位置运动已启动 {dir_str} {revs:.2f}圈 @{speed}RPM")
                return True
            else:
                print(f"❌ RS485Wrapper: 泵 {address} 位置运动启动失败")
                return False
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 泵 {address} 位置运动异常 {e}")
            import traceback
            traceback.print_exc()
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

    # ========== 堵转检测与自动恢复 ==========

    def read_pump_fault(self, address: int) -> int | None:
        """读取泵故障状态（0x3E 命令）
        
        返回值:
            0x00 = 无故障
            0x01 = 堵转保护已触发
            None = 通信失败
        """
        if not self.is_connected():
            return None
        try:
            fault = self._pump_manager.read_fault(address)
            if fault is not None and fault != 0:
                print(f"⚠️ RS485Wrapper: 泵 {address} 故障码 0x{fault:02X}")
            return fault
        except TimeoutError:
            print(f"❌ RS485Wrapper: 泵 {address} 读取故障状态超时")
            return None
        except Exception as e:
            print(f"❌ RS485Wrapper: 泵 {address} 读取故障异常 {e}")
            return None

    def clear_pump_stall(self, address: int) -> bool:
        """解除泵堵转保护（0x3D 命令）
        
        Returns:
            bool: 是否成功解除
        """
        if not self.is_connected():
            return False
        try:
            result = self._pump_manager.clear_stall(address)
            if result:
                print(f"✅ RS485Wrapper: 泵 {address} 堵转已解除")
            else:
                print(f"❌ RS485Wrapper: 泵 {address} 堵转解除失败")
            return result
        except Exception as e:
            print(f"❌ RS485Wrapper: 泵 {address} 堵转解除异常 {e}")
            return False

    def check_and_clear_stall(self, address: int) -> bool:
        """检测并尝试清除堵转
        
        Returns:
            True  = 泵正常（无堵转或已成功清除）
            False = 堵转无法清除
        """
        fault = self.read_pump_fault(address)
        if fault is None:
            # 通信失败，视为异常但不一定是堵转
            return True
        if fault == 0:
            return True
        # 有故障 → 尝试清除
        print(f"⚠️ RS485Wrapper: 泵 {address} 检测到故障 0x{fault:02X}，尝试自动清除...")
        return self.clear_pump_stall(address)

    def start_pump_with_stall_guard(
        self,
        address: int,
        direction: str,
        rpm: int,
        max_retries: int = 3,
        stall_check_delay: float = 0.5,
        on_stall_detected: callable = None,
        on_stall_cleared: callable = None,
        on_stall_alarm: callable = None,
    ) -> bool:
        """带堵转保护的泵启动
        
        流程:
        1. 先检查/清除已有堵转
        2. 启动泵
        3. 延迟后检查是否堵转
        4. 如堵转 → 停机 → 清除 → 重试（最多 max_retries 次）
        5. 仍堵转 → 触发告警回调
        
        Args:
            address: 泵地址
            direction: 方向 "FWD"/"REV"
            rpm: 转速
            max_retries: 堵转重试次数
            stall_check_delay: 启动后多久检查堵转 (秒)
            on_stall_detected: 堵转检测回调 fn(address, attempt)
            on_stall_cleared: 堵转清除成功回调 fn(address, attempt)
            on_stall_alarm: 堵转无法恢复告警回调 fn(address)
            
        Returns:
            bool: 泵是否正常运转
        """
        # Step 1: 预检 - 清除残留堵转
        pre_check = self.check_and_clear_stall(address)
        if not pre_check:
            print(f"⚠️ RS485Wrapper: 泵 {address} 启动前堵转清除失败，仍尝试启动")

        for attempt in range(max_retries + 1):
            # Step 2: 启动泵
            if attempt > 0:
                print(f"🔄 RS485Wrapper: 泵 {address} 堵转恢复重试 {attempt}/{max_retries}")
            
            success = self.start_pump(address, direction, rpm)
            if not success:
                print(f"❌ RS485Wrapper: 泵 {address} 启动命令失败")
                return False

            # Step 3: 延迟后检查堵转
            import time
            time.sleep(stall_check_delay)
            
            fault = self.read_pump_fault(address)
            if fault is None or fault == 0:
                # 无堵转，运行正常
                if attempt > 0 and on_stall_cleared:
                    try:
                        on_stall_cleared(address, attempt)
                    except Exception:
                        pass
                return True

            # Step 4: 检测到堵转
            print(f"🚨 RS485Wrapper: 泵 {address} 堵转! (尝试 {attempt + 1}/{max_retries + 1})")
            if on_stall_detected:
                try:
                    on_stall_detected(address, attempt)
                except Exception:
                    pass

            # 停止泵
            self.stop_pump(address)
            time.sleep(0.1)
            
            # 清除堵转
            cleared = self.clear_pump_stall(address)
            if not cleared:
                print(f"❌ RS485Wrapper: 泵 {address} 堵转清除失败")
                # 再尝试一次清除
                time.sleep(0.2)
                self.clear_pump_stall(address)

            if attempt < max_retries:
                time.sleep(0.3)  # 恢复间隔
        
        # Step 5: 所有重试用尽 → 告警
        print(f"🚨🚨 RS485Wrapper: 泵 {address} 堵转无法恢复!!! 已重试 {max_retries} 次")
        if on_stall_alarm:
            try:
                on_stall_alarm(address)
            except Exception:
                pass
        return False

    def batch_check_stall(self, addresses: list = None) -> dict:
        """批量检查多个泵的堵转状态
        
        Args:
            addresses: 要检查的泵地址列表，默认检查1-12
            
        Returns:
            dict: {address: fault_code} 只含有故障的泵
        """
        if addresses is None:
            addresses = list(range(1, 13))
        
        faults = {}
        for addr in addresses:
            fault = self.read_pump_fault(addr)
            if fault is not None and fault != 0:
                faults[addr] = fault
        
        if faults:
            print(f"⚠️ RS485Wrapper: 批量检查发现 {len(faults)} 个泵故障: {faults}")
        return faults
        
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
    
    def configure_dilution_channels(
        self, 
        channels: List[DilutionChannel],
        calibration_data: Optional[Dict[int, Dict[str, float]]] = None
    ) -> bool:
        """配置配液通道
        
        Args:
            channels: 配液通道列表（来自前端配置对话框）
            calibration_data: 校准数据字典 {pump_address: {"ul_per_encoder_count": float}}
            
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
            >>> calibration = {1: {"ul_per_encoder_count": 0.00006}}
            >>> wrapper.configure_dilution_channels(channels, calibration)
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
                    default_direction=channel.direction,
                    tube_diameter_mm=getattr(channel, 'tube_diameter_mm', 1.0)
                )
                
                diluter = Diluter(
                    config=config,
                    pump_manager=self._pump_manager,
                    logger=self._logger,
                    mock_mode=self._mock_mode
                )
                
                # 应用校准数据
                if calibration_data and channel.pump_address in calibration_data:
                    cal = calibration_data[channel.pump_address]
                    if 'ul_per_encoder_count' in cal:
                        diluter.set_calibration(cal['ul_per_encoder_count'])
                        print(f"  ✅ 已应用校准数据: {cal['ul_per_encoder_count']:.8f} μL/count")
                
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
    
    def start_dilution_by_position(
        self, 
        channel_id: int, 
        volume_ul: float,
        speed: int = 100,
        acceleration: int = 2,
        wait_complete: bool = True,
        callback: Optional[Callable] = None
    ) -> bool:
        """使用位置模式开始配液（SR_VFOC推荐）
        
        使用编码器位移精确控制体积，不依赖时间估算。
        
        Args:
            channel_id: 通道ID（即泵地址）
            volume_ul: 体积（微升）
            speed: 转速 RPM (0-1000)
            acceleration: 加速度等级 (0-255)
            wait_complete: 是否等待完成
            callback: 完成回调函数
            
        Returns:
            bool: 是否成功
        """
        if not self.is_connected():
            print(f"❌ RS485Wrapper: 未连接，无法启动位置模式配液")
            return False
        
        if channel_id not in self._diluters:
            print(f"❌ RS485Wrapper: 通道 {channel_id} 未配置")
            return False
        
        try:
            diluter = self._diluters[channel_id]
            success = diluter.infuse_by_position(
                volume_ul=volume_ul,
                speed=speed,
                acceleration=acceleration,
                wait_complete=wait_complete,
                callback=callback
            )
            
            if success:
                print(f"✅ RS485Wrapper: 通道 {channel_id} 位置模式配液完成 {volume_ul:.2f}μL")
            else:
                print(f"❌ RS485Wrapper: 通道 {channel_id} 位置模式配液失败")
            
            return success
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 位置模式配液异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_diluter_calibration(self, channel_id: int, ul_per_encoder_count: float) -> bool:
        """设置配液器校准参数
        
        Args:
            channel_id: 通道ID（即泵地址）
            ul_per_encoder_count: 每编码器计数对应的微升数
            
        Returns:
            bool: 是否成功
        """
        if channel_id not in self._diluters:
            print(f"❌ RS485Wrapper: 通道 {channel_id} 未配置")
            return False
        
        try:
            diluter = self._diluters[channel_id]
            diluter.set_calibration(ul_per_encoder_count)
            print(f"✅ RS485Wrapper: 通道 {channel_id} 校准已设置: {ul_per_encoder_count:.8f} μL/count")
            return True
        except Exception as e:
            print(f"❌ RS485Wrapper: 设置校准异常: {e}")
            return False

    # ========================================
    # 冲洗功能 (Flusher)
    # ========================================
    
    def configure_flush_channels(
        self,
        inlet_address: int,
        transfer_address: int,
        outlet_address: int,
        inlet_rpm: int = 200,
        transfer_rpm: int = 200,
        outlet_rpm: int = 200,
        inlet_duration_s: float = 10.0,
        transfer_duration_s: float = 10.0,
        outlet_duration_s: float = 10.0,
        default_cycles: int = 3
    ) -> bool:
        """配置冲洗通道
        
        Args:
            inlet_address: 进水泵地址 (1-12)
            transfer_address: 移液泵地址 (1-12)
            outlet_address: 出水泵地址 (1-12)
            inlet_rpm: 进水泵转速
            transfer_rpm: 移液泵转速
            outlet_rpm: 出水泵转速
            inlet_duration_s: 进水持续时间（秒）
            transfer_duration_s: 移液持续时间（秒）
            outlet_duration_s: 出水持续时间（秒）
            default_cycles: 默认循环数
            
        Returns:
            bool: 是否配置成功
        """
        if not BACKEND_AVAILABLE:
            print("❌ RS485Wrapper: 后端不可用，无法配置冲洗")
            return False
        
        try:
            from src.echem_sdl.hardware.flusher import (
                Flusher, FlusherConfig, FlusherPumpConfig
            )
            
            config = FlusherConfig(
                inlet=FlusherPumpConfig(
                    address=inlet_address,
                    name="Inlet",
                    rpm=inlet_rpm,
                    direction="FWD",
                    duration_s=inlet_duration_s
                ),
                transfer=FlusherPumpConfig(
                    address=transfer_address,
                    name="Transfer",
                    rpm=transfer_rpm,
                    direction="FWD",
                    duration_s=transfer_duration_s
                ),
                outlet=FlusherPumpConfig(
                    address=outlet_address,
                    name="Outlet",
                    rpm=outlet_rpm,
                    direction="FWD",
                    duration_s=outlet_duration_s
                ),
                default_cycles=default_cycles
            )
            
            self._flusher = Flusher(
                config=config,
                pump_manager=self._pump_manager,
                logger=self._logger,
                mock_mode=self._mock_mode
            )
            
            print(f"✅ RS485Wrapper: 冲洗配置完成 - "
                  f"Inlet:{inlet_address}, Transfer:{transfer_address}, Outlet:{outlet_address}")
            return True
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 冲洗配置失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def configure_flush_from_config(self, flush_channels: List) -> bool:
        """从FlushChannel配置列表配置Flusher
        
        Args:
            flush_channels: FlushChannel列表
            
        Returns:
            bool: 是否配置成功
        """
        inlet = None
        transfer = None
        outlet = None
        
        for ch in flush_channels:
            work_type = getattr(ch, 'work_type', '').lower()
            if work_type == 'inlet':
                inlet = ch
            elif work_type == 'transfer':
                transfer = ch
            elif work_type == 'outlet':
                outlet = ch
        
        if not all([inlet, transfer, outlet]):
            print("❌ RS485Wrapper: 冲洗配置不完整，需要Inlet/Transfer/Outlet三个通道")
            return False
        
        return self.configure_flush_channels(
            inlet_address=inlet.pump_address,
            transfer_address=transfer.pump_address,
            outlet_address=outlet.pump_address,
            inlet_rpm=getattr(inlet, 'rpm', 200),
            transfer_rpm=getattr(transfer, 'rpm', 200),
            outlet_rpm=getattr(outlet, 'rpm', 200),
            inlet_duration_s=getattr(inlet, 'cycle_duration_s', 10.0),
            transfer_duration_s=getattr(transfer, 'cycle_duration_s', 10.0),
            outlet_duration_s=getattr(outlet, 'cycle_duration_s', 10.0)
        )
    
    def start_flush(
        self,
        cycles: Optional[int] = None,
        on_phase_change: Optional[Callable] = None,
        on_cycle_complete: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> bool:
        """开始冲洗循环
        
        Args:
            cycles: 循环次数（可选，默认使用配置值）
            on_phase_change: 阶段变化回调
            on_cycle_complete: 循环完成回调
            on_complete: 全部完成回调
            on_error: 错误回调
            
        Returns:
            bool: 是否成功启动
        """
        if self._flusher is None:
            print("❌ RS485Wrapper: Flusher未配置")
            return False
        
        try:
            # 注册回调
            if on_phase_change:
                self._flusher.on_phase_change(on_phase_change)
            if on_cycle_complete:
                self._flusher.on_cycle_complete(on_cycle_complete)
            if on_complete:
                self._flusher.on_complete(on_complete)
            if on_error:
                self._flusher.on_error(on_error)
            
            # 设置循环数
            if cycles is not None:
                self._flusher.set_cycles(cycles)
            
            return self._flusher.start()
            
        except Exception as e:
            print(f"❌ RS485Wrapper: 启动冲洗失败: {e}")
            return False
    
    def stop_flush(self) -> bool:
        """停止冲洗
        
        Returns:
            bool: 是否成功停止
        """
        if self._flusher is None:
            print("❌ RS485Wrapper: Flusher未配置")
            return False
        
        try:
            return self._flusher.stop()
        except Exception as e:
            print(f"❌ RS485Wrapper: 停止冲洗失败: {e}")
            return False
    
    def pause_flush(self) -> bool:
        """暂停冲洗"""
        if self._flusher is None:
            return False
        return self._flusher.pause()
    
    def resume_flush(self) -> bool:
        """恢复冲洗"""
        if self._flusher is None:
            return False
        return self._flusher.resume()
    
    def start_evacuate(
        self,
        duration_s: Optional[float] = None,
        on_complete: Optional[Callable] = None
    ) -> bool:
        """开始排空操作
        
        Args:
            duration_s: 排空持续时间（秒）
            on_complete: 完成回调
            
        Returns:
            bool: 是否成功启动
        """
        if self._flusher is None:
            print("❌ RS485Wrapper: Flusher未配置")
            return False
        
        try:
            if on_complete:
                self._flusher.on_complete(on_complete)
            return self._flusher.evacuate(duration_s)
        except Exception as e:
            print(f"❌ RS485Wrapper: 启动排空失败: {e}")
            return False
    
    def start_transfer(
        self,
        duration_s: Optional[float] = None,
        forward: bool = True,
        on_complete: Optional[Callable] = None
    ) -> bool:
        """开始移液操作
        
        Args:
            duration_s: 移液持续时间（秒）
            forward: 方向（True=正向）
            on_complete: 完成回调
            
        Returns:
            bool: 是否成功启动
        """
        if self._flusher is None:
            print("❌ RS485Wrapper: Flusher未配置")
            return False
        
        try:
            if on_complete:
                self._flusher.on_complete(on_complete)
            return self._flusher.transfer(duration_s, forward)
        except Exception as e:
            print(f"❌ RS485Wrapper: 启动移液失败: {e}")
            return False
    
    def get_flush_status(self) -> Optional[Dict]:
        """获取冲洗状态
        
        Returns:
            dict: 状态信息，包含 state, phase, current_cycle, total_cycles, progress 等
        """
        if self._flusher is None:
            return None
        return self._flusher.get_status()
    
    def is_flushing(self) -> bool:
        """是否正在冲洗"""
        if self._flusher is None:
            return False
        return self._flusher.is_running
    
    def reset_flusher(self) -> None:
        """重置Flusher状态"""
        if self._flusher:
            self._flusher.reset()


# 全局单例
_rs485_instance: Optional[RS485Wrapper] = None

def get_rs485_instance(force_reload: bool = False) -> RS485Wrapper:
    """获取RS485实例单例
    
    Args:
        force_reload: 强制重新创建实例（用于配置更改后重载）
    
    不再自动连接，需要手动调用 open_port() 连接。
    """
    global _rs485_instance
    if _rs485_instance is None or force_reload:
        if _rs485_instance and force_reload:
            try:
                _rs485_instance.close_port()
            except:
                pass
        
        _rs485_instance = RS485Wrapper()
        
        # 读取系统配置确定模式
        try:
            import json
            from pathlib import Path
            config_path = Path("config/system.json")
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                mock_mode = config.get('mock_mode', True)
                rs485_port = config.get('rs485_port', 'COM3')
                baudrate = config.get('rs485_baudrate', 38400)
            else:
                mock_mode = True
                rs485_port = 'COM3'
                baudrate = 38400
            
        except Exception as e:
            print(f"⚠️ 读取配置失败，使用默认Mock模式: {e}")
            mock_mode = True
            rs485_port = 'COM3'
            baudrate = 38400
        
        _rs485_instance.set_mock_mode(mock_mode)
        
        # 不再自动连接，等待手动连接
        print(f"✅ RS485Wrapper: 实例已创建 (Mock模式: {mock_mode})，请手动连接")
    
    return _rs485_instance
