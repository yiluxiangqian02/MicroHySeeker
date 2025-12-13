# 变更记录 / 更新说明（动态泵 & 统一 RS485）

## 目录
- [1. 总览](#1-总览)
- [2. 受影响的模块](#2-受影响的模块)
- [3. 具体修改内容](#3-具体修改内容)
- [4. 新增机制](#4-新增机制)
- [5. 与旧架构的对比](#5-与旧架构的对比)
- [6. 兼容性与迁移建议](#6-兼容性与迁移建议)
- [7. 后续工作建议](#7-后续工作建议)

## 1. 总览
- **背景**：需要从固定泵数量扩展到 6→9 台甚至更多，全部共享同一个 RS485 串口，以设备地址区分。
- **更新目标**：
  - 配液泵数量完全由配置决定，新增/减少泵只改配置，无需改代码。
  - RS485 驱动不区分设备类型/数量，按地址路由。
  - 冲洗泵仍为 3 个角色（inlet/outlet/transfer），但地址/参数配置化。
  - UI/核心动态渲染与调度泵状态，不写死数量。

## 2. 受影响的模块
- **RS485Driver**：声明设备数量无限制；回调按地址路由；端口/波特率配置化。
- **Diluter**：移除固定泵数量假设；实例来源于配置数组；体积→步进仅依赖单泵配置。
- **Flusher**：三角色泵地址/参数配置化，仍共享 RS485。
- **LibContext**：从 settings.json 动态创建 `diluters` 列表与地址映射，dispatch 按地址路由。
- **ExperimentEngine**：不再假设泵数量，遍历 `context.diluters` 按步骤/地址调用。
- **settings.json**：新增 `diluter_pumps` 数组，`flusher_pumps` 角色配置；RS485/Positioner 保持。
- **新增概念**：PumpManager（集中泵注册、地址映射，可选实现）。

## 3. 具体修改内容
### RS485Driver
- 不限制设备数量；发现/路由完全按地址。
- 回调交由 LibContext/ PumpManager 映射，驱动不关心泵类型。
- 配置化端口/波特率；支持 mock 模式。

### Diluter
- 新增配置字段：`name/address/calibration(divpermL/volume_per_rev/steps_per_rev/rpm/管径等)`。
- 体积→步进基于自身配置；状态与泵数量无关。
- 实例数量 = `diluter_pumps` 长度；新增泵只改配置。

### Flusher
- Inlet/Outlet/Transfer 三角色地址、rpm、方向、周期时长来自 `flusher_pumps` 配置。
- 流程不变：出液→进液→转移循环；共享 RS485。

### LibContext
- `load_from_settings()`：读取 `diluter_pumps` 动态生成 `diluters`，构建 addr→设备映射。
- `dispatch_pump_message(frame)`：按地址查映射，路由到 Diluter/Flusher。
- 三冲洗泵角色配置化；无泵数量写死。

### ExperimentEngine
- 遍历 `context.diluters` 调度，不依赖固定数量；按步骤/InjectOrder/地址调用。
- UI 需根据 `context.diluters` 动态渲染泵状态。

### settings.json 配置示例
```json
{
  "diluter_pumps": [
    {"name": "A", "address": 1, "high_conc": 1.0, "pump_speed": 120, "divpermL": 19416},
    {"name": "B", "address": 2, "high_conc": 0.5, "pump_speed": 100, "divpermL": 20000},
    {"name": "C", "address": 3, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416},
    {"name": "D", "address": 4, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416},
    {"name": "E", "address": 5, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416},
    {"name": "F", "address": 6, "high_conc": 1.0, "pump_speed": 100, "divpermL": 19416}
  ],
  "flusher_pumps": {
    "inlet":   {"address": 10, "pump_rpm": 200, "direction": "forward", "cycle_duration": 30},
    "outlet":  {"address": 11, "pump_rpm": 200, "direction": "forward", "cycle_duration": 30},
    "transfer":{"address": 12, "pump_rpm": 200, "direction": "forward", "cycle_duration": 30}
  },
  "rs485": {"port": "COM3", "baudrate": 38400}
}
```

## 4. 新增机制
### PumpManager（可选实现）
- **职责**：集中管理 `diluters`（list）与 addr→设备映射；提供注册、查询、路由。
- **接口建议**：
  - `register_pumps(config_list, driver)`
  - `get_by_address(addr)`
  - `route_frame(frame)`
  - `list_pumps()`
- **配置 schema 变化**：`diluter_pumps` 为数组，每项包含 name/address/校准参数（divpermL/volume_per_rev/steps_per_rev/rpm/管径等）；`flusher_pumps` 保持三角色但完全配置化。

## 5. 与旧架构的对比
| 项目               | 旧系统问题                  | 新系统改善                                             |
| ------------------ | --------------------------- | ------------------------------------------------------ |
| 泵数量             | 写死 3/6 台                 | 配置驱动，支持 6–9+ 台，新增泵仅改配置                 |
| RS485 路由         | 依赖固定泵索引              | 纯地址路由，addr→设备映射动态                         |
| 冲洗泵              | 可能硬编码地址/顺序         | 角色固定但地址/参数配置化                             |
| ExperimentEngine   | 假设泵数量/索引             | 遍历 `context.diluters`，数量无假设                   |
| UI                 | 固定控件数量                | 动态渲染泵列表，按配置生成                             |
| 配置               | 通道/泵定义僵化             | `diluter_pumps` 数组 + `flusher_pumps` 角色，易扩展    |

## 6. 兼容性与迁移建议
- 旧配置迁移：将原固定泵定义拆分为 `diluter_pumps` 数组；冲洗泵放入 `flusher_pumps`；保留 RS485/Positioner 等配置。
- 新增泵：仅在 `diluter_pumps` 中添加条目；无需修改 Driver/Diluter/Engine/UI。
- 删除泵：移除配置项；LibContext/PumpManager 按新配置重建。

## 7. 后续工作建议
- **单元测试**：
  - 动态加载 N 个泵（≥6）并路由回调。
  - RS485 多地址收发/路由、校验。
  - Diluter 步进计算基于配置校准。
  - Flusher 角色地址配置化流程。
  - ExperimentEngine 在动态泵列表下的执行。
- **UI 调整**：
  - 泵状态面板/控制动态生成，基于 `context.diluters`。
  - 配置对话框支持编辑 `diluter_pumps` 数组与 `flusher_pumps` 角色。 
