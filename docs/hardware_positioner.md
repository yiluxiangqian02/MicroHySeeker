## 1. 模块职责
- `Positioner` 通过独立串口（115200, 8N1, GB2312 编码）控制三轴电动平台：执行坐标移动、增量移动、归零、拾取/放置，并轮询状态以保持软件坐标与硬件同步。

## 2. 公共 API（名称、参数、返回值、用途）
- 构造 `Positioner()`：初始化默认参数与定时器（未连接串口）。
- `void Initialize()`：设置默认物理/通信参数、重置坐标与轮询定时器。
- `void Connect()`：准备串口、打开并绑定接收事件，刷新状态并同步当前位置到硬件（`SynctoHW()` → `ToPosition`）。
- `void ReadyPort()`：按 `Port` 创建/打开串口、挂接 `SerialDataReceiver`。
- `void DetachDataReader()`：移除接收事件并关闭串口。
- 移动与坐标：
  - `void ToPosition(int r, int c, int l)`：行/列/层移动（自动裁剪到 Max 边界，换算成 cm → 脉冲）。
  - `void IncPosition(int incr, int incc, int incl)`：相对增量移动（越界则进位）。
  - `void PositionByAxis(string axis, int unit)`：单轴按行/列/层单位移动。
  - `void Movetocms(double x, double y, double z)`：以厘米坐标移动。
  - `void MovetoPulse(string axis, int pulse)`：单轴脉冲移动。
  - `void MovetoPulse(int px, int py, int pz)`：三轴脉冲移动。
  - `void PickAndPlace(int r, int c, int l)`：两步式拾取/放置（Z 抬升/下降 + XY 平移 + Z 复位）。
- 归零：
  - `bool ZeroAll()`, `bool ZeroXY()`, `bool ZeroX()`, `bool ZeroY()`, `bool ZeroZ()`：发送归零命令并标记 Busy。
- 队列/状态：
  - `bool Pending()`：是否有未发送完的命令队列。
  - `void UpdateStatus()`：启动状态轮询定时器（CheckStatusTrigger）。
  - `void CheckStatus(object, ElapsedEventArgs)`：直接写入状态查询指令 `CJXSA`。
  - `void CheckLink()`：基于 `LastTalk` 判断静默与掉线，必要时发状态更新或记录错误。
- 迭代/序列：
  - `void Next()`：按 Col→Row→Lay 顺序递增位置，越界则归零。
  - `void NextPickAndPlace()`：类似 `Next` 但执行拾取/放置。
- 事件：
  - `event EventHandler<SerialCommunicationEventArgs> SerialCommunication`：上报串口读写事件（Data, Operation）。

## 3. 内部数据结构
- 通信：`SerialPort serialPort`，事件接收器 `SerialDataReceiver`，`ReadBuffer`（byte[] 累积），`Reading` 标志。
- 物理/配置参数：`Port`，`Speed`，`PulsepercmX/Y/Z`，`cmperRow/Col/Lay`，`MaxRow/Col/Lay`，`PickHeight`。
- 当前/目标坐标：`Row/Col/Lay`，`targetRow/targetCol/targetLay`，`Index`。
- 运行状态：`Busy`（运行中），`Live`（在线），`MsgSent`（掉线告警已发），`SendBuffer`（待发送命令队列）。
- 健康监测：`QuiteTime`（静默阈值秒），`OfflineTime`（判定掉线秒），`LastTalk`（最近通信时间）。
- 定时器：`Timer CheckStatusTrigger`（默认 50ms，单次），用于状态轮询。
- 事件数据类：`SerialCommunicationEventArgs { string Data; SerialCommType Operation }`；`SerialCommType` 枚举 `read/write`。

## 4. 协议与通信机制
- 串口参数：115200 baud, 8 data bits, 1 stop, no parity, read/write timeout 500 ms, 编码 GB2312。
- 命令格式：纯文本指令（ASCII/GB2312），如：
  - 移动三轴：`CJXCgX{strx}Y{stry}Z{strz}F{Speed}$`
  - 单轴移动：`CJXCg{axis}{value}F{Speed}$`
  - 归零：`CJXZX` / `CJXZY` / `CJXZZ`
  - 状态查询：`CJXSA`
