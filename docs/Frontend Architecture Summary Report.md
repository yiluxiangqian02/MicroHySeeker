# Frontend Architecture Summary Report

## 1. 前端整体定位
- 职责与边界：UI 负责实验程序、配置与手动控制的可视化交互，所有业务/硬件操作通过 LibContext、ExperimentEngine、SettingsService 等上层接口完成；不直接操作硬件线程或底层串口。
- 与后端关系：
  - LibContext：提供设备/服务实例与状态。
  - ExperimentEngine：UI 触发运行/停止/装载程序，非阻塞读取状态。
  - Hardware（PumpManager/Flusher/Diluter/RS485Driver/CHIInstrument）：UI 通过高层方法调用，不触碰底层线程。
  - Services（Settings/Logger/Translator/Kafka/DataExporter）：UI 读写配置、显示日志、多语言刷新，消息通过信号。
- 设计原则：动态泵（数量/地址不可写死）；多语言（TranslatorService 驱动 reload_texts）；信号槽线程边界清晰（后台→QtSignal→UI）；非阻塞（无长等待，必要时 QTimer 轮询）；配置与导出统一走 SettingsService/序列化接口。

## 2. 已定义的前端模块总览

| 模块 | 功能定位 | 输入 | 输出/交互 | 主要依赖 |
| --- | --- | --- | --- | --- |
| MainWindow | 主界面：启动/停止实验，显示状态、日志、泵/Flusher/CHI 概览，动态泵渲染 | LibContext, ExperimentEngine, Translator, Logger | 触发引擎运行/停止；定时刷新状态与曲线 | LibContext, ExperimentEngine, Translator, Logger, PumpManager |
| ConfigDialog | 全局配置编辑（动态泵、RS485、CHI、Kafka、导出、语言/日志级别） | SettingsService, Translator, Logger, LibContext | 写回 settings.json，刷新配置 | SettingsService, Translator, Logger, LibContext |
| ProgramEditorDialog | 编辑 ExpProgram/ProgStep，导入导出 JSON，联动 ComboEditor | LibContext, SettingsService, Translator, Logger, ExpProgram | 更新 ExpProgram，供引擎使用 | ExpProgram, ProgStep, Translator, Logger, PumpManager |
| ComboEditorDialog | 编辑参数组合（cur/end/interval）、skip、恒总浓度，组合预览 | ExpProgram, Translator, Logger | 写回参数，调用 fill_param_matrix | ExpProgram, Translator, Logger |
| ManualControlDialog | 手动控制所有泵（Diluter/FlusherPump），动态泵列表 | PumpManager, Translator, Logger | run/stop/rpm/direction，显示状态 | PumpManager, Translator, Logger |
| FlusherDialog | 手动调试 Flusher 三阶段流程，设置 cycle，显示 phase/cycle | Flusher, Translator, Logger | 调用 flusher.start/stop，轮询状态 | Flusher, FlusherPump, Translator, Logger |
| RS485TestDialog | RS485 调试：串口扫描、开关、发帧、回显；mock/真实 | RS485Driver, Translator, Logger | 发送帧，显示回帧 | RS485Driver, Translator, Logger |
| LogViewerDialog | 独立日志窗口：实时追加、过滤、滚动/暂停、清空/搜索/导出 | LoggerService, Translator | 显示过滤日志 | LoggerService, Translator |

## 3. UI 架构一致性检查
- 动态泵渲染：MainWindow、ConfigDialog、ManualControlDialog 基于 PumpManager/Settings 动态生成；FlusherDialog 依赖注入的 Flusher/FlusherPump；未写死数量。
- 日志信号：LogViewerDialog、MainWindow 均要求 logger→QtSignal→UI，机制一致。
- 多语言：所有模块提供 reload_texts，依赖 TranslatorService，一致。
- 线程边界：后台硬件线程禁止直接操作 UI，均通过 QtSignal 或 QTimer 轮询；RS485TestDialog 明确回调需 signal；Manual/Flusher 使用 QTimer 刷新状态。
- Settings 交互：ConfigDialog 通过 SettingsService 读写；Program/Combo 编辑通过 ExpProgram 模型写回；一致。
- 风险排查：无显式写死泵数量/路径；均强调非阻塞。但需实现时关注高频日志/回帧导致 UI 负载，确保节流。

## 4. 完成度评估
- 已完整定义：MainWindow、ConfigDialog、ProgramEditorDialog、ComboEditorDialog、ManualControlDialog、FlusherDialog、RS485TestDialog、LogViewerDialog。
- 待补充信息：实时曲线库选择与节流策略细节；更精细的表单校验规则；主窗口与 app/main 的信号对接清单；UI 资源（图标/主题）。
- 风险点：高频日志/回帧的节流；JSON 导入导出的边界处理；线程跨界（RS485/CHI）必须确保全经由信号；PumpManager 动态变化后的 UI 刷新逻辑需统一。

## 5. 架构建议（全栈视角）
- 组件复用：抽象 PumpCard/PumpRow widget 供 MainWindow 与 ManualControlDialog 复用；抽象通用动态表单生成器用于 ConfigDialog/ComboEditor 的动态表格。
- 事件驱动与轮询：日志、回帧、翻译等用信号驱动；状态刷新用节流的 QTimer（200–500ms），避免过度轮询。
- 状态模型：引入轻量 view-model（dataclass/TypedDict）缓存 UI 状态，便于序列化与测试。
- 动态表单：封装通用 builder 降低 ConfigDialog/ComboEditor 的维护成本。
- 调试支持：在调试对话框中提供 mock 指示、重置按钮、快速导入/导出配置；统一日志 hook 便于观察。

## 6. 前端与后端联调注意事项
- ExperimentEngine：UI 只调用 start/stop/load，避免阻塞；状态通过信号或定时器刷新，防止 race。
- PumpManager：动态列表更新需在注册变更后刷新 UI；address 路由在 PumpManager，UI 不应持久缓存失效引用。
- CHIInstrument：数据点推送须信号到 UI；无设备时 mock，避免阻塞。
- RS485Driver：回调必须经 QtSignal；避免 UI 线程执行长阻塞 open/close。
- SettingsService：ConfigDialog 写回后，如需生效，应由 MainWindow/app 统一重建硬件/引擎，不在 Dialog 内直接操作硬件。
- TranslatorService：集中注册 reload_texts；切换语言时避免长阻塞，可批量刷新。

## 7. 下一步建议
- 生成 MainWindow 与核心 Dialog 的骨架代码（布局+信号槽+节流），统一信号总线。
- 提炼共享 UI 组件（泵控件、动态表单、日志视图）。
- 编写 settings schema/JSON Schema，辅助 ConfigDialog 校验与 UI 自动生成。
- 补充 UI 事件/信号流程图（Logger→LogViewer，RS485→PumpManager→UI，Engine→状态面板）。
- 设计并实现高频数据（日志/曲线）的节流/批量刷新封装，降低性能风险。 
