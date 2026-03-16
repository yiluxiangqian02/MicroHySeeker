# MicroHySeeker 运行监控与 Agent 协同现状及改进规划

日期：2026-03-15

## 1. 目标

本文档用于回答四个问题：

1. MicroHySeeker 当前在运行监控和异常管控方面已经做到什么。
2. 今天通过真实硬件测试，哪些能力已经被验证，哪些还没有真正跑通。
3. AutoHySeeker 中运行监控、故障排查、实验设计三个 agent 应该如何分工与协同。
4. 为了让这套多 agent 系统稳定运行，MicroHySeeker 还需要补哪些接口、状态模型和控制能力。

## 2. 今日真实测试结论

以下结论来自 2026-03-15 在 COM3 上的真实串口测试，不是纸面分析。

### 2.1 已验证通过

- RS485 连接与安全停泵序列可正常执行。
- 泵 1 更换驱动板后，通信稳定性恢复正常，历史上的 fire-and-forget 特殊兜底已移除。
- 泵 11 在 6-12 号泵重新接回后恢复正常通信。
- 连接后“安全全停”耗时已从约 4 到 5 秒降到亚秒级体感范围。
- 后端已增加统一泵速安全上限，超过 300 RPM 的启动请求会被直接拒绝。

### 2.2 已完成的真实测试样例

#### 测试 A：监控连接与回调触发

执行方式：真实连接 COM3，启动后台监控并等待数秒，统计回调数量。

观察结果：

- `open_ok = True`
- 收到 `callback_count = 36`
- 回调覆盖地址 `1..12`

结论：

- 连接成功后，系统确实能收到来自全部 12 个地址的状态回调。
- 但当前回调数据中混入了连接后安全停泵阶段产生的响应帧，不能直接等价为“监控链路已完全按设计稳定运行”。

#### 测试 B：300 RPM 安全上限

执行方式：真实连接 COM3 后，调用 `start_pump(1, 'FWD', 350)`。

观察结果：

- 返回 `start_350_ok = False`
- 日志打印：`RPM=350 超过安全上限 300`

结论：

- 超速请求已经被后端硬拦截，不能再依赖 UI 自觉控制。

### 2.3 尚未完全验证通过的部分

#### 期望状态 vs 实际状态对账

今天已经实现了：

- `desired_state` 记录
- 后台监控启动
- mismatch 回调
- UI 告警入口

但是，用“人工把期望状态设为运行、实际不转”的真实测试，在 3 到 5 秒窗口内没有触发 mismatch。

当前判断：

- 这不代表设计方向错误。
- 这说明现阶段监控链路的实时性和数据口径还不够稳定。
- 更具体地说，当前收到的回调很可能仍主要来自连接初始阶段的命令响应，而不是稳定的周期性监控结果。

这部分应被视为：

- 已完成第一版实现。
- 已完成真实接线测试。
- 但尚未达到“可信赖运行监控”的验收标准。

## 3. MicroHySeeker 当前已具备的运行稳定性基础

## 3.1 设备侧安全控制

- 连接 RS485 后自动全停，降低上电残留状态带来的误动作风险。
- 停止所有泵的耗时已优化。
- 泵 1 的历史特殊通信兜底已移除，系统回到了以真实响应为准的模式。
- 超过 300 RPM 的泵速设置已在后端拒绝。

## 3.2 状态监控基础

- `RS485Wrapper` 已开始维护泵状态缓存。
- `RS485Wrapper` 已开始维护期望状态 `_desired_states`。
- `main_window` 已具备接入状态回调和 mismatch 告警回调的入口。

## 3.3 现有问题

当前最大问题不是“完全没有监控”，而是“监控模型还不够专业”。

主要体现在：

- 监控口径还不够统一。
- 期望状态和实际状态的语义还不完整。
- 回调触发和扫描周期需要进一步量化验证。
- 还缺少统一的告警等级、告警编码和恢复动作模型。

## 4. 当前更专业的运行监控应长什么样

专业系统不应该只问“泵是不是开着”，而应该维护一份完整的设备运行真相表。

建议每个泵至少维护以下字段：

- `commanded_state`：系统期望它在做什么。
- `actual_state`：设备实际报告它在做什么。
- `last_command_at`：最后一次下发命令时间。
- `last_seen_at`：最后一次收到设备响应时间。
- `actual_speed_rpm`：实际速度。
- `target_speed_rpm`：目标速度。
- `fault_code`：设备故障码。
- `comm_status`：通信是否健康。
- `recovery_state`：是否在自动恢复流程中。
- `alarm_state`：当前是否存在未确认告警。

