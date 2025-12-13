1. 模块定位与职责
- 文件：`src/echem_sdl/hardware/chi.py`
- 封装 CH Instruments 电化学工作站；在有设备/DLL 时调用 libec 接口完成技术设置、参数写入、启动/停止实验、轮询运行状态并获取数据点；在无设备或 DLL 缺失时自动进入模拟模式生成虚拟曲线。
- 职责：映射实验参数（CV/LSV/i–t 等）、设置技术与扫描参数、启动/停止实验、轮询 `experimentIsRunning`、拉取实时 (x,y) 数据并写入缓冲供 ExperimentEngine 使用、实验结束时导出数据。CHI 为可选设备，缺失时不得阻断实验。

2. 文件与类结构
- `class CHIInstrument`
  - 初始化参数：
    - `config: dict`
    - `logger: LoggerService | None = None`
    - `context: LibContext | None = None`
    - `mock: bool = False`（如 DLL/设备不可用自动置 True）
    - 可选 `dll_path: str | None = None`
  - 核心字段：
    - 状态：`connected: bool`, `mock: bool`, `running: bool`, `start_time: datetime | None`, `technique: str | None`
    - 参数缓冲：`params: dict`
    - 数据缓冲：`data_points: list[tuple[float, float]]`
    - 线程：`worker: threading.Thread | None`
    - 同步：`lock: threading.RLock`
    - DLL 入口（可用时）：`chi_hasTechnique`, `chi_setTechnique`, `chi_setParameter`, `chi_runExperiment`, `chi_experimentIsRunning`, `chi_getExperimentData`
  - 方法（含类型注解）：
    - `initialize() -> None`
    - `set_experiment(step: ProgStep) -> None`
    - `run() -> None`
    - `stop() -> None`
    - `is_running() -> bool`
    - `get_latest_points() -> list[tuple[float, float]]`
    - `handle_real_data() -> None`（worker 轮询 DLL）
    - `handle_mock_data() -> None`（模拟数据生成）
    - `export(path: Path) -> None`（使用 data_exporter 保存）

3. 依赖说明
- 内部：`core.prog_step.ProgStep`, `lib_context.LibContext`, `services.logger.LoggerService`, 可选 `services.data_exporter.DataExporter`
- 外部：`ctypes`（加载 DLL）、`threading`、`time`、`typing`

4. 线程与异步策略
- `run()` 创建后台线程 `worker`。
- worker 循环（持锁更新状态/数据）：
  - DLL 模式：调用 `chi_experimentIsRunning`；若运行则 `chi_getExperimentData` 追加新点；运行结束跳出。
  - mock 模式：按时间步生成虚拟 (x,y) 曲线，直到达到预估时长或被 `stop()` 打断。
- `stop()` 必须安全终止 worker（置标志、等待退出）。
- ExperimentEngine 不直接触碰 DLL，必须通过 CHIInstrument API。

5. 错误与日志机制
- DLL 加载失败：warning，自动进入 mock。
- 技术/参数设置失败：error。
- `runExperiment` 失败：error 并可转入 mock。
- `experimentIsRunning` 死循环或超时：警告/超时处理。
- 数据读取失败：warning。
- 必记日志：初始化成功/失败、技术设置、参数设置、实验开始/结束、DLL 异常、模拟模式启动、导出完成。

6. 测试要求
- 模拟模式：可运行完整流程，数据点数量递增，时间推进正常，`stop()` 立即结束。
- DLL 模式（可用伪 DLL mock）：参数映射正确（E0/EH/EL/ScanRate 等），`experimentIsRunning` 状态切换正确，`getExperimentData` 解析正确。
- 错误路径：DLL 缺失自动 mock，参数缺失记录错误，线程正常退出无死锁，多次 run/stop 稳定。

7. 文档与注释要求
- 模块 docstring：描述 DLL + 模拟模式、数据流、线程模型。
- 每个方法 docstring：参数、返回、线程注意事项。
- 类型注解完整；DLL 调用与数据解析处加行内注释。

8. 验收标准
- API 完整，可被 ExperimentEngine 直接调用。
- 兼容无设备模式（mock），真实/模拟数据结构一致。
- 线程安全，不阻塞主线程。
- 日志完整，导出可用。
- 测试通过：真实路径、模拟、错误路径。 
