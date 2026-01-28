# MicroHySeeker — PySide6 界面规范（基于 eChemSDL，按用户要求简化）

目的：将原 C# `eChemSDL` 界面一对一重写为 Python/PySide6，但按用户要求做以下三项修改：

1. 仅使用 12 台 RS485 蠕动泵（不区分注射泵/RS485 蠕动泵），在设置窗口“综合/端口连接”后显示“配液通道”和“冲洗通道”，在这两个表格中选择泵地址完成对应配置；
2. 移除三轴平台与样品平台相关功能（不再有换样、平台定位、板位矩阵等）；系统只有一个反应烧杯；
3. 已有并可用的 485 通信实现位于 `485test/通讯`，将在实现阶段直接复用；文档中会标注复用点。

---

## 总览（高层）
- 目标产物：一套 PySide6 GUI 文件与控件映射、数据模型修改说明、校准流程变更说明、与现有 `485test/通讯` 的集成方案。实现前先由你确认文档。
- 主要窗口：主窗口（`MainWindow`）、设置/配置对话（`Configurations`）、程序编辑器（`ProgramEditor`）、手动控制（`Manual`）、校准（`Calibrate`）。

---

## 关键更改汇总（与原 C# 相比）
- 泵类型统一：所有泵视为相同的蠕动泵，界面字段仅保留对蠕动泵有意义的参数（地址、转向、转速/流速标度）。
- 配置窗口：在选择 RS485 串口并连接后，展现两张表格（配液通道 / 冲洗通道），用户在表格中为每个通道选择 `pump_address`（1..12）并设置方向与默认转速；移除注射泵特有参数（轮径/针筒体积等）。
- 去除位置器与换样：删除或隐藏与样品定位、三轴平台相关的所有 UI、数据字段与运行逻辑。
- 校准改为泵级校准：每台泵保存速度→体积映射（或每秒体积），校准流程为“选择泵 → 设定目标体积 → 运行并测量 → 保存标定因子”。

---

## 窗口逐项规范

### 主窗口 `MainWindow`
- 主要区域与行为（沿用原设计，删去与位置器相关按钮）：
  - 菜单与工具栏：保留 `文件(单次/组合/加载/保存/退出)`、`工具(设置/校准/手动/配液/电化学)`、`帮助/关于`。
  - 步骤列表：`stepProgress` 使用 `QListWidget`（自定义绘制以显示步骤状态）。绑定实验步骤数据源（参见数据模型部分）。
  - 运行控制：`Run Single`、`Run Combo`、`Stop`、`Prev`、`Next`、`Jump`、`Reset`（均映射到主控制器方法）。
  - 日志区：`LogMsgbox` 使用 `QTextEdit`（只读，绿色字体或样式）。
  - 绘图区：`VAChart` 建议使用 `pyqtgraph.PlotWidget`（实时绘图），Series 名称 `CHIData`。
  - 状态栏：显示 `RS485` 连接状态、`CHI` 仪器状态（若存在）、系统模式等。

### 配置对话 `Configurations`（重点修改）
- 布局：顶部选择 RS485 串口（`cmb485Port`），`Connect` 按钮。连接成功后右侧/下方展示两个可编辑表格：
  1. 配液通道（Dilution Channels）表格
      - 列：`ChannelName`（或 `SolutionName`，下拉/可编辑以选择现有溶液配方）、`StockConcentration`（数值，单位统一为 `mol/L`）、`PumpAddress`（下拉 1..12）、`Direction`（Forward/Reverse）、`DefaultRPM`（整数）、`Color`（颜色按钮）
      - 交互：`PumpAddress` 从当前连接并响应的 pump 列表中选择（若未连接则禁用）。界面上 `SolutionName` 应来自一个可管理的溶液配方列表（后续可扩展为溶液库）。
  2. 冲洗通道（Flush Channels）表格
     - 列：`PumpName`、`PumpAddress`（下拉）、`Direction`、`RPM`、`CycleDuration`（秒）
- 按钮：`Save`（保存到配置文件）、`Cancel`、`Scan Addresses`（对选中串口扫描 1..12 并显示可用地址）。
- 事件处理简述：
  - 切换串口/点击 `Connect` → 调用 485 模块（来自 `485test/通讯`）打开端口并扫描，返回可用地址列表并填充下拉。成功则启用表格编辑。
  - `Save` 写入配置 JSON（字段见数据模型）。
- 不含项：移除注射泵专用字段（轮径、针筒体积、注射/抽吸模式等），移除位置器/样品台相关设置。

