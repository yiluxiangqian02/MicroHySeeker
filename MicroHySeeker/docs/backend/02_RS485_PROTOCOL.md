# 02 - RS485Protocol 模块规范

> **文件路径**: `src/echem_sdl/hardware/rs485_protocol.py`  
> **优先级**: P0 (核心模块)  
> **依赖**: 无  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs` (帧构建部分)

---

## 一、模块职责

RS485Protocol 是协议层模块，负责：
1. 定义 RS485 通信协议常量
2. 帧封装（构建发送帧）
3. 帧解析（解析接收帧）
4. 校验和计算与验证
5. 命令与数据的编解码

**设计原则**: 纯函数实现，无状态，可独立测试

---

## 二、常量定义

### 2.1 帧头常量

```python
# 帧头定义
TX_HEADER = 0xFA  # 发送帧头
RX_HEADER = 0xFB  # 接收帧头
```

### 2.2 命令常量

```python
# 读取命令 (Query)
CMD_READ_ENCODER = 0x30      # 读取编码器位置
CMD_READ_SPEED = 0x32        # 读取当前转速
CMD_READ_IO = 0x34           # 读取IO状态
CMD_READ_ENABLE = 0x3A       # 读取使能状态
CMD_READ_FAULT = 0x3E        # 读取故障状态
CMD_READ_VERSION = 0x40      # 读取固件版本

