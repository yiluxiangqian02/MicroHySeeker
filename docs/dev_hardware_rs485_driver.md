## 1. 模块定位与职责
- 文件：`src/echem_sdl/hardware/rs485_driver.py`
- 作用：封装 RS485 串口通信，提供帧封装/解析、读写线程、地址发现与回调注册；为 Diluter/Flusher 等硬件模块提供底层通信。驱动对设备数量/类型不设限制，所有设备以地址区分。支持线程模式（可选 asyncio），包含自动重连、超时检测、线程安全与 mock 模式。

## 2. 文件与类结构
- `class RS485Driver`：
  - 初始化参数：`port: str`, `baudrate: int = 38400`, `timeout: float = 1.0`, `logger: LoggerService | None = None`, `mock_mode: bool = False`
  - 字段：
    - `serial: serial.Serial | None`
    - `lock: threading.RLock`
    - `running: bool`
    - `read_thread: threading.Thread | None`
    - `callback: Callable[[bytes], None] | None`
    - `last_comm_time: datetime`
    - `mock_mode: bool`
    - 可选：`queue: Queue[bytes]`
  - 方法（含类型注解）：
    - `open() -> None`: 打开串口并启动读取线程（mock_mode 跳过串口）。
    - `close() -> None`: 停止线程并关闭串口。
    - `send_frame(addr: int, cmd: int, data: bytes = b"") -> None`: 封装并发送一帧。
    - `read_loop() -> None`: 持续读取串口、切帧、校验，并调用回调。
    - `set_callback(cb: Callable[[bytes], None]) -> None`
    - `discover_devices(addresses: Iterable[int] | None = None) -> list[int]`: 轮询地址段返回在线设备（数量不限）。
    - `encode_frame(addr: int, cmd: int, data: bytes) -> bytes`: 按协议封装。
    - `decode_frame(frame: bytes) -> dict`: 解析帧并校验。
    - `mock_send_frame(addr: int, cmd: int, data: bytes = b"") -> None`: 在 mock 模式下直接触发回调。
    - 可选异步：`async send_async(...)`, `async listen_async(...)`.

## 3. 依赖说明
- 标准库：`threading`, `time`, `datetime`, `queue`, `struct`, `typing`
- 第三方：`pyserial`
- 内部：`services.logger.LoggerService`, `utils.constants`（协议常量）

## 4. 线程与异步策略
- 读写线程独立运行；`read_loop` 在后台线程执行。
- 写操作持 `lock`；回调在读线程执行（调用方需处理 UI 线程切换）。
- asyncio 作为可选模式；默认使用线程。

## 5. 错误与日志处理机制
- 打开串口失败：记录 error，抛异常或进入 mock 模式（视参数）。
- 写入超时/校验失败：warning；读帧异常：warning，继续循环；严重错误可尝试重连。
- 掉线检测：基于 `last_comm_time`，超时记录 warning/error。
- mock_mode：info，所有收发走模拟路径。

## 6. 测试要求
- 打开/关闭：状态正确，线程启动/退出。
- 帧收发：`encode_frame`/`decode_frame` 符合协议；发送调用串口写或 mock 回调。
- 回调：收到帧后调用注册回调（模拟数据）。
- 并发：多线程 `send_frame` 无竞争（锁生效）。
- 超时/掉线：模拟无响应检测与日志。
- 错误路径：串口不可用、校验错误，行为符合预期。
- `discover_devices`：返回可控结果（mock 可预置响应），不限制数量。

## 7. 文档与注释要求
- 模块 docstring：说明协议封装、线程模型、mock 模式、回调线程、设备数量不限制。
- 方法 docstring：参数、返回、异常、线程注意事项。
- 类型注解完整；在锁/校验/切帧处添加行内注释。

## 8. 验收标准
- 类与接口完整，协议封装/解析正确。
- 线程安全；日志输出规范。
- mock 模式可独立运行。
- 测试通过：收发/解析/异常/并发/掉线检测。
- 可直接被 Diluter/Flusher 等模块使用，支持任意数量设备。 
