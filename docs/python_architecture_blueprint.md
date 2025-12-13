## 1. 总体架构概述
- 目标：将 WinForms/.NET 版 eChemSDL 迁移为 Python（PySide6/Qt + 可选 asyncio）应用，保留实验/硬件逻辑，重构为依赖注入、事件驱动、分层解耦的架构。
- 设计理念：
  - **分层**：UI（视图/对话框）、Core（实验状态机）、Hardware（设备适配器）、Services（配置/日志/翻译/导出/Kafka）、Context（共享状态）、Utils（通用工具）。
  - **依赖注入**：所有硬件/服务实例通过 `LibContext` 或构造注入，不再依赖全局静态。
  - **事件驱动**：使用 Qt 信号槽或事件总线传递状态/日志/数据；硬件与核心状态变更推送到 UI。
  - **异步模型**：UI 线程保持响应；后台 IO（串口/Kafka/文件导出）使用线程/asyncio/Qt 信号，统一超时与错误处理。

## 2. 包结构树（建议）
```
src/echem_sdl/
  app.py                      # QApplication 入口，装配上下文与主窗体
  lib_context.py              # 依赖注入容器，持有设备/服务/运行时状态
  core/
    experiment_engine.py      # 实验主循环/状态机
    prog_step.py              # 步骤模型与状态判定
    exp_program.py            # 组合参数矩阵、迭代逻辑
    errors.py                 # 核心异常/错误码
  hardware/
    rs485_driver.py           # RS485 驱动，帧收发与解析
    diluter.py                # 配液泵适配
    flusher.py                # 冲洗/移液控制
    positioner.py             # 三轴平台
    chi.py                    # CHI 仪器封装/模拟
    mocks.py                  # 可选模拟设备
  services/
    logger.py                 # 结构化日志/事件
    settings_service.py       # 配置加载/保存
    translator.py             # 翻译/多语言
    data_exporter.py          # CSV/Excel 导出
    kafka_client.py           # 可选 Kafka 生产/消费
  ui/
    main_window.py            # 主窗体，心跳/状态刷新
    dialogs/
      config_dialog.py
      program_editor.py
      combo_editor.py
      calibrate_dialog.py
      flush_dialog.py
      manual_controls.py      # 调试/手动界面
      positioner_dialog.py
      rs485_test_dialog.py
  utils/
    constants.py              # 常量/技术映射（ECTechs）
    types.py                  # TypedDict/数据模型
    event_bus.py              # 轻量事件总线（可选）
  assets/
    translations/             # 翻译文件
    icons/                    # 图标
  config/
    defaults.json             # 默认配置
    settings.json             # 用户配置（可生成）
```

## 3. 主要模块职责
- **hardware**
  - `rs485_driver.py`: 管理串口连接、帧封装/校验/切帧、回调分发。
  - `diluter.py`: 体积→分度计算，发送位置命令，跟踪注液状态。
  - `flusher.py`: 管理进/出/转移泵的顺序与定时循环。
  - `positioner.py`: 文本协议控制三轴平台，队列/状态轮询、掉线检测。
  - `chi.py`: DLL/接口封装，运行实验、采集数据，模拟模式。
- **core**
  - `prog_step.py`: 定义步骤类型/参数/状态、描述生成、完成判定。
  - `exp_program.py`: 组合实验参数矩阵生成/进位/过滤、当前参数加载。
  - `experiment_engine.py`: 主状态机/计时器，调度硬件，组合循环，事件/信号发出。
  - `errors.py`: 标准错误与异常类型。
- **services**
  - `logger.py`: 线程安全/异步日志，级别、sink（控制台/文件/UI）。
  - `settings_service.py`: 读写 defaults/settings，合并/校验。
  - `translator.py`: 键值翻译，支持热切换语言。
  - `data_exporter.py`: CSV/Excel 导出，命名规则与输出目录。
  - `kafka_client.py`: 生产/消费封装，可选启用。
- **lib_context**
  - 管理共享状态：通道/泵配置、设备实例、运行数据（曲线点、ExpID、工程模式）、命名字符串、日志缓冲；提供绑定回调/路由帧等方法。
- **ui**
  - `main_window.py`: 创建/绑定上下文，驱动心跳（QTimer），触发实验运行，展示日志/状态/曲线。
  - `dialogs/`: 配置、校准、程序编辑、冲洗、手动/测试等交互界面，调用 services/core/hardware。
