# Backend Developer Onboarding Guide

## 1. 系统整体架构
后端为 eChemSDL 的核心控制层，负责串口通信、设备调度、实验状态机、数据采集与导出、配置与多语言、日志与消息（可选 Kafka）。前端通过 LibContext/ExperimentEngine/服务接口与后端交互，硬件层包含 RS485 总线泵（动态数量）、Flusher（三阶段流程）、Positioner（可禁用）、CHIInstrument（DLL/模拟双模式）。流程概要：UI 指令 → ExperimentEngine → 调度 ProgStep → 调用硬件抽象（Diluter/Flusher/Positioner/CHI）→ RS485Driver/PumpManager 路由 → 设备回调 → 状态反馈给引擎/前端。

## 2. 核心概念
- 动态泵系统：泵数量 6–12（可配置），地址区分，PumpManager 统一注册/路由，UI 动态渲染。
- RS485 总线：共享串口，地址区分设备；RS485Driver 负责帧封装/切帧/校验/读写线程。
- PumpManager：addr→设备实例映射，统一 dispatch_frame，注册/注销泵，调试列表。
- ExperimentEngine 状态机：单线程 tick（1s），驱动 ProgStep 序列与组合实验，调用硬件，推进状态。
- ProgStep/ExpProgram：步骤模型与组合参数矩阵；ProgStep 表示单步操作，ExpProgram 生成与遍历组合参数。
- CHI 模拟/真实模式：CHIInstrument 封装 DLL 调用；无 DLL/设备时自动进入模拟模式生成虚拟曲线。
- SettingsService：配置系统，加载 defaults/settings，提供校验与合并，驱动动态泵/串口/CHI/Kafka/导出等。
- Translator/Logger：多语言键值翻译；日志统一入口（线程安全），支持 UI 回调。

## 3. 线程模型
- RS485Driver read-loop：后台线程读取串口 → decode frame → PumpManager.dispatch_frame → 设备 handle_response（需线程安全）。
- CHIInstrument worker thread：后台轮询 experimentIsRunning/getExperimentData（或模拟生成曲线），通过锁保护状态/数据。
- ExperimentEngine tick loop：单线程周期调度（如 1s）；调用 ProgStep.start/update_state；不持有重锁，仅访问受保护的设备接口。
- 锁需求：串口 send/handle_response 序列化；PumpManager 注册/dispatch 加锁；CHI 数据/状态加锁；避免在 UI/Engine 持长锁。
- mock 模式：RS485Driver/CHI/Positioner 可不启动真实串口/ DLL，线程可降级或省略。

## 4. 关键模块说明
- RS485Driver：封装串口读写、帧封装/校验、读线程、回调；支持 discover/mock；不限制设备数量。
- PumpManager：管理所有泵实例（Diluter + FlusherPump），注册/注销、addr 映射、dispatch_frame；保证线程安全。
- Diluter：体积→步进计算，发送 TurnTo/Run 命令，跟踪注液状态（infusing/infused/failed），处理 0xFB 响应。
- Flusher / FlusherPump：Flusher 编排三阶段（排空→进液→转移，支持循环）；FlusherPump 执行 run/stop，保持状态；均地址配置化。
- CHIInstrument：封装 libec.dll，设置技术/参数，运行实验，轮询 running 状态，获取数据点；支持模拟模式（随机/预设曲线），结束导出 CSV。
- Positioner（可禁用）：独立串口文本协议（CJXSA/CJXCg...），移动/归零/取放，状态轮询，mock/disabled 模式。
- ExperimentEngine：运行控制器；tick 驱动 ProgStep，调度硬件，组合参数遍历，跟踪时间与状态。
- ProgStep：描述单步操作（配液/冲洗/电化学/换样等），状态 idle/busy/end/failed，预计算/启动/更新状态。
- ExpProgram：步骤列表，参数矩阵生成（cur/end/interval），skip/恒总浓度，组合索引迭代/序列化。
- SettingsService：pydantic/校验；加载 defaults/settings；合并/保存；提供 get/set；驱动泵/串口/CHI/Kafka/导出等参数。
- TranslatorService：加载多语言资源；get/reload；回调通知；线程安全。
- LoggerService：结构化日志；多 handler（控制台/文件/UI 回调）；线程安全；异常记录。
- DataExporter：CSV/Excel 导出；同步或线程池异步；线程安全写文件。
- KafkaClient（可选）：生产/消费；失败自动禁用；线程安全；mock 模式不影响流程。

