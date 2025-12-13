## 1. 总体职责
- 实验引擎由 `ProgStep`、`ExpProgram`、`Experiment` 组成：定义与管理实验步骤，生成组合参数矩阵，按定时驱动硬件（Diluter/Flusher/Positioner/CHI）执行，并跟踪实验/步骤/组合的运行状态与时间。引擎不假设泵数量，所有泵/地址由配置动态提供。

## 2. 组成模块职责分工
- **ProgStep**：描述单个实验步骤（配液、冲洗、电化学、移液、换样、空白）；包含操作参数、持续时间、状态标志；计算/准备每步执行参数，并按当前硬件状态判断完成。
- **ExpProgram**：维护步骤列表及可变参数的起始/终值/步长；生成组合矩阵；遍历/筛选/跳转；提供当前参数加载。
- **Experiment**：运行时控制器；持有当前程序与活跃步骤；定时器驱动状态机，调度硬件，累计时间与进度；管理组合实验循环与重置。

## 3. 关键数据结构
- `ProgStep`: `OperType`（PrepSol/EChem/Flush/Transfer/Change/Blank）、状态 `StepState`、配液成分/总量/InjectOrder、冲洗参数、泵地址、位移增量、电化学参数、持续时间等。
- `ExpProgram`: `Steps`、`ParamCur/End/Intervals`、`ParamMatrix`、`ParamIndex`、`ComboExpToggle`、`ConstConcIndex`、`UserSkipList`、`CurrentExpIndex`、`TotalExpCount` 等。
- `Experiment`: 定时器 `Clock`，`Program`，`ActiveSteps`，`CurrentStep`，`Running`/`ComboRunning`/`Interim`，时间戳与累计时间，`Duration` 预估。

## 4. 状态机设计（Experiment）
- 状态：Idle → Running；当前步骤：idle → running → nextsol/end。
- Tick（默认 1s）：更新总/步/组合时间；若步骤 idle → 初始化并执行；若 nextsol → 重复执行；若 end → 前进步序；步序超出则完成程序，若组合未结束则切换下一组参数并重启；组合结束则标记完成。
- `ProgStep.GetState(elapsed)`：
  - PrepSol：查看参与的 `Diluter` 状态（`isInfusing/hasInfused`），决定 busy/nextsol/end。
  - EChem：依赖 `CHI.CHIRunning`。
  - Change：依赖 Positioner `Live/Busy/Pending` 与超时。
  - Flush/Transfer/Blank：基于 Duration 与 elapsed。

## 5. 核心方法及流程
- `ProgStep.PreptoExcute()`: 预计算持续时间与参数（配液体积/顺序、EChem 时长估算、冲洗周期换算、换样距离→时长），重置 `DurUnit="sec"`。
- `ExpProgram.FillParamMatrix()`: 按当前/终值/步长生成组合，计算 `TotalExpCount`，初始化索引。
- `ExpProgram.LoadParamValues()`: 根据 `ParamIndex` 将取值写回 `ParamCurValues`；恒总浓度不符标记跳过。
- `Experiment.PrepareSteps()`: 清空曲线点，调用每步 `PreptoExcute`，累加总时长。
- `Experiment.ResetStates()`: 重置步骤状态，重新初始化全部 `Diluter`（数量动态，遍历列表）、`Flusher`、`CHI`。
- `Experiment.RunProgram/RunComboProgram`: 加载/选择参数，设置时间戳，启动状态机；组合模式遍历参数集。
- `Experiment.ClockTick`: 主循环（见状态机设计）。
- `Experiment.ExecuteStep`: 按类型调用硬件：`Diluter`（遍历配置参与的泵，按 InjectOrder 注液）、`Flusher`（三角色地址来自配置）、`Positioner`（换样）、`CHI`（电化学）。

## 6. 与其他模块的依赖关系
- `LibContext`: 提供动态泵列表、三冲洗泵配置、位置器、CHI、日志/命名字符串/ExpID/曲线数据。
- 硬件：`Diluter`（数量动态，地址从配置）、`Flusher`（三角色、地址配置化）、`Positioner`、`CHI`。
- UI：MainWin/QTimer 驱动状态显示与启动/停止；UI 渲染泵状态应遍历 `context.diluters`。
- JSON 序列化：`ExpProgram` 用于参数持久化。

## 7. Python 重写必须保留的逻辑
- 步骤模型与状态机；时间驱动 Tick；组合矩阵生成/遍历；硬件调用顺序。
- 动态泵：不假设泵数量；通过配置/地址确定参与泵。
- 运行计时与状态判定。

## 8. Python 可改进的部分
- 事件/异步：`asyncio`/`QTimer` + await 硬件；显式状态枚举含错误/暂停。
- 依赖注入：无全局静态；配置/翻译/日志注入。
- 错误处理：统一超时/重试/异常；结构化日志。
- 数据结构：不可变/深拷贝管理；组合矩阵校验更健壮。
- 并发：硬件响应事件驱动，而非纯时间估算。

## 9. 数据流与执行流程（文字）
UI 启动实验 → 加载 `ExpProgram` → `FillParamMatrix`/`SelectCombParams` → `PrepareSteps`（遍历动态泵/冲洗/位置器参数） → Tick 驱动：运行/判断/前进步骤 → 若组合未完，进位参数并重启 → 完成时导出数据/更新 UI → 等待下一次运行。  
硬件调用中配液泵列表由配置驱动，ExperimentEngine 不写死数量，仅按步骤与地址调用。
