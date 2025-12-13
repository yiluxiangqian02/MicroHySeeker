## 1. 模块定位与职责
- 文件：`src/echem_sdl/ui/dialogs/combo_editor_dialog.py`
- 作用：图形化编辑 ExpProgram 的参数组合矩阵（Combo 实验参数）。
- 职责：
  - 编辑 `param_cur_values / param_end_values / param_intervals`
  - 动态生成参数表格（参数数量不固定，禁止写死列数）
  - 编辑 `skip` 列表（跳过的组合）
  - 设置 `const_conc_mode`（恒总浓度筛选）
  - 可视化展示组合数量预估与变化
  - 将用户编辑内容安全写回 ExpProgram
- 不直接生成组合矩阵，最终矩阵由 `ExpProgram.fill_param_matrix()` 完成。

## 2. 文件与类结构
- `class ComboEditorDialog(QDialog)`
  - 初始化参数：
    - `program: ExpProgram`
    - `translator: TranslatorService`
    - `logger: LoggerService | None = None`
    - 可选：`context: LibContext | None = None`
  - 字段：
    - `program: ExpProgram`
    - 动态 UI：
      - `table_params: QTableWidget`（行=参数名，列=cur/end/interval）
      - `skip_list_widget: QListWidget`
      - `checkbox_const_conc: QCheckBox`
      - `label_total_combos: QLabel`
      - `btn_apply`, `btn_cancel`
    - 临时数据：
      - `temp_cur: dict[str, float]`
      - `temp_end: dict[str, float]`
      - `temp_intervals: dict[str, float]`
      - `temp_skip: list[int]`
  - 方法（含类型注解）：
    - `_build_ui() -> None`
    - `_connect_signals() -> None`
    - `_load_program_values() -> None`
    - `_collect_ui_changes() -> None`
    - `_apply_changes() -> None`
    - `_update_combo_count_preview() -> None`
    - `reload_texts() -> None`

## 3. 依赖说明
- 内部：`core.exp_program.ExpProgram`, `services.translator.TranslatorService`, `services.logger.LoggerService`
- 外部：PySide6 (`QDialog`, `QTableWidget`, `QCheckBox`, `QListWidget`, `QLabel`, `QPushButton`, `QMessageBox`)，标准库 `typing`, `json`

## 4. 线程与异步策略
- 完全在 UI 主线程执行。
- 禁止耗时任务；组合数量计算需轻量即时完成。

## 5. 错误与日志处理机制
- 数值非法（负步长/反向区间）：阻止保存，QMessageBox 警告，`logger.warning("Invalid combo parameter values")`
- 组合生成失败（ExpProgram 校验）：UI 提示阻止保存，`logger.error("Failed to rebuild parameter matrix")`
- 解析 UI 输入失败：提示用户，阻止写回 ExpProgram。
- 所有异常不得导致 UI 崩溃。

## 6. 测试要求
- 参数表格动态渲染：参数数量动态加载；用户可修改 cur/end/interval。
- skip 编辑：可添加/删除 skip，写回 `program.user_skip_list`。
- 恒总浓度：checkbox 状态正确写入 `program.const_conc_mode`。
- 组合预览：修改任意参数后即时更新组合数量（预估，无需生成矩阵）。
- 多语言：文本通过 translator 刷新。
- 错误路径：非数字输入弹窗；interval 为 0 警告阻止保存。

## 7. 文档与注释要求
- 模块 docstring：解释 ComboEditor 的作用、参数结构、与 ExpProgram 的关系。
- 方法 docstring：参数、返回、异常。
- 行内注释：动态渲染参数表格；skip 列表与 UI 同步逻辑；组合数量计算（预估）说明。

## 8. 验收标准
- UI 可编辑任意数量参数，不写死列/行。
- 修改的 `param_cur/end/interval/skip/const_conc` 全部正确写回 ExpProgram。
- 组合数量预览准确。
- 多语言支持完整。
- 错误处理完备，稳定不崩溃。
- 可直接与 MainWindow、ExperimentEngine 集成使用。 
