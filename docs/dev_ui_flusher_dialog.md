## 1. 模块定位与职责
- 文件：`src/echem_sdl/ui/dialogs/flusher_dialog.py`
- 作用：为冲洗系统提供手动调试界面，可启动/停止 Flusher 的三阶段流程（evacuate → fill → transfer）、设置循环次数、显示实时阶段状态（phase/cycle/is_running）与三台 FlusherPump 的基础状态。
- 约束：不直接操作 RS485，所有动作通过 `Flusher` 实例调用；必须兼容 mock 模式（Flusher/FlusherPump 为 mock 时仍可显示与运行）。

## 2. 文件与类结构
- `class FlusherDialog(QDialog)`
  - 初始化参数：
    - `flusher: Flusher`
    - `translator: TranslatorService`
    - `logger: LoggerService`
    - 可选：`parent: QWidget | None = None`
  - 字段：
    - `flusher: Flusher`
    - 控件：循环次数输入（`QSpinBox`）；阶段显示标签（evacuate/fill/transfer）；当前 cycle 显示；`btn_start`、`btn_stop`；三泵状态显示（inlet/outlet/transfer）；状态刷新定时器 `QTimer`
    - 内部状态：`timer: QTimer`, `ui_refresh_interval: int = 200`
  - 方法（含类型注解）：
    - `_build_ui() -> None`
    - `_connect_signals() -> None`
    - `_init_timer() -> None`
    - `start_flushing() -> None`
    - `stop_flushing() -> None`
    - `reload_status() -> None`（从 flusher 拉取状态更新 UI）
    - `reload_texts() -> None`

## 3. 依赖说明
- 内部：`hardware.flusher.Flusher`, `hardware.flusher_pump.FlusherPump`, `services.translator.TranslatorService`, `services.logger.LoggerService`
- 外部：PySide6（QDialog/QLabel/QPushButton/QSpinBox/QHBoxLayout/QVBoxLayout/QTimer），标准库 `typing`

## 4. 线程与异步策略
- Flusher 阶段切换可能由内部 `threading.Timer` 或 Engine external tick 驱动；后台线程不可直接操作 UI → 通过 UI `QTimer` 轮询 `reload_status`。
- `start_flushing`/`stop_flushing` 必须非阻塞；FlusherPump/Flusher 线程安全由硬件模块保证，Dialog 不加锁。

## 5. 错误与日志处理机制
- Flusher 未初始化：QMessageBox + error log。
- cycle 输入非法（<=0）：提示并拒绝启动。
- `flusher.start()`/`stop()` 抛异常：warning + QMessageBox。
- 状态刷新异常：`logger.warning`，UI 不崩溃。
- mock 模式：按钮可操作，状态模拟可显示。

## 6. 测试要求
- 功能：设置 cycles 并 start → Flusher 进入 evacuate；阶段按 evacuate→fill→transfer→下一轮；stop 立即终止；mock 模式下可演示。
- UI：阶段名称正确更新/高亮；cycle 显示正确；三泵状态显示 is_running/错误等。
- 异常：未提供 flusher 禁用按钮并提示；负数/0 循环阻止启动；FlusherPump run/stop 失败 warning 不崩溃。
- 并发：200ms 刷新不卡顿；多次 start/stop 无死锁/异常。

## 7. 文档与注释要求
- 模块 docstring：说明三阶段调试、动态泵兼容、mock 支持。
- 方法 docstring：参数/返回/线程注意事项。
- 行内注释：状态刷新来源（如 `flusher.get_phase()`）；兼容 Timer 与 external_tick 模式的说明。

## 8. 验收标准
- Dialog 可完整操作 Flusher（start/stop、cycle 设置），阶段刷新稳定。
- 模拟/真实模式均可用；与 MainWindow/Engine/LibContext 集成无冲突。
- 多语言可切换；测试通过功能/异常/并发/UI 更新场景。 
