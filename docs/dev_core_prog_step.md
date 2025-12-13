## 1. 模块定位与职责
- 文件：`src/echem_sdl/core/prog_step.py`
- 作用：定义实验步骤（ProgStep）的数据结构与逻辑；描述单步实验（配液、冲洗、电化学、换样、等待/空白等），保存参数、持续时间与状态，提供预处理、启动执行、状态更新与描述接口，供 ExperimentEngine 调度。

## 2. 文件与类结构
- 依赖枚举：可直接引用 `utils.constants.OperationType`、`utils.constants.StepState`（或本模块内定义后映射）。
- `class ProgStep`（可用 pydantic BaseModel 或普通类，保持类型注解）：
  - 字段（示例）：
    - `operation: OperationType`
    - `state: StepState = StepState.IDLE`
    - `params: dict[str, Any]`（通用参数：配液成分/电化学参数/泵设置/位移等）
    - `duration: float = 0.0`（秒）
    - `started: bool = False`
    - `completed: bool = False`
    - `start_time: datetime | None = None`
    - `end_time: datetime | None = None`
  - 方法：
    - `prepare(context: LibContext) -> None`: 执行前预计算（体积→分度/估计时长/冲洗周期/位置距离等），填充/规范化 `params` 与 `duration`。
    - `start(context: LibContext) -> None`: 根据 `operation` 调用对应硬件（Diluter/Flusher/Positioner/CHI），记录 `start_time`，标记 `started`。
    - `update_state(context: LibContext, elapsed: float) -> StepState`: 依据硬件状态或时间判断当前状态（running/done/failed），更新 `state/completed/end_time` 并返回。
    - `get_desc(context: LibContext | None = None) -> str`: 生成用于 UI/日志的步骤描述。
    - `reset() -> None`: 重置状态字段为初始值。

## 3. 依赖说明
- 内部：`lib_context.LibContext`, `utils.constants`（OperationType, StepState, 默认值等）
- 标准库：`datetime`, `typing`
- 第三方：可选 `pydantic`（若使用 BaseModel 建模参数与校验）。

## 4. 线程与异步策略
- 由 ExperimentEngine 的主循环/tick 调用，默认单线程上下文；不需内部创建线程。
- `update_state` 应幂等、可重复调用；避免修改硬件状态，仅读取并返回判断结果。

## 5. 错误与日志处理机制
- 参数缺失/非法：抛出 `ValueError` 并使用 `context.logger.error` 记录。
- 硬件启动失败（start）：记录 error，`state = StepState.FAILED`。
- 状态更新异常：捕获、记录 warning，不应导致主循环崩溃；可将 `state` 置为 FAILED 视情况而定。
- 日志统一通过 `context.logger`，必要时写入 `context.log_buffer`。

## 6. 测试要求
- 创建/初始化：字段默认值正确（state=IDLE，started=False 等）。
- `prepare()`：对不同 operation 正确计算/规范 `duration` 与参数（可用 mock context 验证）。
- `start()`：按 operation 调用对应硬件接口（使用 mock Diluter/Flusher/Positioner/CHI），异常时转 FAILED。
- `update_state()`：根据 mock 硬件状态与 elapsed 返回正确 StepState（idle→running→done/failed）；时间超时判定。
- 错误路径：缺参/非法类型/硬件抛异常；保证记录日志且不崩溃。

## 7. 文档与注释要求
- 模块 docstring：说明 ProgStep 角色、状态流转、与 ExperimentEngine 的关系。
- 类/方法 docstring：参数、返回、可能异常、线程/调用约束。
- 类型注解完整；在状态流转/硬件分支处添加简短注释。

## 8. 验收标准
- 类与接口按上述定义实现；状态转换合理，幂等调用安全。
- 异常与日志输出符合预期（错误路径有记录）。
- 测试通过：字段初始化、prepare/start/update、错误路径、状态流转。
- 可被 ExperimentEngine 调用无错误，能够驱动对应硬件或模拟。
