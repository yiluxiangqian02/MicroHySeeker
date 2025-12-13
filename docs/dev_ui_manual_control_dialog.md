## 1. 模块定位与职责
- 文件：`src/echem_sdl/ui/dialogs/manual_control_dialog.py`
- 作用：提供手动控制所有泵设备（Diluter + FlusherPump）的 UI 对话框。
- 职责：动态加载 PumpManager 中全部泵（数量不固定）；对选中泵执行 `run()/stop()`，并可设置 rpm/direction；显示泵运行状态（is_running/最近响应）；mock 模式下完全可操作，不依赖真实硬件；主要用于调试，不影响正式实验。

## 2. 文件与类结构
- `class ManualControlDialog(QDialog)`
  - 初始化参数：
    - `pump_manager: PumpManager`
    - `translator: TranslatorService`
    - `logger: LoggerService | None = None`
    - 可选：`context: LibContext | None = None`
  - 字段：
    - `pump_manager: PumpManager`
    - 动态 UI：`combo_pumps: QComboBox`（列出全部泵：地址+名称）；控制按钮 `btn_run`, `btn_stop`, `btn_refresh`；可选 `spin_rpm: QSpinBox`, `combo_direction: QComboBox`; 状态显示 `label_status`, `label_last_response`
    - 内部缓存：`current_pump: Diluter | FlusherPump | None`
  - 方法（含类型注解）：
    - `_build_ui() -> None`
    - `_connect_signals() -> None`
    - `_refresh_pump_list() -> None`
    - `_select_pump(index: int) -> None`
    - `run_selected_pump() -> None`
    - `stop_selected_pump() -> None`
    - `_update_status() -> None`（QTimer 定时刷新）
    - `reload_texts() -> None`

## 3. 依赖说明
- 内部：`hardware.pump_manager.PumpManager`, `hardware.diluter.Diluter`, `hardware.flusher_pump.FlusherPump`, `services.translator.TranslatorService`, `services.logger.LoggerService`
- 外部：PySide6 Widgets；标准库 `typing`, `datetime`

## 4. 线程与异步策略
- 所有 UI 更新在主线程（Qt 事件循环）执行。
- 泵的 `run/stop` 同步触发，底层 RS485Driver 后台线程执行，不阻塞 UI。
- 禁止在 UI 线程等待硬件响应；使用 `QTimer`（200–500ms）周期刷新状态。

## 5. 错误与日志处理机制
- 无 pump（PumpManager 为空）：QMessageBox + `logger.warning`
- 泵运行失败（异常）：QMessageBox + `logger.error`
- 非法操作（rpm=0/方向非法）：提示 + `logger.warning`
- 操作日志：运行 `logger.info(f"Manual run pump {addr}")`，停止 `logger.info(f"Manual stop pump {addr}")`，刷新列表 `logger.debug("Pump list refreshed")`
- 所有错误不得导致 UI 崩溃。

## 6. 测试要求
- 动态泵列表：注册 N 个泵即显示 N 项，地址/名称正确。
+- 控制：run/stop 正确映射到选中泵；mock 下 run/stop 不访问串口但更新状态。
+- 状态刷新：QTimer 正确显示 is_running/last_response；切换泵显示同步更新。
+- 错误路径：无设备/非法参数/运行异常均有提示且不崩溃。

## 7. 文档与注释要求
- 模块 docstring：说明线程切换、泵动态渲染与调试用途。
- 方法 docstring：参数/返回/异常/线程注意事项。
- 行内注释：关键处说明泵列表动态生成、状态刷新与信号调用。

## 8. 验收标准
- 能安全控制任意泵，动态数量支持；mock/真实模式均可操作。
- 状态显示准确，操作与日志符合预期；多语言支持。
- 不阻塞 UI，不崩溃；测试通过上述场景。 
