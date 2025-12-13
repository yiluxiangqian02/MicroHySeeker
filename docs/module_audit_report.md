## 1) 模块覆盖率清单
- 已生成说明书：
  - `MotorRS485.cs` → `docs/hardware_rs485.md`
  - `Diluter.cs` → `docs/hardware_diluter.md`
  - `Flusher.cs` → `docs/hardware_flusher.md`
  - `Positioner.cs` → `docs/hardware_positioner.md`
  - `ProgStep.cs` / `ExpProgram.cs` / `Experiment.cs` → `docs/core_experiment_engine.md`
  - `CHInstrument.cs` → `docs/hardware_chinstrument.md`
  - 集成层 `LIB.cs` / `KafkaMsg.cs` / `SaveAsExcel.cs` / `MainWin.cs` → `docs/system_context_and_ui.md`
- 未覆盖（需评估）：
  - UI 窗体/设计器：`AboutBox*.cs/resx`、`Calibrate*.cs/resx`、`ComboExpEditor*.cs/resx`、`Configurations*.cs/resx`、`Degas*.cs/resx`、`EChem*.cs/resx`、`EnterSelected*.cs/resx`、`JumptoCmbExp*.cs/resx`、`ManMotorsOnRS485*.cs/resx`、`ManPositioner*.cs/resx`、`Manual*.cs/resx`、`PrepSolution*.cs/resx`、`ProgramEditor*.cs/resx`、`Tester*.cs/resx`、`RS485TestForm*.cs/resx`、`MainWin.Designer.cs` 等 —— 类别：UI；迁移必要性：可合并为 Python/Qt UI 设计，当前说明书未逐窗体覆盖。
  - 工具/枚举：`ECTechs.cs`（电化学技术枚举），`MotorsOnRS485.cs`（旧抽象，基本废弃），`Kafkamsg` 已覆盖，`SaveAsExcel` 已覆盖。
  - 配置/资源：`Properties/Settings.settings`、`app.config`、`UserStrings*.resx`、`MainWin*.resx`、各窗体 resx —— 类别：配置/多语言；迁移必要性：需要整体梳理到 Python 配置与翻译系统。
  - 文件/其他：`图标.ico`、`笔记.txt`、`debug.log`、`packages.config`、`Resources/*.png` —— 类别：资源/临时；迁移必要性：按需。

## 2) 模块依赖一致性
- 主要依赖链：
  - `MainWin` → `LIB` → `MotorRS485`/`Diluter`/`Flusher`/`Positioner`/`CHInstrument` → 设备
  - `Experiment` → `ProgStep` → `Diluter`/`Flusher`/`Positioner`/`CHInstrument`
  - `CHInstrument` → `LIB.VAPoints`/`MixedSol`/日志
  - `KafkaMsg` 独立使用 Kafka 客户端，不被其他核心模块直接依赖
  - `SaveAsExcel` 独立导出（可由实验或 UI 调用）
- 未见循环依赖（逻辑上由 UI/Experiment 下行调用硬件；硬件通过回调路由数据返回，但不回调 UI 直接）。
- 未定义接口调用：`CHInstrument` 直接 P/Invoke `libec.dll`，需在迁移时明确接口；`MotorsOnRS485` 旧类未在现行逻辑中调用。
- 说明书覆盖遗漏但出现于依赖：UI 窗体（手动/校准/配置等）未逐一说明；`ECTechs.cs`（技术编号）被 CHInstrument 使用，应在迁移时保留映射。

## 3) 工具类与资源文件检查
- 辅助类：`ECTechs.cs`（电化学技术枚举，需迁移）；`MotorsOnRS485.cs`（旧 RS485 抽象，可能可弃用）；`LogMsgBuffer` 在 `LIB` 内已覆盖；无独立 Logger/Utils。
- 配置文件：`Properties/Settings.settings`、`app.config`（需迁移到 JSON/YAML/ENV）；`packages.config`（NuGet 依赖，仅供参考）。
- 语言资源：`UserStrings*.resx`、`MainWin*.resx`、各窗体 resx（需整体迁移到 Python 翻译体系）。
- 资源：`Resources/*.png`、`图标.ico`（按需迁移）。

## 4) 测试与调试窗体
- `RS485TestForm`、`ManMotorsOnRS485`、`ManPositioner`、`Tester` 等：测试/手动调试 UI。迁移建议：保留功能性（手动测试界面）可简化为一个综合“调试/设备面板”，或以 CLI/独立工具替代。

## 5) Python 实现支撑模块建议
- 日志与事件：结构化 logger（info/warn/error）、UI 可观察的事件总线。
- 配置管理：JSON/YAML 读写、默认值合并、用户设置保存。
- 翻译系统：JSON/Qt 翻译文件加载与键值访问。
- 硬件抽象：RS485 驱动、Diluter、Flusher、Positioner、CHI 封装，均注入上下文。
- 实验引擎：步骤模型、组合参数矩阵、状态机、计时与调度。
- 数据导出：CSV/Excel（pandas/openpyxl），可注入输出目录与命名规则。
- 消息总线：Kafka 客户端（可选），支持生产/消费、可关闭。
- UI 支撑：状态面板/日志窗口/实时曲线/配置对话框，信号槽与后台任务管理。

## 6) 潜在风险与改进建议
- 全局静态 `LIB` 耦合，线程安全依赖有限（日志有锁，其他集合无显式锁）；迁移时应采用依赖注入与线程安全容器。
- 异步/线程：`MotorRS485` 发送/接收锁弱，`Flusher` 多定时器易重入，`CHInstrument` 用 BackgroundWorker；建议统一事件循环或任务调度，增加超时与错误处理。
- 硬编码配置（Kafka 凭据、端口、路径）需外置化，支持环境变量/用户配置。
- UI 跨线程更新未显式 Invoke；迁移时用 Qt 信号槽。
- 错误处理与日志：多处捕获不足，失败仅置标志；需统一异常流转和用户提示。
- 资源/翻译散落 resx：迁移时集中管理，避免键缺失。

## 7) 总结与下一步建议
- 覆盖度：核心硬件、实验引擎、集成层、CHI 已有说明书，约 85–90% 核心逻辑覆盖；UI 窗体与辅助枚举/旧类未细化。
- 待补充说明书：UI 体系（可合并为一份“UI/对话框行为说明”）、`ECTechs.cs`（技术映射），如需保留旧 `MotorsOnRS485` 则补简述。
- 可合并为 Python 通用服务：上下文管理、配置/翻译、日志/事件、导出、Kafka。
- UI 层可延后迁移：各 WinForms 对话框/测试窗体可在核心逻辑稳定后再设计 Qt 界面，先用最小可用 UI 验证硬件与状态机。
