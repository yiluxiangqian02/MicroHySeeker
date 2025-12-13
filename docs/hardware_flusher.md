## 1. 模块职责
- `Flusher` 管理冲洗/排空/转移流程，使用 3 台角色化的蠕动泵：Inlet（进液）、Outlet（出液）、Transfer（转移）。每台泵通过 RS485 地址区分，地址/参数来自配置文件。流程按周期启动与停止泵，协调定时器完成单次或多次冲洗循环，并维护泵状态。

## 2. 公共 API（名称、参数、用途）
- 构造 `Flusher()`：初始化定时器，默认不绑定驱动。
- `void Initialize()`: 绑定全局 `RS485Driver`，重置标志，停止定时器。
- `void UpdateFlusherPumps()`: 同步 RS485 设备状态到配置的三台泵。
- 流程控制：
  - `void SetCycle(int cycleNum)`: 设置循环次数。
  - `void Flush()`: 若 `CycleNumber > 0` 启动排空流程 `Evacuate()`。
  - `void Evacuate()`: 启动 Outlet（地址来自配置），计时结束后进入 Fill/Transfer。
  - `void Fill(...)`（由延迟触发）：启动 Inlet。
  - `void StopFill(...)`: 停止 Inlet，延迟后转移。
  - `void FlushTrsf(...)`: 启动 Transfer（地址/参数来自配置）。
  - `void Transfer(addr, rpm, dir, runtime)`: 运行转移泵。
  - `void StopTransfer(...)`: 停止转移泵，递减循环并触发下一轮。
  - `void StopEvacuate(...)`: 停止 Outlet。
  - 其它辅助：`StartEvacuate(...)`, `StopMotor(...)`。

## 3. 内部数据结构
- 控制：`RS485Driver Controller`（共享驱动，设备数量不限）。
- 配置来源：`flusher_pumps`（inlet/outlet/transfer）三角色的地址/RPM/方向/周期时长。
- 定时器：`InletTimer`, `OutletTimer`, `DelayTimer`（命令间隔），`TrsfTimer`（转移时长）。
- 状态：`StopAddress`、`Bidirectional`（未用）、`CurrentDirection`、`CycleNumber`。

## 4. 工作流程与状态机
- 单次循环（三角色固定，但参数来自配置）：
  1) `Evacuate()` 启动 Outlet（地址/方向/转速配置化），`OutletTimer` 计时。
  2) `StopEvacuate()` 停止 Outlet；若需下一阶段，`DelayTimer`→`Fill()`。
  3) `Fill()` 启动 Inlet，`InletTimer` 计时；到时 `StopFill()` 停止并进入 Transfer。
  4) `FlushTrsf()` 调用 `Transfer(...)` 启动 Transfer，`TrsfTimer` 计时；到时 `StopTransfer()` 停止并递减循环，若未完则 `StartEvacuate()` 进入下一轮。
- 延迟/定时：`DelayTimer` 默认 500ms；各泵运行时长取自配置的 `CycleDuration` 或调用时传入的 runtime。
- 状态记录：更新配置中泵的 `PumpStatus.IsRunning`；`CycleNumber` 控制循环。
- 错误处理：缺省为静默；建议在 Python 版加入可用性检测/异常日志。

## 5. 与其他模块的依赖关系
- `LibContext`：提供 RS485 驱动与 `flusher_pumps` 配置；日志命名字符串。
- `RS485Driver`：发送 Run/Stop 命令；设备数量不限。
- `Experiment`/`ProgStep`：在冲洗/移液步骤调用 `Flush()`/`Transfer()`，不假设泵数量，只依赖三角色配置。
- UI：显示泵状态时使用配置的三角色信息。

## 6. Python 重写必须保留的逻辑
- 三角色（inlet/outlet/transfer）流程与顺序；运行时长依据配置。
- RS485 地址来自配置，不写死；驱动与设备数量无关。
- 循环计数与延迟机制；状态更新与 UI/核心查询。

## 7. Python 可改进的部分
- 显式状态机（Idle → Evacuating → Filling → Transferring → Completed/Failed），增加超时/错误处理。
- 配置注入与校验；地址/方向/时长来自 settings.json。
- 使用 Qt 定时器或 asyncio 任务代替多 `System.Timers.Timer` 重入问题。
- 日志与可观测性：记录启动/停止/方向/剩余循环；错误可视化。
- 线程安全：回调/定时器交叉更新时加锁或切到主循环。

## 8. 数据流描述（文字）
配置加载（flusher_pumps: inlet/outlet/transfer 地址/参数）  
→ 初始化 Flusher 绑定 RS485  
→ SetCycle/Flush 触发排空 → Out 计时 → 停 Out → Delay → Fill → 停 In → Delay → Transfer → 停 Transfer → 循环递减 → 重复或结束  
→ RS485 回调可选用于状态同步 → 状态供 UI/Experiment 查询。  

## 9. 动态泵要求
- 配液泵数量由配置决定；冲洗泵角色固定为 3，但其地址/参数完全由配置文件提供。
- RS485Driver 对设备一视同仁，路由由 LibContext 动态映射。 
