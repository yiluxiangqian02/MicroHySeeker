"""
RS485 Protocol Layer

RS485 协议层模块，负责帧封装、解析、校验和编解码。
纯函数实现，无状态，可独立测试。

参考：
- 原C#项目: D:/AI4S/eChemSDL/eChemSDL/MotorRS485.cs
- 文档: docs/backend/02_RS485_PROTOCOL.md
"""

from typing import Tuple, Optional, Callable
from dataclasses import dataclass
from ..utils.constants import (
    TX_HEADER, RX_HEADER,
    CMD_ENABLE, CMD_SPEED, CMD_POSITION,
    CMD_READ_ENCODER, CMD_READ_SPEED, CMD_READ_VERSION,
    ENCODER_DIVISIONS_PER_REV, MAX_RPM, MIN_RPM,
    DEFAULT_ACCELERATION,
    DIRECTION_FORWARD, DIRECTION_REVERSE
)
from ..utils.errors import ChecksumError, FrameError, InvalidAddressError


# ============================================================================
# 校验和计算
# ============================================================================

def checksum(data: bytes) -> int:
    """计算校验和
    
    算法: 所有字节求和，取低8位
    
    Args:
        data: 待计算的字节数据（不含校验和字节）
        
    Returns:
        int: 校验和值 (0-255)
        
    Example:
        >>> checksum(b'\\xFA\\x01\\xF3\\x01')
        239
    """
    return sum(data) & 0xFF


# ============================================================================
# 帧构建
# ============================================================================

def build_frame(
    addr: int,
    cmd: int,
    payload: bytes = b""
) -> bytes:
    """构建发送帧
    
    帧格式: [TX_HEADER, ADDR, CMD, PAYLOAD..., CHECKSUM]
    
    Args:
        addr: 设备地址 (1-255)
        cmd: 命令字节
        payload: 数据载荷
        
    Returns:
        bytes: 完整帧数据
        
    Raises:
        InvalidAddressError: 地址超出范围
        
    Example:
        >>> build_frame(1, CMD_ENABLE, b'\\x01')
        b'\\xFA\\x01\\xF3\\x01\\xEF'
    """
    if not (1 <= addr <= 255):
        raise InvalidAddressError(f"Invalid address: {addr}, must be 1-255")
    
    frame = bytes([TX_HEADER, addr & 0xFF, cmd & 0xFF]) + payload
    chk = checksum(frame)
    return frame + bytes([chk])


# ============================================================================
# 帧验证与解析
# ============================================================================

def verify_frame(
    frame: bytes,
    header: int = RX_HEADER
) -> bool:
    """验证接收帧校验和
    
    Args:
        frame: 完整帧数据
        header: 期望的帧头
        
    Returns:
        bool: 校验是否通过
        
    Example:
        >>> verify_frame(b'\\xFB\\x01\\xF3\\x01\\xF0')
        True
    """
    if len(frame) < 4:
        return False
    if frame[0] != (header & 0xFF):
        return False
    return checksum(frame[:-1]) == frame[-1]


def parse_frame(
    frame: bytes,
    header: int = RX_HEADER
) -> Tuple[int, int, bytes]:
    """解析接收帧
    
    Args:
        frame: 完整帧数据
        header: 期望的帧头
        
    Returns:
        tuple: (addr, cmd, payload)
        
    Raises:
        FrameError: 帧格式错误
        ChecksumError: 校验和错误
        
    Example:
        >>> parse_frame(b'\\xFB\\x01\\xF3\\x01\\xF0')
        (1, 243, b'\\x01')
    """
    if len(frame) < 4:
        raise FrameError(f"Frame too short: {len(frame)} bytes")
    
    if frame[0] != (header & 0xFF):
        raise FrameError(f"Invalid header: 0x{frame[0]:02X}, expected 0x{header:02X}")
    
    if checksum(frame[:-1]) != frame[-1]:
        raise ChecksumError(
            f"Checksum mismatch: got 0x{frame[-1]:02X}, "
            f"expected 0x{checksum(frame[:-1]):02X}"
        )
    
    addr = frame[1]
    cmd = frame[2]
    payload = frame[3:-1]
    return addr, cmd, payload


def safe_parse_frame(
    frame: bytes,
    header: int = RX_HEADER
) -> Optional[Tuple[int, int, bytes]]:
    """安全解析帧，错误时返回 None
    
    Args:
        frame: 帧数据
        header: 期望帧头
        
    Returns:
        tuple | None: (addr, cmd, payload) 或 None
    """
    try:
        return parse_frame(frame, header)
    except (FrameError, ChecksumError, IndexError):
        return None


