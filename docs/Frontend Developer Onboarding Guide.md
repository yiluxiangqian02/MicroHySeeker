# Frontend Developer Onboarding Guide

## 1. 项目简介
eChemSDL 前端负责实验程序配置、运行监控与硬件手动调试的可视化层。后端通过 LibContext 汇集硬件与服务实例，ExperimentEngine 驱动实验状态机，硬件包含 RS485 总线泵（动态数量）、Flusher（三阶段流程）、Positioner、CHIInstrument 等。前端须遵循：动态泵数量、多语言、线程安全（后台线程→QtSignal→UI）、mock/真实双模式、非阻塞与节流。

## 2. 前端架构总览
- MainWindow：主控界面，装配 Context/Engine/Services，动态渲染泵状态，触发实验运行/停止，展示日志与曲线。
- Dialogs：  
  - ConfigDialog：全局配置编辑（动态泵、RS485、CHI、Kafka、导出、语言/日志级别）。  
  - ProgramEditorDialog：编辑 ExpProgram/ProgStep，导入导出 JSON，打开 ComboEditor。  
  - ComboEditorDialog：编辑参数 cur/end/interval，skip，恒总浓度，预览组合数。  
  - ManualControlDialog：动态泵列表手动 run/stop/rpm/direction。  
  - FlusherDialog：三阶段冲洗流程调试，设置 cycle，显示 phase/cycle。  
  - RS485TestDialog：串口扫描/开关、发帧/回显，mock/真实。  
  - LogViewerDialog：日志实时查看/过滤/滚动/暂停/清空/搜索/导出。  
- Services：Settings/Translator/Logger/DataExporter/Kafka。  
- Context：LibContext + PumpManager；ExperimentEngine 控制实验状态机。  
- 关系：MainWindow <-> Dialogs；UI 通过 Context/Engine/Services 与后端交互；硬件事件经信号进入 UI。

## 3. 线程模型 & 信号机制
- 硬件线程 → QtSignal → UI：RS485Driver 读线程、CHI worker 等回调必须经信号切到 UI 线程；UI 不得直接访问硬件线程。
- UI 不能直接访问硬件：防止跨线程崩溃与阻塞。
- QTimer 与节流：状态刷新/曲线更新使用 QTimer（200–500ms）节流；高频日志/回帧需批量追加或限频。
- 日志 & RS485 回调边界：LoggerService → QtSignal → LogViewer/MainWindow；RS485 回调同样经 PumpManager/设备后发信号或由 UI 轮询。

## 4. 动态泵系统如何在 UI 中工作
- 泵数量不固定：从 Settings/PumpManager 读取 diluter_pumps、flusher_pumps；Flusher 三角色同样配置化。
- PumpManager 注入：LibContext 提供 address→设备映射；UI 动态生成泵控件（MainWindow、ConfigDialog、ManualControlDialog）。
- 动态渲染：不写死行数/地址，使用列表/表格或可复用的 PumpCard/PumpRow 组件。
- 逻辑复用：泵选择下拉、状态显示、run/stop 控件可提取共用；FlusherDialog/ManualControlDialog 共用泵状态展示思路。

## 5. 所有前端模块的职责清单
- MainWindow：启动/停止实验，显示步骤/组合进度、泵/Flusher/CHI 状态，日志/曲线，动态泵渲染，多语言。
- ConfigDialog：编辑 settings（动态泵、RS485、CHI、Kafka、导出、语言/日志级别），校验并写回。
- ProgramEditorDialog：编辑 ExpProgram/ProgStep，动态步骤，导入/导出 JSON，泵选择动态，打开 ComboEditor。
- ComboEditorDialog：编辑参数 cur/end/interval、skip、恒总浓度，预览组合数，写回 ExpProgram。
- ManualControlDialog：动态泵列表手动控制 run/stop/rpm/direction，显示状态，mock 兼容。
- FlusherDialog：手动三阶段冲洗，设置 cycle，显示 phase/cycle/泵状态，兼容 Timer 或 external tick。
- RS485TestDialog：串口扫描/开关，发送 HEX/ASCII，回显帧，mock/真实。
- LogViewerDialog：日志实时追加、过滤、滚动/暂停、清空/搜索/导出，信号驱动，节流防卡顿。

