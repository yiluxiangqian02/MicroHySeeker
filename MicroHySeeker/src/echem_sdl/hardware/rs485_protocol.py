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
    CMD_READ_ENCODER_ACCUM, CMD_READ_RUN_STATUS,
    CMD_POSITION_REL, CMD_POSITION_ABS, CMD_STOP_EMERGENCY,
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
# 累加编码器值编解码 (位置模式专用)
# ============================================================================

def decode_encoder_accum(data: bytes) -> int:
    """解码累加制多圈编码器值 (0x31命令返回)
    
    这是用于位置模式的累加坐标值，支持多圈记录。
    数据格式为6字节有符号整数（int48, 大端序）。
    
    Args:
        data: 6字节累加编码器数据
        
    Returns:
        int: 累加坐标值 (16384单位 = 1圈)
             正值 = 正转累计，负值 = 反转累计
        
    Example:
        >>> decode_encoder_accum(b'\\x00\\x00\\x00\\x00\\x40\\x00')  # 1圈
        16384
        >>> decode_encoder_accum(b'\\xFF\\xFF\\xFF\\xFF\\xC0\\x00')  # -1圈
        -16384
    """
    if len(data) < 6:
        return 0
    
    # 6字节有符号大端序
    # Python没有直接的int48支持，需要手动处理符号位
    raw_value = int.from_bytes(data[:6], 'big')
    
    # 检查符号位 (第48位)
    if raw_value & 0x800000000000:  # 如果最高位为1
        # 负数：需要转换为有符号值
        raw_value = raw_value - 0x1000000000000
    
    return raw_value


def encode_axis_value(axis: int) -> bytes:
    """编码坐标值为4字节有符号整数
    
    用于位置模式3/4的坐标参数。
    
    Args:
        axis: 坐标值 (int32, 16384单位 = 1圈)
        
    Returns:
        bytes: 4字节坐标编码（有符号大端序）
        
    Example:
        >>> encode_axis_value(16384).hex()  # 正转1圈
        '00004000'
        >>> encode_axis_value(-16384).hex()  # 反转1圈
        'ffffc000'
    """
    # 限制到int32范围
    axis = max(-2147483648, min(2147483647, axis))
    return axis.to_bytes(4, 'big', signed=True)


def decode_axis_value(data: bytes) -> int:
    """解码4字节有符号坐标值
    
    Args:
        data: 4字节坐标数据
        
    Returns:
        int: 坐标值 (有符号)
    """
    if len(data) < 4:
        return 0
    return int.from_bytes(data[:4], 'big', signed=True)


def decode_run_status(data: bytes) -> int:
    """解码运行状态 (0xF1命令返回)
    
    Args:
        data: 1字节状态数据
        
    Returns:
        int: 运行状态码
            1 = 电机停止
            2 = 电机加速中
            3 = 电机减速中
            4 = 电机全速运行中
            5 = 电机归零中
            6 = 电机校准中
    """
    if len(data) < 1:
        return 0
    return data[0]


def decode_position_response(data: bytes) -> int:
    """解码位置模式响应 (0xF4/0xF5命令返回)
    
    Args:
        data: 1字节状态数据
        
    Returns:
        int: 响应状态码
            1 = 指令开始执行
            2 = 指令执行完成
            3 = 运行中触碰限位
    """
    if len(data) < 1:
        return 0
    return data[0]


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


def build_position_rel_frame(
    addr: int,
    rel_axis: int,
    speed: int = 100,
    acceleration: int = DEFAULT_ACCELERATION
) -> bytes:
    """构建位置模式3命令帧 - 按坐标值相对运动 (0xF4)
    
    使用编码器坐标值(16384/圈)作为单位。
    这是SR_VFOC模式下推荐的位置控制方式。
    
    帧格式: FA addr F4 speed(2) acc relAxis(4,signed) CRC
    
    Args:
        addr: 设备地址 (1-255)
        rel_axis: 相对坐标值 (int32, 16384单位 = 1圈)
                  正值=正转, 负值=反转
        speed: 运行速度 (0-3000 RPM)
        acceleration: 加速度参数 (0-255)
        
    Returns:
        bytes: 完整命令帧 (11字节)
        
    Example:
        >>> build_position_rel_frame(1, 16384, 600, 2).hex()  # 正转1圈
        'fa01f402580200004000xx'
    """
    # 速度: 2字节大端序 (无符号)
    speed = max(0, min(3000, speed))
    speed_bytes = speed.to_bytes(2, 'big')
    
    # 加速度: 1字节
    acc_byte = bytes([acceleration & 0xFF])
    
    # 相对坐标: 4字节有符号大端序
    rel_axis_bytes = rel_axis.to_bytes(4, 'big', signed=True)
    
    payload = speed_bytes + acc_byte + rel_axis_bytes
    return build_frame(addr, CMD_POSITION_REL, payload)