# 控制命令 (Control)
CMD_ENABLE = 0xF3            # 使能/禁用电机
CMD_SPEED = 0xF6             # 设置转速
CMD_POSITION = 0xFD          # 设置目标位置
CMD_STOP = 0xFE              # 紧急停止
```

### 2.3 编码器参数

```python
# 编码器参数
ENCODER_DIVISIONS_PER_REV = 16384  # 编码器分度/圈
MAX_RPM = 3000                      # 最大转速
MIN_RPM = 0                         # 最小转速
```

---

## 三、函数定义

### 3.1 校验和计算

```python
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
```

### 3.2 帧构建

```python
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
        
    Example:
        >>> build_frame(1, CMD_ENABLE, b'\\x01')
        b'\\xFA\\x01\\xF3\\x01\\xEF'
    """
    frame = bytes([TX_HEADER, addr & 0xFF, cmd & 0xFF]) + payload
    chk = checksum(frame)
    return frame + bytes([chk])
```

### 3.3 帧验证

```python
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
```

### 3.4 帧解析

```python
def parse_frame(
    frame: bytes,
    header: int = RX_HEADER
) -> tuple[int, int, bytes]:
    """解析接收帧
    
    Args:
        frame: 完整帧数据
        header: 期望的帧头
        
    Returns:
        tuple: (addr, cmd, payload)
        
    Raises:
        ValueError: 帧格式或校验错误
        
    Example:
        >>> parse_frame(b'\\xFB\\x01\\xF3\\x01\\xF0')
        (1, 243, b'\\x01')
    """
    if not verify_frame(frame, header=header):
        raise ValueError("invalid frame: checksum mismatch or invalid header")
    addr = frame[1]
    cmd = frame[2]
    payload = frame[3:-1]
    return addr, cmd, payload
```

### 3.5 转速编码

```python
def encode_speed(rpm: int, forward: bool = True) -> bytes:
    """编码转速为2字节（带符号）
    
    Args:
        rpm: 转速绝对值 (0-3000)
        forward: 是否正转
        
    Returns:
        bytes: 2字节转速编码（大端序，带符号）
        
    Example:
        >>> encode_speed(100, True)
        b'\\x00\\x64'
        >>> encode_speed(100, False)
        b'\\xFF\\x9C'
    """
    rpm = max(MIN_RPM, min(MAX_RPM, rpm))
    value = rpm if forward else -rpm
    return value.to_bytes(2, 'big', signed=True)
```

### 3.6 转速解码

```python
def decode_speed(data: bytes) -> tuple[int, bool]:
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
    value = int.from_bytes(data[:2], 'big', signed=True)
    forward = value >= 0
    rpm = abs(value)
    return rpm, forward
```

### 3.7 编码器位置编码

```python
def encode_position(divisions: int) -> bytes:
    """编码编码器位置
    
    Args:
        divisions: 目标分度数 (0 - ENCODER_DIVISIONS_PER_REV)
        
    Returns:
        bytes: 4字节位置编码（大端序）
    """
    divisions = max(0, min(ENCODER_DIVISIONS_PER_REV, divisions))
    return divisions.to_bytes(4, 'big')
```

### 3.8 编码器位置解码

```python
def decode_position(data: bytes) -> int:
    """解码编码器位置
    
    Args:
        data: 4字节位置数据
        
    Returns:
        int: 编码器分度值
    """
    return int.from_bytes(data[:4], 'big')
```

### 3.9 使能命令编码

```python
def encode_enable(enable: bool) -> bytes:
    """编码使能命令
    
    Args:
        enable: 是否使能
        
    Returns:
        bytes: 1字节使能数据
    """
    return bytes([0x01 if enable else 0x00])
```

---

## 四、帧格式详解

### 4.1 发送帧结构

```
偏移  字段      大小    说明
----  --------  ------  ----------------------
0     帧头      1字节   固定 0xFA
1     地址      1字节   设备地址 1-255
2     命令      1字节   命令字节
3..N  数据      N字节   命令相关数据
N+1   校验和    1字节   前面所有字节求和取低8位
```

### 4.2 接收帧结构

```
偏移  字段      大小    说明
----  --------  ------  ----------------------
0     帧头      1字节   固定 0xFB
1     地址      1字节   设备地址
2     命令      1字节   响应命令
3..N  数据      N字节   响应数据
N+1   校验和    1字节   校验和
```

### 4.3 常用命令帧示例

**使能电机 (CMD_ENABLE = 0xF3)**:
```
TX: FA 01 F3 01 EF      # 使能地址1的电机
RX: FB 01 F3 01 F0      # 确认响应
```

**设置转速 (CMD_SPEED = 0xF6)**:
```
TX: FA 01 F6 00 64 5B   # 设置地址1转速100rpm正转
RX: FB 01 F6 01 F9      # 确认响应
```

**读取编码器 (CMD_READ_ENCODER = 0x30)**:
```
TX: FA 01 30 2B         # 读取地址1编码器
RX: FB 01 30 00 00 40 00 CC  # 返回16384分度
```

---

## 五、错误处理

### 5.1 异常定义

```python
class RS485ProtocolError(Exception):
    """RS485协议错误基类"""
    pass

class ChecksumError(RS485ProtocolError):
    """校验和错误"""
    pass

class FrameError(RS485ProtocolError):
    """帧格式错误"""
    pass
```

### 5.2 安全解析

```python
def safe_parse_frame(
    frame: bytes,
    header: int = RX_HEADER
) -> tuple[int, int, bytes] | None:
    """安全解析帧，错误时返回 None
    
    Args:
        frame: 帧数据
        header: 期望帧头
        
    Returns:
        tuple | None: (addr, cmd, payload) 或 None
    """
    try:
        return parse_frame(frame, header)
    except (ValueError, IndexError):
        return None
```

---

## 六、测试要求

### 6.1 单元测试

```python
# tests/test_rs485_protocol.py

import pytest
from echem_sdl.hardware.rs485_protocol import *

class TestChecksum:
    def test_checksum_basic(self):
        assert checksum(b'\xFA\x01\xF3\x01') == 0xEF
    
    def test_checksum_empty(self):
        assert checksum(b'') == 0
    
    def test_checksum_overflow(self):
        # 验证只取低8位
        assert checksum(b'\xFF\xFF') == 0xFE

class TestBuildFrame:
    def test_build_enable_frame(self):
        frame = build_frame(1, CMD_ENABLE, b'\x01')
        assert frame == b'\xFA\x01\xF3\x01\xEF'
    
    def test_build_speed_frame(self):
        frame = build_frame(1, CMD_SPEED, encode_speed(100, True))
        assert len(frame) == 6
        assert frame[0] == TX_HEADER
    
    def test_build_empty_payload(self):
        frame = build_frame(1, CMD_READ_ENCODER)
        assert len(frame) == 4

class TestVerifyFrame:
    def test_verify_valid_frame(self):
        frame = b'\xFB\x01\xF3\x01\xF0'
        assert verify_frame(frame) == True
    
    def test_verify_invalid_checksum(self):
        frame = b'\xFB\x01\xF3\x01\xFF'
        assert verify_frame(frame) == False
    
    def test_verify_wrong_header(self):
        frame = b'\xFA\x01\xF3\x01\xEF'
        assert verify_frame(frame, RX_HEADER) == False
    
    def test_verify_short_frame(self):
        frame = b'\xFB\x01'
        assert verify_frame(frame) == False

class TestParseFrame:
    def test_parse_valid_frame(self):
        frame = b'\xFB\x01\xF3\x01\xF0'
        addr, cmd, payload = parse_frame(frame)
        assert addr == 1
        assert cmd == CMD_ENABLE
        assert payload == b'\x01'
    
    def test_parse_invalid_frame(self):
        with pytest.raises(ValueError):
            parse_frame(b'\xFB\x01\xF3\x01\xFF')

class TestSpeedEncoding:
    def test_encode_forward(self):
        data = encode_speed(100, True)
        assert data == b'\x00\x64'
    
    def test_encode_reverse(self):
        data = encode_speed(100, False)
        assert int.from_bytes(data, 'big', signed=True) == -100
    
    def test_decode_forward(self):
        rpm, forward = decode_speed(b'\x00\x64')
        assert rpm == 100
        assert forward == True
    
    def test_decode_reverse(self):
        rpm, forward = decode_speed(encode_speed(100, False))
        assert rpm == 100
        assert forward == False
    
    def test_round_trip(self):
        for rpm in [0, 100, 1000, 3000]:
            for fwd in [True, False]:
                data = encode_speed(rpm, fwd)
                r, f = decode_speed(data)
                assert r == rpm
                assert f == fwd

class TestPositionEncoding:
    def test_encode_position(self):
        data = encode_position(16384)
        assert len(data) == 4
    
    def test_decode_position(self):
        data = b'\x00\x00\x40\x00'
        pos = decode_position(data)
        assert pos == 16384
```

---

## 七、使用示例

```python
from echem_sdl.hardware.rs485_protocol import (
    build_frame, parse_frame, verify_frame,
    encode_speed, decode_speed,
    CMD_ENABLE, CMD_SPEED, CMD_READ_ENCODER
)

# 构建使能命令帧
enable_frame = build_frame(addr=1, cmd=CMD_ENABLE, payload=b'\x01')
print(f"使能帧: {enable_frame.hex()}")

# 构建转速命令帧
speed_data = encode_speed(rpm=200, forward=True)
speed_frame = build_frame(addr=1, cmd=CMD_SPEED, payload=speed_data)
print(f"转速帧: {speed_frame.hex()}")

# 解析响应帧
response = b'\xFB\x01\x30\x00\x00\x40\x00\xCC'
if verify_frame(response):
    addr, cmd, payload = parse_frame(response)
    print(f"响应: addr={addr}, cmd={cmd:02X}, payload={payload.hex()}")
```

---

## 八、验收标准

- [ ] 所有函数按规范实现
- [ ] 校验和计算正确
- [ ] 帧构建/解析正确
- [ ] 转速/位置编解码正确
- [ ] 单元测试覆盖率 > 95%
- [ ] 类型注解完整
- [ ] docstring 规范
- [ ] 无外部依赖（纯 Python 标准库）
---

## 前端对接说明

**RS485Protocol是底层协议模块，不直接与前端对接。**

此模块提供纯函数的帧解析/构建功能，被 RS485Driver 调用。前端通过 RS485Wrapper → PumpManager → RS485Driver → RS485Protocol 的调用链间接使用。

**源项目参考**: `D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs` 中的帧解析代码。