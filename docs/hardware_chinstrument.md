## 1. 模块职责
- `CHInstrument` 封装与 CH Instruments 电化学工作站 DLL（`libec.dll`）的交互：加载技术列表、设置参数/技术、启动实验、轮询运行状态、采集曲线数据，并在无设备时提供模拟模式；完成后自动导出 CSV 并记录运行状态。

## 2. 公共 API（名称、参数、返回值、用途）
- 构造 `CHInstrument()`：初始化 DLL、背景采集线程、默认参数，检测连接性。
- `void CHIInitialize()`：配置 BackgroundWorker，查询支持的技术，设置默认参数（灵敏度、初始电位等），默认设定 CV 技术并尝试运行以检测连接。
- `void SetExperiment(ProgStep ps)`：根据步骤类型（CV/LSV/i-t）写入 DLL 参数、选择技术、生成描述字符串，设置步长 `StepSeconds`。
- `void RunExperiment(ProgStep ps)`：设置实验参数并启动采集线程。
- `void RunExperiment()`：若后台采集未忙，则启动 `ReadData`。
- `void CancelSimulation()`：请求取消后台采集（用于模拟模式）。
- 低层 DLL 入口（P/Invoke）：`CHI_hasTechnique`, `CHI_setTechnique`, `CHI_setParameter`, `CHI_runExperiment`, `CHI_experimentIsRunning`, `CHI_showErrorStatus`, `CHI_getExperimentData`, `CHI_getErrorStatus`, `CHI_getParameter`。

## 3. 内部数据结构
- P/Invoke 句柄：上述 DLL 函数。
- 参数与状态：`Sensitivity`（默认 1e-6 A/V）、`Technique`、`Description`、`StepSeconds`、`duration`（未使用）、`CHIRunning`、`StartTime`。
- 数据缓存：`float[] x`, `float[] y`（长度 `n=65536`），`List<int> Techniques`（支持的技术编号）。
- 线程：`BackgroundWorker ReadData`（DoWork/ProgressChanged/RunWorkerCompleted）。
- 文件输出：使用 `LIB.DataFilePath`、`LIB.ExpIDString`、`Technique` 组合文件名，UTF-8 CSV。

## 4. 工作流程与状态机
- 初始化：
  - 构建 BackgroundWorker（支持进度、取消；绑定事件）。
  - 查询 0..44 技术支持，填充 `Techniques`。
  - 设置默认参数 `m_iSens`、`m_ei/eh/el/ef`、`m_inpcl`，设定 CV 技术。
  - 试跑 `CHI_runExperiment()`，若报 “Link failed” 则标记 `LIB.CHIConnected=false` 并写警告日志。
- 运行（`ReadData_DoWork`）：
  - 标记 `CHIRunning=true`，清空 `LIB.VAPoints`，初始化 x/y 数组。
  - 若已连接：
    - 调用 `CHI_runExperiment()`（失败则显示错误状态）。
    - 循环 `while CHI_experimentIsRunning()==1`：检查取消 → `CHI_getExperimentData(x,y,n)` → 从上次索引复制非零 y 点 → 追加到 `LIB.VAPoints`（加锁） → `Thread.Sleep(50)`。
  - 未连接（模拟）：随机生成点，持续到 `StepSeconds`。
  - 完成后 `ReportProgress(100)`。
- 完成回调（`RunWorkerCompleted`）：
  - `CHIRunning=false`。
  - 拼接描述 + 电解液信息 + 曲线点，写入 CSV (`[ExpID] Technique HHmmss.csv`)。
  - 记录“数据已保存”日志。
- 状态标志：`CHIRunning` 控制 Experiment 判定；连接状态在 `LIB.CHIConnected`。

## 5. 典型调用链
- `Experiment.ExecuteStep` (EChem) → `LIB.CHI.RunExperiment(ps)` → `SetExperiment(ps)` 设置参数/技术 → `RunExperiment()` 启动后台采集 → DLL 实验运行中 → `ReadData_DoWork` 轮询数据 → 完成后生成 CSV 与日志。

## 6. 与其他模块的依赖关系
- `ProgStep`：读取电化学参数（E0/EH/EL/EF、ScanRate、QuietTime、RunTime、SamplingInterval、SegNum、Sensitivity、AutoSensibility、ScanDir）。
- `LIB`：全局状态/命名字符串/日志；`MixedSol`（用于导出电解液信息）、`VAPoints` 数据曲线、`ExpIDString`、`DataFilePath`、`CHIConnected`。
- Experiment：使用 `CHIRunning` 判断步骤状态结束；调用入口 `RunExperiment(ps)`。
- UI/日志：依赖 `LIB.NamedStrings` 消息；文件输出用于数据查看。

## 7. 必须在 Python 重写中保留的逻辑（语言无关）
- DLL 接口语义：设置技术/参数、启动实验、轮询是否运行、读取数据缓冲。
- 参数映射：CV/LSV/i-t 对应的 DLL 参数键（`m_ei/m_eh/m_el/m_ef/m_vv/m_qt/m_inpcl/m_pn/m_inpsi/m_bAutoSens/m_iSens` 等）。
- 实验运行标志与结束判定：以 DLL `experimentIsRunning` 返回值为准。
- 数据采集循环：增量取新数据点、追加到全局曲线；模拟模式替代无设备。
- 结果导出：实验结束后生成 CSV，包括描述与电解液信息。
- 连接检测与错误处理：初始化试跑失败时标记未连接并写警告。

## 8. Python 重写可改进的部分（语言相关）
- 异步模型：使用 `asyncio`/线程池而非 BackgroundWorker；显式超时与取消。
- 数据获取：支持实时事件/回调将新点推给 UI，而非全局锁列表。
- 错误处理：捕获 DLL 调用异常、提供详细错误码；初始化时提供显式 Connect/Disconnect。
- 文件与数据管线：可选实时绘图、二进制缓存、延迟保存；文件名/路径可配置。
- 配置注入：拆除对全局 `LIB` 的硬依赖，使用上下文注入 logger、数据缓冲、路径。
- 线程安全：采用线程安全队列或信号槽避免手动锁。

## 9. 数据流描述（文字）
Experiment 触发电化学步骤 → `SetExperiment` 将 ProgStep 参数写入 DLL、选择技术 → `RunExperiment` 启动后台采集 → DLL `runExperiment` 开始 → 循环 `experimentIsRunning`：`getExperimentData` 取新点 → 追加到曲线缓冲 → 结束 → 生成描述 + 电解液信息 + 曲线 CSV，记录日志 → `CHIRunning` 置 false，Experiment 检测到步骤完成。
