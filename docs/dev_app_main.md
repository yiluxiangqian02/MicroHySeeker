## 1. 模块定位与职责
- 文件：`src/echem_sdl/app.py`
- 作用：系统装配与启动入口（Composition Root），创建 QApplication，加载配置并初始化基础服务（Logger/Settings/Translator），初始化硬件（RS485Driver、PumpManager、Diluters、Flusher、CHIInstrument、DataExporter、KafkaClient），创建 LibContext、ExperimentEngine、MainWindow，绑定跨线程信号并启动 UI 事件循环。硬件缺失（CHI/Kafka/Positioner 等）时需降级为 mock/禁用，不能阻断程序。
- 要求：app.py 仅做装配与启动，不包含业务逻辑；所有实例集中创建，依赖关系清晰；动态泵数量与配置驱动。

## 2. 文件与类结构
- 文件：`src/echem_sdl/app.py`
- 主要方法：
  - `def create_app() -> QApplication`: 初始化 QApplication，加载 Qt 翻译（如使用），返回实例。
  - `def build_services(base_dir: Path) -> tuple[SettingsService, LoggerService, TranslatorService]`: 创建 LoggerService；创建 SettingsService（加载 defaults.json + settings.json）；创建 TranslatorService（加载语言包）；返回三项服务。
  - `def build_hardware(settings: SettingsService, logger: LoggerService, context: LibContext) -> dict`: 创建 RS485Driver（配置端口/波特率）；创建 PumpManager 并注册 diluter_pumps + flusher_pumps；创建 Diluter 列表；创建 Flusher（inlet/outlet/transfer）；创建 CHIInstrument（DLL 存在→真实，否则 mock）；返回硬件字典。
  - `def build_engine(context: LibContext, settings: SettingsService, logger: LoggerService) -> ExperimentEngine`: 创建 ExperimentEngine，注入 context/services。
  - `def build_ui(context: LibContext, engine: ExperimentEngine, translator: TranslatorService, logger: LoggerService) -> MainWindow`: 创建 MainWindow，绑定信号槽（日志/语言切换/硬件事件），注入 services/engine，返回实例。
  - `def main() -> None`: 全流程：create_app → build_services → build LibContext → build_hardware → build_engine → build_ui → show → exec。

## 3. 依赖说明
- 内部：`services.logger.LoggerService`, `services.settings_service.SettingsService`, `services.translator.TranslatorService`, `services.data_exporter.DataExporter`, `services.kafka_client.KafkaClient`, `hardware.rs485_driver.RS485Driver`, `hardware.pump_manager.PumpManager`, `hardware.diluter.Diluter`, `hardware.flusher.Flusher`, `hardware.flusher_pump.FlusherPump`, `hardware.chi.CHIInstrument`, `core.experiment_engine.ExperimentEngine`, `ui.main_window.MainWindow`, `lib_context.LibContext`.
- 外部：PySide6 (QApplication/QtCore), pathlib/json/sys/typing。

## 4. 线程与异步策略
- app.py 不直接创建线程（RS485Driver、CHI 等内部含线程）。
- 信号流：LoggerService → UI（QtSignal）；RS485Driver → PumpManager → Devices → UI（QtSignal/queued）；硬件线程不得直接操作 UI，统一在主线程更新。

## 5. 错误与日志处理机制
- 配置缺失：使用 defaults + warning。
- RS485 打开失败：error + mock/禁用。
- CHI DLL 缺失：warning + mock。
- Kafka 连接失败：warning + enabled=False。
- UI 初始化失败：error + 弹窗。
- app.py 不因硬件缺失退出，所有错误写入 logger（info/warning/error）。

## 6. 测试要求
- 服务初始化：Logger/Settings/Translator 创建；settings.json 损坏自动 fallback。
- 硬件初始化：diluter_pumps 数量变化时 PumpManager 注册正确；RS485Driver mock 模式正常；CHI 无 DLL 不抛异常。
- 引擎与 UI 注入：context 中设备数量与配置一致；MainWindow 动态显示泵列表；start/stop 流程可触发 Engine。
- 主流程：`main()` 在 mock 环境不崩溃；UI 可启动/退出；日志/翻译/硬件事件信号链可触发。

## 7. 文档与注释要求
- 顶部模块 docstring：说明 app.py 启动流程与 DI 职责。
- 每个 `build_*` 方法 docstring：参数、返回、异常说明。
- 关键位置（硬件初始化、PumpManager 注册）添加行内注释；`main()` 用步骤注释标明启动顺序。

## 8. 验收标准
- app.py 作为唯一可靠入口；全平台运行（Windows/Linux），mock 模式无需硬件。
- 支持动态泵数量、配置驱动、语言切换、日志显示；所有组件经 context 装配无强耦合。
- 测试通过：初始化/mock 运行/UI 启动/日志链路/配置变更。 