## 6. 与后端协作方式
- LibContext：统一获取 PumpManager、设备与服务实例，UI 通过高层接口而非直接硬件操作。
- ExperimentEngine：MainWindow 触发 start/stop/load；状态通过信号/QTimer 刷新，避免阻塞。
- SettingsService：ConfigDialog 读写；变更后由 MainWindow/app 统一重建硬件/引擎，Dialog 不直接操作硬件。
- Hardware 抽象：Diluter/Flusher/FlusherPump/RS485Driver/CHIInstrument 经 PumpManager 或注入传递；回调需信号或轮询。
- TranslatorService：所有界面实现 reload_texts，集中刷新文案；切换语言时批量刷新。
- LoggerService：绑定 UI handler→QtSignal→追加显示，线程安全并节流。

## 7. 如何使用任务书生成代码
- 指导 LLM 生成：逐模块提供对应任务书，先生成骨架（类/字段/方法签名/信号槽/布局占位），再填充逻辑（数据绑定、校验、序列化），最后调试（信号连接、节流、异常处理）。
- 推荐顺序：
  1) MainWindow 骨架 + 信号总线 + 定时器。  
  2) 基础 Dialog：LogViewerDialog、RS485TestDialog。  
  3) 配置/程序编辑：ConfigDialog、ProgramEditorDialog、ComboEditorDialog。  
  4) 调试控制：ManualControlDialog、FlusherDialog。  
- 示例提示词：  
  - “根据 docs/dev_ui_program_editor_dialog.md 生成 ProgramEditorDialog 的 PySide6 骨架，保留类型注解和方法签名，空方法体用 pass，包含 reload_texts 和信号连接。”  
  - “实现 LogViewerDialog，要求 logger→QtSignal→UI，追加日志需节流（50ms flush），支持过滤/清空/暂停。”  
  - “在 MainWindow 中动态渲染 PumpManager 返回的泵列表，使用可复用 PumpCard 组件，避免硬编码数量。”
- 代码迭代流程：先骨架 → 再逻辑 → 再调试；每步运行最小可行测试（UI 构建、信号触发、mock 数据）。

## 8. 前端文件结构建议
```
src/echem_sdl/ui/
    main_window.py
    dialogs/
        config_dialog.py
        program_editor_dialog.py
        combo_editor_dialog.py
        manual_control_dialog.py
        flusher_dialog.py
        rs485_test_dialog.py
        log_viewer_dialog.py
```

## 9. 新模型上手 checklist
- [ ] 已加载 LibContext/ExperimentEngine
- [ ] 可从 PumpManager 动态渲染泵列表
- [ ] LoggerService 日志信号可接收并显示
- [ ] TranslatorService 切换语言后 UI 文本刷新
- [ ] ConfigDialog 可读写 settings 并校验
- [ ] ProgramEditorDialog/ComboEditorDialog 可导入/导出/编辑
- [ ] ManualControlDialog/FlusherDialog 可安全 run/stop（含 mock）
- [ ] RS485TestDialog 可扫描/开关/发帧/回显
- [ ] LogViewerDialog 高频日志不卡顿

## 10. 风险与注意事项
- RS485 高频回调/CHI 数据：UI 线程压力，需 QtSignal + 节流。
- 日志大量写入：必须批量追加或限频刷新。
- 语言切换：集中 reload_texts，避免遗漏，必要时批量刷新防卡顿。
- Settings 修改：若影响硬件/Engine，需由 MainWindow/app 统一重建实例，Dialog 不直接操作硬件。
- PumpManager 动态变化：UI 需刷新机制，避免缓存过期实例。

## 11. 后续建议（继续开发）
- 扩展 UI：封装复用组件（泵卡片、动态表单、日志视图），提供主题/图标支持。
- 新增模块：沿任务书模式扩展新的调试/监控对话框，复用信号/节流/多语言模式。
- 绑定新硬件：在 PumpManager/LibContext 注册新设备，UI 通过动态列表/表单生成，无需写死。
- 优化结构：引入轻量 view-model，集中信号总线，统一节流/错误处理/多语言刷新工具函数，减少重复代码。 
