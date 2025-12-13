## 1. 模块定位与职责
- 文件：`src/echem_sdl/services/data_exporter.py`
- 作用：统一的数据导出服务（CSV/Excel），为 CHIInstrument、ExperimentEngine、UI 提供安全、线程友好的数据写入能力。
- 特点：
  - 使用 pandas/openpyxl/csv 等库格式化输出；
  - 与 CHIInstrument 的 `data_points` 结构（list[tuple[x, y]]) 完全兼容；
  - 文件路径来自 `settings_service`（如 `export_dir`），可自动创建目录；
  - 可选异步写入（ThreadPool），避免 UI 阻塞。

## 2. 文件与类结构
- `class DataExporter`
  - 初始化参数：
    - `export_dir: Path`
    - `logger: LoggerService | None = None`
    - `async_mode: bool = False`
    - 可选：`executor: ThreadPoolExecutor | None = None`
  - 字段：
    - `export_dir: Path`
    - `logger: LoggerService`
    - `async_mode: bool`
    - `executor`
    - 可选：`lock: threading.RLock`
  - 主要方法（含类型注解）：
    - `export_csv(data: list[tuple[float, float]], filename: str) -> Path`
    - `export_excel(data: list[tuple[float, float]], filename: str) -> Path`
    - `export_dict_list(rows: list[dict], filename: str) -> Path`
    - `ensure_dir() -> None`
    - `run_async(func: Callable, *args, **kwargs) -> Future | Path`
    - 可选：`export_generic(data: Any, format: str, filename: str) -> Path`

## 3. 依赖说明
- 内部：`services.logger.LoggerService`；`services.settings_service.SettingsService`（由调用方提供 export_dir）
- 外部：`pandas`、`openpyxl`（Excel 写入）、`csv`、`pathlib.Path`
- 标准库：`threading`, `concurrent.futures`, `typing`, `json`

## 4. 线程与异步策略
- `async_mode=True` 时提交任务到 ThreadPool，避免 UI 卡顿；否则同步写。
- 文件写操作需线程安全，必要时用 `lock`。
- 异步模式返回 Future，调用方可选择等待。
- 日志输出需线程安全。

## 5. 错误与日志机制
- 写入失败（权限/路径/磁盘）：记录 error 并抛异常。
- 自动创建 `export_dir`，创建失败记录 error。
- 数据为空：warning，但仍生成空文件。
- Excel 写入异常：error，必要时回退 CSV。
- 导出成功：info（文件路径、数据点数量）。

## 6. 测试要求
- CSV 导出：行数正确、格式正确、文件可读。
- Excel 导出：表结构正确、单元格可读。
- 异步模式：Future 正常返回，文件生成完整。
- 并发：多线程导出不同文件不冲突。
- 错误路径：只读目录/非法路径记录日志、不崩溃。
- 空数据导出：文件存在且结构正确。

## 7. 文档与注释要求
- 模块 docstring：描述同步/异步模式、数据格式、线程模型。
- 方法 docstring：参数、返回值、异常说明。
- 类型注解完整；关键点（文件创建、异常处理）添加行内注释。

## 8. 验收标准
- 支持 CSV 与 Excel 输出，接口完整。
- 同步/异步模式可靠。
- 错误处理健壮，日志完整。
- 测试通过：CSV/Excel/async/并发/错误路径。
- 可被 CHIInstrument、ExperimentEngine、UI 安全调用。 