- **utils**
  - `constants.py`: 技术编号映射、默认值、协议常量。
  - `event_bus.py`: 简易发布订阅（若不使用 Qt 信号）。

## 4. 依赖关系与数据流（文本）
- 调用链：UI → Core (`experiment_engine`) → Hardware (`diluter/flusher/positioner/chi/rs485`) → 设备。
- 数据横向流：
  - 日志：Hardware/Core/Services → `logger`/事件 → UI/文件。
  - 状态：Hardware/Core → `LibContext`/事件 → UI。
  - 数据导出：Core/CHI → `data_exporter`（CSV/Excel）。
  - 消息：Core/Services → `kafka_client`（可选）。
- 异步/信号流：串口/CHI/Kafka 后台线程或 asyncio → 发信号/事件 → UI/核心状态机；QTimer 驱动心跳/进度刷新。

## 5. 类与接口设计摘要（关键示例）
- `RS485Driver`: `set_callback(cb)`, `run_speed(addr,rpm,forward)`, `turn_to(addr,div,speed,forward)`, `discover()`, `close()`；回调传递帧。
- `Diluter`: `prepare(target_conc,is_solvent,solvent_vol)`, `infuse()`, `get_duration()`, `handle_response(frame)`, 状态查询 `is_infusing/has_infused`.
- `Flusher`: `set_cycle(n)`, `flush()`, `evacuate()`, `transfer(addr,rpm,dir,seconds)`, 状态查询。
- `Positioner`: `connect()`, `to_position(row,col,lay)`, `inc_position(dr,dc,dl)`, `pick_and_place(...)`, `zero_all/axis`, `check_link()`, `handle_response(...)`.
- `CHIInstrument`: `set_experiment(step)`, `run()`, `cancel()`, `is_running()`, `on_data(points)`, `export()`, 支持模拟。
- `ProgStep`: 数据类 + `precompute(context)`, `get_state(elapsed, context)`, `describe()`.
- `ExpProgram`: `fill_param_matrix()`, `load_param_values()`, `next_combo()`, `select_combo()`, `reset_combo()`.
- `ExperimentEngine`: `load_program(ep)`, `prepare_steps()`, `start(combo=False)`, `tick()`, `execute_step()`, 事件 `on_step_started/finished`, `on_combo_advance`.
- `LibContext`: 持有配置/设备/状态；`attach_rs485(driver)`, `dispatch_pump_message(frame)`, `log_buffer`, `available_ports`, `named_strings`, `va_points`, `exp_id`。
- Services：`LoggerService.log(level,msg)`, `SettingsService.load/save`, `DataExporter.write_csv/xlsx`, `KafkaClient.produce/consume`, `Translator.gettext`.
- UI：`MainWindow` 绑定上下文，连接按钮→核心方法，监听事件/信号更新控件。

## 6. 线程与异步模型设计
- UI 线程：Qt 事件循环，`QTimer` 心跳（UI 刷新/进度）。
+- 后台 IO：
  - RS485/Positioner：独立线程读取串口，解析后通过线程安全队列/Qt 信号通知；发送使用锁序列化。
  - CHI：线程或 asyncio 任务轮询 `experimentIsRunning`/`getExperimentData`，推送曲线点。
  - Kafka：可用线程或 asyncio client；消费回调经事件总线。
- 协调：UI 更新通过信号槽（跨线程自动切换）；核心状态机 `tick` 由 QTimer 或事件触发；统一超时/取消令牌。

## 7. 模块化扩展与可维护性建议
- 边界清晰：Core 不直接依赖 UI；Hardware 通过接口/事件；Services 无环依赖。
- 注入策略：构造注入 `LibContext`、Logger、Translator、Settings；便于测试与模拟设备。
- 单元测试：为 Core（参数矩阵/状态机）、Hardware（帧解析/命令编码）、Services（配置/导出）编写独立测试；Mock 设备与 Kafka。
- 扩展机制：`mocks.py` 提供模拟设备；事件总线可插拔；配置/翻译可热加载。

## 8. 总结
- 该蓝图将 WinForms/全局静态模型转化为 Qt + DI + 事件驱动的 Python 架构。目录与职责清晰，支持硬件真实运行与模拟测试，并为后续 UI 重构、异步改进、云端集成留出扩展点。
