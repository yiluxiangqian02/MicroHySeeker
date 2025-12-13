## 1. 模块定位与职责
- 文件：`src/echem_sdl/lib_context.py`
- 作用：依赖注入容器与全局上下文管理器，统一持有服务实例（settings/logger/translator）、硬件实例（`rs485_driver`、动态 `diluters` 列表、三角色 `flusher`、`positioner`、`chi`）、运行状态（`va_points`/`exp_id`/`named_strings`/`log_buffer`），提供帧路由、日志入口、默认配置装配及资源回收。泵数量由配置决定，严禁写死。

## 2. 文件与类结构
- `LibContext` 类
  - 初始化参数：`settings: SettingsService`, `logger: LoggerService`, `translator: TranslatorService`, `mock_mode: bool = False`
  - 属性（示例类型）：
    - 服务：`settings`, `logger`, `translator`
    - 设备：`rs485_driver: RS485Driver | None`, `diluters: list[Diluter]`, `flusher: Flusher | None`, `positioner: Positioner | None`, `chi: CHIInstrument | None`
    - 运行数据：`va_points: list[tuple[float, float]]`, `exp_id: str | None`, `named_strings: dict[str, str]`, `log_buffer: queue.Queue[str]` 或锁保护列表
    - 配置镜像：`diluter_configs`, `flusher_config`（inlet/outlet/transfer）、`positioner_config`, `rs485_config`, `kafka_config`, `defaults`
    - 内部：`_lock: threading.RLock`, `address_map`（addr→设备实例）
  - 方法：
    - `attach_device(name: str, device: Any) -> None`
    - `get_device(name: str) -> Any`
    - `load_from_settings() -> None`: 读取 settings.json，创建 RS485Driver、动态 Diluter 列表、Flusher/Positioner/CHI 实例并注册路由。
    - `dispatch_pump_message(frame: bytes) -> None`: 按地址动态路由到 Diluter/Flusher（不假设数量）。
    - `log(level: str, msg: str, **kwargs) -> None`
    - `generate_exp_id() -> str`
    - `get_named_string(key: str, default: str = "") -> str`
    - `close_all() -> None`
    - 可选：`create_default_channels/pumps()`（仅从 defaults 构造，仍动态）

## 3. 依赖说明
- 内部：`services.logger.LoggerService`, `services.settings_service.SettingsService`, `services.translator.TranslatorService`, `utils.constants`
- 未来：`hardware.*`（通过 attach 注入），`core` 读取状态
- 标准库：`threading`, `queue`, `typing`, `datetime`, `pathlib`

## 4. 线程与异步策略
- 写操作持 `_lock`；`dispatch_pump_message` 在串口线程触发，需要线程安全查找映射。
 - `log_buffer` 使用线程安全容器。
- 不强制异步；若与 Qt 配合由调用方在 UI 线程消费。

## 5. 错误与日志处理机制
- 未 attach 设备调用硬件：warning。
 - 设备 attach 失败/名称冲突：抛异常或记录 error。
 - 未知地址帧：warning/error 并忽略。
 - 日志统一通过 LoggerService；可写入 log_buffer。

## 6. 测试要求
- 实例创建：注入服务后属性可用。
 - `load_from_settings`：读取配置创建动态泵列表（>=6 或更多）、三冲洗泵；地址映射正确。
 - attach/get_device：注册/获取一致，重复注册行为符合预期。
 - 帧路由：模拟多地址帧路由到对应 Diluter/Flusher；未知地址不抛异常。
 - 日志写入：`log()` 调用 LoggerService，log_buffer 可消费。
 - 并发：多线程 log/dispatch 无竞态。
 - mock_mode：注入假设备可正常路由。

## 7. 文档与注释要求
- 模块 docstring：说明 DI 角色、资源持有、动态泵与地址映射、线程安全策略。
- 方法 docstring：参数、返回、异常、线程注意事项。
- 类型注解完整；路由/锁使用处加简短注释。
- README 片段：示例在 `app.py` 装配 context、从 settings 加载动态泵、注册回调。

## 8. 验收标准
- 类与接口按定义实现；动态泵加载与地址映射正确；线程安全。
- 未知地址与缺设备处理健壮；日志输出规范。
- 测试通过：实例化、加载配置、设备注入、帧路由、日志、并发、mock 模式。
- 可直接供 `app.py` 和核心/硬件层使用，无写死泵数量假设。 
