## 1. 模块定位与职责
- 文件：`src/echem_sdl/ui/dialogs/log_viewer_dialog.py`
- 作用：独立日志查看器，支持实时追加日志（QtSignal）、日志级别过滤（ALL/INFO/WARNING/ERROR/DEBUG）、自动滚动/暂停、搜索与清空、可选导出，支持多语言。
- 要求：非阻塞，高频日志不卡 UI；与 LoggerService 解耦，仅通过信号接收；多语言可切换。

## 2. 文件与类结构
- `class LogViewerDialog(QDialog)`
  - 初始化参数：`logger: LoggerService`, `translator: TranslatorService`, 可选 `parent: QWidget | None = None`
  - 字段：
    - UI：`text_view: QTextEdit`（只读），`combo_filter: QComboBox`（ALL/INFO/WARNING/ERROR/DEBUG），`edit_search: QLineEdit`（可选），`chk_autoscroll: QCheckBox`，`chk_pause: QCheckBox`，`btn_clear: QPushButton`，可选 `btn_export: QPushButton`
    - 状态：`paused: bool`，`current_filter: str`，`cached_logs: list[LogRecord]`
    - 信号：`append_log_signal: QtCore.Signal(LogRecord)`（LoggerService → UI 线程追加）
  - 方法（含类型注解）：
    - `_build_ui() -> None`
    - `_connect_signals() -> None`
    - `append_log(record: LogRecord) -> None`（槽，UI 线程写入）
    - `_filter_record(record: LogRecord) -> bool`
    - `_apply_filter() -> None`
    - `set_filter(level: str) -> None`
    - `_scroll_to_bottom() -> None`
    - `clear_logs() -> None`
    - 可选：`export_logs() -> None`
    - `reload_texts() -> None`

## 3. 依赖说明
- 内部：`services.logger.LoggerService`, `services.translator.TranslatorService`
- 外部：PySide6 (`QtWidgets`, `QtCore`, `QtGui`)，标准库 `typing`, `datetime`, `json`（导出）

## 4. 线程与异步策略
- LoggerService 通过 QtSignal emit 日志到 UI；后台线程不可直接操作 UI。
- 追加文本需轻量，可选节流/批量（如 50ms flush 缓冲）以防卡顿。
- `paused=True` 时暂停追加或仅缓冲，不滚动。

## 5. 错误与日志处理机制
- UI 错误提示 warning，不影响主程序。
- 导出失败（权限等）：QMessageBox + `logger.error`
- 过滤条件非法：回退 ALL。

## 6. 测试要求
- 高频日志：快速 1000+ 追加不卡顿，自动滚动准确。
- 过滤：切换等级实时刷新；多语言切换文本更新。
- 控件：清空有效；暂停不滚动；搜索/导出（如实现）正常。
- 线程安全：后台 emit 高频日志，UI 无跨线程错误。

## 7. 文档与注释要求
- 模块 docstring：说明日志查看目的、信号机制、性能注意点。
- 方法 docstring：参数/返回/异常/线程注意事项。
- 行内注释：过滤逻辑、自动滚动逻辑、Signal→slot 线程切换。

## 8. 验收标准
- 稳定显示系统日志，不冻结、不丢日志。
- 支持过滤/清空/暂停，搜索/导出（若实现）；多语言可切换。
- UI 与线程安全，性能良好；通过功能/异常/压力测试。 