def expected_rx_length(cmd: int) -> int | None:
    """Return expected RX frame length (bytes) for a given command.

    Protocol used by the pump returns small fixed-size frames:
    - Most commands: header + addr + cmd + 1-byte payload + checksum = 5
    - Read speed (0x32): header + addr + cmd + 2-byte payload + checksum = 6
    - Read encoder (0x30): header + addr + cmd + 4-byte payload + checksum = 8
    """
    
    from ..utils.constants import (
        CMD_READ_ENABLE, CMD_READ_FAULT, CMD_READ_RUN_STATUS,
        CMD_READ_IO, CMD_READ_VERSION, CMD_READ_ALL_SETTINGS, CMD_READ_ALL_STATUS
    )

    # 1字节响应的命令
    if cmd in (CMD_READ_ENABLE, CMD_READ_FAULT, CMD_READ_RUN_STATUS, 
               CMD_ENABLE, CMD_SPEED, CMD_POSITION, CMD_READ_IO):
        return 5
    # 2字节响应的命令
    if cmd in (CMD_READ_SPEED, CMD_READ_VERSION):
        return 6
    # 4字节响应的命令
    if cmd == CMD_READ_ENCODER:
        return 8
    # 多字节响应的命令（暂不支持）
    if cmd in (CMD_READ_ALL_SETTINGS, CMD_READ_ALL_STATUS):
        return None  # 需要特殊处理
    
    # 默认：单字节响应
    return 5


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
    
    Args:
        header: 期望的帧头字节 (默认 0xFB)
        expected_length: 根据命令字节返回期望帧长度的函数
        strict_checksum: 是否严格验证校验和 (默认 True)
                        设为 False 可兼容校验和不稳定的设备（如某些泵1）
    """

    def __init__(
        self,
        header: int = RX_HEADER,
        expected_length: Callable[[int], int | None] = expected_rx_length,
        strict_checksum: bool = True,
    ) -> None:
        self._header = header & 0xFF
        self._expected_length = expected_length
        self._buffer = bytearray()
        self._strict_checksum = strict_checksum

    def push(self, data: bytes) -> list[ParsedFrame]:
        self._buffer.extend(data)
        return self._drain()

    def clear(self) -> None:
        self._buffer.clear()
    
    def set_strict_checksum(self, strict: bool) -> None:
        """设置校验和验证模式"""
        self._strict_checksum = strict

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
            
            # 宽松模式下，如果命令未知，尝试使用默认长度5
            if length is None:
                if not self._strict_checksum:
                    length = 5  # 默认最小帧长度
                else:
                    self._buffer.pop(0)
                    continue
            
            if len(self._buffer) < length:
                break

            raw = bytes(self._buffer[:length])
            
            # 校验和验证
            if self._strict_checksum:
                if not verify_frame(raw, header=self._header):
                    self._buffer.pop(0)
                    continue
            # 宽松模式：只检查帧头和地址，不验证校验和
            # 这对于硬件校验和有问题的设备很有用
            
            # 解析帧（不验证校验和）
            try:
                addr = raw[1]
                parsed_cmd = raw[2]
                payload = raw[3:-1]
                frames.append(ParsedFrame(addr=addr, cmd=parsed_cmd, payload=payload, raw=raw))
            except (IndexError, ValueError):
                pass
            
            del self._buffer[:length]

        return frames


# ============================================================================
# 转速编解码
# ============================================================================

def encode_speed(rpm: int, forward: bool = True) -> bytes:
    """编码转速为2字节（带符号）
    
    Args:
        rpm: 转速绝对值 (0-3000)
        forward: 是否正转
        
    Returns:
        bytes: 2字节转速编码（大端序，带符号）
        
    Example:
        >>> encode_speed(100, True).hex()
        '0064'
        >>> encode_speed(100, False).hex()
        'ff9c'
    """
    rpm = max(MIN_RPM, min(MAX_RPM, rpm))
    value = rpm if forward else -rpm
    return value.to_bytes(2, 'big', signed=True)


def decode_speed(data: bytes) -> Tuple[int, bool]:
    """解码转速
    
    Args:
        data: 2字节转速数据
        
    Returns:
        tuple: (rpm, is_forward)
        
    Example:
        >>> decode_speed(b'\\x00\\x64')
        (100, True)
        >>> decode_speed(b'\\xFF\\x9C')
        (100, False)
    """
    if len(data) < 2:
        return 0, True
    
    value = int.from_bytes(data[:2], 'big', signed=True)
    forward = value >= 0
    rpm = abs(value)
    return rpm, forward


# ============================================================================
# 编码器位置编解码
# ============================================================================

def encode_position(divisions: int) -> bytes:
    """编码编码器位置为4字节
    
    Args:
        divisions: 目标分度数 (0 - ENCODER_DIVISIONS_PER_REV)
        
    Returns:
        bytes: 4字节位置编码（大端序）
        
    Example:
        >>> encode_position(16384).hex()
        '00004000'
    """
    divisions = max(0, min(ENCODER_DIVISIONS_PER_REV * 10, divisions))  # 允许多圈
    return divisions.to_bytes(4, 'big')


def decode_position(data: bytes) -> int:
    """解码编码器位置
    
    Args:
        data: 4字节位置数据
        
    Returns:
        int: 编码器分度值
        
    Example:
        >>> decode_position(b'\\x00\\x00\\x40\\x00')
        16384
    """
    if len(data) < 4:
        return 0
    return int.from_bytes(data[:4], 'big')


def encode_degrees(degrees: float) -> bytes:
    """编码角度为编码器分度
    
    Args:
        degrees: 角度值 (单位: 度)
        
    Returns:
        bytes: 4字节编码器分度
        
    Example:
        >>> encode_degrees(360.0).hex()
        '00004000'
    """
    divisions = int(degrees * ENCODER_DIVISIONS_PER_REV / 360.0)
    return encode_position(divisions)


def decode_degrees(data: bytes) -> float:
    """解码编码器分度为角度
    
    Args:
        data: 4字节位置数据
        
    Returns:
        float: 角度值 (单位: 度)
    """
    divisions = decode_position(data)
    return divisions * 360.0 / ENCODER_DIVISIONS_PER_REV


# ============================================================================
# 使能命令编解码
# ============================================================================

def encode_enable(enable: bool) -> bytes:
    """编码使能命令
    
    Args:
        enable: 是否使能
        
    Returns:
        bytes: 1字节使能数据
        
    Example:
        >>> encode_enable(True).hex()
        '01'
        >>> encode_enable(False).hex()
        '00'
    """
    return bytes([0x01 if enable else 0x00])


# ============================================================================
# 高级命令帧构建
# ============================================================================

def build_enable_frame(addr: int, enable: bool = True) -> bytes:
    """构建使能/禁用命令帧
    
    Args:
        addr: 设备地址
        enable: 是否使能
        
    Returns:
        bytes: 完整命令帧
    """
    return build_frame(addr, CMD_ENABLE, encode_enable(enable))


def build_speed_frame(
    addr: int,
    rpm: int,
    forward: bool = True,
    acceleration: int = DEFAULT_ACCELERATION
) -> bytes:
    """构建速度模式命令帧
    
    Args:
        addr: 设备地址
        rpm: 转速 (0-3000)
        forward: 是否正转
        acceleration: 加速度参数
        
    Returns:
        bytes: 完整命令帧
    """
    speed_data = encode_speed(rpm, forward)
    payload = speed_data + bytes([acceleration & 0xFF])
    return build_frame(addr, CMD_SPEED, payload)


def build_position_frame(
    addr: int,
    divisions: int,
    speed: int = 100,
    forward: bool = True,
    acceleration: int = DEFAULT_ACCELERATION
) -> bytes:
    """构建相对位置模式命令帧
    
    Args:
        addr: 设备地址
        divisions: 目标分度数
        speed: 运行速度
        forward: 运行方向
        acceleration: 加速度参数
        
    Returns:
        bytes: 完整命令帧
    """
    speed_data = encode_speed(speed, forward)
    pos_data = encode_position(divisions)
    payload = speed_data + bytes([acceleration & 0xFF]) + pos_data
    return build_frame(addr, CMD_POSITION, payload)


def build_read_encoder_frame(addr: int) -> bytes:
    """构建读取编码器命令帧
    
    Args:
        addr: 设备地址
        
    Returns:
        bytes: 完整命令帧
    """
    return build_frame(addr, CMD_READ_ENCODER)


def build_read_speed_frame(addr: int) -> bytes:
    """构建读取速度命令帧
    
    Args:
        addr: 设备地址
        
    Returns:
        bytes: 完整命令帧
    """
    return build_frame(addr, CMD_READ_SPEED)


def build_read_version_frame(addr: int) -> bytes:
    """构建读取版本命令帧
    
    Args:
        addr: 设备地址
        
    Returns:
        bytes: 完整命令帧
    """
    return build_frame(addr, CMD_READ_VERSION)


# ============================================================================
# 工具函数
# ============================================================================

def frame_to_hex(frame: bytes) -> str:
    """将帧转换为可读的十六进制字符串
    
    Args:
        frame: 帧数据
        
    Returns:
        str: 十六进制字符串，用空格分隔
        
    Example:
        >>> frame_to_hex(b'\\xFA\\x01\\xF3\\x01\\xEF')
        'FA 01 F3 01 EF'
    """
    return ' '.join(f'{b:02X}' for b in frame)


def hex_to_frame(hex_str: str) -> bytes:
    """将十六进制字符串转换为帧
    
    Args:
        hex_str: 十六进制字符串 (可用空格分隔)
        
    Returns:
        bytes: 帧数据
        
    Example:
        >>> hex_to_frame('FA 01 F3 01 EF')
        b'\\xFA\\x01\\xF3\\x01\\xEF'
    """
    hex_str = hex_str.replace(' ', '').replace('-', '')
    return bytes.fromhex(hex_str)


