"""High-level pump communications on top of RS485Driver."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

from ..services.logger import LoggerService
from .rs485_driver import RS485Driver
from .rs485_protocol import (
    CMD_ENABLE,
    CMD_READ_ENABLE,
    CMD_READ_FAULT,
    CMD_READ_SPEED,
    CMD_SPEED,
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

    def request(self, addr: int, cmd: int, payload: bytes = b"", timeout_s: float | None = None) -> ParsedFrame:
        if addr < 1 or addr > 255:
            raise ValueError("addr must be 1..255")

        timeout = self.timeout_s if timeout_s is None else float(timeout_s)
        key = (addr, cmd)

        with self._request_lock:
            pending = _PendingRequest(event=threading.Event())
            with self._pending_lock:
                self._pending[key] = pending

            try:
                self.driver.write(build_frame(addr, cmd, payload))
            except Exception:
                with self._pending_lock:
                    self._pending.pop(key, None)
                raise

            ok = pending.event.wait(timeout=timeout)
            with self._pending_lock:
                self._pending.pop(key, None)

            if not ok or pending.frame is None:
                self._note_timeout(addr, cmd)
                raise TimeoutError(f"pump 0x{addr:02X} cmd 0x{cmd:02X} timeout")

            self._note_response(pending.frame)
            return pending.frame

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
