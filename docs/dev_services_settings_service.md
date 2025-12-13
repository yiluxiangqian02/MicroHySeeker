## 1. 模块定位与职责
- 文件：`src/echem_sdl/services/settings_service.py`
- 作用：集中管理配置（加载/保存/合并/校验），提供默认配置与用户配置的合并结果，供 `lib_context` 构建设备/上下文，供硬件/服务读取运行参数；记录配置异常（缺失/损坏）并尝试恢复。
- 与其他层交互：
  - `lib_context`: 调用 `load_defaults()` / `load_user_settings()` 获取合并后的配置；可通过 `save_user_settings()` 持久化运行时更改。
  - `logger`: 记录加载/保存/恢复事件与错误。
  - 硬件/核心：通过配置参数（端口、波特率、通道设置、泵设置、位置器参数、导出路径等）初始化实例。

## 2. 文件与类结构
- 使用 `pydantic` 模型定义配置结构（示例）：
  - `class ChannelConfig(BaseModel)`, `PeriPumpConfig`, `PositionerConfig`, `RS485Config`, `KafkaConfig`, `DefaultsConfig` 等（字段参考 C# Settings.settings 与现有上下文）。
  - `class AppSettings(BaseModel)`: 汇总用户配置（locale、data_path、channels、flushing_pumps、positioner、rs485、kafka、engineering_mode 等）。
  - `class Defaults(BaseModel)`: 默认配置项（同 DefaultsConfig）。
- `class SettingsService`:
  - 初始化参数：`base_dir: Path`, 可选 `logger: LoggerService | None`.
  - 路径属性：`defaults_path`（如 config/defaults.json），`user_path`（如 config/settings.json）。
  - 方法（含类型注解）：
    - `load_defaults() -> dict | Defaults`: 读取默认配置文件，如缺失则返回内置默认值。
    - `load_user_settings() -> dict | AppSettings`: 读取用户配置，若缺失或损坏则返回空/默认并记录日志。
    - `save_user_settings(settings: AppSettings | dict) -> None`
    - `merge_defaults(raw_defaults: dict, raw_user: dict) -> dict`: 合并逻辑（用户覆盖默认，缺失补默认）。
    - `validate_settings(raw: dict) -> AppSettings`: 用 pydantic 校验并返回模型；失败时抛出/恢复。
    - `get(key: str, default: Any = None) -> Any`
    - `set(key: str, value: Any) -> None`（更新内存态，可选延迟保存）
  - 可选：`reload()` 重新加载磁盘配置。

## 3. 依赖说明
- 标准库：`json`, `pathlib.Path`, `typing`, `copy`, `contextlib`.
- 第三方：`pydantic`（数据模型/校验）。
- 内部：`services.logger.LoggerService`（可选注入）。

## 4. 线程与异步策略
- 加载/保存通常在主线程进行；方法内部需使用文件锁或简单互斥（threading.Lock）防止并发写。
- 不强制异步；如后台更新需调用方保证序列化访问或在 UI/事件线程调度。

## 5. 错误与日志处理机制
- 缺失文件：记录 info/warning，使用内置默认或生成示例文件。
- JSON 解析/校验失败：记录 error，回退到默认配置；可选择重命名坏文件备份。
- 保存失败：抛出异常并记录 error（调用方决定重试/提示）。
- 版本/字段缺失：合并默认值并记录 warning。

## 6. 测试要求
- 加载默认配置：无用户文件时返回默认并不抛异常。
- 保存/读取往返：写入用户配置后可正确读取并校验。
- 合并逻辑：用户覆盖默认，未提供字段使用默认；嵌套结构合并正确。
- 校验失败恢复：损坏 JSON/非法字段应记录错误并回退默认。
- 并发写保护：多线程写入不产生损坏（可使用伪并发测试或锁验证）。
- 路径处理：相对/绝对路径正确解析。

## 7. 文档与注释要求
- 模块 docstring：描述职责、路径约定、线程注意事项。
- 类/方法 docstring：说明参数、返回、异常、线程安全。
- 类型注解齐全；在合并/校验逻辑处添加简短注释。
- 提供配置文件示例（字段说明）在 docstring 或 README 片段中。

## 8. 验收标准
- 提供 `SettingsService` 和 pydantic 模型，接口完整（load/save/merge/validate/get/set）。
- 能正确处理缺省/损坏配置并记录日志；合并与校验逻辑符合设计。
- 测试通过：覆盖加载/保存/合并/校验/错误恢复/并发保护。
- 代码含 docstring、类型注解；可被 `lib_context` 直接使用。
