## 1. 模块定位与职责
- 文件：`src/echem_sdl/ui/dialogs/program_editor_dialog.py`
- 作用：创建/编辑 `ExpProgram`（实验程序），包含步骤列表 `ProgStep` 编辑、程序参数设置、组合参数编辑入口（不生成矩阵）、导入/导出 JSON。
- 职责：
  - 动态创建/删除步骤（禁止写死数量）
  - 编辑单步 `operation/params/duration` 等字段
  - 导入/导出 ExpProgram 的 JSON（序列化/反序列化）
  - 渲染并写回 ExpProgram，使其可被 ExperimentEngine 直接使用
  - 多语言刷新（TranslatorService）
  - Combo 参数矩阵生成由 ComboEditorDialog 负责，本对话框不生成矩阵。

## 2. 文件与类结构
- `class ProgramEditorDialog(QDialog)`
  - 初始化参数：
    - `context: LibContext`
    - `settings: SettingsService`
    - `translator: TranslatorService`
    - 可选：`logger: LoggerService | None = None`
  - 字段：
    - `program: ExpProgram`（当前编辑程序）
    - UI：`step_table: QWidget`（动态表格/列表显示步骤），`step_editor_panel: QWidget`（参数编辑区），`import_button`/`export_button`，`add_step_button`/`remove_step_button`
    - 缓冲：`temp_data: dict`（UI → 程序暂存）
  - 方法（含类型注解）：
    - `_build_ui() -> None`（构建步骤列表、参数区、按钮区）
    - `_load_program(program: ExpProgram) -> None`（从 ExpProgram 填充 UI，动态行数）
    - `_serialize_program() -> dict`（UI → ExpProgram 字典）
    - `_apply_changes() -> None`（写回内部 ExpProgram）
    - `_add_step() -> None`
    - `_delete_step() -> None`
    - `reload_texts() -> None`（国际化刷新）

## 3. 依赖说明
- 内部：`core.exp_program.ExpProgram`, `core.prog_step.ProgStep`, `services.translator.TranslatorService`, `services.logger.LoggerService`, `services.settings_service.SettingsService`, `lib_context.LibContext`
- 外部：PySide6(QtWidgets/QtCore)，标准库 `json`, `typing`, `pathlib`

## 4. 线程与异步策略
- UI 仅运行在 Qt 主线程，无后台线程。
- JSON 导入/导出同步进行。
- 不允许在 UI 中调用长时间阻塞的 ExperimentEngine 逻辑。

## 5. 错误与日志处理机制
- JSON 导入失败：QMessageBox + `logger.error`
- 非法数值（如 duration 负数）：QMessageBox + `logger.warning`
- 步骤字段缺失：提示并拒绝保存
- UI 更新异常：记录日志但不崩溃 UI

## 6. 测试要求
- 动态渲染：添加/删除/编辑步骤无误；任意数量步骤（1–50）不卡顿
- UI→Program：序列化结果与输入一致；Program→UI：加载后完整回显
- JSON：导入后正确渲染；导出可重载，往返一致
- 国际化：`reload_texts()` 后文本正确变化
- 边界：空步骤列表；参数字段不完整时提示且不写入

## 7. 文档与注释要求
- 模块 docstring：说明用于编辑 ExpProgram，不负责参数矩阵生成
- 方法 docstring：参数/返回/异常
- 行内注释：动态生成步骤行的逻辑；参数字典映射到 ProgStep 的方式

## 8. 验收标准
- 支持任意数量步骤的添加/删除/修改
- JSON 导入/导出正确、往返一致
- UI 不阻塞主线程，多语言支持完善
- 与 ExperimentEngine 完全兼容，可直接保存/加载运行程序
- 通过加载/保存/导入/导出/编辑/错误路径等测试。 
