1. 模块定位与职责
- 文件：`src/echem_sdl/hardware/flusher.py`
- 作用：冲洗系统流程控制器，管理三台 `FlusherPump`（inlet/outlet/transfer），按排空→进液→转移的固定流程执行，支持多次循环。
- Flusher 负责：启动/停止冲洗流程，控制各阶段泵动作，基于阶段时长切换阶段（内部定时或外层 tick），管理循环次数，提供状态查询。
- 特点：三个泵均由配置 + PumpManager 实例化为 `FlusherPump` 传入；Flusher 仅编排，不直接发送 RS485；不得写死泵数量/地址/方向；状态可被 ExperimentEngine/ProgStep 查询。

2. 文件与类结构
- `class Flusher`
  - 初始化参数：
    - `inlet: FlusherPump`
    - `outlet: FlusherPump`
    - `transfer: FlusherPump`
    - `logger: LoggerService | None = None`
    - `mock: bool = False`
    - 可选 `use_external_tick: bool = False`（True 时由 ExperimentEngine tick 驱动阶段切换）
  - 字段：
    - `inlet`, `outlet`, `transfer`: FlusherPump
    - `logger: LoggerService | None`
    - `mock: bool`
    - 配置/状态：`cycle_count: int = 1`, `current_cycle: int = 0`, `current_phase: str | None`（"evacuate"/"fill"/"transfer"/None）
    - 运行状态：`is_running: bool = False`, `phase_start_time: datetime | None`, `phase_duration: float`（当前阶段时长，取对应 FlusherPump.cycle_duration）
    - 定时：`timer: threading.Timer | None`, `use_external_tick: bool`
    - 并发：`lock: threading.RLock`
  - 方法（含类型注解）：
    - 流程控制：`set_cycles(n: int) -> None`, `start() -> None`, `stop() -> None`, `advance_phase() -> None`（外部 tick 模式调用）
    - 阶段启动：`start_evacuate() -> None`, `start_fill() -> None`, `start_transfer() -> None`
    - 阶段停止：`stop_evacuate() -> None`, `stop_fill() -> None`, `stop_transfer() -> None`
    - 状态查询：`is_flushing() -> bool`, `get_phase() -> str | None`, `get_progress() -> dict`
    - 内部工具：`_schedule_next_phase(seconds: float) -> None`, `_cancel_timer() -> None`, `_log_phase_change(phase: str) -> None`

3. 依赖说明
- 内部：`hardware.flusher_pump.FlusherPump`, `services.logger.LoggerService`, `utils.constants`
- 标准库：`threading`, `datetime`, `typing`

4. 线程与异步策略
- 所有状态变更必须在 `lock` 内执行。
- 定时模式：
  - 内部 Timer（默认）：按 `phase_duration` 启动 `threading.Timer` 触发下一阶段。
  - 外部 tick：`use_external_tick=True` 时由 ExperimentEngine 周期调用 `advance_phase()`，不创建 Timer。
- Flusher 不直接触碰 RS485，仅调用 FlusherPump.run/stop；mock 模式不操作串口，只更新状态。

5. 错误与日志处理机制
- 缺失 FlusherPump 实例：error，拒绝启动。
- pump.run()/stop() 失败：warning，流程继续但记录。
- 阶段切换异常：error，停止流程。
- 循环完成：info（记录 cycle 数/总耗时）。

6. 测试要求
- 流程测试：`start()` → phase="evacuate" 调用 outlet.run；阶段结束进入 fill→inlet.run；再到 transfer→transfer.run；一循环完成后 `current_cycle++`；达到 `cycle_count` 自动 stop。
- 外部 tick：`advance_phase()` 能正确推进阶段（无 Timer）。
- 泵行为：各阶段仅触发对应泵动作，无交叉。
- 并发：run/stop/advance_phase 多线程下无竞争（锁有效）。
- mock：无串口动作但时序与状态流正常。
- 错误路径：pump.run 失败 warning；缺泵配置 error 阻止启动；Timer 异常 error 后自动 stop。

7. 文档与注释要求
- 模块 docstring：说明 Flusher 职责、三阶段流程、内部 Timer vs 外部 tick 模式。
- 方法 docstring：参数、返回、异常、线程注意事项。
- 类型注解完整；阶段切换逻辑处添加行内注释。

8. 验收标准
- 100% 配置驱动，无硬编码数量/地址。
- 三阶段流程稳定，可多次循环；与 FlusherPump 集成正确。
- 支持 Timer 和 external tick 模式。
- 线程安全，日志规范；测试通过（流程/并发/mock/异常）。 