- 坐标编码：脉冲值字符串，千分位插入小数点；X/Z 方向取负值（设备坐标系约定）。
- 返回解析：读取串口字节 → 以 GB2312 解码为字符串 → 查找帧头 `"控制器"`，帧尾 `"Out:"` + `\r\n`；帧包含 `"运行中"` 或 `"已停止"` 与 `X:/Y:/Z:` 坐标。
- 解析逻辑：
  - 若含 `"已停止"`：设 `Busy=false`，解析 X/Y/Z 坐标（去小数点，按脉冲→cm→行列层换算）。如有 `SendBuffer`，立即发送下一条并继续轮询。
  - 若含 `"运行中"`：设 `Busy=true`，若未在 Reading 状态则继续轮询。
  - `Live=true`，更新时间戳 `LastTalk`；读到有效帧后清空 `ReadBuffer`。
- 错误处理：`TimeoutException` 时通过事件上报 `"读取超时"`；占用串口时记录警告日志。

## 5. 工作流程与状态机
- 连接：`Connect()` → `ReadyPort()` 打开串口、挂接接收；`UpdateStatus()` + `SynctoHW()` 将当前软件坐标发送到硬件。
- 移动请求：
  1) 上层调用移动/归零/拾取等 API → 生成文本命令并调用 `SendCommand`.
  2) 若 `Busy=false` 直接写串口；否则加入 `SendBuffer` 排队。
  3) 发送后标记 `Busy=true`，启动 `UpdateStatus()`（状态轮询）。
- 接收与状态更新：`SerialDataReceiver` 解析设备反馈；根据 `"运行中"`/`"已停止"` 更新 `Busy` 与坐标；处理命令队列。
- 健康监测：`CheckLink()` 依据静默/离线阈值发起 `UpdateStatus()` 或记录掉线错误。
- 完成/异常：设备报告 `"已停止"` 视为一次动作完成；无显式超时终止，依赖轮询与掉线检测。

## 6. 与其他模块的依赖关系
- `LIB`: 配置（`PositionerJSON` → `Port` 等）、命名/日志（`LogMsgBuffer`，`NamedStrings`），全局上下文在 `MainWin` 初始化时绑定。
- UI：手动控制窗体（如 `ManPositioner`）、流程编辑器通过 `Positioner` 发命令和读取 `Busy/Live`、坐标。
- `Experiment`：步骤需要移动/取放时调用 `ToPosition`/`PickAndPlace`/`Next` 等，并等待 `Busy` 清零或 `hasInfused` 类似的完成标志。
- 串口硬件：独立于 RS485 的 COM 口。

## 7. 必须在 Python 重写中保留的逻辑（语言无关）
- 三轴坐标换算：行/列/层与 cm/pulse 的映射（`Pulsepercm*`, `cmper*`），X/Z 取负方向的约定。
- 命令→串口→响应解析的循环；`Busy`/`Live` 的更新以及命令队列发送策略。
- 状态轮询与静默/掉线检测（`QuiteTime`/`OfflineTime`），掉线告警。
- 拾取/放置两步式 Z 轴 + XY + Z 的动作序列。
- 归零命令与逐轴/全轴逻辑。

## 8. Python 重写可改进的部分（语言相关）
- 异步 I/O：用 `asyncio`/线程安全队列/`pyserial-asyncio` 处理读写，避免事件交叉与 `SendBuffer` 竞争。
- 状态机：显式定义 Idle/Moving/Homing/PickPlace/Errored/Offline，带超时与错误码。
- 解析健壮性：按帧界定和校验，处理半包/多包，避免简单字符串搜索带来的误判；规范化坐标解析与方向。
- 自动重连与端口管理：检测串口丢失自动重连；连接失败时返回详细错误。
- 日志/国际化：使用注入式 logger/translator，避免静态全局。
- API 设计：Promise/await 异步完成通知，取代轮询 `Busy`；提供事件/回调给 UI。

## 9. 数据流描述（文字）
上层（UI/Experiment）发出移动/归零/拾取请求  
→ 生成文本命令（含坐标/速度）  
→ `SendCommand`：若空闲则立即写串口；若忙则入队  
→ 串口设备执行并回传状态/坐标文本  
→ `SerialDataReceiver` 解码/切帧，解析 `"运行中"`/`"已停止"` 与 `X/Y/Z`  
→ 更新 `Busy/Live/Row/Col/Lay`，出队下一个命令（若有）  
→ 触发 `SerialCommunication` 事件供 UI/日志使用；`CheckLink` 定期检测静默/掉线，必要时重发状态查询或记录错误。

## 10. 追加说明
文件为 `docs/hardware_positioner.md`，后续可补充命令全集与坐标换算示例。
