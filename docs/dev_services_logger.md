## 1. 模块定位与职责
- 文件：`src/echem_sdl/services/logger.py`  
- 角色：提供全局可注入的结构化日志服务，支持多 sink（控制台/文件/可选 UI 回调），线程安全，统一格式与级别过滤，为硬件/核心/UI/服务模块提供一致的日志出口。

## 2. 文件与类结构
- `LoggerService` 类
  - 初始化参数：`level: str = "INFO"`, `fmt: str | None`, `datefmt: str | None`, `handlers: list[logging.Handler] | None`, `ui_callback: Callable[[LogRecord], None] | None`, `queue_size: int = 1000`.
  - 属性：内部 `logging.Logger`，线程安全队列（若使用队列处理）、级别映射。
  - 方法签名（均返回 None，除非特殊说明）：
    - `log(level: str, msg: str, **kwargs) -> None`
    - `info(msg: str, **kwargs) -> None`
    - `warning(msg: str, **kwargs) -> None`
    - `error(msg: str, **kwargs) -> None`
    - `debug(msg: str, **kwargs) -> None`
    - `exception(msg: str, exc: BaseException | None = None, **kwargs) -> None`（记录异常堆栈）
    - `bind_ui_callback(callback: Callable[[logging.LogRecord], None]) -> None`
    - `add_file_handler(path: Path, level: str | None = None) -> None`
    - `add_console_handler(level: str | None = None) -> None`
    - 可选：`start_queue_listener()` / `stop_queue_listener()` 若采用队列处理。
- 辅助：
  - 日志格式常量（默认格式/日期格式）
  - 级别映射字典

## 3. 依赖说明
- 标准库：`logging`, `logging.handlers`, `queue`, `threading`, `pathlib`.
- 可选：`typing`（类型注解）、`PySide6.QtCore.Signal` 或 UI 回调类型（不直接依赖 UI，使用可注入回调）。
- 内部依赖：无强耦合；可被 `lib_context`/其他服务注入。

## 4. 线程与异步策略
- 线程安全：使用 logging 内置锁；如支持 UI sink，采用线程安全队列或跨线程回调（在 UI 线程消费）。
- 异步刷新：可选队列 + `QueueListener`，后台线程将日志分发到 handler/UI 回调。
- UI 展示：`ui_callback` 接收 `LogRecord`，由调用方确保在 UI 线程处理（例如在 Qt 信号槽中转）。

## 5. 错误与日志处理机制
- 统一格式：`[%(asctime)s] [%(levelname)s] %(name)s - %(message)s`
- 级别过滤：实例级别 + handler 级别；`log(level, msg)` 校验有效级别。
- 异常：`exception()` 自动附带 traceback；遇到 handler 创建失败应记录并抛出可诊断错误。
- 不应吞掉用户异常，记录后允许向上抛出（由调用方决定）。

## 6. 测试要求
- 多线程写日志：并发调用 `info/debug/error` 不丢失、不交叉格式。
- 级别过滤：低于当前级别的日志不输出；handler 自身级别生效。
- 文件写入：`add_file_handler` 输出内容符合格式，文件可打开读取。
- UI sink：绑定回调后可收到 `LogRecord`，记录内容与级别正确；在单元测试中用伪回调或队列验证。
- 异常记录：`exception()` 含 traceback。
- 可选队列模式：启用后仍然保证顺序与完整性。

## 7. 文档与注释要求
- 每个公开方法提供 docstring（职责、参数、返回、线程/回调注意事项）。
- 模块头部简述用途与线程模型。
- 类型注解完整（PEP 484）；必要处添加简短行内注释说明非显式逻辑（如 UI 回调线程责任）。
- README/内嵌注释说明如何在 `lib_context` 或 UI 中注入/绑定。

## 8. 验收标准
- 提供上述类/方法，接口完整且带类型注解与 docstring。
- 支持至少控制台 + 文件 handler，可绑定 UI 回调。
- 日志级别过滤/格式正确；异常记录包含栈信息。
- 所有测试用例通过：并发、级别过滤、文件输出、UI 回调、异常日志。
- 无未处理的线程安全问题；模块可独立运行（可通过简单示例验证）。
