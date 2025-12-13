## 1. 模块定位与职责
- 文件：`src/echem_sdl/core/exp_program.py`
- 作用：定义实验程序（ExpProgram）模型，维护步骤列表与可变参数组合矩阵；支持多参数组合实验（Combo），提供生成/遍历/筛选/跳转/序列化功能，供 ExperimentEngine 调用加载当前参数集。

## 2. 文件与类结构
- 依赖：`core.prog_step.ProgStep`, `utils.constants`, 标准库/可选 pydantic。
- `class ExpProgram`：
  - 字段示例：
    - `steps: list[ProgStep]`
    - `param_cur_values: dict[str, float | str]`（当前参数快照，可选）
    - `param_end_values: dict[str, float | str]`
    - `param_intervals: dict[str, float | str]`
    - `param_matrix: list[dict[str, Any]]`（组合列表，笛卡尔积结果）
    - `param_index: int = 0`（当前组合索引）
    - `combo_enabled: bool = False`
    - `total_exp_count: int = 0`
    - `const_conc_mode: bool = False`
    - `user_skip_list: list[int] = []`
  - 方法（含类型注解）：
    - `fill_param_matrix() -> None`: 根据当前/终值/步长生成组合矩阵（笛卡尔积）。
    - `load_param_values(index: int | None = None) -> dict[str, Any]`: 加载指定或当前索引的参数到 steps/cur_values。
    - `next_combo() -> bool`: 索引前进一项（跳过 skip 条目），返回是否成功。
    - `previous_combo() -> bool`: 索引回退一项，返回是否成功。
    - `select_combo(index: int) -> None`: 跳转到指定索引（边界检查）。
    - `refresh_params() -> None`: 重新生成矩阵/计数，重置索引。
    - `set_const_conc_mode(enable: bool) -> None`: 开关恒总浓度筛选。
    - `skip_current() -> None`: 将当前索引加入 skip 列表。
    - `is_combo_completed() -> bool`: 判断是否到达末尾。
    - `serialize() -> str | dict`: 导出 JSON 兼容结构。
    - `deserialize(data: str | dict) -> None`: 从 JSON/字典恢复状态。

## 3. 依赖说明
- 内部：`core.prog_step.ProgStep`, `utils.constants`（默认值/类型）；可选 `lib_context` 只用于日志（不强依赖）。
- 第三方：可选 `pydantic`（参数校验），或 `dataclasses`。
- 标准库：`typing`, `copy`, `json`, `itertools`.

## 4. 线程与异步策略
- 默认单线程（ExperimentEngine 调用）；无锁需求。确保索引操作边界检查，方法幂等。
- 不进行硬件操作。

## 5. 错误与日志处理机制
- 参数不匹配/空矩阵：记录 error/raise ValueError。
- 索引越界：记录 warning，维持当前索引或纠正到边界。
- JSON 解析失败：记录 error，抛异常或回退默认。
- 生成/加载/跳转等重要操作使用 logger（若提供）记录 info/debug。

## 6. 测试要求
- 参数矩阵生成：多参数笛卡尔积正确（含升降步长/零步长处理）。
- 加载参数：返回并应用到 steps/cur_values 正确。
- next/previous：索引移动正确，边界行为符合预期。
- 恒总浓度筛选逻辑：启用时正确过滤组合。
- 跳过/skip：skip 列表生效，组合计数与进度正确。
- 序列化/反序列化：往返一致，状态保持。
- 错误路径：空参数/非法步长/JSON 损坏。

## 7. 文档与注释要求
- 模块 docstring：说明组合矩阵生成/遍历原理，恒总浓度/skip 策略。
- 类/方法 docstring：参数、返回、异常、边界行为。
- 类型注解完整；在矩阵生成和索引调整处添加行内注释。

## 8. 验收标准
- 类与接口按定义实现；矩阵生成与遍历正确。
- 错误与日志处理符合预期（空矩阵/越界/解析失败有提示）。
- 测试通过：矩阵生成、加载、跳转、筛选、序列化。
- 可被 ExperimentEngine 直接调用，无运行时错误。
