## 1. 模块职责
- `Diluter` 封装单个配液泵的业务逻辑：依据泵配置（名称/地址/校准参数等）计算注射量，调用 `RS485Driver` 发送命令驱动电机完成配液，并维护注射状态与剩余体积估算。泵数量完全动态，由配置文件定义，实例在启动时按配置生成。

## 2. 公共 API（名称、参数、返回值、用途）
- 构造 `Diluter(pump_config, driver)`: 从配置（包含 name/address/divpermL/tube/wheel/rpm 等）初始化实例。
- `void Initialize(pump_config)`: 以新的泵配置重置内部参数/状态。
- `void Prepare(double targetconc, bool issolvent, double solvenvolt)`: 按目标浓度/是否为溶剂计算本次注射体积 `PartVol`（无关泵数量，仅依赖自身配置）。
- `void Infuse()`: 将 `PartVol` 转换为编码分度（`divpermL` 或校准因子）并调用 `RS485Driver.TurnTo`/`SendFrame`，异常记录错误并置失败。
- `double GetDuration()`: 基于 `PartVol`、`divpermL`、`speed` 估算注射持续时间（秒）。
- `void HandleResponse(byte[] message)`: 处理 RS485 响应，更新 `infusing/infused/failed` 状态，记录开始/结束时间。
- 状态查询：`bool isInfusing()`, `bool hasInfused()`, `double GetRemainingVol()`, `double GetInfusedVol()`, `string GetTestMsg()`.

## 3. 内部数据结构
- 泵配置：`Name`, `HighConc`, `LowConc`, `TotalVol`, `PartVol`, `ChannelColor`, `Address`, `TubeInnerDiameter`, `WheelDiameter`, `DivpermL`（或其他校准参数）, `PumpSpeed`。
- 控制引用：`RS485Driver Controller`（通用驱动，不限制设备数量）。
- 状态：`infusing`, `infused`, `failed`, `starttime`。
- 其他：`TestMsg`（调试信息）。

## 4. 工作流程与状态机
- 准备：`Prepare()` 根据溶剂/溶质计算体积（无泵数量假设）。
- 体积→步数：`divs = round(PartVol * divpermL)` 或根据校准因子换算（16384/圈）。
- 发送：`Infuse()` 检查驱动是否就绪，发送位置/速度命令；异常记录并置失败。
- 响应：`HandleResponse` 关注 `FB addr F4 ...`（与地址匹配），0x01 开始、0x02 完成、其他失败。
- 剩余体积：若 infusing 按时间估算，否则返回未完成的体积或 0。
- 无专用定时器；依赖回执与时间估算。

## 5. 与其他模块的依赖关系
- `LibContext`: 提供泵配置列表、RS485 驱动、命名/日志；启动时遍历配置创建 `Diluter` 列表（数量动态）。
- `RS485Driver`: 统一发送/接收帧；`OnMessageReceived` 通过 `LibContext.dispatch` 路由到匹配地址的 `Diluter`。
- `Experiment`/`ProgStep`: 在执行配液步骤时调用 `Prepare()` 与 `Infuse()`，不假设泵数量，只按配置中的泵参与步骤。
- UI: 应根据 `context.diluters` 动态渲染泵状态与进度。

## 6. Python 重写必须保留的逻辑（语言无关）
- 体积到编码分度的计算（基于配置的校准值，而非固定泵数）。
- RS485 命令/响应状态更新（0x01/0x02/其他）。
- 状态估算与剩余体积计算。
- 泵实例来自配置，数量动态；新增泵仅需修改 settings.json。

## 7. Python 重写可改进的部分（语言相关）
- 异步/await 包装 RS485 调用，统一超时与错误传播。
- 显式状态枚举（Idle/Infusing/Completed/Failed/Timeout）与失败原因。
- 注入式 logger/translator，无全局静态。
- 校准参数/单位检查，提前校验非法配置。
- 进度估算结合回执/编码计数而非纯时间。

## 8. 数据流示意（文字）
配置加载 → LibContext 为每个 `diluter_pumps` 条目创建 `Diluter` → UI/Experiment 选择参与泵 → `Prepare()` 计算体积 → `Infuse()` 体积→分度→发送 0xF4 → RS485 回执 → `RS485Driver` 回调 → `LibContext.dispatch` → `Diluter.HandleResponse` 更新状态 → 上层通过 `isInfusing()/hasInfused()/GetRemainingVol()` 轮询/显示进度。

## 9. 动态泵管理说明
- 泵数量不写死；`LibContext.diluters` 为 `list[Diluter]`，来源于 settings.json `diluter_pumps` 数组。
- 添加/减少泵仅需改配置；代码无需改动。
