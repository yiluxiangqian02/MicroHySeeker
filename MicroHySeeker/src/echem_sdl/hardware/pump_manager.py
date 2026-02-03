"""High-level pump communications on top of RS485Driver."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

from ..services.logger import LoggerService
from ..utils.constants import (
    CMD_ENABLE,
    CMD_READ_ENABLE,
    CMD_READ_FAULT,
    CMD_READ_RUN_STATUS,
    CMD_READ_SPEED,
    CMD_SPEED
)
from .rs485_driver import RS485Driver
from .rs485_protocol import (
    ParsedFrame,
    build_frame,
)


@dataclass(slots=True)
class PumpState:
    address: int
    online: bool = False
    enabled: bool | None = None
    speed: int | None = None
    fault: int | None = None
    last_seen: datetime | None = None
    last_cmd: int | None = None
    note: str = ""


@dataclass(slots=True)
class _PendingRequest:
    event: threading.Event
    frame: ParsedFrame | None = None


class PumpManager:
    """Coordinates requests/responses for pumps 1-12.

    - Uses a single outstanding request lock (RS485 bus)
    - Supports synchronous request/response (blocking)
    - Optional background scan loop for polling state
    """

    def __init__(
        self,
        driver: RS485Driver | None = None,
        logger: LoggerService | None = None,
        timeout_s: float = 0.6,
        max_failures: int = 3,
    ) -> None:
        self._logger = logger
        self.driver = driver or RS485Driver(logger=logger)
        self.timeout_s = float(timeout_s)
        self.max_failures = int(max_failures)

        self._request_lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending: dict[tuple[int, int], _PendingRequest] = {}

        self._states_lock = threading.RLock()
        self._states: dict[int, PumpState] = {addr: PumpState(addr) for addr in range(1, 13)}
        self._failures: dict[int, int] = {addr: 0 for addr in range(1, 13)}

        self._state_handlers: list[callable[[PumpState], None]] = []
        self._scan_stop = threading.Event()
        self._scan_thread: threading.Thread | None = None

        self.driver.on_frame(self._on_frame)
        self.driver.on_error(self._on_error)

    def on_state(self, handler: callable[[PumpState], None]) -> None:
        self._state_handlers.append(handler)

    def connect(self, port: str, baudrate: int, timeout: float = 0.1) -> None:
        self.driver.open(port=port, baudrate=baudrate, timeout=timeout)

    def disconnect(self) -> None:
        self.stop_scan()
        self.driver.close()

    def get_state(self, addr: int) -> PumpState:
        with self._states_lock:
            state = self._states.get(addr)
            if state is None:
                state = PumpState(addr)
                self._states[addr] = state
            return replace(state)

    def request(
        self, 
        addr: int, 
        cmd: int, 
        payload: bytes = b"", 
        timeout_s: float | None = None,
        retries: int = 3
    ) -> ParsedFrame:
        """发送命令并等待响应
        
        Args:
            addr: 设备地址 (1-255)
            cmd: 命令字节
            payload: 数据载荷
            timeout_s: 超时时间（秒）
            retries: 重试次数（针对通信不稳定的设备，如泵1）
            
        Returns:
            ParsedFrame: 响应帧
            
        Raises:
            TimeoutError: 所有重试都超时
        """
        if addr < 1 or addr > 255:
            raise ValueError("addr must be 1..255")

        timeout = self.timeout_s if timeout_s is None else float(timeout_s)
        key = (addr, cmd)
        last_error = None

        for attempt in range(retries):
            with self._request_lock:
                pending = _PendingRequest(event=threading.Event())
                with self._pending_lock:
                    self._pending[key] = pending

                try:
                    self.driver.write(build_frame(addr, cmd, payload))
                except Exception as e:
                    with self._pending_lock:
                        self._pending.pop(key, None)
                    last_error = e
                    continue

                ok = pending.event.wait(timeout=timeout)
                with self._pending_lock:
                    self._pending.pop(key, None)

                if ok and pending.frame is not None:
                    self._note_response(pending.frame)
                    return pending.frame
                
                last_error = TimeoutError(f"pump 0x{addr:02X} cmd 0x{cmd:02X} timeout")
                
                # 如果不是最后一次尝试，记录重试日志
                if attempt < retries - 1 and self._logger:
                    self._logger.debug(f"泵 {addr} 通信重试 {attempt + 1}/{retries}")
                    time.sleep(0.05)  # 重试间隔

        # 所有重试都失败
        self._note_timeout(addr, cmd)
        raise last_error or TimeoutError(f"pump 0x{addr:02X} cmd 0x{cmd:02X} timeout")

    def read_enable(self, addr: int) -> bool | None:
        frame = self.request(addr, CMD_READ_ENABLE)
        return self._parse_enable(frame)

    def read_speed(self, addr: int) -> int | None:
        frame = self.request(addr, CMD_READ_SPEED)
        return self._parse_speed(frame)

    def read_fault(self, addr: int) -> int | None:
        frame = self.request(addr, CMD_READ_FAULT)
        return self._parse_fault(frame)

    def set_enable(self, addr: int, enable: bool) -> bool | None:
        payload = bytes([0x01 if enable else 0x00])
        frame = self.request(addr, CMD_ENABLE, payload=payload)
        return self._parse_enable(frame)

    def set_speed(
        self,
        addr: int,
        rpm: int,
        direction: Literal["forward", "reverse"] = "forward",
        ramp: int = 0x10,
    ) -> None:
        if rpm < 0 or rpm > 3000:
            raise ValueError("rpm must be 0..3000")

        if rpm == 0:
            payload = bytes([0x00, 0x00, ramp & 0xFF])
        else:
            speed_bytes = int(rpm).to_bytes(2, "little", signed=False)
            high = speed_bytes[1]
            if direction == "forward":
                high |= 0x80
            payload = bytes([high & 0xFF, speed_bytes[0] & 0xFF, ramp & 0xFF])

        self.request(addr, CMD_SPEED, payload=payload)

    def start_scan(
        self,
        addresses: list[int] | None = None,
        poll_interval_s: float = 0.02,
        commands: tuple[int, ...] = (CMD_READ_ENABLE, CMD_READ_SPEED, CMD_READ_FAULT),
    ) -> None:
        self.stop_scan()
        addrs = addresses or list(range(1, 13))
        self._scan_stop.clear()
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            args=(addrs, float(poll_interval_s), commands),
            daemon=True,
        )
        self._scan_thread.start()

    def stop_scan(self) -> None:
        self._scan_stop.set()
        if self._scan_thread is not None:
            self._scan_thread.join(timeout=1.0)
            self._scan_thread = None

    def _scan_loop(self, addresses: list[int], poll_interval_s: float, commands: tuple[int, ...]) -> None:
        for addr in self._failures:
            self._failures[addr] = 0
        while not self._scan_stop.is_set():
            for addr in addresses:
                if self._scan_stop.is_set():
                    return
                for cmd in commands:
                    if self._scan_stop.is_set():
                        return
                    try:
                        self.request(addr, cmd)
                    except TimeoutError:
                        pass
                    time.sleep(poll_interval_s)

    def _on_frame(self, frame: ParsedFrame) -> None:
        key = (frame.addr, frame.cmd)
        with self._pending_lock:
            pending = self._pending.get(key)
            if pending is not None:
                pending.frame = frame
                pending.event.set()

        with self._states_lock:
            state = self._states.get(frame.addr)
            if state is None:
                state = PumpState(frame.addr)
                self._states[frame.addr] = state

            state.online = True
            state.last_seen = datetime.now()
            state.last_cmd = frame.cmd

            if frame.cmd in (CMD_READ_ENABLE, CMD_ENABLE):
                state.enabled = self._parse_enable(frame)
            elif frame.cmd == CMD_READ_SPEED:
                state.speed = self._parse_speed(frame)
            elif frame.cmd == CMD_READ_FAULT:
                state.fault = self._parse_fault(frame)

            self._failures[frame.addr] = 0

            snapshot = replace(state)

        for handler in list(self._state_handlers):
            try:
                handler(snapshot)
            except Exception:
                pass

    def _on_error(self, exc: BaseException) -> None:
        if self._logger is not None:
            self._logger.error("rs485 error")
            self._logger.exception("rs485 error", exc=exc)

    def _note_timeout(self, addr: int, cmd: int) -> None:
        with self._states_lock:
            failures = self._failures.get(addr, 0) + 1
            self._failures[addr] = failures
            state = self._states.get(addr)
            if state is None:
                state = PumpState(addr)
                self._states[addr] = state
            state.last_cmd = cmd
            if failures >= self.max_failures:
                state.online = False
                state.note = f"timeout x{failures}"
                snapshot = replace(state)
            else:
                return

        for handler in list(self._state_handlers):
            try:
                handler(snapshot)
            except Exception:
                pass

    def _note_response(self, frame: ParsedFrame) -> None:
        if self._logger is not None:
            self._logger.debug(
                f"pump rx addr=0x{frame.addr:02X} cmd=0x{frame.cmd:02X} payload={frame.payload.hex(' ')}"
            )

    @staticmethod
    def _parse_enable(frame: ParsedFrame) -> bool | None:
        return (frame.payload[0] == 0x01) if frame.payload else None

    @staticmethod
    def _parse_speed(frame: ParsedFrame) -> int | None:
        if len(frame.payload) < 2:
            return None
        return int.from_bytes(frame.payload[:2], "big", signed=True)

    @staticmethod
    def _parse_fault(frame: ParsedFrame) -> int | None:
        return frame.payload[0] if frame.payload else None

    # ==================== 便捷方法（简化前端调用）====================

    def start_pump(self, addr: int, direction: str, rpm: int, fire_and_forget: bool = False) -> bool:
        """便捷方法：启动泵
        
        组合使能和设置速度操作，简化前端调用。
        
        Args:
            addr: 泵地址 (1-12)
            direction: 方向 "FWD"/"forward" 或 "REV"/"reverse"
            rpm: 转速 (0-3000)
            fire_and_forget: 如果True，发送命令后不等待响应确认
                            适用于响应不稳定的设备（如泵1）
            
        Returns:
            bool: 是否成功（fire_and_forget模式下始终返回True）
            
        Example:
            >>> manager.start_pump(1, "FWD", 120)
            True
        """
        dir_flag = "forward" if direction.upper() in ("FWD", "FORWARD") else "reverse"
        
        if fire_and_forget:
            # 发送命令但不等待确认（用于响应不稳定的设备）
            try:
                if self._logger:
                    self._logger.info(f"启动泵 {addr}: {direction} {rpm}RPM (fire_and_forget)")
                
                # 发送使能命令
                payload = bytes([0x01])
                self.driver.send_frame(addr, CMD_ENABLE, payload)
                time.sleep(0.02)
                
                # 发送速度命令
                if rpm == 0:
                    speed_payload = bytes([0x00, 0x00, 0x10])
                else:
                    speed_bytes = int(rpm).to_bytes(2, "little", signed=False)
                    high = speed_bytes[1]
                    if dir_flag == "forward":
                        high |= 0x80
                    speed_payload = bytes([high & 0xFF, speed_bytes[0] & 0xFF, 0x10])
                
                self.driver.send_frame(addr, CMD_SPEED, speed_payload)
                
                if self._logger:
                    self._logger.info(f"泵 {addr}: 已发送启动命令")
                return True
            except Exception as e:
                if self._logger:
                    self._logger.debug(f"泵 {addr}: fire_and_forget 发送异常 - {e}")
                return True  # 即使异常也返回True
        
        try:
            if self._logger:
                self._logger.info(f"启动泵 {addr}: {direction} {rpm}RPM")
            
            # 1. 使能电机
            if self._logger:
                self._logger.debug(f"泵 {addr}: 发送使能命令...")
            
            enable_result = self.set_enable(addr, True)
            
            if self._logger:
                self._logger.debug(f"泵 {addr}: 使能结果 = {enable_result}")
            
            # enable_result 为 True 表示成功使能
            if enable_result is None:
                if self._logger:
                    self._logger.error(f"泵 {addr}: 使能无响应")
                return False
            
            # 2. 设置速度和方向
            if self._logger:
                self._logger.debug(f"泵 {addr}: 设置速度 {rpm}RPM {direction}...")
            
            self.set_speed(addr, rpm, dir_flag)
            
            if self._logger:
                self._logger.info(f"泵 {addr}: 启动成功")
            
            return True
            
        except TimeoutError as e:
            if self._logger:
                self._logger.error(f"泵 {addr}: 通信超时 - {e}")
            return False
        except Exception as e:
            if self._logger:
                self._logger.error(f"泵 {addr}: 启动失败 - {e}")
            import traceback
            if self._logger:
                self._logger.debug(traceback.format_exc())
            return False
    
    def stop_pump(self, addr: int, fire_and_forget: bool = False) -> bool:
        """便捷方法：停止泵
        
        先停止转动（设速度为0），再禁用电机。
        
        Args:
            addr: 泵地址 (1-12)
            fire_and_forget: 如果True，发送命令后不等待响应确认
                            适用于响应不稳定的设备（如泵1）
            
        Returns:
            bool: 是否成功（fire_and_forget模式下始终返回True）
            
        Example:
            >>> manager.stop_pump(1)
            True
        """
        if fire_and_forget:
            # 发送命令但不等待确认（用于快速关闭或响应不稳定的设备）
            try:
                if self._logger:
                    self._logger.debug(f"停止泵 {addr} (fire_and_forget)")
                # 直接发送停止命令，不等待响应
                payload = bytes([0x00, 0x00, 0x10])  # 速度=0
                self.driver.write(build_frame(addr, CMD_SPEED, payload))
                time.sleep(0.02)  # 短暂延迟
                # 发送禁用命令
                payload = bytes([0x00])
                self.driver.write(build_frame(addr, CMD_ENABLE, payload))
                return True
            except:
                return True  # 即使失败也返回True，不阻塞
                
        try:
            if self._logger:
                self._logger.info(f"停止泵 {addr}")
            
            # 1. 停止转动（速度设为0）
            if self._logger:
                self._logger.debug(f"泵 {addr}: 设置速度为0...")
            
            self.set_speed(addr, 0, "forward")
            
            # 2. 禁用电机
            if self._logger:
                self._logger.debug(f"泵 {addr}: 禁用电机...")
            
            disable_result = self.set_enable(addr, False)
            
            if self._logger:
                self._logger.debug(f"泵 {addr}: 禁用结果 = {disable_result}")
            
            # 返回True表示成功（enabled应该是False表示禁用成功）
            success = disable_result is not None and disable_result == False
            
            if self._logger:
                if success:
                    self._logger.info(f"泵 {addr}: 停止成功")
                else:
                    self._logger.warning(f"泵 {addr}: 停止可能未完全成功")
            
            return success
            
        except TimeoutError as e:
            if self._logger:
                self._logger.error(f"泵 {addr}: 通信超时 - {e}")
            return False
        except Exception as e:
            if self._logger:
                self._logger.error(f"泵 {addr}: 停止失败 - {e}")
            return False
    
    def scan_devices(self, addresses: list[int] | None = None, timeout_per_addr: float = 0.3, retries: int = 5) -> list[int]:
        """扫描在线设备
        
        批量扫描指定地址的泵，返回在线的泵地址列表。
        使用速度命令(0xF6)发送速度0来探测，这是最可靠的方法。
        
        针对通信不稳定的设备（如泵1、泵11），会进行特殊处理：
        - 多次重试
        - 如果重试失败，但设备在已知问题列表中，仍然假设在线
        
        Args:
            addresses: 要扫描的地址列表，默认 1-12
            timeout_per_addr: 每个地址的超时时间（秒）
            retries: 每个地址的重试次数（默认5次，以处理不稳定设备）
            
        Returns:
            list[int]: 在线泵的地址列表
            
        Example:
            >>> manager.scan_devices()
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        """
        if addresses is None:
            addresses = list(range(1, 13))
        
        # 已知响应异常但通常能工作的泵列表
        # 这些泵即使扫描不到响应，也假设在线（因为它们能接收和执行命令）
        RESPONSE_UNSTABLE_PUMPS = [1, 11]
        
        online_pumps = []
        
        for addr in addresses:
            is_detected = False
            
            try:
                # 使用速度命令 (0xF6) 发送速度0来探测设备
                # 这与 MKS 软件使用的方法一致，更可靠
                # payload: [speed_hi, speed_lo, acceleration]
                payload = bytes([0x00, 0x00, 0x10])  # 速度=0, 加速度=0x10
                # 使用较多重试次数以处理通信不稳定的设备（如泵1）
                frame = self.request(addr, CMD_SPEED, payload=payload, timeout_s=timeout_per_addr, retries=retries)
                if frame is not None:
                    is_detected = True
                    if self._logger:
                        self._logger.debug(f"泵 {addr} 在线 (响应正常)")
                        
            except TimeoutError:
                if self._logger:
                    self._logger.debug(f"泵 {addr} 扫描超时 (经 {retries} 次重试)")
            except Exception as e:
                if self._logger:
                    self._logger.debug(f"泵 {addr} 检测异常: {e}")
            
            # 如果正常检测到了，或者是已知的响应异常但能工作的泵，都认为在线
            if is_detected or addr in RESPONSE_UNSTABLE_PUMPS:
                online_pumps.append(addr)
                if not is_detected and addr in RESPONSE_UNSTABLE_PUMPS:
                    if self._logger:
                        self._logger.debug(f"泵 {addr} 在线 (已知响应异常但可控制)")
        
        if self._logger:
            self._logger.info(f"扫描完成，在线泵: {online_pumps}")
        
        return online_pumps
    
    def stop_all(self, addresses: list[int] | None = None, fire_and_forget: bool = True) -> int:
        """停止所有泵
        
        Args:
            addresses: 要停止的地址列表，默认 1-12
            fire_and_forget: 如果True，快速发送停止命令不等待响应
                            用于快速关闭窗口场景
            
        Returns:
            int: 发送停止命令的泵数量
        """
        if addresses is None:
            addresses = list(range(1, 13))
        
        success_count = 0
        for addr in addresses:
            try:
                if self.stop_pump(addr, fire_and_forget=fire_and_forget):
                    success_count += 1
            except:
                continue
        
        if self._logger:
            self._logger.info(f"已发送停止命令给 {success_count} 个泵")
        
        return success_count
    
    def get_all_states(self) -> dict[int, PumpState]:
        """获取所有泵的状态快照
        
        Returns:
            dict: {地址: PumpState}
        """
        with self._states_lock:
            return {addr: replace(state) for addr, state in self._states.items()}