在此基础上，异常不再只是一个布尔值，而应拆为几类：

- 通信异常：超时、连续丢包、设备离线。
- 行为异常：期望运行但实际不转，期望停止但实际仍转。
- 参数异常：转速超限、体积超限、方向非法、配置缺失。
- 故障异常：堵转、驱动板故障、过流、过热。
- 时序异常：启动过慢、停机超时、步骤超时。

## 5. 建议的异常管控矩阵

### P0 必须立即落地

- 泵速上限硬限制：已实现 300 RPM。
- 地址合法性校验：地址必须属于配置中的有效泵集合。
- 未连接禁止动作：已存在。
- 启动前通道配置校验：缺泵地址、缺方向、缺校准时直接拒绝执行。
- 实验启动前系统健康快照：确认 RS485、CHI、必要泵地址在线。

### P1 应尽快补齐

- 单泵连续超时计数和阈值告警。
- 启动后 N 秒内未进入运行态则报警。
- 停止后 N 秒内仍检测到转动则报警。
- 堵转自动清除失败后升级为 critical。
- 同一告警去抖与限频，避免 UI 日志刷屏。

### P2 自动恢复能力

- 通信重连。
- 单泵重新初始化。
- 自动全停后重试当前步骤。
- 自动将实验标记为 paused，而不是直接失败。

## 6. AutoHySeeker 三个关键 Agent 的合理分工

## 6.1 运行监控 Agent

建议继续由 AutoHySeeker 的 `exp_supervisor` 承担，但职责要更明确。

它不是“读日志的 agent”，而是：

- 订阅 MicroHySeeker 的运行状态流。
- 识别异常等级。
- 决定是继续观察、触发恢复、还是交给 Diagnostics。
- 负责实验生命周期状态机：`idle -> preparing -> running -> degraded -> recovering -> paused -> failed -> completed`。

其输出不应只是文字，而应是结构化决策：

```json
{
  "decision": "continue|pause|recover|dispatch_diagnostics|abort",
  "reason": "...",
  "severity": "info|warning|error|critical",
  "actions": ["stop_all", "reconnect_rs485", "retry_step"]
}
```

## 6.2 故障排查 Agent

建议继续由 `diagnostics` 承担，但它不应直接拥有执行权。

它应该负责：

- 根因归类。
- 证据汇总。
- 给出恢复方案及其风险。
- 给出“是否允许自动恢复”的建议。

它的核心产出不是一句自然语言，而是一份结构化诊断单：

```json
{
  "root_cause": "pump_not_rotating_after_start",
  "confidence": 0.86,
  "severity": "error",
  "recommended_actions": [
    "reconnect_rs485",
    "stop_all",
    "retry_current_step_once"
  ],
  "requires_human": false
}
```

## 6.3 实验设计 Agent

`exp_designer` 不应参与故障恢复过程本身，而应在以下场景介入：

- 当前实验因设备能力不足需要改方案。
- 某些泵或模块临时不可用，需要重新规划下一轮实验。
- 上一轮实验完成后，根据监控和数据表现决定下一步怎么做。

一句话：

- `Supervisor` 管运行。
- `Diagnostics` 管故障。
- `Designer` 管下一步策略。

## 7. 推荐协同流程

### 7.1 正常运行链路

1. MicroHySeeker 执行实验。
2. MicroHySeeker 持续输出状态快照和事件。
3. AutoHySeeker `exp_supervisor` 订阅并做规则判断。
4. 无异常则继续执行。
5. 实验完成后把结果交给分析和实验设计链路。

### 7.2 异常运行链路

1. MicroHySeeker 输出告警事件。
2. `exp_supervisor` 判断是否达到升级阈值。
3. 达到阈值则调用 `diagnostics`。
4. `diagnostics` 返回根因和建议动作。
5. `exp_supervisor` 根据策略执行恢复动作。
6. 恢复成功则继续实验。
7. 恢复失败则转为 `paused` 或 `failed`。
8. 如硬件条件改变，`exp_designer` 重新规划后续实验。

## 8. MicroHySeeker 必须提供的接口

当前如果要让 AutoHySeeker 真正接管“运行监控 + 故障排查 + 恢复”，MicroHySeeker 需要从“桌面应用”升级为“可订阅、可控制、可审计的执行内核”。

至少需要以下接口。

### 8.1 状态接口

