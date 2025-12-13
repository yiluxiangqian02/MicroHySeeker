## 1. 模块职责
- `RS485Driver` 负责通过串口与 RS485 设备通信：封装/发送命令帧、事件式接收并切帧、校验、维护设备状态快照，并向上层（LibContext/Diluter/Flusher 等）分发原始帧。驱动不限制设备数量，地址由配置决定。

## 2. 公共 API（名称、参数、用途）
- 事件：`OnMessageReceived(frame: bytes)`（或 `set_callback(cb)`）：收到完整帧后回调订阅者。
- 生命周期：`Open()/Close()/Dispose()`；`InitializeAsync()`/`Initialize()`（创建串口、注册接收、发现设备）；属性 `IsReady`/`IsOpen`。
- 发现：`DiscoverMotorsAsync()`：轮询地址段查找在线设备。
- 查询：`GetVersionAsync(addr)`、`ReadAllSettingsAsync(addr)`(0x47)、`ReadAllStatusAsync(addr)`(0x48)、`GetRunStatusAsync(addr)`(0xF1)。
- 运动：`RunRelativePositionModeAsync(addr, degrees|divisions, speed, forward, accel)`、`StopRelativePositionModeAsync(addr, decel)`、`RunSpeedModeAsync(addr, speed, forward, accel)`、`StopSpeedModeAsync(addr, decel)`。
- 便捷别名：`Run/Stop/CWRun/CCWRun/Turn/TurnTo/Break/RunbySpeed` 等调用上述方法。
- 实用：`SendCommand(cmd: byte[])` 自定义帧；`GetAddressStr()/GetAddressBytes()` 返回已发现地址。

## 3. 数据结构
- 串口：`SerialPort serialPort`。
- 并发：`SemaphoreSlim commandLock`（或锁）序列化写；`isReceiving` 标识接收过程。
- 缓冲：`receiveBuffer` 按帧切分；`motorStates`（addr → `MotorState{IsRunning, LastSeen, LastResponse}`），支持任意数量地址。
- 状态：`MotorsOnline`（是否发现设备）；方向常量 `FWD/RWD`。

## 4. 协议格式
- 帧头：请求 `0xFA`，响应 `0xFB`；长度由命令决定。
- 校验：逐字节求和低 8 位。
- 常用命令：速度模式 `0xF6`，位置模式 `0xF4`，运行状态 `0xF1`，版本 `0x40`，设置 `0x47`，状态参数 `0x48`。
- 响应长度：0x32→6，0x39→8，0x40→8，0x47→38，0x48→31，其余默认 5。
- 方向位：速度高字节最高位表示方向；位置模式同。

## 5. 串口处理流程（发送/接收/线程）
- 发送：持锁 → 可选等待接收结束 → 清理输入缓冲 → 写入帧 → 轻微延时。
- 接收：串口 `DataReceived` 事件线程读取 → 累积到缓冲 → 查找 0xFB → 按命令推断长度 → 校验 → 更新 `motorStates` → 回调 `OnMessageReceived`。
- 发现：轮询地址（不限数量，默认 1..31，但可扩展）；等待接收线程填充状态。
- 串口参数：默认 38400, 8N2，读/写超时 500ms（可配置）。

## 6. 状态与管理
- 无显式命令状态机；维护 `motorStates`（addr→运行/最后帧/时间）。
- 不限制设备数量，地址空间完全由配置/发现决定。
- 掉线判断可基于 `LastSeen`（需要上层实现）。

## 7. 与其他模块交互
- `LibContext`：持有驱动并注册回调；`DispatchPumpMessage(frame)` 按 `frame[1]` 地址动态路由到匹配的 `Diluter`/Flusher/测试工具，无泵数量假设。
- `Diluter/Flusher`：通过 Run/Stop/Turn 接口发送命令，依赖回调路由处理状态。
- UI：通过 `motorStates`/地址列表动态展示设备，不假设泵数量。

## 8. Python 重写必须保留的逻辑
- 帧格式与校验、方向位约定、按命令定长切帧。
- 发送串行化、回调路由机制；设备状态缓存以地址为键。
- 驱动与设备数量解耦，所有地址一视同仁；上层路由决定目标。

## 9. Python 可改进点
- 接收时校验 checksum，丢弃坏帧并记录。
- 命令-响应关联与超时/重试；避免固定延时。
- 线程模型：后台线程或 asyncio + 队列，回调在安全上下文分发。
- 配置注入：端口/波特率/地址范围由 settings.json 加载；移除全局静态依赖。
- 自动重连与错误报告。

## 10. 数据流示意（文字）
上层生成指令（含 addr/cmd/data）  
→ `RS485Driver.encode_frame`/`send` 写串口  
→ 设备回传 `0xFB...`  
→ 读线程切帧+校验 → 更新 `motorStates`  
→ 触发回调 → `LibContext.dispatch` 按地址分发给对应设备（Diluter/Flusher/测试窗体等）  
→ 上层根据设备状态刷新 UI/日志。  

### 动态泵支持说明
- 驱动层不感知泵数量/类型；所有设备以地址区分。
- 路由层（LibContext）按配置建立地址→设备实例映射，支持任意数量（6、9 甚至更多）。
