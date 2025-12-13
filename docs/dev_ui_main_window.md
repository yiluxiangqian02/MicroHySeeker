## 1. 模块定位与职责
- **MainWindow 职责**：系统主界面（启动/停止实验，显示状态与日志）；动态渲染泵状态（Diluter 多台 + Flusher 三泵）；展示电化学数据（实时曲线占位/可选图表）；绑定 ExperimentEngine、Hardware、SettingsService 等；接收 TranslatorService 语言切换信号并更新文本；提供引擎事件入口（start/stop/pause/resume）。
- **Dialogs 职责**：
  - 配置对话框：编辑 `settings.json`（diluter_pumps/flusher_pumps/RS485/CHI/Kafka 等）。
  - ProgramEditorDialog：编辑 ExpProgram/参数矩阵。
  - Combo 参数编辑器：参数区间、步长、skip、恒浓度模式。
  - 手动控制：泵手动运行、Flusher 手动流程（调试）、CHI 手动运行（可选）。
  - RS485 测试：端口扫描、发帧、查看回帧。
  - 日志窗口：级别过滤、自动追加。
- UI 不能假设固定泵数量，必须从 `context.pump_manager` 动态生成组件。

## 2. 文件与类结构
必须文件：
```
ui/
  main_window.py
  dialogs/
    config_dialog.py
    program_editor_dialog.py
    combo_editor_dialog.py
    manual_control_dialog.py
    flusher_dialog.py
    rs485_test_dialog.py
    log_viewer_dialog.py
```
- `class MainWindow(QMainWindow)`
  - 字段：
    - `context: LibContext`
    - `experiment_engine: ExperimentEngine`
    - `translator: TranslatorService`
    - `logger: LoggerService`
    - 动态组件：`pump_widgets: dict[int, QWidget]`, `flusher_widgets: dict[str, QWidget]`
    - 图形：start/stop/pause/settings/program_editor 按钮；状态标签（current step、combo index、elapsed）；曲线区域占位；日志面板（QTextEdit）
  - 方法（带类型注解）：
    - UI 构建：`_build_ui() -> None`, `_build_pump_panel() -> None`, `_build_menu() -> None`, `_connect_signals() -> None`
    - 实验操作：`start_experiment() -> None`, `stop_experiment() -> None`, `update_status() -> None`（QTimer 驱动）
    - 多语言：`reload_texts() -> None`（translator 回调）
    - 日志：`append_log(record: LogRecord) -> None`
    - 图表：`update_plot(points: list[tuple[float, float]]) -> None`
- Dialogs：`class XxxDialog(QDialog)`；读取/写回 settings.json 或 ExpProgram；动态 UI（支持泵数量）；方法：`_load_from_settings() -> None`, `_apply_changes() -> None`, `reload_texts() -> None`

## 3. 依赖说明
- 内部：LibContext / ExperimentEngine；LoggerService / SettingsService / TranslatorService；Hardware（pump_manager, diluter, flusher, chi）；ExpProgram / ProgStep
- 外部：PySide6.QtWidgets/QtCore/QtGui；matplotlib 或 pyqtgraph（可选实时曲线）；标准库 typing/json/pathlib

## 4. 线程与异步策略
- 硬件后台线程（RS485Driver、CHI worker）通过 Qt Signal 切到 UI 线程更新；禁止后台直接操作 UI。
- 使用 `QTimer`（200–500ms）驱动 `update_status()`；按钮回调调用 engine 安全方法。
- 日志回调经 QtSignal 到 UI 线程；曲线更新需节流（如 200ms 一次）。

## 5. 错误与日志处理机制
- 硬件异常 try/except → QMessageBox 提示。
- 配置读写错误 → error 日志 + 弹窗。
- UI 操作（start/stop/program loaded）写 logger.info。
- 语言切换失败 → warning。

## 6. 测试要求
- MainWindow：动态泵面板随 PumpManager 注册数量生成；start/stop 控制 ExperimentEngine；状态显示 step/combo/time/phase/chi；日志实时追加。
- Dialogs：settings_dialog 写回后 engine 可读取新配置；program_editor_dialog 序列化/反序列化一致；manual_control_dialog 能对任意泵发命令（mock 下不报错）；rs485_test_dialog 能扫描端口/发帧；多语言切换文本刷新。
- 并发/线程安全：后台大量日志 UI 不冻结；CHI 高频数据曲线不崩溃；多次打开/关闭 dialog 无泄漏。

## 7. 文档与注释要求
- 每个 UI 模块模块 docstring 说明用途/依赖；方法 docstring 说明参数/返回/线程注意事项；关键动态渲染处行内注释。
- 主窗口示例图可文字描述；Dialogs 关系可文字描述。

## 8. 验收标准
- 完全支持动态泵数量；语言可切换；运行/停止可靠；实时数据稳定；UI 不崩溃且不阻塞硬件线程；所有 dialogs 功能可用并与 settings/engine 整合；测试通过流程/错误路径/动态更新场景。 
