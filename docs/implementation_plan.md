## 1. 开发顺序与依赖图
- 阶段 0（基础服务）：`services/logger.py` → `services/settings_service.py` → `services/translator.py` → `utils/constants.py`  
  依赖：标准库，配置文件。
- 阶段 1（上下文与模型）：`lib_context.py`，`core/prog_step.py`，`core/exp_program.py`  
  依赖：基础服务；常量；配置模型。
- 阶段 2（硬件驱动）：`hardware/rs485_driver.py` → `hardware/diluter.py` → `hardware/flusher.py` → `hardware/positioner.py` → `hardware/chi.py`（含模拟）  
  依赖：logger/settings/context；constants（协议）；可能的 asyncio/threading。
- 阶段 3（核心引擎）：`core/experiment_engine.py` (+ `core/errors.py`)  
  依赖：prog_step/exp_program/hardware/context/logger。
- 阶段 4（数据/消息）：`services/data_exporter.py` → `services/kafka_client.py`（可选）  
  依赖：logger/settings/context。
- 阶段 5（UI）：`ui/main_window.py` → dialogs（config/program_editor/combo_editor/calibrate/flush/manual/positioner/rs485_test）  
  依赖：core/hardware/services/context；Qt 信号槽/QTimer。
- 阶段 6（装配/入口）：`app.py`（装配上下文、服务、UI），资产/配置打包。  
  依赖：全部已完成。

## 2. 模块分组与任务说明
- 核心（必须）
  - `lib_context.py`: 上下文容器、设备/服务注入、帧路由、运行状态。
  - `core/prog_step.py`: 步骤模型、描述、状态判定。
  - `core/exp_program.py`: 组合参数矩阵、迭代、筛选。
  - `core/experiment_engine.py`: 状态机、定时驱动、硬件调度。
  - `hardware/rs485_driver.py`: 串口帧协议、接收线程/asyncio。
  - `hardware/diluter.py`: 体积→分度、状态跟踪、RS485 调用。
  - `hardware/flusher.py`: 三泵循环/转移控制。
  - `hardware/positioner.py`: 文本协议、队列、掉线检测。
  - `hardware/chi.py`: DLL/模拟、参数映射、数据采集。
  - `services/logger.py`: 结构化日志、线程安全、UI sink 钩子。
  - `services/settings_service.py`: 读写 defaults/settings，校验。
  - `services/translator.py`: 多语言键值获取。
- 辅助（推荐）
  - `services/data_exporter.py`: CSV/Excel 导出。
  - `utils/constants.py`: ECTechs 映射、协议常量、默认值。
  - `utils/event_bus.py`（可选）：轻量事件总线。
  - `services/kafka_client.py`: 可选消息总线。
  - `hardware/mocks.py`: 模拟设备/测试桩。
- UI（可迭代）
  - `ui/main_window.py`: 主界面、心跳、状态展示。
  - `ui/dialogs/*`: 配置、编辑、校准、冲洗、手动测试等。
- 装配
  - `app.py`: 创建 QApplication、加载 settings/translations、build context、装配 UI。

## 3. 实现建议
- 并发/异步：UI 用 Qt/QTimer；硬件 IO 用线程 + 队列或 `asyncio`（与 Qt 可用 qasync）；确保跨线程 UI 更新通过信号槽。
- 错误与日志：统一 logger（级别、异常捕获、上下文标签）；硬件调用加超时/重试；将错误冒泡到核心/UI 事件。
- 测试：使用 pytest；为硬件编写 mock（rs485/positioner/chi）；核心引擎测试组合矩阵、状态机 tick、持续时间计算；rs485 帧编码/解析单元测试。

## 4. 开发输出规范
- 每模块提供：
  - 代码文件（含类型注解、docstring，关键方法内联注释）。
  - 对应测试文件（同名 `test_*.py`），覆盖主流程和错误路径。
  - 简短 docstring/README（模块职责、主要 API、线程/异步约束）。

## 5. 文件组织建议（参考 `src/echem_sdl/`）
- `app.py`: 入口装配。
- `lib_context.py`: 上下文定义与构建工厂。
- `core/`: `experiment_engine.py`, `prog_step.py`, `exp_program.py`, `errors.py`.
- `hardware/`: `rs485_driver.py`, `diluter.py`, `flusher.py`, `positioner.py`, `chi.py`, `mocks.py`.
- `services/`: `logger.py`, `settings_service.py`, `translator.py`, `data_exporter.py`, `kafka_client.py`.
- `ui/`: `main_window.py`, `dialogs/*.py`.
- `utils/`: `constants.py`, `event_bus.py`, `types.py`.
- `assets/`: `translations/`, `icons/`.
- `config/`: `defaults.json`, `settings.json`（生成）。
- `tests/`: 对应模块的 `test_*.py`。

## 6. 下一步操作提示（Step 2.2）
- 挑选阶段 0/1 核心模块先行（logger/settings/translator/constants/lib_context/prog_step/exp_program）。
- 为每个模块生成“任务书”：目标、输入/输出、依赖、验收标准（包含测试用例概述）。
- 执行顺序按依赖推进：先服务与模型，再硬件适配，再核心状态机，再数据/消息，最后 UI 与装配。
