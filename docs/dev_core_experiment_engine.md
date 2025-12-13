## 1. 模块定位与职责
- 文件：`src/echem_sdl/core/experiment_engine.py`
- 作用：实验引擎主控制器，协调 `ExpProgram` 与 `ProgStep`，驱动实验生命周期（加载→准备→启动→周期 tick→结束），按时序调用硬件模块，管理单步与组合实验的状态机与进度。引擎不假设泵数量；所有泵/地址由配置和 `LibContext.diluters` 提供。

## 2. 文件与类结构
- 依赖：`core.prog_step.ProgStep`, `core.exp_program.ExpProgram`, `lib_context.LibContext`, `utils.constants`, `services.logger`.
- `class ExperimentEngine`：
  - 初始化参数：`context: LibContext`, `tick_interval: float = 1.0`
  - 字段：`context`, `program`, `current_step`, `running`, `combo_running`, `tick_interval`, `elapsed_time`, `elapsed_step_time`, `start_time`, `combo_start_time`, `step_index`, `lock`
  - 方法：`load_program()`, `prepare_steps()`, `start()`, `stop()`, `tick()`, `execute_step()`, `advance_step()`, `is_running()`, `get_progress()`, 可选 `pause()/resume()`、事件钩子。

## 3. 依赖说明
- 内部：ProgStep/ExpProgram/LibContext/constants/logger
- 标准库：`datetime`, `threading`, `typing`, `time`
- 第三方：无必需（Qt 信号在 UI 层处理）

## 4. 状态机设计
- 状态：Idle → Running → StepExecuting → StepCompleted → NextStep → (NextCombo) → Done。
- 流程：`load_program` → `start` 初始化；`tick` 更新计时，若 step idle 则 `execute_step`，运行中检查 `update_state`，完成则 `advance_step`，末步且 combo 启用则 `program.next_combo()+load_param` 重启；全部组合完成后 `stop`。

## 5. 线程与异步策略
- 默认单线程；`tick` 由 UI QTimer 或后台线程调用。共享状态修改持 `lock`，进度查询可并发读取。
- 无内部新线程（硬件线程由设备自身管理）。

## 6. 错误与日志处理机制
- 加载/准备失败：error + 停止。
- Step 执行异常：error，置 StepState.FAILED；视设计跳过或终止。
- Combo 跳转失败：warning。
- 完成/中止：summary 日志。
- 日志统一 `context.logger`；可写入 `context.log_buffer`。

## 7. 测试要求
- 加载/启动：正常加载 ExpProgram，动态泵列表可用（>6 支持）。
- tick 推进：步骤推进、时间累计正确。
- 状态流转：idle→running→done/failed，`step_index` 正确递增。
- 组合模式：多参数循环正确；结束条件正确。
- 错误路径：空 program、step 异常、combo 越界；日志记录且不崩溃。
- 并发：并发 tick/进度查询无竞争（锁生效）。

## 8. 文档与注释要求
- 模块 docstring：描述状态机、tick 驱动、动态泵假设（通过地址/列表识别）。
- 类/方法 docstring：参数、返回、异常、状态说明。
- 类型注解完整；锁/状态转移处添加简短注释。

## 9. 验收标准
- 类与接口完整；状态机逻辑正确；支持动态泵数量（无写死 3/6 的假设）。
- 异常与日志输出符合预期；测试通过：单步/组合/错误路径/并发。
- 可被 UI 或 CLI 驱动；类型注解、docstring 与测试齐全。 