### 程序编辑器 `ProgramEditor`
- 主控件：左侧 `QListWidget` 显示步骤，右侧为动态编辑区（`QStackedWidget` 或基于布局动态插入）。
- 操作类型（Radio / 下拉）：`PrepSol`、`Flush`、`EChem`、`Transfer`、`Blank`（去掉 `Change`/换样分支）。
- 关键编辑容器：
  - `Transfer`：字段 `pump_address`（下拉）、`direction`（下拉）、`rpm`（数值）、`volume`（uL 或 `duration` 两者其一）、可选 `delay`。
  - `PrepSol`：用于配液步骤的编辑面板。按照你的要求，`PrepSol` 步骤仅需配置：
    - `target_concentration`（目标浓度，数值，单位统一为 `mol/L`），
    - `is_solvent`（布尔，标记该注入通道是否为溶剂/稀释剂），
    - `injection_order`（有序列表，按注入顺序列出通道名或对应 `pump_address`），
    - `total_volume_ul`（最终混合物总体积，单位 uL）。
    - 不包含流量/速度字段（如 `pump_rpm`），流量由泵的校准因子与运行引擎按体积控制实现。
  - `Flush`：选择冲洗通道（对应 `Flush Channels` 表中定义的 pump），设定 `rpm`、`cycle_duration`、循环次数。
  - `EChem`：保持原有电化学设置（Technique、E0/EH/EL、ScanRate、SampleInterval、Sensitivity、Autosensitivity 等），与泵无直接依赖。
- 步骤模型（ProgStep）变更摘要：
  - 删除字段：与注射泵/位置器/换样相关的字段；
  - 保留并明确字段：`step_type`、`pump_address`（可空）、`pump_direction`、`pump_rpm`、`volume`、`duration`、`ec_settings`（如适用）、`notes`。
- 序列化：保存为 JSON（与现有 Python 项目序列化格式保持兼容），建议字段名使用下划线风格（snake_case）。

### 手动控制窗口 `Manual`
- 列表/下拉：显示 12 台泵（从已连接 RS485 端口扫描得到）。
- 控件：`Run`（启动单次/持续，取决实现）、`Stop`、`FastForward`/`Reverse`（按下开始、释放停止）、`speedBox` + `speedUnit`（设置并发送到泵）。
- 日志：显示每次命令/响应（复用 `LogMsgbox` 或独立 `testMsgbox`）。
- 行为：所有命令通过 `485test/通讯` 的接口发送，UI 仅负责选择目标地址与参数并发起调用。

### 校准窗口 `Calibrate`（改动详述）
- 目的：对 12 台蠕动泵逐台进行体积/速度标定。
- UI 元素：泵地址选择下拉、目标体积（uL）输入、`Start`、`Stop`、`Measure`（由实验者实际测量后录入量），`Compute`（计算标定因子）、`Save`。
- 流程：
  1. 选择待标定泵地址；
  2. 输入目标体积（例如 1000 uL）或目标运行时间；
  3. 点击 `Start`，UI 通过 `485test/通讯` 启动泵以设定 rpm；
  4. 运行到实验者停止（或到时自动停止），实验者测量实际排出体积并在 `Measured Volume` 中录入；
  5. 点击 `Compute` → 计算 `uL_per_sec` 或 `uL_per_rpm`（根据实现选一种），并显示；
  6. 点击 `Save` → 将标定因子写入配置（对应 pump address 字段）。
- 与原校准模块的区别：移除注射泵专用校准参数（针筒体积、注射行程等），只保留泵流量标定表征。

---

### 电化学测试 — OCPT 开关（新增）

- 目的：在执行电化学步骤（尤其是安培/计时类 i-t 或需要检测反向/突变电流的实验）时，检测并响应反向电流（Reverse Current / Over-Current in the reverse polarity），避免对样品或仪器造成损害。
- UI 元素：在 `EChem` 设置面板增加一项 `OCPT`（复选框/开关）以及相关参数输入：
  - `ocpt_enabled`（布尔，复选框）
  - `ocpt_threshold_uA`（数值输入，单位 μA，默认值建议 -50 μA 表示反向电流阈值）
  - `ocpt_action`（下拉，选项 `log` / `pause` / `abort`，默认 `log`）
  - `ocpt_monitor_window_ms`（整数，监测窗口时长，以 ms 为单位，用于短时电流尖峰的滤波，默认 100 ms）