## 5. 模块间依赖图
典型调用链：  
UI → ExperimentEngine → ProgStep → 硬件抽象（Diluter/Flusher/Positioner/CHI） → RS485Driver/PumpManager → 设备 → 回调 → PumpManager.handle_response → 设备状态更新 → Engine/前端状态刷新。  
配置链：SettingsService → 构建 RS485Driver/PumpManager/设备/Engine → 提供给 LibContext → UI/Engine 使用。  
日志链：后端模块 → LoggerService → handler/QtSignal → UI LogViewer。

## 6. 如何基于任务书生成代码
- 编写顺序建议：
  1) 基础服务：LoggerService、SettingsService、TranslatorService、DataExporter、KafkaClient（可选）。  
  2) 核心 IO：RS485Driver（含 mock）、PumpManager。  
  3) 设备层：Diluter、FlusherPump、Flusher、Positioner（可禁用）、CHIInstrument（含模拟）。  
  4) 实验模型与引擎：ProgStep、ExpProgram、ExperimentEngine。  
  5) 集成：LibContext 装配。  
- 骨架生成：根据任务书创建类/字段/方法签名，添加类型注解和 docstring，空实现先 pass。
- 填充逻辑：  
  - 串口封装/校验，读线程启动/关闭，send 加锁。  
  - PumpManager 注册/dispatch、线程安全。  
  - 设备命令编码/解码、状态更新（锁保护）。  
  - Engine tick 调度，ProgStep prepare/start/update_state。  
  - 配置加载/合并/校验/保存。  
- 线程/锁/回调细节：  
  - 所有串口写需持锁；读线程 catch 异常不中断；回调不阻塞。  
  - CHI worker 检查 running，获取数据加锁。  
  - Engine 单线程，不持重锁；调用设备时注意非阻塞。  
- 自测（mock）：  
  - RS485Driver mock_send_frame → PumpManager.handle_response。  
  - CHIInstrument mock 曲线生成。  
  - Positioner mock/disabled 不触串口。  
  - Engine 结合 mock 设备跑简单 ProgStep 流程。

## 7. 配置系统（settings.json）结构说明
- 动态泵：`diluter_pumps` 数组（name/address/calibration/volume_per_rev/rpm/...）；`flusher_pumps` 对象（inlet/outlet/transfer 各含 address/rpm/direction/cycle_duration）。
- RS485：`port`、`baudrate`、`mock`。
- Flusher：使用上述 flusher_pumps 配置；周期/方向来自配置。
- CHI：`dll_path`、`mock`、技术/参数默认。
- Kafka：`enable`、`broker`、`topics`、凭据（可选）。
- Export：`export_dir`、文件命名规则（可在服务内默认）。
- 语言/日志：`locale`、`log_level` 等全局设置。

## 8. 调试策略
- 无硬件（mock）：RS485Driver/CHI/Positioner 设置 mock/disabled；PumpManager 注册 mock 设备；Engine 跑模拟步骤。
- RS485 调试：使用 RS485TestDialog + driver.mock_mode；验证帧封装/回显；检查 PumpManager 路由。
- CHI 模拟：mock 曲线生成，验证数据收集/导出；无 DLL 不崩溃。
- PumpManager 路由：模拟帧地址 → 对应设备 handle_response 被调用；未知地址告警。
- ExperimentEngine 状态机：用 mock 设备跑 ProgStep/ExpProgram 组合，验证 tick 推进、状态转换、时间累加。

## 9. 风险与注意事项
- 并发/死锁：串口写锁与设备锁交叉要谨慎；回调中避免再次持有 send 锁；Engine 不应等待硬件锁。
- 阻塞：避免在回调/Engine tick 中做阻塞 IO；串口 open/close 放在短路径内。
- 配置错误：缺字段/非法值需校验并回退默认；地址重复禁止注册。
- 高频日志/回调 storm：必须节流/批量处理，防止 UI/日志 IO 卡顿。
- mock/真实切换：注意线程生命周期与资源释放（串口关闭、worker join）。

## 10. 后续扩展建议
- 扩展更多泵：通过 SettingsService 增加 diluter_pumps，PumpManager 自动注册；UI 动态渲染无需改代码。
- 替换 RS485 协议：封装协议常量，调整 encode/decode；保持 PumpManager/设备接口不变。
- 增加电化学技术：在 CHIInstrument 映射新技术与参数键，保持接口一致；模拟模式补齐新技术生成逻辑。
- 远程控制：Kafka/WebSocket 集成，复用 Logger/Translator；确保消息线程通过队列/信号与 Engine/设备交互，避免直接跨线程调用。
