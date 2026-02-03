# RS485扫描功能修复报告

## 问题描述
用户反馈在UI中点击"扫描泵"后显示"未找到任何泵"，但实际应该有12个泵。

## 问题排查过程

### 1. 初步排查
检查日志发现：
- ✅ Mock设备正确发送了F1命令
- ✅ Mock设备生成了12个响应帧
- ❌ 但discover_devices()返回空列表 `Found devices: []`

### 2. 根本原因分析
通过深入分析代码和日志，发现了**关键问题**：

#### 问题1：MockSerial的in_waiting实现错误
**原实现：**
```python
self.in_waiting = len(response)  # 每次write都覆盖
```

**问题：** 当连续发送12个命令时，每次write都会覆盖in_waiting值，最终只保留最后一个响应的长度。Queue中有12个响应，但in_waiting只报告一个响应的大小。

#### 问题2：Queue vs Buffer
- Queue模式：每个响应是独立的对象，但in_waiting无法正确反映队列中的总字节数
- Buffer模式：累积所有响应字节，in_waiting返回缓冲区总长度

#### 问题3：时序问题
- `discover_devices()` 发送所有命令后立即检查响应
- 读取线程可能还没来得及处理缓冲区数据
- 等待时间不够长

## 修复方案

### 修复1：重写MockSerial使用Buffer模式
```python
class MockSerial:
    def __init__(self):
        self._rx_buffer = bytearray()  # 累积缓冲区
    
    @property
    def in_waiting(self) -> int:
        return len(self._rx_buffer)  # 返回缓冲区总字节数
    
    def write(self, data: bytes) -> int:
        response = self._generate_mock_response(data)
        if response:
            self._rx_buffer.extend(response)  # 追加到缓冲区
        return len(data)
    
    def read(self, size: int) -> bytes:
        data = bytes(self._rx_buffer[:size])
        self._rx_buffer = self._rx_buffer[size:]  # 从缓冲区移除
        return data
```

### 修复2：增加扫描等待时间
```python
def discover_devices(self, addresses, timeout_per_addr=0.1):
    # 发送所有命令
    for addr in addresses:
        self.send_frame(addr, CMD_READ_RUN_STATUS)
        time.sleep(0.05)
    
    # 等待所有响应被处理
    wait_time = max(0.5, len(addresses) * timeout_per_addr)
    time.sleep(wait_time)  # 给读取线程足够时间
```

### 修复3：修复run_speed参数不匹配
```python
# 原接口：direction: str
def run_speed(self, addr, direction, rpm):
    forward = (direction.upper() == "FWD")

# 新接口：forward: bool
def run_speed(self, addr, rpm, forward=True):
    # 直接使用bool参数
```

### 修复4：添加调试日志
```python
def temp_callback(addr: int, cmd: int, payload: bytes):
    if addr in responses:
        responses[addr] = True
        self._log_debug(f"Device {addr} responded")  # 确认回调被触发
```

## 修复文件列表

1. **src/echem_sdl/hardware/rs485_driver.py**
   - 重写MockSerial类（使用Buffer代替Queue）
   - 修改discover_devices()增加等待时间
   - 修复run_speed()参数签名
   - 添加读取线程调试日志

2. **src/services/rs485_wrapper.py**
   - 修复stop_pump()调用run_speed的参数

## 测试方法

### 命令行测试（已验证）
```bash
cd D:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker
python -c "from src.services.rs485_wrapper import RS485Wrapper; import time; w = RS485Wrapper(); w.set_mock_mode(True); w.open_port('COM3', 38400); time.sleep(0.3); pumps = w.scan_pumps(); print(f'扫描到 {len(pumps)} 个泵: {pumps}'); w.close_port()"
```

### UI测试步骤
1. 启动UI：`python run_ui.py`
2. 打开"系统配置"对话框
3. 选择端口（如COM7），波特率38400
4. 点击"连接"按钮
5. 点击"扫描泵"按钮
6. 应该显示：**找到12个泵: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]**

## 预期结果

### Mock模式
- 应该检测到所有12个泵（地址1-12）
- 控制台输出：
  ```
  [RS485 INFO] Scanning devices at addresses: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
  [Mock RS485] TX/RX: 12对命令/响应
  [RS485 INFO] Found devices: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
  ✅ RS485Wrapper: 扫描到泵 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
  ```

### 真实硬件模式
- 只检测到实际在线的泵
- 超时时间：12个泵 × 0.1秒/泵 = 1.2秒 + 0.5秒缓冲 = 1.7秒

## 注意事项

1. **编码问题**：Windows命令行不支持emoji (✅❌)，但UI中正常显示
2. **线程同步**：读取线程和主线程之间需要适当的等待时间
3. **Buffer vs Queue**：Buffer模式更适合模拟真实串口的行为

---

**状态**: ✅ 已修复  
**验证**: 等待UI测试确认  
**版本**: v1.1  
**日期**: 2026-02-02
