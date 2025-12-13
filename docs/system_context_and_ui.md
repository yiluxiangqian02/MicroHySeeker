## 1. 总体职责
- `LibContext`、`KafkaMsg`、`SaveAsExcel`、`MainWin` 共同组成上下文与集成层：提供全局设备/配置/资源容器，统一日志与命名，桥接硬件与实验引擎；负责远程消息、数据导出，以及 UI 主循环与心跳驱动。所有泵/设备数量由配置动态决定，不写死在代码中。

## 2. 模块分工
- **LibContext**：全局容器与路由。持有服务（logger/settings/translator）、设备实例（`RS485Driver`、`diluters: list`、`flusher`、`positioner`、`chi`）、运行数据（`va_points`、`exp_id`、`named_strings`、`log_buffer`）。从 settings.json 读取 `diluter_pumps` 数组动态创建 `Diluter` 列表；`flusher` 读取 `flusher_pumps`（inlet/outlet/transfer）配置；`dispatch_pump_message` 按地址映射，无泵数量假设。
- **KafkaMsg**：封装 Confluent.Kafka 生产/消费（凭据/主题应配置化）。用于发送/订阅实验事件、日志等。
- **SaveAsExcel**：基于 EPPlus 导出实验数据到 Excel/CSV（可替换为 pandas/openpyxl 在 Python 端）。
- **MainWin**：WinForms 主窗体，负责文化设置、加载配置/多语言、初始化设备与 LibContext、启动心跳定时器、驱动 Experiment 引擎（加载/运行/组合）、更新 UI 状态/日志/图形。UI 展示泵状态时应根据 `LibContext.diluters` 动态渲染，不固定数量。

## 3. 配置结构示例（settings.json）
```json
{
  "locale": "zh",
  "data_path": "data/",
  "diluter_pumps": [
    {"name": "A", "address": 1, "high_conc": 1.0, "pump_speed": 120, "divpermL": 19416},
    {"name": "B", "address": 2, "high_conc": 0.5, "pump_speed": 100, "divpermL": 20000},
    {"name": "C", "address": 3, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416},
    {"name": "D", "address": 4, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416},
    {"name": "E", "address": 5, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416},
    {"name": "F", "address": 6, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416}
  ],
  "flusher_pumps": {
    "inlet":   {"address": 10, "pump_rpm": 200, "direction": "forward", "cycle_duration": 30},
    "outlet":  {"address": 11, "pump_rpm": 200, "direction": "forward", "cycle_duration": 30},
    "transfer":{"address": 12, "pump_rpm": 200, "direction": "forward", "cycle_duration": 30}
  },
  "rs485": {"port": "COM3", "baudrate": 38400},
  "positioner": {"port": "COM5", "baudrate": 115200},
  "kafka": {"bootstrap.servers": "broker:9092", "username": "", "password": ""},
  "engineering_mode": false
}
```
- 扩展泵数量仅需在 `diluter_pumps` 中增减项，代码无需改动。

## 4. 关键数据结构与全局对象
- LibContext：
  - 配置/资源：`named_strings`、`defaults`、`exp_id`、`data_file_path`。
  - 设备：`rs485_driver`、`diluters (list[Diluter])`、`flusher`（含 inlet/outlet/transfer 配置）`positioner`、`chi`。
  - 运行：`va_points` 曲线、`log_buffer`、`available_ports`。
  - 路由：地址→设备实例映射（动态）。
- Kafka：`Producer`/`Consumer`、broker/凭据/主题（配置化）。
- SaveAsExcel：`DataExcel`、`DataSheet`、`FilePath`、`Pointer`。
- MainWin：心跳计时器、绘图点、状态标志、Experiment 实例；UI 控件应绑定动态泵列表。

## 5. UI 与系统流程（启动到实验执行）
1) `Program.cs` → `MainWin` 启动，设置文化/翻译。  
2) 加载 settings.json / defaults.json：构建 `diluter_pumps`、`flusher_pumps`、`rs485`、`positioner`、`kafka` 等配置。  
3) 初始化 LibContext：创建 RS485Driver；按 `diluter_pumps` 动态生成 `Diluter` 列表；创建 `Flusher` 并注入 inlet/outlet/transfer 配置（仍固定三角色，但地址/参数来自配置）；创建 Positioner/CHI；注册 RS485 回调路由。  
4) 启动心跳计时器：刷新日志、状态、剩余体积/颜色、图形；驱动 ExperimentEngine `tick`。  
5) 用户操作：配置/校准/程序编辑/手动控制/运行；UI 根据 `context.diluters` 渲染 N 个泵。  
6) 实验执行：ExperimentEngine 调度 `ProgStep` → 调用对应 `Diluter/Flusher/Positioner/CHI`；状态/日志通过 UI 展示，Kafka 可选发布；完成后导出数据并更新 UI。

## 6. 与其他模块依赖关系
- LibContext 为 ExperimentEngine/硬件/UI 提供共享实例与配置；`dispatch_pump_message` 动态路由帧。
- KafkaMsg 独立，UI/业务可调用发送/订阅（凭据配置化）。
- SaveAsExcel 用于导出，CHI/Experiment 完成后写文件。
- MainWin 协调上下文、硬件、UI；依赖 settings/translator/logger。

## 7. Python 重写必须保留的逻辑
- 动态泵：`diluter_pumps` 配置驱动实例数量；UI/核心不假设泵个数。
- RS485 驱动与设备解耦：按地址路由。
- 心跳/定时驱动核心与 UI。
- 配置加载/默认回退；日志/翻译。

## 8. Python 可改进的部分
- 依赖注入：上下文对象取代全局静态；配置/翻译热加载。
- Kafka/导出模块化；凭据外置。
- UI 使用 Qt 信号槽，动态生成泵控件列表。
- 配置校验（pydantic）；错误可视化与自动重连。

## 9. 数据流描述（文字）
应用启动 → 读取配置/翻译 → 构建 LibContext（动态泵列表、三冲洗泵角色、位置器、CHI、RS485 回调路由） → 心跳刷新日志/状态/图形 → 用户启动实验 → ExperimentEngine 逐步调用硬件（按地址） → 状态经 UI/Kafka/日志传播 → 结束导出数据 → 等待下一次运行。

## 10. 动态泵管理要求
- 代码中不得写死泵数量（6/3 等）；配液泵完全由配置数组决定。
- 冲洗泵固定角色（inlet/outlet/transfer），但地址/参数来自配置。
- ExperimentEngine 与 UI 只基于泵地址/配置识别泵，自动渲染/调度。