- 行为说明：
  1. 当 `ocpt_enabled` 为真，电化学步骤运行时（包括 CV/LSV/i-t 等），CHI/电流采样循环将同时计算电流并对比 `ocpt_threshold_uA`：若检测到电流小于阈值（反向极性，数值小于阈值），则视为触发。监测采用滑动窗口与短时平均（`ocpt_monitor_window_ms`）以减少瞬时噪声误触发。
  2. 触发后执行 `ocpt_action` 对应操作：
     - `log`：记录一条带时间戳的警告日志（写入 `LogMsgbox`），并在步骤结果中标记 `ocpt_triggered: true` 与触发时电流值。
     - `pause`：暂停当前电化学步骤（即短暂停止扫描/采样），弹出对话提示（用户可选择继续或中止）；此模式适用于需要人工判定的实验。
     - `abort`：立即中止当前步骤与整个实验序列，调用主控制器的停止流程，并把错误写入日志与步骤结果返回。
  3. 所有触发事件应记录详细记录（时间戳、采样索引、电位/电流值、步骤索引），并可在实验结果文件中导出为 `ocpt_events` 列表。

- 数据模型扩展：在 `ec_settings` 中加入如下字段示例：
```
"ec_settings": {
  "technique": "i-t",
  "e0": null,
  "scan_rate": null,
  "sample_interval_ms": 100,
  "sensitivity": "AUTO",
  "ocpt_enabled": true,
  "ocpt_threshold_uA": -50.0,
  "ocpt_action": "pause",
  "ocpt_monitor_window_ms": 100
}
```

- 实现注意事项：
  - CHI 仪器的采样回调或数据缓冲应提供电流值的实时访问；若使用外部库（如仪器 SDK），应在数据接收线程内实现 OCPT 判定并通过信号/回调上报 UI。
  - 为避免阻塞 GUI，OCPT 判定与处理应发生在工作线程，UI 通过信号通知用户并执行 `pause`/`abort` 动作。
  - 实验结果的导出格式应包括 `ocpt_events`，便于后续分析与审计。

---

## 数据模型（概要）
- `config.json`（示例字段）
```
{ 
  "rs485_port": "COM4",
  "pumps": [
    {"address": 1, "name": "P1", "direction": "FWD", "default_rpm": 120, "calibration": {"ul_per_sec": 0.5}},
    ... up to 12 ...
  ],
  "dilution_channels": [ {"solution_name":"SolA","stock_concentration":0.1,"stock_concentration_unit":"mol/L","pump_address":1,"direction":"FWD","default_rpm":120,"color":"#00FF00"} ],
  "flush_channels": [ {"pump_address":2,"rpm":100, "cycle_duration":30} ]
}
```
- `prog_step` JSON（示例）
```
{
  "step_type": "transfer",
  "pump_address": 3,
  "pump_direction": "FWD",
  "pump_rpm": 100,
  "volume_ul": 500,
  "duration_s": null,
  "ec_settings": null
}
```

---

## 与现有 485 通信代码的集成
- 已实现并测试的代码位置：工作区相对路径 `[485test/通讯](485test/通讯)`。实现阶段将：
  - 在 PySide6 项目中通过合适的包导入或在 `sys.path` 中添加该路径，复用其串口打开/关闭、地址扫描、命令发送/响应处理函数；
  - 统一错误/超时处理接口并在 UI 中显示。 

注意：文档只是规范，实际导入时可能需将 `485test/通讯` 中的模块做少量包装以符合桌面应用的异步/线程模型（串口 I/O 推荐在单独线程或使用 asyncio + 线程池）。

---

## 实现建议（技术栈细节）
- 主界面与对话：`PySide6`（Qt Designer 可选）
- 表格：`QTableView` + `QAbstractTableModel`（推荐用于较复杂的数据绑定），或 `QTableWidget`（快速实现）
- 步骤列表：`QListWidget` + 自定义 `QStyledItemDelegate` 绘制状态色与图标
- 实时绘图：`pyqtgraph`（性能好、易于实时更新）
- 串口通信复用：在单独线程封装 `485test/通讯` 的同步 API；UI 通过信号/槽接收状态更新

---

## 下一步（待你确认后我会继续）
- 我已把规范草案写好，确认后我将按下列文件布局开始编码：
  - `main_window.py`、`config_dialog.py`、`program_editor.py`、`manual_control.py`、`calibrate.py`、`models.py`、`services/rs485_wrapper.py`（封装 `485test/通讯`）。
- 实施将遵循文档中字段与事件定义，先实现配置 + 手动控制 + 校准，再实现程序编辑与运行引擎。

---

如需我调整文档格式（例如改为表格列出每个控件的属性/事件行），或把文档另存为 `rst`/`md`/`pdf`，请告知。