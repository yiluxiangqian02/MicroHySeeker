## 1. 模块定位与职责
- 文件：`src/echem_sdl/hardware/flusher_pump.py`
- 作用：冲洗系统中的单泵设备（inlet/outlet/transfer），提供基本动作：运行（正/反转）、停止、状态上报。流程控制由 Flusher 负责，FlusherPump 只负责执行。
- 特点：独立 RS485 地址，由 PumpManager 统一注册并路由；参数 100% 来自配置（address/rpm/direction/cycle_duration）；禁止写死泵数量/角色/地址；是 Diluter 的简化执行器（无体积计算）。

## 2. 文件与类结构
- `class FlusherPump`
  - 初始化参数：
    - `address: int`
    - `driver: RS485Driver`
    - `pump_rpm: int`
    - `direction: str`（"forward" | "reverse"）
    - `cycle_duration: float`
    - `name: str | None = None`
    - `logger: LoggerService | None = None`
    - `mock: bool = False`
  - 字段：
    - `address: int`
    - `driver: RS485Driver`
    - `logger: LoggerService | None`
    - `pump_rpm: int`
    - `direction: str`
    - `cycle_duration: float`
    - `name: str | None`
    - 状态：`is_running: bool = False`, `last_start_time: datetime | None`, `last_stop_time: datetime | None`, `last_response: dict | None`, `has_error: bool = False`
    - 并发：`lock: threading.RLock`
  - 方法（含类型注解）：
    - `run() -> None`: 发送启动命令（rpm + direction）。
    - `stop() -> None`: 发送停止命令。
    - `is_pumping() -> bool`
    - `status() -> dict`
    - `handle_response(frame: bytes) -> None`: PumpManager 路由后调用，解析状态帧。
    - `set_rpm(rpm: int) -> None`
    - `set_direction(direction: str) -> None`
    - mock 支持：`mock_tick() -> None`

## 3. 依赖说明
- 内部：`hardware.rs485_driver.RS485Driver`, `services.logger.LoggerService`, `utils.constants`（命令/方向常量）
- 标准库：`threading`, `datetime`, `struct`, `typing`

## 4. 线程与异步策略
- 所有发送命令需持 `lock`（RS485 写序列化）。
- `handle_response` 在 RS485Driver 读线程执行，需线程安全。
- FlusherPump 不创建线程，仅被 Flusher/Engine 调用；mock 模式下 run/stop 仅更新状态不发命令。

## 5. 错误与日志处理机制
- 配置缺失字段（address/rpm/direction/cycle_duration）：error。
- 非法 rpm/direction：error，拒绝执行。
- 发送失败：warning；响应解析失败：warning。
- 泵启动/停止成功：info；mock 模式启动：info。

## 6. 测试要求
- 注册与实例化：传入配置生成实例，多个泵互不干扰。
- 行为：`run()` 设置状态/发正确帧；`stop()` 关闭；`handle_response` 更新状态。
- mock：run/stop 不访问串口；`mock_tick` 按 `cycle_duration` 模拟结束。
- 路由：PumpManager 收帧 → 正确调用 `handle_response`。
- 并发：run + stop 多线程安全。
- 错误路径：非法 rpm/direction → error 不执行；未知地址在 PumpManager 记录 warning。

## 7. 文档与注释要求
- 模块 docstring：说明 FlusherPump 作为最小执行器、配置化参数。
- 方法 docstring：参数、返回、异常、线程注意事项。
- 类型注解完整；关键处（帧封装、解析）添加行内注释。

## 8. 验收标准
- 100% 配置驱动，无硬编码数量/地址。
- RS485 命令发送正确，状态更新可靠；mock/真实模式状态结构一致。
- 线程安全，无竞争；与 PumpManager、Flusher 集成正常。
- 全部测试（正常/异常/并发）通过。 
