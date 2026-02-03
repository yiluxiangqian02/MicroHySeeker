# 01 - RS485Driver 模块规范

> **文件路径**: `src/echem_sdl/hardware/rs485_driver.py`  
> **优先级**: P0 (核心模块)  
> **依赖**: `rs485_protocol.py`, `services/logger.py`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs`

---

## 一、模块职责

RS485Driver 是底层串口通信驱动，负责：
1. 管理串口连接（打开/关闭/状态检测）
2. 封装/发送 RS485 帧
3. 接收/解析响应帧
4. 帧路由与回调分发
5. 设备地址扫描与发现
6. 线程安全的读写操作
7. 支持 Mock 模式用于无硬件开发/测试

---

## 二、类设计

### 2.1 类定义

```python
from typing import Callable, Optional, List, Dict, Any
from threading import Thread, RLock, Event
from queue import Queue
import serial
from datetime import datetime

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
    
    Example:
        >>> driver = RS485Driver(port='COM3', baudrate=38400)
        >>> driver.set_callback(my_callback)
        >>> driver.open()
        >>> driver.send_frame(addr=1, cmd=0xF3, data=b'\\x00\\x01')
        >>> driver.close()
    """
```

### 2.2 构造函数

```python
def __init__(
    self,
    port: str = "COM1",
    baudrate: int = 38400,
    timeout: float = 1.0,
    logger: Optional["LoggerService"] = None,
    mock_mode: bool = False
) -> None:
    """初始化 RS485 驱动
    
    Args:
        port: 串口端口名
        baudrate: 波特率，默认 38400 (与原C#一致)
        timeout: 读取超时秒数
        logger: 日志服务实例
        mock_mode: 是否启用模拟模式
    """
```

### 2.3 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `port` | `str` | 串口端口名 |
| `baudrate` | `int` | 波特率 |
| `timeout` | `float` | 超时秒数 |
| `mock_mode` | `bool` | 是否模拟模式 |
| `is_open` | `bool` | 串口是否打开（只读） |
| `last_comm_time` | `datetime` | 最后通信时间 |

### 2.4 公开方法

#### open()
```python
def open(self) -> bool:
    """打开串口并启动读取线程
    
    Returns:
        bool: 打开是否成功
        
    Raises:
        SerialException: 串口打开失败时抛出
        
    Note:
        Mock 模式下始终返回 True，不实际打开串口
    """
```

#### close()
```python
def close(self) -> None:
    """关闭串口并停止读取线程
    
    确保读取线程正确退出，释放串口资源。
    """
```

#### send_frame()
```python
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
```

#### set_callback()
```python
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
```

#### discover_devices()
```python
def discover_devices(
    self,
    addresses: Optional[List[int]] = None,
    timeout_per_addr: float = 0.1
) -> List[int]:
    """扫描在线设备地址
    
    Args:
        addresses: 要扫描的地址列表，默认 1-12
        timeout_per_addr: 每个地址的超时秒数
        
    Returns:
        List[int]: 在线设备地址列表
    """
```

#### run_speed()
```python
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
        forward: 是否正转
        
    Returns:
        bool: 命令发送是否成功
    """
```

#### turn_to()
```python
def turn_to(
    self,
    addr: int,
    divisions: int,
    speed: int = 100,
    forward: bool = True
) -> bool:
    """转动到指定分度
    
    Args:
        addr: 设备地址
        divisions: 目标分度数
        speed: 转速
        forward: 方向
        
    Returns:
        bool: 命令发送是否成功
    """
```

#### enable_motor()
```python
def enable_motor(self, addr: int, enable: bool = True) -> bool:
    """使能/禁用电机
    
    Args:
        addr: 设备地址
        enable: 是否使能
        
    Returns:
        bool: 命令发送是否成功
    """
```

---

## 三、协议规范

### 3.1 帧格式

**发送帧 (TX)**:
```
| 帧头 | 地址 | 命令 | 数据 (N字节) | 校验和 |
| 0xFA | 1字节 | 1字节 | 0-N字节 | 1字节 |
```

**接收帧 (RX)**:
```
| 帧头 | 地址 | 命令 | 数据 (N字节) | 校验和 |
| 0xFB | 1字节 | 1字节 | 0-N字节 | 1字节 |
```

### 3.2 命令字节定义

| 命令 | 字节值 | 说明 |
|------|--------|------|
| CMD_ENABLE | 0xF3 | 使能/禁用电机 |
| CMD_SPEED | 0xF6 | 设置转速 |
| CMD_READ_ENCODER | 0x30 | 读取编码器 |
| CMD_READ_SPEED | 0x32 | 读取当前转速 |
| CMD_READ_IO | 0x34 | 读取IO状态 |
| CMD_READ_ENABLE | 0x3A | 读取使能状态 |
| CMD_READ_FAULT | 0x3E | 读取故障状态 |
| CMD_READ_VERSION | 0x40 | 读取固件版本 |

### 3.3 校验和计算

```python
def checksum(data: bytes) -> int:
    """计算校验和 (所有字节求和取低8位)"""
    return sum(data) & 0xFF
```

### 3.4 转速编码

```python
# 转速编码 (带符号16位)
# 正转: rpm (0-3000)
# 反转: -rpm 补码表示

def encode_speed(rpm: int, forward: bool) -> bytes:
    """编码转速为2字节"""
    value = rpm if forward else -rpm
    return value.to_bytes(2, 'big', signed=True)
```

---

## 四、线程模型

### 4.1 读取线程

```python
def _read_loop(self) -> None:
    """读取线程主循环
    
    持续读取串口数据，进行帧切分、校验、回调分发。
    
    帧切分策略:
    1. 查找帧头 0xFB
    2. 读取后续字节
    3. 校验校验和
    4. 调用回调
    """
```

### 4.2 线程安全

- 所有写操作使用 `RLock` 保护
- 回调在读取线程中执行
- 状态查询可并发读取

```python
# 线程安全写入示例
with self._lock:
    self._serial.write(frame)
    self._last_comm_time = datetime.now()
```

---

## 五、Mock 模式

### 5.1 Mock 行为

```python
class MockSerial:
    """模拟串口，用于无硬件测试"""
    
    def __init__(self):
        self._rx_queue: Queue[bytes] = Queue()
        self._is_open = False
    
    def open(self) -> bool:
        self._is_open = True
        return True
    
    def write(self, data: bytes) -> int:
        # 模拟响应
        response = self._generate_mock_response(data)
        self._rx_queue.put(response)
        return len(data)
    
    def read(self, size: int) -> bytes:
        try:
            return self._rx_queue.get(timeout=0.1)
        except:
            return b''
```

### 5.2 预置响应

```python
MOCK_RESPONSES = {
    CMD_ENABLE: lambda addr, data: bytes([0xFB, addr, 0xF3, 0x01]),
    CMD_SPEED: lambda addr, data: bytes([0xFB, addr, 0xF6, 0x01]),
    CMD_READ_ENCODER: lambda addr, data: bytes([0xFB, addr, 0x30, 0x00, 0x00, 0x40, 0x00]),
}
```

---

## 六、错误处理

### 6.1 异常类型

| 异常 | 触发条件 | 处理方式 |
|------|----------|----------|
| `SerialException` | 串口打开失败 | 记录ERROR，返回False |
| `TimeoutError` | 读取超时 | 记录WARNING，继续循环 |
| `ChecksumError` | 校验和不匹配 | 记录WARNING，丢弃帧 |
| `FrameError` | 帧格式错误 | 记录WARNING，丢弃帧 |

### 6.2 掉线检测

```python
def _check_connection(self) -> bool:
    """检测设备是否在线
    
    基于 last_comm_time，超过阈值则认为掉线
    """
    elapsed = (datetime.now() - self._last_comm_time).total_seconds()
    if elapsed > self.OFFLINE_THRESHOLD:
        self._logger.warning(f"RS485 通信超时: {elapsed:.1f}秒")
        return False
    return True
```

---

## 七、测试要求

### 7.1 单元测试

```python
# tests/test_rs485_driver.py

def test_open_close():
    """测试打开关闭"""
    driver = RS485Driver(mock_mode=True)
    assert driver.open() == True
    assert driver.is_open == True
    driver.close()
    assert driver.is_open == False

def test_send_frame():
    """测试帧发送"""
    driver = RS485Driver(mock_mode=True)
    driver.open()
    result = driver.send_frame(addr=1, cmd=0xF3, data=b'\x01')
    assert result == True

def test_callback():
    """测试回调触发"""
    received = []
    def callback(addr, cmd, data):
        received.append((addr, cmd, data))
    
    driver = RS485Driver(mock_mode=True)
    driver.set_callback(callback)
    driver.open()
    driver.send_frame(addr=1, cmd=0xF3, data=b'\x01')
    time.sleep(0.2)
    assert len(received) == 1

def test_discover_devices():
    """测试设备扫描"""
    driver = RS485Driver(mock_mode=True)
    driver.open()
    devices = driver.discover_devices([1, 2, 3])
    assert isinstance(devices, list)

def test_thread_safety():
    """测试并发安全"""
    driver = RS485Driver(mock_mode=True)
    driver.open()
    
    def send_task():
        for _ in range(100):
            driver.send_frame(addr=1, cmd=0xF6, data=b'\x00\x64')
    
    threads = [Thread(target=send_task) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 无异常即通过
```

### 7.2 集成测试

```python
def test_real_device_connection():
    """测试真实设备连接 (需要硬件)"""
    driver = RS485Driver(port='COM3', mock_mode=False)
    if driver.open():
        devices = driver.discover_devices()
        print(f"发现设备: {devices}")
        driver.close()
```

---

## 八、使用示例

### 8.1 基本使用

```python
from echem_sdl.hardware.rs485_driver import RS485Driver
from echem_sdl.services.logger import LoggerService

logger = LoggerService()
driver = RS485Driver(
    port='COM3',
    baudrate=38400,
    logger=logger,
    mock_mode=False
)

def on_response(addr: int, cmd: int, data: bytes):
    print(f"收到响应: addr={addr}, cmd={cmd:02X}, data={data.hex()}")

driver.set_callback(on_response)
driver.open()

# 扫描设备
devices = driver.discover_devices()
print(f"在线设备: {devices}")

# 启动电机
driver.run_speed(addr=1, rpm=100, forward=True)

# 关闭
driver.close()
```

### 8.2 与 Diluter 配合

```python
# 在 Diluter 中使用
class Diluter:
    def __init__(self, driver: RS485Driver, addr: int):
        self._driver = driver
        self._addr = addr
        driver.set_callback(self._on_response)
    
    def _on_response(self, addr: int, cmd: int, data: bytes):
        if addr == self._addr:
            self._handle_response(cmd, data)
```

---

## 九、前端对接说明

**RS485Driver是底层驱动模块，不直接与前端对接。**

### 9.1 调用层级

```
前端 (UI)
  ↓
RS485Wrapper (前端适配器)
  ↓
PumpManager / Diluter / Flusher (硬件管理层)
  ↓
RS485Driver (底层驱动) ← 本模块
  ↓
串口硬件
```

### 9.2 如何使用

前端通过 **RS485Wrapper** 间接使用 RS485Driver：

```python
# RS485Wrapper初始化时创建Driver（通过LibContext）
wrapper = RS485Wrapper()
wrapper.open_port("COM3", 38400)  # 内部调用RS485Driver

# 前端不需要直接使用RS485Driver
```

### 9.3 源项目参考

**C# 文件**: `D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs`

**重点参考**：
- 串口打开/关闭逻辑
- 异步读取线程实现
- 帧格式和校验
- 设备扫描机制

---

## 十、验收标准

- [ ] 类与接口按规范实现
- [ ] 支持真实串口和 Mock 模式
- [ ] 帧封装/解析符合协议
- [ ] 线程安全（锁保护写操作）
- [ ] 回调在读取线程触发
- [ ] 掉线检测功能正常
- [ ] 能被PumpManager等上层模块正确使用
- [ ] test_rs485_connection.py 通过
- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] docstring 规范
- [ ] 可被 Diluter/Flusher 直接使用
