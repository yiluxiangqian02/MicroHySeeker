## 1. 模块定位与职责
- 文件：`src/echem_sdl/hardware/diluter.py`
- 作用：配液泵高层控制。根据溶液体积/比例计算步进数，通过 `RS485Driver` 发送命令驱动电机注液/抽液，维护运行状态（is_running/has_infused），提供注液/停止/状态查询接口，供 `ProgStep`/ExperimentEngine 调用。泵数量完全动态，由配置 (`diluter_pumps`) 决定，不得写死。

## 2. 文件与类结构
- `class Diluter`：
  - 初始化参数：
    - `address: int`, `driver: RS485Driver`,
    - `rpm: int = 100`, `microstep: int = 16`,
    - `volume_per_rev: float = 0.5`, `steps_per_rev: int = 200`,
    - `name: str | None = None`, `calibration: dict | None = None`,
    - `logger: LoggerService | None = None`
  - 字段：
    - `address: int`
    - `driver: RS485Driver`
    - `logger: LoggerService | None`
    - `rpm: int`
    - `microstep: int`
    - `volume_per_rev: float`（默认 ml/rev，可配置/校准）
    - `steps_per_rev: int`
    - `name: str | None`
    - `calibration: dict | None`（如 divpermL/volume_per_rev/steps_per_rev 等）
    - `is_running: bool = False`
    - `has_infused: bool = False`
    - `runtime: float = 0.0`
    - `last_command: str | None`
    - 可选：`lock: threading.RLock`
  - 方法（含类型注解）：
    - `infuse(volume_ml: float, forward: bool = True) -> None`: 计算步进量并发送运行命令。
    - `stop() -> None`: 发送停止命令。
    - `is_infusing() -> bool`
    - `has_infused() -> bool`
    - `compute_steps(volume_ml: float) -> int`: 体积转步进。
    - `handle_response(frame: bytes) -> None`: 解析回调，更新状态。
    - `status_query() -> dict`: 请求并解析状态。
    - 可选：`async infuse_async(...)`

## 3. 依赖说明
- 内部依赖：`hardware.rs485_driver.RS485Driver`, `services.logger.LoggerService`, `utils.constants`
- 标准库：`threading`, `time`, `struct`, `typing`

## 4. 线程与异步策略
- 所有命令发送需持锁（防止并发写 RS485）。
- `handle_response` 可能在读线程执行，需线程安全更新状态。
- 典型模式：同步控制（主线程调用 infuse/stop），状态由回调更新；可选 asyncio 封装。

## 5. 错误与日志处理机制
- 参数非法（负体积/缺 driver）：记录 error 并抛出或返回。
- 发送失败/校验错误：warning；超时未响应：warning；RS485 异常：error。
- 启动/停止/完成等关键事件：info 日志。

## 6. 测试要求
- 步进计算：给定体积与步距/校准参数计算正确。
- 命令封装：生成帧格式符合协议，并通过 mock Driver 验证调用。
- 运行状态：`is_running`/`has_infused` 切换正确。
- 响应处理：`handle_response` 按帧内容更新状态。
- 错误路径：异常参数/掉线/超时；日志与状态符合预期。
- 并发：多线程 infuse + stop 不冲突（锁有效）。
- mock 模式：与 RS485Driver 模拟交互正常。
- 动态泵：可实例化多个 Diluter（≥6），互不影响。

## 7. 文档与注释要求
- 模块 docstring：描述体积→步进换算、通信协议、状态流；强调泵列表由配置加载，新增泵无需改代码。
-, 方法 docstring：参数、返回、异常、线程注意事项。
- 类型注解完整；在关键计算/发送/解析处添加行内注释。

## 8. 验收标准
- 类与接口完整；体积→步进逻辑正确；状态流合理。
- 日志输出符合预期；线程安全；支持动态泵数量与 mock。
- 测试通过：步进计算、收发/解析、状态更新、异常路径、并发。
- 可直接被 `ProgStep`/ExperimentEngine 使用，无写死泵数量。 
