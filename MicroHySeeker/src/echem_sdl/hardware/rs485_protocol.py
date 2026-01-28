"""RS485 pump protocol helpers.

This module is extracted from the working `485test` project and kept UI-agnostic
so it can be reused by `MicroHySeeker` regardless of the GUI toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

TX_HEADER = 0xFA
RX_HEADER = 0xFB

CMD_READ_ENCODER = 0x30
CMD_READ_SPEED = 0x32
CMD_READ_IO = 0x34
CMD_READ_ENABLE = 0x3A
CMD_READ_FAULT = 0x3E
CMD_READ_VERSION = 0x40
CMD_ENABLE = 0xF3
CMD_SPEED = 0xF6


def checksum(data: bytes) -> int:
    return sum(data) & 0xFF


def build_frame(addr: int, cmd: int, payload: bytes = b"") -> bytes:
    frame = bytes([TX_HEADER, addr & 0xFF, cmd & 0xFF]) + payload
    chk = checksum(frame)
    return frame + bytes([chk])


def verify_frame(frame: bytes, header: int = RX_HEADER) -> bool:
    if len(frame) < 4:
        return False
    if frame[0] != (header & 0xFF):
        return False
    return checksum(frame[:-1]) == frame[-1]


def parse_frame(frame: bytes, header: int = RX_HEADER) -> tuple[int, int, bytes]:
    if not verify_frame(frame, header=header):
        raise ValueError("invalid frame")
    addr = frame[1]
    cmd = frame[2]
    payload = frame[3:-1]
    return addr, cmd, payload


def expected_rx_length(cmd: int) -> int | None:
    """Return expected RX frame length (bytes) for a given command.

    Protocol used by the pump returns small fixed-size frames:
    - Most commands: header + addr + cmd + 1-byte payload + checksum = 5
    - Read speed (0x32): header + addr + cmd + 2-byte payload + checksum = 6
    """

    if cmd in (CMD_READ_ENABLE, CMD_READ_FAULT, CMD_ENABLE, CMD_SPEED):
        return 5
    if cmd == CMD_READ_SPEED:
        return 6
    return None


@dataclass(slots=True)
class ParsedFrame:
    addr: int
    cmd: int
    payload: bytes
    raw: bytes


class FrameStreamParser:
    """Incremental parser for the pump's byte stream.

    The RS485 device may return data in arbitrary chunks. This parser buffers
    bytes, finds frame boundaries, validates checksum, and returns complete frames.
    """

    def __init__(
        self,
        header: int = RX_HEADER,
        expected_length: Callable[[int], int | None] = expected_rx_length,
    ) -> None:
        self._header = header & 0xFF
        self._expected_length = expected_length
        self._buffer = bytearray()

    def push(self, data: bytes) -> list[ParsedFrame]:
        self._buffer.extend(data)
        return self._drain()

    def clear(self) -> None:
        self._buffer.clear()

    def _drain(self) -> list[ParsedFrame]:
        frames: list[ParsedFrame] = []
        while len(self._buffer) >= 4:
            if self._buffer[0] != self._header:
                self._buffer.pop(0)
                continue

            if len(self._buffer) < 3:
                break

            cmd = self._buffer[2]
            length = self._expected_length(cmd)
            if length is None:
                self._buffer.pop(0)
                continue
            if len(self._buffer) < length:
                break

            raw = bytes(self._buffer[:length])
            if not verify_frame(raw, header=self._header):
                self._buffer.pop(0)
                continue

            addr, parsed_cmd, payload = parse_frame(raw, header=self._header)
            frames.append(ParsedFrame(addr=addr, cmd=parsed_cmd, payload=payload, raw=raw))
            del self._buffer[:length]

        return frames

