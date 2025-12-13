## 1. 模块定位与职责
- 文件：`src/echem_sdl/ui/dialogs/rs485_test_dialog.py`
- 作用：RS485 通信调试界面，支持扫描本机串口、打开/关闭指定串口、发送自定义帧（HEX/ASCII）、显示实时回帧，兼容 RS485Driver 的 mock/真实模式。仅用于调试，不影响主流程，支持动态泵数量/地址。

## 2. 文件与类结构
- `class RS485TestDialog(QDialog)`
  - 初始化参数：
    - `driver: RS485Driver`
    - `translator: TranslatorService`
    - `logger: LoggerService`
    - 可选：`parent: QWidget | None = None`
  - 字段：
    - UI 控件：串口下拉框（可用端口列表），波特率选择（默认来自 settings），`open`/`close` 按钮，帧输入框（HEX/ASCII 模式切换），`send` 按钮，回显窗口（QTextEdit），清空日志按钮
    - 状态：当前串口状态（opened/closed），最近接收帧
    - 并发：`lock: threading.RLock`，QtSignal（driver 回调→UI 更新）
  - 方法（含类型注解）：
    - `_build_ui() -> None`
    - `_connect_signals() -> None`
    - `scan_ports() -> None`
    - `open_port() -> None`
    - `close_port() -> None`
    - `send_frame() -> None`（自动判断 HEX/ASCII，转 bytes 调用 driver.send_frame 或 driver.serial.write）
    - `handle_response(frame: bytes) -> None`（QtSignal 更新 UI）
    - `_append_rx_log(text: str) -> None`
    - `reload_texts() -> None`

## 3. 依赖说明
- 内部：`hardware.rs485_driver.RS485Driver`, `services.logger.LoggerService`, `services.translator.TranslatorService`
- 外部：PySide6（QDialog, QLabel, QPushButton, QComboBox, QTextEdit, QLineEdit, QCheckBox, QHBoxLayout, QVBoxLayout, QTimer），标准库 `serial.tools.list_ports`, `typing`, `binascii`

## 4. 线程与异步策略
- RS485Driver `callback` 在后台线程触发，必须通过 QtSignal 将数据推入 UI。
- 所有 UI 更新在主线程执行；`send_frame()` 需立即返回不阻塞。
- 串口扫描可同步执行；driver.open/close 需 try/except 并快速返回。

## 5. 错误与日志处理机制
- 串口打开失败：QMessageBox + `logger.error`
- 发送失败：warning + UI 提示
- 非法 HEX：提示并拒绝发送
- 回帧解析失败：`logger.warning`（仍显示原始内容）
- 端口关闭时尝试发送：QMessageBox + `logger.warning`
- mock 模式：UI 显示 “MOCK MODE”
- 日志：开/关端口 info；发送帧 debug（hex）；收到帧 debug（hex）

## 6. 测试要求
- 串口：扫描可用端口；open/close 正常切换且无崩溃；多次开关无异常。
- 帧交互：合法 HEX 转 bytes 成功发送；接收帧正确显示（十六进制+ASCII）；mock 模式模拟回帧并显示。
- UI 行为：未打开端口 send 按钮禁用；日志窗口自动滚动；清空按钮生效。
- 异常：非法 HEX 弹框；发送中断开 warning 不崩溃；关闭 Dialog 可选安全断联。

## 7. 文档与注释要求
- 模块 docstring：说明 RS485 调试用途、mock 模式、回调机制。
- 方法 docstring：参数、返回值、线程注意事项。
- 行内注释：HEX 转 bytes、QtSignal 派发、串口 open/close 逻辑。

## 8. 验收标准
- 可进行 RS485 基础调试（扫描/开关端口/发送帧/查看回帧），支持 mock/real。
- UI 稳定不崩溃，不阻塞主线程；错误处理可靠，日志清晰；多语言可刷新。
- 测试通过所有正常/异常路径。 
