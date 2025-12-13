1. 模块定位与职责
- 文件：`src/echem_sdl/hardware/positioner.py`
- 三轴平台（Positioner）的高层控制模块，**当前系统默认不启用**。需要在启用/禁用（mock）两种模式下安全运行：启用时正常连接独立串口，禁用时不连接硬件且所有 API 不抛错。
- 使用独立串口（pyserial），文本协议沿用 C# 版（指令如 CJXSA / CJXCgX…Y…Z…），编码 GB2312。
- 配置驱动（通过 `settings_service` 的 `positioner` 字段）：端口、波特率（默认 31400）、脉冲换算参数、点位表、超时等；不得写死端口/速度。
- ExperimentEngine 不得强依赖此模块；Positioner 不工作不会阻断配液/冲洗/电化学流程。

2. 协议与硬件约定（基于旧 C# Positioner）
- 串口参数：`baudrate` 可配置（默认 **31400**），`bytesize=8`，`parity='N'`，`stopbits=1`，编码 GB2312。
- 典型指令（文本协议）：
  - 三轴移动：`CJXCgX{px}Y{py}Z{pz}F{speed}$`
  - 单轴移动：`CJXCgX{px}F{speed}$`（轴名可换 X/Y/Z）
  - 状态查询：`CJXSA`
  - 归零：`CJXZX` / `CJXZY` / `CJXZZ` / `CJXZALL`
- 响应格式：包含 `"运行中"` / `"已停止"`，以及 `X:xxx Y:xxx Z:xxx` 坐标。
- 坐标换算：cm ↔ 脉冲（`pulse_per_cmX/Y/Z`）；行/列/层 ↔ cm（`cm_per_row/col/lay`）。

3. 文件与类结构
- `class Positioner`
  - 初始化参数：
    - `port: str | None`
    - `baudrate: int = 31400`
    - `timeout: float = 0.5`
    - `config: dict | None = None`
    - `logger: LoggerService | None = None`
    - `mock: bool = False`（禁用模式）
  - 字段：
    - 串口：`serial: serial.Serial | None`，`connected: bool`
    - 物理参数（均来自 config）：`pulse_per_cmX/Y/Z`，`cm_per_row/col/lay`，`max_row/col/lay`，`pick_height`
    - 当前坐标：`row/col/lay`，`px/py/pz`
    - 状态：`busy: bool`，`live: bool`，`last_talk: datetime`，`offline_timeout: float`（默认 3 秒）
    - 队列与锁：`_queue: list[str]`，`_lock: threading.RLock`
    - 其他：`default_z: float`

4. 方法（含类型标注）
- 串口管理：`connect()`, `disconnect()`, `is_connected() -> bool`
- 运动控制（mock 模式下不报错）：`move_to(row: int, col: int, lay: int)`, `move_inc(dr: int, dc: int, dl: int)`, `move_to_cm(x: float, y: float, z: float)`, `home_all()`, `home_axis(axis: str)`, `pick_and_place(row, col, lay)`
- 状态与解析：`is_busy() -> bool`, `update_status()`, `handle_response(data: str) -> None`, `check_link()`
- 队列与封装：`enqueue(cmd: str)`, `_send_next()`, 坐标换算工具 `rowcol_to_cm(...)` / `cm_to_pulse(...)`

5. 线程与异步策略
- 启用模式下必须有读线程：持续读串口文本，触发 `handle_response`；发送命令需加锁串行化。
- `handle_response` 在读线程执行，需线程安全更新坐标与 busy/live。
- mock 模式：不启动线程、不打开串口、不解析数据，所有控制方法直接返回且维护合理的本地状态。

6. 错误与日志机制
- 串口打开失败：记录 error，自动切换到 mock/未连接状态。
- 解析状态失败：warning，不中断流程。
- 坐标越界：`ValueError` + error 日志。
- 掉线检测：`last_talk` 超时记录 warning。
- 关键动作（移动、归零、pick_and_place）：info 日志。

7. 测试要求
- mock 模式：不连接串口也能调用全部 API，无异常。
- 坐标换算：pulse ↔ cm ↔ row/col/lay 正确。
- 命令封装：move/home/status 帧文本格式正确（含速度、终止符）。
- 状态解析：busy/live 切换正确，坐标更新正确。
- 掉线检测：超时后触发 warning；恢复后状态可重置。
- 队列与锁：多线程调用 move/status_query 不产生竞争或丢命令。

8. 文档与注释要求
- 模块 docstring 解释：当前默认禁用、独立串口设计、波特率配置化。
- 所有方法具备 docstring 与类型注解；坐标换算与协议解析处添加行内注释。
- 明示 ExperimentEngine 不应依赖 Positioner 的可用性。