- `GET /runtime/snapshot`
  返回当前实验、当前步骤、设备状态、告警、最近动作。

- `GET /system/health`
  返回 RS485、CHI、泵、磁盘、日志系统健康状态。

- `GET /devices/pumps`
  返回全部泵的结构化状态。

### 8.2 事件接口

- `GET /runtime/events/stream`
  SSE 或 WebSocket，持续推送：状态变化、告警、步骤开始/结束、恢复动作结果。

事件建议统一格式：

```json
{
  "ts": "2026-03-15T16:45:00",
  "event_type": "pump_state_changed|alarm|step_started|step_finished|recovery_action",
  "severity": "info|warning|error|critical",
  "source": "pump/1",
  "payload": {}
}
```

### 8.3 控制接口

- `POST /control/stop_all`
- `POST /control/pump/start`
- `POST /control/pump/stop`
- `POST /control/recover/reconnect_rs485`
- `POST /control/recover/retry_step`
- `POST /control/experiment/pause`
- `POST /control/experiment/resume`
- `POST /control/experiment/abort`

### 8.4 诊断与审计接口

- `GET /alarms/active`
- `POST /alarms/{alarm_id}/ack`
- `GET /logs/recent`
- `GET /runs/{run_id}/summary`
- `GET /runs/{run_id}/artifacts`
- `GET /metrics/runtime`

## 9. MicroHySeeker 内部还需要补的能力

### 9.1 状态模型升级

需要把现在的 `_pump_states` 从“松散字典”升级成统一状态模型，例如：

- `desired_state`
- `actual_state`
- `transition_state`
- `fault_state`
- `comm_state`
- `alarm_state`

### 9.2 告警系统升级

建议所有告警带编码，例如：

- `PUMP_SPEED_LIMIT_EXCEEDED`
- `PUMP_START_TIMEOUT`
- `PUMP_STOP_TIMEOUT`
- `PUMP_STALL_DETECTED`
- `RS485_OFFLINE`
- `CHI_AUTOMATION_BLOCKED`

这样 agent 才能基于编码做稳定策略，而不是读中文日志猜意思。

### 9.3 恢复动作库

MicroHySeeker 应内置一组可调用的恢复动作：

- `stop_all`
- `reset_rs485`
- `reconnect_port`
- `retry_last_command`
- `retry_current_step`
- `skip_current_step`
- `clear_pump_stall`

Agent 不应直接拼底层操作，而应调用这些经过验证的恢复动作。

## 10. 优先级路线图

### P0：本周应完成

- 统一状态对象和告警编码。
- 把运行监控从“UI 附属功能”升级为“核心运行内核”。
- 提供最小状态快照接口和 stop/retry/reconnect 控制接口。
- 为监控链路增加可验证的调试指标：扫描周期、最后一轮轮询时长、最近一次状态更新时间。

### P1：下周应完成

- 故障恢复动作库。
- agent 可调用的恢复执行接口。
- 运行监控 agent 的自动升级策略。
- diagnostics 的结构化输出格式。

### P2：随后完成

- 将 Designer 接入“设备能力约束”上下文。
- 当某模块不可用时自动重规划下一步实验。
- 完整的实验级闭环：执行、监控、诊断、恢复、继续、优化。

## 11. 对当前实现的明确判断

### 已经做对的

- 先把硬件稳定性问题和连接时延问题处理掉，再谈 agent，是对的。
- 用后端硬限制做 RPM 安全边界，是对的。
- 开始引入 `desired_state` 与实际状态对账，是对的。
- AutoHySeeker 中 Supervisor → Diagnostics → Designer 的职责链条方向也是对的。

### 还不够的

- 当前监控链路还没有到“可作为自动恢复依据”的可靠程度。
- 当前告警还是偏日志化，不够结构化。
- 当前 agent 调用更多是架构骨架，离生产级执行协调还有明显距离。

## 12. 建议的下一步实施顺序

1. 先把 MicroHySeeker 运行状态模型做成结构化快照，并暴露接口。
2. 把告警和恢复动作做成统一编码与 API。
3. 让 AutoHySeeker 的 `exp_supervisor` 从“轮询文字状态”升级为“消费结构化运行事件”。
4. 再让 `diagnostics` 接管根因分析和恢复建议。
5. 最后再把 `exp_designer` 接到“后续实验重规划”链路上。

这条路径的好处是：先把执行内核打稳，再让 agent 真正参与控制，而不是让 agent 去猜系统现在发生了什么。