"""
RS485 Driver Module

RS485 串口通信驱动，负责串口连接、帧收发、设备发现、线程安全。
支持 Mock 模式用于无硬件开发/测试。

参考：
- 原C#项目: D:/AI4S/eChemSDL/eChemSDL/MotorRS485.cs
- 文档: docs/backend/01_RS485_DRIVER.md
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from queue import Queue, Empty

from .rs485_protocol import (
    FrameStreamParser, ParsedFrame,
    build_frame, build_enable_frame, build_speed_frame,
    build_read_encoder_frame, build_read_speed_frame,
    frame_to_hex
)

from ..utils.constants import (
    DEFAULT_BAUDRATE, DEFAULT_TIMEOUT,
    DEFAULT_CMD_INTERVAL_MS, OFFLINE_THRESHOLD_SEC,
    SCAN_ADDRESS_RANGE, get_cmd_name, get_expected_response_length,
    CMD_READ_RUN_STATUS, CMD_ENABLE, CMD_SPEED, CMD_POSITION,
    CMD_READ_ENCODER, CMD_READ_SPEED, RX_HEADER
)
from ..utils.errors import (
    SerialPortError, DeviceNotFoundError,
    CommunicationTimeoutError
)

try:
    import serial  # type: ignore
    import serial.tools.list_ports  # type: ignore
    SERIAL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    serial = None  # type: ignore
    SERIAL_AVAILABLE = False


# ============================================================================
# Mock Serial Port (用于测试)
# ============================================================================

class MockSerial:
    """模拟串口，用于无硬件测试"""
    
    def __init__(self):
        self._rx_buffer = bytearray()  # 累积接收缓冲区
        self._is_open = False
        self.port = ""
        self.baudrate = 38400
        self.timeout = 0.5
    
    def open(self) -> None:
        self._is_open = True
        print(f"[Mock RS485] Opened {self.port} @ {self.baudrate}")
    
    def close(self) -> None:
        self._is_open = False
        self._rx_buffer.clear()
        print(f"[Mock RS485] Closed {self.port}")
    
    @property
    def is_open(self) -> bool:
        return self._is_open
    
    @property
    def in_waiting(self) -> int:
        """返回缓冲区中的字节数"""
        return len(self._rx_buffer)
    
    def write(self, data: bytes) -> int:
        """写入数据并生成模拟响应"""
        if not self._is_open:
            raise SerialPortError("Port is not open")
        
        print(f"[Mock RS485] TX: {frame_to_hex(data)}")
        
        # 生成模拟响应并追加到缓冲区
        response = self._generate_mock_response(data)
        if response:
            print(f"[Mock RS485] RX (mock): {frame_to_hex(response)}")
            self._rx_buffer.extend(response)
        
        return len(data)
    
    def read(self, size: int) -> bytes:
        """读取数据"""
        if not self._rx_buffer:
            return b''
        
        # 从缓冲区读取指定字节数
        data = bytes(self._rx_buffer[:size])
        self._rx_buffer = self._rx_buffer[size:]
        return data
    
    def _generate_mock_response(self, request: bytes) -> Optional[bytes]:
        """生成模拟响应"""
        if len(request) < 4:
            return None
        
        addr = request[1]
        cmd = request[2]
        payload = request[3:-1] if len(request) > 4 else b''
        
        # 根据命令生成不同的响应
        from ..utils.constants import (
            CMD_ENABLE, CMD_SPEED, CMD_POSITION,
            CMD_READ_ENCODER, CMD_READ_SPEED, CMD_READ_RUN_STATUS,
            CMD_READ_ENABLE, CMD_READ_IO, CMD_READ_VERSION,
            CMD_READ_FAULT, CMD_CLEAR_STALL,
            RX_HEADER
        )
        
        if cmd == CMD_ENABLE:
            # 使能确认: 返回设置的状态值
            # 请求: FA addr F3 <enable_byte> checksum
            # 响应: FB addr F3 <enable_byte> checksum
            enable_byte = payload[0] if payload else 0x01
            response = bytes([RX_HEADER, addr, cmd, enable_byte])
        elif cmd == CMD_SPEED:
            # 速度设置确认
            response = bytes([RX_HEADER, addr, cmd, 0x01])
        elif cmd == CMD_POSITION:
            # 位置设置确认
            response = bytes([RX_HEADER, addr, cmd, 0x01])
        elif cmd == CMD_READ_RUN_STATUS:
            # 读取运行状态: FB addr F1 01 checksum (运行中)
            response = bytes([RX_HEADER, addr, cmd, 0x01])
        elif cmd == CMD_READ_ENABLE:
            # 读取使能状态: FB addr 3A 01 checksum (已使能)
            response = bytes([RX_HEADER, addr, cmd, 0x01])
        elif cmd == CMD_READ_IO:
            # 读取IO状态: FB addr 34 00 checksum
            response = bytes([RX_HEADER, addr, cmd, 0x00])
        elif cmd == CMD_READ_ENCODER:
            # 读取编码器: FB addr 30 00 00 40 00 checksum (16384分度)
            response = bytes([RX_HEADER, addr, cmd, 0x00, 0x00, 0x40, 0x00])
        elif cmd == CMD_READ_SPEED:
            # 读取速度: FB addr 32 00 64 checksum (100 RPM)
            response = bytes([RX_HEADER, addr, cmd, 0x00, 0x64])
        elif cmd == CMD_READ_VERSION:
            # 读取版本: FB addr 40 01 02 checksum (版本1.2)
            response = bytes([RX_HEADER, addr, cmd, 0x01, 0x02])
        elif cmd == CMD_READ_FAULT:
            # 读取故障状态: FB addr 3E <fault_code> checksum
            # 0x00 = 无故障, 0x01 = 堵转
            # Mock 可通过 self._mock_stall_flags 注入堵转
            fault_byte = getattr(self, '_mock_stall_flags', {}).get(addr, 0x00)
            response = bytes([RX_HEADER, addr, cmd, fault_byte])
        elif cmd == CMD_CLEAR_STALL:
            # 解除堵转确认: FB addr 3D 01 checksum (成功)
            # 同时清除模拟堵转标志
            if hasattr(self, '_mock_stall_flags'):
                self._mock_stall_flags.pop(addr, None)
            response = bytes([RX_HEADER, addr, cmd, 0x01])
        else:
            # 默认ACK（单字节响应）
            response = bytes([RX_HEADER, addr, cmd, 0x01])
        
        # 计算校验和
        from .rs485_protocol import checksum
        chk = checksum(response)
        return response + bytes([chk])


# ============================================================================
# RS485 Driver
# ============================================================================

class RS485Driver:
    """RS485 串口通信驱动
    
    提供线程安全的 RS485 帧收发、设备发现、回调路由。
    支持 Mock 模式用于无硬件开发。
    
    Attributes:
        port: 串口端口名 (如 'COM1')
        baudrate: 波特率 (默认 38400)
        timeout: 读取超时秒数
        mock_mode: 是否为模拟模式
        is_open: 串口是否已打开
        strict_checksum: 是否严格验证校验和
    
    Example:
        >>> driver = RS485Driver(port='COM3', baudrate=38400)
        >>> driver.set_callback(my_callback)
        >>> driver.open()
        >>> driver.send_frame(addr=1, cmd=0xF3, data=b'\\x00\\x01')
        >>> driver.close()
    """
    
    def __init__(
        self,
        port: str = "COM1",
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT,
        logger: Optional[Any] = None,
        mock_mode: bool = False,
        strict_checksum: bool = False  # 默认宽松模式以兼容更多设备
    ) -> None:
        """初始化 RS485 驱动
        
        Args:
            port: 串口端口名
            baudrate: 波特率，默认 38400 (与原C#一致)
            timeout: 读取超时秒数
            logger: 日志服务实例
            mock_mode: 是否启用模拟模式
            strict_checksum: 是否严格验证校验和 (默认False以兼容校验和有问题的设备)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.mock_mode = mock_mode
        self._logger = logger
        
        # 串口对象
        self._serial: Optional[Any] = None
        
        # 线程同步
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._reader_thread: Optional[threading.Thread] = None
        
        # 帧解析器（使用宽松模式以兼容校验和有问题的设备）
        self._parser = FrameStreamParser(strict_checksum=strict_checksum)
        
        # 回调函数
        self._frame_callback: Optional[Callable[[int, int, bytes], None]] = None
        
        # 通信状态
        self._last_comm_time = datetime.now()
        self._online_devices: Dict[int, datetime] = {}
    
    @property
    def is_open(self) -> bool:
        """串口是否打开"""
        if self._serial is None:
            return False
        return getattr(self._serial, 'is_open', False)
    
    @property
    def last_comm_time(self) -> datetime:
        """最后通信时间"""
        return self._last_comm_time
    
    @staticmethod
    def list_ports() -> List[str]:
        """列出可用串口
        
        Returns:
            list: 可用串口列表
        """
        if not SERIAL_AVAILABLE or serial is None:
            return []
        try:
            return [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            return []
    
    def open(self) -> bool:
        """打开串口并启动读取线程
        
        Returns:
            bool: 打开是否成功
            
        Raises:
            SerialPortError: 串口打开失败时抛出
            
        Note:
            Mock 模式下始终返回 True，不实际打开串口
        """
        if self.is_open:
            self._log_info(f"Port {self.port} already open")
            return True
        
        try:
            if self.mock_mode:
                self._serial = MockSerial()
                self._serial.port = self.port
                self._serial.baudrate = self.baudrate
                self._serial.timeout = self.timeout
                self._serial.open()
            else:
                if not SERIAL_AVAILABLE or serial is None:
                    raise SerialPortError("pyserial is required but not available")
                
                self._serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=8,
                    stopbits=2,  # 原C#项目: StopBits.Two
                    parity='N',  # 无校验
                    timeout=self.timeout
                )
            
            # 清空缓冲区
            self._parser.clear()
            
            # 启动读取线程
            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._read_loop,
                name="RS485-Reader",
                daemon=True
            )
            self._reader_thread.start()
            
            self._log_info(f"Opened RS485 port: {self.port} @ {self.baudrate} bps")
            return True
            
        except Exception as e:
            self._log_error(f"Failed to open port {self.port}: {e}")
            raise SerialPortError(f"Failed to open port {self.port}: {e}")
    
    def close(self) -> None:
        """关闭串口并停止读取线程
        
        确保读取线程正确退出，释放串口资源。
        """
        if not self.is_open:
            return
        
        # 停止读取线程
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None
        
        # 关闭串口
        if self._serial:
            try:
                self._serial.close()
            except Exception as e:
                self._log_error(f"Error closing port: {e}")
        
        self._serial = None
        self._log_info(f"Closed RS485 port: {self.port}")
    
    def set_callback(
        self,
        callback: Callable[[int, int, bytes], None]
    ) -> None:
        """设置帧接收回调
        
        Args:
            callback: 回调函数，参数为 (addr, cmd, payload)
            
        Note:
            回调在读取线程中执行，若需更新 UI 请使用信号
        """
        self._frame_callback = callback
    
    def send_frame(
        self,
        addr: int,
        cmd: int,
        data: bytes = b""
    ) -> bool:
        """发送 RS485 帧
        
        Args:
            addr: 设备地址 (1-255)
            cmd: 命令字节
            data: 数据载荷
            
        Returns:
            bool: 发送是否成功
            
        Thread Safety:
            此方法是线程安全的，使用锁保护写操作
        """
        if not self.is_open or not self._serial:
            self._log_warning("Cannot send: port not open")
            return False
        
        try:
            frame = build_frame(addr, cmd, data)
            
            with self._lock:
                self._serial.write(frame)
                self._last_comm_time = datetime.now()
                
                # 添加命令间隔 (原C#项目: 25ms)
                time.sleep(DEFAULT_CMD_INTERVAL_MS / 1000.0)
            
            self._log_debug(
                f"TX -> Addr={addr} Cmd={get_cmd_name(cmd)} "
                f"Frame={frame_to_hex(frame)}"
            )
            return True
            
        except Exception as e:
            self._log_error(f"Send frame error: {e}")
            return False
    
    def discover_devices(
        self,
        addresses: Optional[List[int]] = None,
        timeout_per_addr: float = 0.1
    ) -> List[int]:
        """扫描在线设备地址
        
        对于响应异常但通常能工作的泵（如泵1、泵11），会特殊处理：
        - 即使扫描不到响应，也假设在线（因为它们能接收和执行命令）
        
        Args:
            addresses: 要扫描的地址列表，默认 1-12
            timeout_per_addr: 每个地址的超时秒数
            
        Returns:
            List[int]: 在线设备地址列表
        """
        if addresses is None:
            addresses = list(SCAN_ADDRESS_RANGE)
        
        # 已知响应异常但通常能工作的泵列表
        RESPONSE_UNSTABLE_PUMPS = [1, 11]
        
        self._log_info(f"Scanning devices at addresses: {addresses}")
        found_devices: List[int] = []
        
        # 临时收集响应
        responses: Dict[int, bool] = {addr: False for addr in addresses}
        
        def temp_callback(addr: int, cmd: int, payload: bytes):
            if addr in responses:
                responses[addr] = True
                self._log_debug(f"Device {addr} responded")
        
        # 保存原回调
        old_callback = self._frame_callback
        self._frame_callback = temp_callback
        
        try:
            # 发送所有查询命令
            for addr in addresses:
                self.send_frame(addr, CMD_READ_RUN_STATUS)
                time.sleep(0.05)  # 命令间隔
            
            # 等待所有响应（给足够时间让读取线程处理）
            wait_time = max(0.5, len(addresses) * timeout_per_addr)
            self._log_debug(f"Waiting {wait_time}s for responses...")
            time.sleep(wait_time)
            
            # 收集结果：正常响应的泵 + 已知问题泵
            for addr in addresses:
                if responses[addr]:
                    found_devices.append(addr)
                    self._log_debug(f"Device {addr} found (响应正常)")
                elif addr in RESPONSE_UNSTABLE_PUMPS:
                    found_devices.append(addr)
                    self._log_debug(f"Device {addr} found (已知响应异常但可控制)")
            
        finally:
            # 恢复原回调
            self._frame_callback = old_callback
        
        self._log_info(f"Found devices: {found_devices}")
        return found_devices
    
    def run_speed(
        self,
        addr: int,
        rpm: int,
        forward: bool = True
    ) -> bool:
        """设置电机转速
        
        Args:
            addr: 设备地址
            rpm: 转速 (0-3000)
            forward: 是否正转 (True=正转, False=反转)
            
        Returns:
            bool: 命令发送是否成功
        """
        frame = build_speed_frame(addr, rpm, forward)
        if not self.is_open or not self._serial:
            return False
        
        try:
            with self._lock:
                self._serial.write(frame)
                self._last_comm_time = datetime.now()
                time.sleep(DEFAULT_CMD_INTERVAL_MS / 1000.0)
            
            self._log_debug(f"RUN_SPEED: Addr={addr}, RPM={rpm}, FWD={forward}")
            return True
        except Exception as e:
            self._log_error(f"Run speed error: {e}")
            return False
    
    def enable_motor(self, addr: int, enable: bool = True) -> bool:
        """使能/禁用电机
        
        Args:
            addr: 设备地址
            enable: 是否使能
            
        Returns:
            bool: 命令发送是否成功
        """
        frame = build_enable_frame(addr, enable)
        if not self.is_open or not self._serial:
            return False
        
        try:
            with self._lock:
                self._serial.write(frame)
                self._last_comm_time = datetime.now()
                time.sleep(DEFAULT_CMD_INTERVAL_MS / 1000.0)
            
            self._log_debug(f"ENABLE_MOTOR: Addr={addr}, Enable={enable}")
            return True
        except Exception as e:
            self._log_error(f"Enable motor error: {e}")
            return False
    
    def _read_loop(self) -> None:
        """读取线程主循环
        
        持续读取串口数据，进行帧切分、校验、回调分发。
        """
        self._log_info("Read loop started")
        
        while not self._stop_event.is_set():
            try:
                if not self._serial or not self.is_open:
                    break
                
                # 检查是否有数据
                waiting = getattr(self._serial, 'in_waiting', 0)
                if waiting > 0:
                    self._log_debug(f"Reading {waiting} bytes from buffer...")
                    data = self._serial.read(waiting)
                    if data:
                        self._log_debug(f"Read {len(data)} bytes: {frame_to_hex(data)}")
                        self._process_rx_data(data)
                else:
                    time.sleep(0.01)  # 避免空轮询
                    
            except Exception as e:
                self._log_error(f"Read loop error: {e}")
                time.sleep(0.1)
        
        self._log_info("Read loop stopped")
    
    def _process_rx_data(self, data: bytes) -> None:
        """处理接收到的数据
        
        Args:
            data: 接收到的原始数据
        """
        # 更新通信时间
        self._last_comm_time = datetime.now()
        
        # 解析帧
        frames = self._parser.push(data)
        
        self._log_debug(f"Parsed {len(frames)} frames from {len(data)} bytes")
        
        for frame in frames:
            self._log_debug(
                f"RX <- Addr={frame.addr} Cmd={get_cmd_name(frame.cmd)} "
                f"Payload={frame.payload.hex()}"
            )
            
            # 更新设备在线状态
            self._online_devices[frame.addr] = datetime.now()
            
            # 调用回调
            if self._frame_callback:
                try:
                    self._log_debug(f"Calling callback for addr={frame.addr}")
                    self._frame_callback(frame.addr, frame.cmd, frame.payload)
                except Exception as e:
                    self._log_error(f"Callback error: {e}")
    
    # ========================================================================
    # 日志方法
    # ========================================================================
    
    def _log_debug(self, msg: str) -> None:
        if self._logger and hasattr(self._logger, 'debug'):
            self._logger.debug(f"[RS485] {msg}")
        elif not self.mock_mode:
            pass  # 静默
    
    def _log_info(self, msg: str) -> None:
        if self._logger and hasattr(self._logger, 'info'):
            self._logger.info(f"[RS485] {msg}")
        else:
            print(f"[RS485 INFO] {msg}")
    
    def _log_warning(self, msg: str) -> None:
        if self._logger and hasattr(self._logger, 'warning'):
            self._logger.warning(f"[RS485] {msg}")
        else:
            print(f"[RS485 WARNING] {msg}")
    
    def _log_error(self, msg: str) -> None:
        if self._logger and hasattr(self._logger, 'error'):
            self._logger.error(f"[RS485] {msg}")
        else:
            print(f"[RS485 ERROR] {msg}")
    
    # ========================================================================
    # 上下文管理器支持
    # ========================================================================
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def __del__(self):
        """析构时自动关闭"""
        try:
            self.close()
        except:
            pass