def build_position_abs_frame(
    addr: int,
    abs_axis: int,
    speed: int = 100,
    acceleration: int = DEFAULT_ACCELERATION
) -> bytes:
    """构建位置模式4命令帧 - 按坐标值绝对运动 (0xF5)
    
    使用编码器坐标值(16384/圈)作为单位。
    支持速度和坐标实时更新。
    
    帧格式: FA addr F5 speed(2) acc absAxis(4,signed) CRC
    
    Args:
        addr: 设备地址 (1-255)
        abs_axis: 绝对坐标值 (int32, 16384单位 = 1圈)
        speed: 运行速度 (0-3000 RPM)
        acceleration: 加速度参数 (0-255)
        
    Returns:
        bytes: 完整命令帧 (11字节)
        
    Example:
        >>> build_position_abs_frame(1, 0x4000, 600, 2).hex()  # 绝对运动到1圈位置
        'fa01f502580200004000xx'
    """
    # 速度: 2字节大端序 (无符号)
    speed = max(0, min(3000, speed))
    speed_bytes = speed.to_bytes(2, 'big')
    
    # 加速度: 1字节
    acc_byte = bytes([acceleration & 0xFF])
    
    # 绝对坐标: 4字节有符号大端序
    abs_axis_bytes = abs_axis.to_bytes(4, 'big', signed=True)
    
    payload = speed_bytes + acc_byte + abs_axis_bytes
    return build_frame(addr, CMD_POSITION_ABS, payload)


def build_position_stop_frame(
    addr: int,
    acceleration: int = DEFAULT_ACCELERATION,
    cmd: int = CMD_POSITION_REL
) -> bytes:
    """构建位置模式停止命令帧
    
    当acc≠0时减速停止，acc=0时立即停止。
    
    Args:
        addr: 设备地址
        acceleration: 减速度 (0=立即停止, 其他=减速停止)
        cmd: 使用的位置命令 (CMD_POSITION_REL 或 CMD_POSITION_ABS)
        
    Returns:
        bytes: 完整命令帧
    """
    # 速度=0, acc, 坐标=0
    payload = bytes([0x00, 0x00, acceleration & 0xFF, 0x00, 0x00, 0x00, 0x00])
    return build_frame(addr, cmd, payload)


def build_speed_mode_frame(
    addr: int,
    rpm: int,
    forward: bool = True,
    acceleration: int = DEFAULT_ACCELERATION
) -> bytes:
    """构建速度控制模式命令帧 (0xF6)
    
    SR_VFOC模式下的速度控制。
    
    帧格式: FA addr F6 dir|speed_hi speed_lo acc CRC
    其中: 字节4最高位=方向, 低4位+字节5=速度
    
    Args:
        addr: 设备地址 (1-255)
        rpm: 转速 (0-3000 RPM)
        forward: 是否正转 (True=CCW/0, False=CW/1)
        acceleration: 加速度参数 (0-255)
        
    Returns:
        bytes: 完整命令帧 (7字节)
        
    Example:
        >>> build_speed_mode_frame(1, 640, True, 2).hex()
        'fa01f6028002xx'  # speed=0x280, acc=2, dir=0
    """
    rpm = max(0, min(3000, rpm))
    
    # 方向位在字节4的bit7
    dir_bit = 0x00 if forward else 0x80
    
    # 速度分成高4位和低8位
    speed_hi = (rpm >> 8) & 0x0F  # 低4位
    speed_lo = rpm & 0xFF
    
    # 字节4 = 方向位 | 速度高4位
    byte4 = dir_bit | speed_hi
    
    payload = bytes([byte4, speed_lo, acceleration & 0xFF])
    return build_frame(addr, CMD_SPEED, payload)


def build_speed_stop_frame(
    addr: int,
    acceleration: int = DEFAULT_ACCELERATION
) -> bytes:
    """构建速度模式停止命令帧
    
    当acc≠0时减速停止，acc=0时立即停止。
    
    Args:
        addr: 设备地址
        acceleration: 减速度 (0=立即停止, 其他=减速停止)
        
    Returns:
        bytes: 完整命令帧
    """
    # speed=0, acc
    payload = bytes([0x00, 0x00, acceleration & 0xFF])
    return build_frame(addr, CMD_SPEED, payload)


def build_read_encoder_accum_frame(addr: int) -> bytes:
    """构建读取累加制多圈编码器值命令帧 (0x31)
    
    用于获取位置模式下的坐标值。
    
    Args:
        addr: 设备地址
        
    Returns:
        bytes: 完整命令帧
    """
    return build_frame(addr, CMD_READ_ENCODER_ACCUM)


def build_read_run_status_frame(addr: int) -> bytes:
    """构建读取运行状态命令帧 (0xF1)
    
    Args:
        addr: 设备地址
        
    Returns:
        bytes: 完整命令帧
    """
    return build_frame(addr, CMD_READ_RUN_STATUS)


def build_serial_enable_frame(addr: int, enable: bool = True) -> bytes:
    """构建串行模式使能/禁用命令帧 (0xF3)
    
    在SR_VFOC模式下，使能状态由此命令控制，不受En引脚影响。
    
    Args:
        addr: 设备地址
        enable: 是否使能
        
    Returns:
        bytes: 完整命令帧
    """
    payload = bytes([0x01 if enable else 0x00])
    return build_frame(addr, CMD_ENABLE, payload)


def build_emergency_stop_frame(addr: int) -> bytes:
    """构建紧急停止命令帧 (0xF7)
    
    警告: 电机转速超过1000RPM时不建议使用！
    
    Args:
        addr: 设备地址
        
    Returns:
        bytes: 完整命令帧
    """
    return build_frame(addr, CMD_STOP_EMERGENCY)


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


