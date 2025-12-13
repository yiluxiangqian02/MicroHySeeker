## 1. 模块定位与职责
- 文件：`src/echem_sdl/ui/dialogs/config_dialog.py`
- 作用：全局配置编辑器，读取/展示/修改并写回 `settings.json`。编辑范围：
  - 动态泵配置：`diluter_pumps`（数量可变）
  - 冲洗泵配置：`flusher_pumps`（inlet/outlet/transfer）
  - RS485：端口/波特率
  - CHI：dll/模拟模式/参数
  - Kafka：broker/topics/enable
  - 数据导出路径
  - 语言设置（可选）
- 要求：UI 动态生成（泵数量不可写死）；字段严格映射 SettingsService 数据结构；修改后立即校验并可写回 JSON；语言切换实时刷新文本。

## 2. 文件与类结构
- `class ConfigDialog(QDialog)`
  - 初始化参数：`settings: SettingsService`, `translator: TranslatorService`, `logger: LoggerService`, 可选 `context: LibContext`, 可选 `parent: QWidget | None = None`
  - 字段：
    - UI：diluter 泵表格（动态行）、flusher 泵配置区（inlet/outlet/transfer）、RS485 区（port/baudrate）、CHI 区（dll/enable/mock）、Kafka 区（enable/broker/topics）、Export 区（目录选择器）、按钮（保存/应用/取消）
    - 状态：`_buffer: dict`（临时配置）、`_current_locale: str`
    - 语言刷新：QtSignal → `reload_texts()`
  - 方法（类型注解）：
    - `_build_ui() -> None`
    - `_connect_signals() -> None`
    - `_load_from_settings() -> None`（读取 SettingsService dict，填充 UI）
    - `_collect_ui_values() -> dict`（从 UI 生成配置 dict）
    - `_validate_config(cfg: dict) -> bool`（校验泵配置/端口/数值范围）
    - `_apply_changes() -> None`（写回 SettingsService → 保存 JSON，提示需重启部分硬件）
    - `reload_texts() -> None`（翻译所有标签）
    - `refresh_dynamic_pump_table() -> None`（重建 diluter 表格行）

## 3. 依赖说明
- 内部：`services.settings_service.SettingsService`, `services.translator.TranslatorService`, `services.logger.LoggerService`, `lib_context.LibContext`
- 外部：PySide6(QtWidgets/QtCore), `json`, `pathlib`, `typing`

## 4. 线程与异步策略
- 配置加载/保存在主线程执行；禁止后台线程修改 UI。
- 若保存 IO 较重，可选 QtConcurrent，但默认同步。
- 不直接调用硬件；硬件刷新需在 MainWindow 重建 LibContext/Engine。

## 5. 错误与日志处理机制
- 加载失败：QMessageBox + `logger.error`
- 非法值：UI 提示 + 禁止保存
- 保存失败：QMessageBox + `logger.error`
- 关键事件：保存成功 → `logger.info("Settings saved")`
- 端口不存在 warning；路径无权限 error；address 重复 error 禁止保存；rpm/divpermL 非数字 warning。

## 6. 测试要求
- 配置加载：diluter_pumps 任意数量（1–12）行数匹配；flusher 三泵加载；RS485/CHI/Kafka 字段可编辑。
- 配置保存：修改后 JSON 写回一致；SettingsService.reload 后与 UI 匹配。
- 校验：非法 address/rpm/baudrate 阻止保存；缺失字段提示。
- 多语言：切 locale 文本更新。

## 7. 文档与注释要求
- 模块 docstring：说明动态 UI、写回机制、与 SettingsService 关系。
- 方法 docstring：参数/返回/异常/线程提示。
- 行内注释：泵表格动态生成、settings 映射（settings→UI、UI→settings）、校验规则。

## 8. 验收标准
- 能完整编辑 `settings.json` 所有字段，支持任意数量泵。
- 校验与保存稳定；多语言支持；线程安全；与 LibContext/ExperimentEngine 集成正常。
- 测试通过加载/保存/校验/多语言。 
