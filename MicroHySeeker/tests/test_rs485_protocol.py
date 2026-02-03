"""
Unit Tests for RS485 Protocol Module

测试 RS485 协议层的帧构建、解析、校验和编解码功能。
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from echem_sdl.hardware.rs485_protocol import (
    checksum, build_frame, verify_frame, parse_frame, safe_parse_frame,
    encode_speed, decode_speed,
    encode_position, decode_position,
    encode_degrees, decode_degrees,
    encode_enable,
    build_enable_frame, build_speed_frame, build_position_frame,
    build_read_encoder_frame, build_read_speed_frame,
    frame_to_hex, hex_to_frame
)
from echem_sdl.utils.constants import (
    TX_HEADER, RX_HEADER,
    CMD_ENABLE, CMD_SPEED, CMD_POSITION,
    CMD_READ_ENCODER, CMD_READ_SPEED,
    ENCODER_DIVISIONS_PER_REV
)
from echem_sdl.utils.errors import FrameError, ChecksumError, InvalidAddressError


class TestChecksum:
    """测试校验和计算"""
    
    def test_checksum_basic(self):
        """基本校验和计算"""
        assert checksum(b'\xFA\x01\xF3\x01') == 0xEF
    
    def test_checksum_empty(self):
        """空数据校验和"""
        assert checksum(b'') == 0
    
    def test_checksum_overflow(self):
        """验证只取低8位"""
        assert checksum(b'\xFF\xFF') == 0xFE
    
    def test_checksum_single_byte(self):
        """单字节校验和"""
        assert checksum(b'\x42') == 0x42


class TestBuildFrame:
    """测试帧构建"""
    
    def test_build_enable_frame(self):
        """构建使能命令帧"""
        frame = build_frame(1, CMD_ENABLE, b'\x01')
        assert frame[0] == TX_HEADER
        assert frame[1] == 1
        assert frame[2] == CMD_ENABLE
        assert frame[3] == 0x01
        assert frame[-1] == checksum(frame[:-1])
    
    def test_build_speed_frame(self):
        """构建速度命令帧"""
        frame = build_frame(1, CMD_SPEED, encode_speed(100, True))
        assert len(frame) == 6  # header + addr + cmd + 2速度 + checksum
        assert frame[0] == TX_HEADER
    
    def test_build_empty_payload(self):
        """构建无载荷帧"""
        frame = build_frame(1, CMD_READ_ENCODER)
        assert len(frame) == 4  # header + addr + cmd + checksum
    
    def test_build_invalid_address(self):
        """构建无效地址帧应抛出异常"""
        with pytest.raises(InvalidAddressError):
            build_frame(0, CMD_ENABLE)
        
        with pytest.raises(InvalidAddressError):
            build_frame(256, CMD_ENABLE)


class TestVerifyFrame:
    """测试帧验证"""
    
    def test_verify_valid_frame(self):
        """验证有效帧"""
        frame = b'\xFB\x01\xF3\x01\xF0'
        assert verify_frame(frame) == True
    
    def test_verify_invalid_checksum(self):
        """验证校验和错误的帧"""
        frame = b'\xFB\x01\xF3\x01\xFF'
        assert verify_frame(frame) == False
    
    def test_verify_wrong_header(self):
        """验证帧头错误的帧"""
        frame = b'\xFA\x01\xF3\x01\xEF'
        assert verify_frame(frame, RX_HEADER) == False
    
    def test_verify_short_frame(self):
        """验证过短的帧"""
        frame = b'\xFB\x01'
        assert verify_frame(frame) == False
    
    def test_verify_empty_frame(self):
        """验证空帧"""
        assert verify_frame(b'') == False


class TestParseFrame:
    """测试帧解析"""
    
    def test_parse_valid_frame(self):
        """解析有效帧"""
        frame = b'\xFB\x01\xF3\x01\xF0'
        addr, cmd, payload = parse_frame(frame)
        assert addr == 1
        assert cmd == CMD_ENABLE
        assert payload == b'\x01'
    
    def test_parse_invalid_frame(self):
        """解析无效帧应抛出异常"""
        with pytest.raises(ChecksumError):
            parse_frame(b'\xFB\x01\xF3\x01\xFF')
    
    def test_parse_short_frame(self):
        """解析过短帧应抛出异常"""
        with pytest.raises(FrameError):
            parse_frame(b'\xFB\x01')
    
    def test_safe_parse_valid(self):
        """安全解析有效帧"""
        frame = b'\xFB\x01\xF3\x01\xF0'
        result = safe_parse_frame(frame)
        assert result is not None
        assert result[0] == 1
    
    def test_safe_parse_invalid(self):
        """安全解析无效帧返回None"""
        frame = b'\xFB\x01\xF3\x01\xFF'
        result = safe_parse_frame(frame)
        assert result is None


class TestSpeedEncoding:
    """测试转速编解码"""
    
    def test_encode_forward(self):
        """编码正转转速"""
        data = encode_speed(100, True)
        assert data == b'\x00\x64'
    
    def test_encode_reverse(self):
        """编码反转转速"""
        data = encode_speed(100, False)
        value = int.from_bytes(data, 'big', signed=True)
        assert value == -100
    
    def test_encode_zero(self):
        """编码零转速"""
        data = encode_speed(0, True)
        assert data == b'\x00\x00'
    
    def test_decode_forward(self):
        """解码正转转速"""
        rpm, forward = decode_speed(b'\x00\x64')
        assert rpm == 100
        assert forward == True
    
    def test_decode_reverse(self):
        """解码反转转速"""
        rpm, forward = decode_speed(encode_speed(100, False))
        assert rpm == 100
        assert forward == False
    
    def test_speed_round_trip(self):
        """转速编解码往返测试"""
        test_cases = [
            (0, True),
            (100, True),
            (100, False),
            (1000, True),
            (3000, False),
        ]
        
        for rpm, fwd in test_cases:
            data = encode_speed(rpm, fwd)
            r, f = decode_speed(data)
            assert r == rpm, f"RPM mismatch: expected {rpm}, got {r}"
            assert f == fwd, f"Direction mismatch: expected {fwd}, got {f}"


class TestPositionEncoding:
    """测试位置编解码"""
    
    def test_encode_position(self):
        """编码位置"""
        data = encode_position(16384)
        assert len(data) == 4
        assert data == b'\x00\x00\x40\x00'
    
    def test_decode_position(self):
        """解码位置"""
        data = b'\x00\x00\x40\x00'
        pos = decode_position(data)
        assert pos == 16384
    
    def test_position_round_trip(self):
        """位置编解码往返测试"""
        test_values = [0, 1000, 16384, 32768]
        for val in test_values:
            data = encode_position(val)
            result = decode_position(data)
            assert result == val
    
    def test_encode_degrees(self):
        """编码角度"""
        data = encode_degrees(360.0)
        # 360度 = 1圈 = 16384分度
        pos = decode_position(data)
        assert pos == ENCODER_DIVISIONS_PER_REV
    
    def test_decode_degrees(self):
        """解码角度"""
        data = encode_position(ENCODER_DIVISIONS_PER_REV)
        degrees = decode_degrees(data)
        assert abs(degrees - 360.0) < 0.01


class TestEnableEncoding:
    """测试使能编码"""
    
    def test_encode_enable_true(self):
        """编码使能"""
        data = encode_enable(True)
        assert data == b'\x01'
    
    def test_encode_enable_false(self):
        """编码禁用"""
        data = encode_enable(False)
        assert data == b'\x00'


class TestHighLevelFrameBuilders:
    """测试高级帧构建函数"""
    
    def test_build_enable_frame(self):
        """构建使能帧"""
        frame = build_enable_frame(1, True)
        assert frame[0] == TX_HEADER
        assert frame[1] == 1
        assert frame[2] == CMD_ENABLE
        assert verify_frame(frame, TX_HEADER)
    
    def test_build_speed_frame(self):
        """构建速度帧"""
        frame = build_speed_frame(1, 100, True)
        assert frame[0] == TX_HEADER
        assert frame[2] == CMD_SPEED
        assert verify_frame(frame, TX_HEADER)
    
    def test_build_position_frame(self):
        """构建位置帧"""
        frame = build_position_frame(1, 16384, 100, True)
        assert frame[0] == TX_HEADER
        assert frame[2] == CMD_POSITION
        assert verify_frame(frame, TX_HEADER)
    
    def test_build_read_encoder_frame(self):
        """构建读取编码器帧"""
        frame = build_read_encoder_frame(1)
        assert frame[0] == TX_HEADER
        assert frame[2] == CMD_READ_ENCODER
        assert len(frame) == 4
    
    def test_build_read_speed_frame(self):
        """构建读取速度帧"""
        frame = build_read_speed_frame(1)
        assert frame[0] == TX_HEADER
        assert frame[2] == CMD_READ_SPEED
        assert len(frame) == 4


class TestUtilityFunctions:
    """测试工具函数"""
    
    def test_frame_to_hex(self):
        """帧转十六进制字符串"""
        frame = b'\xFA\x01\xF3\x01\xEF'
        hex_str = frame_to_hex(frame)
        assert hex_str == 'FA 01 F3 01 EF'
    
    def test_hex_to_frame(self):
        """十六进制字符串转帧"""
        hex_str = 'FA 01 F3 01 EF'
        frame = hex_to_frame(hex_str)
        assert frame == b'\xFA\x01\xF3\x01\xEF'
    
    def test_hex_round_trip(self):
        """十六进制往返转换"""
        original = b'\xFA\x01\xF3\x01\xEF'
        hex_str = frame_to_hex(original)
        result = hex_to_frame(hex_str)
        assert result == original
    
    def test_hex_to_frame_no_spaces(self):
        """无空格的十六进制字符串"""
        hex_str = 'FA01F301EF'
        frame = hex_to_frame(hex_str)
        assert frame == b'\xFA\x01\xF3\x01\xEF'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
