# C# 核心模块详细分析报告

> 用于 Python 迁移的详细规范文档  
> 生成日期：2026年1月31日

---

## 目录

1. [MotorRS485.cs - RS485驱动](#1-motorrs485cs---rs485驱动)
2. [Diluter.cs - 配液器](#2-dilutercs---配液器)
3. [Flusher.cs - 冲洗器](#3-flushercs---冲洗器)
4. [Positioner.cs - 定位器](#4-positionercs---定位器)
5. [CHInstrument.cs - CHI电化学仪器](#5-chinstrumentcs---chi电化学仪器)
6. [LIB.cs - 全局上下文](#6-libcs---全局上下文)
7. [Experiment.cs - 实验引擎](#7-experimentcs---实验引擎)
8. [ProgStep.cs - 程序步骤](#8-progstepcs---程序步骤)
9. [ExpProgram.cs - 实验程序](#9-expprogramcs---实验程序)
10. [ECTechs.cs - 电化学技术枚举](#10-ectechscs---电化学技术枚举)

---

## 1. MotorRS485.cs - RS485驱动

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `MotorRS485` |
| **继承** | `IDisposable` |
| **功能** | RS485总线电机控制驱动，支持多从机地址的步进电机控制 |

### 内部类

#### `MotorState`
```csharp
public class MotorState
{
    public bool IsRunning { get; set; }       // 电机运行状态
    public DateTime LastSeen { get; set; }    // 最后一次通讯时间
    public byte[] LastResponse { get; set; } // 最后一次响应数据
}
```

### 公开字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `MotorsOnline` | `bool` | 指示是否有电机在线 |

### 公开属性

| 属性名 | 类型 | 访问 | 说明 |
|--------|------|------|------|
| `MotorList` | `ReadOnlyDictionary<byte, MotorState>` | get | 已发现的电机列表（地址→状态） |
| `IsReady` | `bool` | get | 串口是否已创建并打开 |
| `IsOpen` | `bool` | get | 串口是否打开 |

### 事件定义

| 事件名 | 委托类型 | 说明 |
|--------|----------|------|
| `OnMessageReceived` | `Action<byte[]>` | 接收到电机响应时触发 |

### 公开方法

#### 初始化与连接

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `InitializeAsync()` | `Task` | 异步初始化，创建串口、打开连接、发现电机 |
| `Initialize()` | `Task` | `InitializeAsync()` 的别名 |
| `Open()` | `void` | 打开串口 |
| `Close()` | `void` | 关闭串口 |
| `Dispose()` | `void` | 释放资源 |
| `DetachDataReader()` | `void` | 断开数据接收事件并关闭串口 |

#### 电机发现

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `DiscoverMotorsAsync()` | `Task` | 异步扫描地址1-31，发现在线电机 |
| `GetAddressStr()` | `string[]` | 获取已发现电机的地址字符串数组（格式"DD"） |
| `GetAddressBytes()` | `byte[]` | 获取已发现电机的地址字节数组 |

#### 速度模式运行

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `RunSpeedModeAsync(byte addr, ushort speed = 100, bool forward = true, byte acceleration = 0x10)` | `Task<byte[]>` | 速度模式运行 |
| `StopSpeedModeAsync(byte addr, byte deceleration = 0x10)` | `Task<byte[]>` | 停止速度模式 |
| `Run(byte addr)` | `Task<byte[]>` | 默认速度运行 |
| `Run(byte addr, ushort speed, bool dir)` | `Task<byte[]>` | 指定速度和方向运行 |
| `RunbySpeed(byte addr, ushort speed, bool dir, byte acc)` | `Task<byte[]>` | 完整参数速度运行 |
| `CWRun(byte addr, ushort speed)` | `Task<byte[]>` | 顺时针运行 |
| `CCWRun(byte addr, ushort speed)` | `Task<byte[]>` | 逆时针运行 |
| `Stop(byte addr)` | `Task<byte[]>` | 停止速度模式运行 |

#### 位置模式运行

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `RunRelativePositionModeAsync(byte addr, float degrees, ushort speed, bool forward, byte acceleration = 0x10)` | `Task<byte[]>` | 相对位置模式（角度） |
| `RunRelativePositionModeAsync(byte addr, int divisions, ushort speed, bool forward, byte acceleration = 0x10)` | `Task<byte[]>` | 相对位置模式（编码器分度） |
| `StopRelativePositionModeAsync(byte addr, byte deceleration = 0x10)` | `Task<byte[]>` | 停止位置模式 |
| `Turn(byte addr, int degrees, ushort speed, bool forward, byte acceleration = 0x10)` | `Task<byte[]>` | 转动指定角度 |
| `TurnTo(byte addr, int divisions)` | `Task<byte[]>` | 转到指定编码器位置 |
| `TurnTo(byte addr, float degrees)` | `Task<byte[]>` | 转到指定角度 |
| `Break(byte addr)` | `Task<byte[]>` | 停止位置模式运行 |

#### 状态查询

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `GetVersionAsync(byte addr)` | `Task<byte[]>` | 查询版本信息 |
| `ReadAllSettingsAsync(byte addr)` | `Task<byte[]>` | 查询所有设置参数 |
| `ReadAllStatusAsync(byte addr)` | `Task<byte[]>` | 查询所有状态参数 |
| `GetRunStatusAsync(byte addr)` | `Task<byte[]>` | 查询运行状态 |
| `SendCommand(byte[] cmd)` | `Task` | 发送原始命令 |

### RS485 协议细节

#### 串口配置
```
端口名: 从配置读取 Properties.Settings.Default.RS485Port
波特率: 38400
数据位: 8
停止位: 2
校验位: None
读超时: 500ms
写超时: 500ms
```

#### 帧格式

**发送帧结构：**
```
| 帧头 | 地址 | 命令 | 数据... | 校验 |
| 0xFA | addr | cmd  | data... | sum  |
```

**接收帧结构：**
```
| 帧头 | 地址 | 命令 | 数据... | 校验 |
| 0xFB | addr | cmd  | data... | sum  |
```

**校验算法：** 所有字节累加和取低8位

**命令码与响应长度：**

| 命令码 | 功能 | 响应长度 |
|--------|------|----------|
| 0x32 | 查询电机速度 | 6 |
| 0x39 | 查询电机角度误差 | 8 |
| 0x40 | 版本信息 | 8 |
| 0x47 | 电机状态信息 | 38 |
| 0x48 | 电机设置参数 | 31 |
| 0xF1 | 运行状态查询 | 5 |
| 0xF4 | 相对位置模式 | 5 |
| 0xF6 | 速度模式 | 5 |
| 其他 | 默认 | 5 |

**速度模式命令帧 (0xF6)：**
```
[0xFA, addr, 0xF6, speed_hi|dir, speed_lo, acceleration, checksum]
长度: 7字节
dir: 0x80=正转, 0x00=反转 (OR到speed_hi)
```

**相对位置模式命令帧 (0xF4)：**
```
[0xFA, addr, 0xF4, speed_hi|dir, speed_lo, acceleration, pos[3], pos[2], pos[1], pos[0], checksum]
长度: 11字节
位置单位: 编码器分度数 (1圈=16384)
角度转换: divisions = degrees * 16384 / 360
```

**运行状态响应 (0xF1)：**
```
data[3] == 0x01: 电机停止
data[3] > 0x01: 电机运行中
```

### 线程/异步处理

| 机制 | 说明 |
|------|------|
| `SemaphoreSlim commandLock(1,1)` | 命令发送互斥锁，保证同一时间只有一个命令在发送 |
| `volatile bool isReceiving` | 标记是否正在接收数据 |
| `SerialPort.DataReceived` 事件 | 异步接收数据，在事件处理器中解析帧 |
| `await Task.Delay()` | 命令发送后延迟25ms等待响应 |

### 依赖关系

| 依赖模块 | 用途 |
|----------|------|
| `LIB.AvailablePorts` | 获取可用串口列表 |
| `LIB.NamedStrings` | 多语言字符串 |
| `LogMsgBuffer` | 日志记录 |
| `Properties.Settings.Default.RS485Port` | 串口配置 |

---

## 2. Diluter.cs - 配液器

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `Diluter` |
| **功能** | 单通道配液控制，管理蠕动泵注射溶液 |

### 公开属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `Name` | `string` | 通道名称 |
| `HighConc` | `double` | 原液高浓度 (mol/L) |
| `LowConc` | `double` | 目标低浓度 (mol/L) |
| `TotalVol` | `double` | 总体积 (mL) |
| `PartVol` | `double` | 当前注射体积 (mL) |
| `ChannelColor` | `Color` | 通道显示颜色 |
| `TestMsg` | `string` | 测试消息 |

### 公开字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Address` | `byte` | RS485电机地址 |

### 私有字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Controller` | `MotorRS485` | RS485控制器引用 |
| `tubeInnerDiameter` | `double` | 管道内径 (mm) |
| `wheelDiameter` | `double` | 蠕动泵辊轮直径 (mm) |
| `divpermL` | `int` | 每毫升液体对应的编码器分度数 |
| `speed` | `ushort` | 转速 (RPM) |
| `infusing` | `bool` | 是否正在注射 |
| `infused` | `bool` | 是否已完成注射 |
| `failed` | `bool` | 是否注射失败 |
| `starttime` | `DateTime` | 开始注射时间 |

### 构造函数

```csharp
public Diluter(LIB.ChannelSettings ch)
```

### 公开方法

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `Initialize(LIB.ChannelSettings ch)` | `void` | 根据通道设置初始化 |
| `Prepare(double targetconc, bool issolvent, double solvenvolt)` | `void` | 准备配液参数 |
| `Infuse()` | `void` | 开始注射（发送电机命令） |
| `GetDuration()` | `double` | 获取注射时长（秒） |
| `GetRemainingVol()` | `double` | 获取剩余注射体积 |
| `GetInfusedVol()` | `double` | 获取已注射体积 |
| `isInfusing()` | `bool` | 是否正在注射 |
| `hasInfused()` | `bool` | 是否已完成注射 |
| `HandleResponse(byte[] message)` | `void` | 处理电机响应消息 |
| `GetTestMsg()` | `string` | 获取测试消息 |

### 核心算法

#### 注射体积计算
```csharp
// 溶质注射体积
PartVol = TotalVol * targetconc / HighConc;

// 溶剂直接使用传入体积
PartVol = solvenvolt;

// 编码器分度数计算
int divs = (int)Math.Round(PartVol * divpermL);
```

#### 注射时长计算
```csharp
// 返回秒数
return PartVol * divpermL / 16384.0 / speed * 60;
```

#### 剩余体积计算
```csharp
if (infusing) {
    TimeSpan elapsedtime = DateTime.Now - starttime;
    double fraction = elapsedtime.TotalSeconds / GetDuration();
    volume = PartVol * (1 - fraction);
}
```

### 响应处理

接收帧格式：`[0xFB, address, 0xF4, status, ...]`

| status值 | 含义 |
|----------|------|
| 0x01 | 开始注射 |
| 0x02 | 完成注射 |
| 其他 | 异常/失败 |

### 依赖关系

| 依赖模块 | 用途 |
|----------|------|
| `LIB.RS485Driver` | RS485控制器 |
| `LIB.ChannelSettings` | 通道配置 |
| `LogMsgBuffer` | 日志记录 |

---

## 3. Flusher.cs - 冲洗器

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `Flusher` |
| **功能** | 控制进水泵、出水泵、移液泵进行电解池冲洗 |

### 公开字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Bidirectional` | `bool` | 是否双向冲洗模式 |
| `CurrentDirection` | `LIB.PeriPumpSettings.PumpDirection` | 当前运转方向 |
| `CycleNumber` | `int` | 冲洗周期数 |

### 私有字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Controller` | `MotorRS485` | RS485控制器 |
| `InletTimer` | `Timer` | 进水计时器 |
| `OutletTimer` | `Timer` | 出水计时器 |
| `DelayTimer` | `Timer` | 命令间隔计时器 (500ms) |
| `TrsfTimer` | `Timer` | 移液计时器 |
| `StopAddress` | `byte` | 待停止的电机地址 |

### 构造函数

```csharp
public Flusher()
// 初始化所有计时器，AutoReset=false，绑定事件处理器
```

### 公开方法

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `Initialize()` | `void` | 初始化冲洗器，获取控制器引用 |
| `UpdateFlusherPumps()` | `void` | 更新泵状态 |
| `SetCycle(int cycleNum)` | `void` | 设置冲洗周期数 |
| `Flush()` | `void` | 开始冲洗流程 |
| `Evacuate()` | `void` | 排空电解池 |
| `Transfer(byte address, ushort rpm, bool direction, double runtime)` | `void` | 移液操作 |

### 冲洗流程（三泵模式）

```
Evacuate =(DelayTimer)=> Fill =====(InletTimer)=====> StopFill 
    =(DelayTimer)=> Transfer =====(TrsfTimer)=====> StopTransfer 
    =(DelayTimer)=> Evacuate (重复)
           =====(OutletTimer)=====> StopEvacuate
```

### 事件处理器

| 处理器 | 触发时机 | 动作 |
|--------|----------|------|
| `Fill` | DelayTimer.Elapsed | 启动进水泵 |
| `StopFill` | InletTimer.Elapsed | 停止进水泵，启动移液 |
| `FlushTrsf` | DelayTimer.Elapsed | 启动移液泵 |
| `StopTransfer` | TrsfTimer.Elapsed | 停止移液泵，可能开始下一周期 |
| `StopEvacuate` | OutletTimer.Elapsed | 停止出水泵 |
| `StartEvacuate` | DelayTimer.Elapsed | 开始排空 |
| `StopMotor` | DelayTimer.Elapsed | 停止指定电机 |

### 依赖关系

| 依赖模块 | 用途 |
|----------|------|
| `LIB.RS485Driver` | RS485控制器 |
| `LIB.PPs` | 蠕动泵设置列表 |
| `LIB.PeriPumpSettings` | 泵配置类 |

---

## 4. Positioner.cs - 定位器

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `Positioner` |
| **功能** | XYZ三轴定位平台控制 |

### 公开属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `Port` | `string` | 串口名 |
| `Speed` | `int` | 运动速度 |
| `PulsepercmX/Y/Z` | `int` | 每厘米脉冲数 |
| `cmperRow/Col/Lay` | `double` | 行列层间距 (cm) |
| `MaxRow/Col/Lay` | `int` | 最大行列层数 |
| `Row/Col/Lay` | `int` | 当前位置 |
| `PickHeight` | `int` | 拾取高度 |
| `Index` | `int` | 当前索引 |
| `Busy` | `bool` | 是否忙碌 |
| `Live` | `bool` | 是否在线 |
| `MsgSent` | `bool` | 消息是否已发送 |
| `QuiteTime` | `int` | 静默超时 (秒) |
| `OfflineTime` | `int` | 离线超时 (秒) |

### 内部类型

```csharp
public enum SerialCommType
{
    read,
    write
}

public class SerialCommunicationEventArgs : EventArgs
{
    public string Data { get; set; }
    public SerialCommType Operation { get; set; }
}
```

### 事件

| 事件名 | 类型 | 说明 |
|--------|------|------|
| `SerialCommunication` | `EventHandler<SerialCommunicationEventArgs>` | 串口通讯事件 |

### 公开方法

#### 初始化与连接

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `Initialize()` | `void` | 初始化默认参数 |
| `Connect()` | `void` | 连接平台 |
| `ReadyPort()` | `void` | 准备串口 |
| `DetachDataReader()` | `void` | 断开串口 |

#### 位置控制

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `ToPosition(int r, int c, int l)` | `void` | 移动到指定行列层 |
| `IncPosition(int incr, int incc, int incl)` | `void` | 增量移动 |
| `PositionByAxis(string axis, int unit)` | `void` | 单轴移动 |
| `Next()` | `void` | 移动到下一位置 |
| `NextPickAndPlace()` | `void` | 带取放的下一位置 |
| `PickAndPlace(int r, int c, int l)` | `void` | 取放操作 |

#### 归零

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `ZeroAll()` | `bool` | 全部归零 |
| `ZeroXY()` | `bool` | XY归零 |
| `ZeroX()` | `bool` | X轴归零 |
| `ZeroY()` | `bool` | Y轴归零 |
| `ZeroZ()` | `bool` | Z轴归零 |

#### 底层控制

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `Movetocms(double x, double y, double z)` | `void` | 移动到厘米坐标 |
| `MovetoPulse(string axis, int pulse)` | `void` | 单轴脉冲移动 |
| `MovetoPulse(int px, int py, int pz)` | `void` | 三轴脉冲移动 |
| `SendCommand(string cmd)` | `void` | 发送命令 |

#### 状态检查

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `Pending()` | `bool` | 是否有待执行命令 |
| `SynctoHW()` | `void` | 同步到硬件 |
| `CheckLink()` | `void` | 检查连接状态 |
| `UpdateStatus()` | `void` | 更新状态 |

### 串口配置

```
波特率: 115200
数据位: 8
停止位: 1
校验位: None
编码: GB2312
读超时: 500ms
写超时: 500ms
```

### 命令协议

**移动命令格式：**
```
CJXCgX{x}Y{y}Z{z}F{speed}$    // 三轴移动
CJXCg{axis}{pulse}F{speed}$   // 单轴移动
CJXZX                          // X轴归零
CJXZY                          // Y轴归零
CJXZZ                          // Z轴归零
CJXSA                          // 状态查询
```

**响应解析：**
- 帧头标记：`"控制器"`
- 帧尾标记：`"Out:"` 后接 `"\r\n"`
- 状态：`"已停止"` 或 `"运行中"`
- 坐标：`"X:"`, `"Y:"`, `"Z:"` 后接数值

### 线程处理

| 机制 | 说明 |
|------|------|
| `CheckStatusTrigger` Timer | 50ms间隔状态轮询 |
| `SendBuffer` | 命令缓冲队列，忙时排队 |
| `SerialPort.DataReceived` | 异步接收数据 |

### 依赖关系

| 依赖模块 | 用途 |
|----------|------|
| `LIB.NamedStrings` | 多语言字符串 |
| `LogMsgBuffer` | 日志记录 |

---

## 5. CHInstrument.cs - CHI电化学仪器

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `CHInstrument` |
| **功能** | CHI电化学工作站控制，通过DLL调用实现 |

### DLL导入声明

```csharp
[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern byte CHI_hasTechnique(int x);

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern void CHI_setTechnique(int x);

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern void CHI_setParameter(byte[] id, float newValue);

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern bool CHI_runExperiment();

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern byte CHI_experimentIsRunning();

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern void CHI_showErrorStatus();

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern void CHI_getExperimentData(float[] x, float[] y, int n);

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern void CHI_getErrorStatus(byte[] buffer, int length);

[DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
public static extern float CHI_getParameter(byte[] id);
```

### 公开字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Sensitivity` | `float` | 灵敏度 (V/A)，默认 0.000001F |
| `x` | `float[]` | X轴数据数组 |
| `y` | `float[]` | Y轴数据数组 |
| `n` | `int` | 数据缓冲区大小，默认 65536 |
| `duration` | `int` | 持续时间 |
| `StartTime` | `DateTime` | 开始时间 |
| `StepSeconds` | `double` | 步骤秒数 |
| `CHIRunning` | `bool` | 是否正在运行 |
| `Description` | `string` | 实验描述 |
| `Technique` | `string` | 技术名称 |
| `Techniques` | `List<int>` | 支持的技术列表 |

### 公开方法

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `CHIInitialize()` | `void` | 初始化CHI仪器，检测连接 |
| `SetExperiment(ProgStep ps)` | `void` | 设置实验参数 |
| `RunExperiment(ProgStep ps)` | `void` | 设置并运行实验 |
| `RunExperiment()` | `void` | 运行实验（异步） |
| `CancelSimulation()` | `void` | 取消模拟实验 |

### CHI参数ID映射

| 参数ID | 含义 | 数据类型 |
|--------|------|----------|
| `m_iSens` | 灵敏度 | float |
| `m_ei` | 初始电位 E0 | float |
| `m_eh` | 高电位 EH | float |
| `m_el` | 低电位 EL | float |
| `m_ef` | 终止电位 EF | float |
| `m_vv` | 扫描速率 | float |
| `m_qt` | 静止时间 | float |
| `m_inpcl` | 段数/循环数 | float |
| `m_pn` | 扫描方向 | float |
| `m_inpsi` | 采样间隔 | float |
| `m_bAutoSens` | 自动灵敏度 | float |
| `m_st` | 运行时间 | float |

### 支持的电化学技术

- **CV (循环伏安):** 参数包括 E0, EH, EL, EF, 扫描速率, 静止时间, 段数, 方向
- **LSV (线性扫描伏安):** 使用CV实现，参数包括 E0, EF, 扫描速率
- **i-t (计时电流):** 参数包括 E0, 静止时间, 运行时间

### 线程处理

| 机制 | 说明 |
|------|------|
| `BackgroundWorker ReadData` | 后台工作线程运行实验 |
| `WorkerReportsProgress = true` | 支持进度报告 |
| `WorkerSupportsCancellation = true` | 支持取消 |
| `DoWork` | 运行实验循环 |
| `RunWorkerCompleted` | 完成后保存数据 |

### 模拟模式

当DLL不可用或仪器未连接时，使用随机数据模拟：
```csharp
// 随机数模拟
Random random = new Random();
simdata = new PointF(i, (float)random.NextDouble());
```

### 数据保存

完成后自动保存CSV文件：
- 路径：`LIB.DataFilePath`
- 文件名格式：`[{ExpID}] {Technique} HHmmss.csv`
- 内容：描述信息 + 电解液信息 + X,Y数据

### 依赖关系

| 依赖模块 | 用途 |
|----------|------|
| `LIB.CHIConnected` | 连接状态标志 |
| `LIB.VAPoints` | 共享数据点列表 |
| `LIB.MixedSol` | 混合溶液信息 |
| `LIB.DataFilePath` | 数据保存路径 |
| `LIB.ExpIDString` | 实验ID字符串 |
| `LIB.NamedStrings` | 多语言字符串 |
| `LogMsgBuffer` | 日志记录 |
| `ECTechs` | 技术代码常量 |

---

## 6. LIB.cs - 全局上下文

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `LIB` (静态类) |
| **功能** | 全局共享资源、配置和辅助方法 |

### 内部类定义

#### `SingleSolution` - 单一溶液组分
```csharp
public class SingleSolution
{
    public string Solute { get; set; }        // 溶质名称
    public double LowConc { get; set; }       // 目标浓度
    public bool IsSolvent { get; set; }       // 是否为溶剂
    public bool InConstConc { get; set; }     // 是否参与恒定浓度计算
    public int InjectOrder { get; set; }      // 注入顺序
    public int ChannelIndex { get; set; }     // 通道索引
}
```

#### `PeriPumpSettings` - 蠕动泵设置
```csharp
public class PeriPumpSettings
{
    public string PumpName { get; set; }      // 泵名称
    public byte Address { get; set; }         // RS485地址
    public ushort PumpRPM { get; set; }       // 转速
    public PumpDirection Direction { get; set; } // 方向
    public MotorRS485.MotorState PumpStatus { get; set; } // 状态
    public int CycleDuration { get; set; }    // 周期时间(秒)
    
    public enum PumpDirection { idle, forward, reverse }
    
    public void DefaultSettings() { ... }
}
```

#### `ChannelSettings` - 通道设置
```csharp
public class ChannelSettings
{
    public string ChannelName { get; set; }        // 通道名
    public double HighConc { get; set; }           // 高浓度
    public ushort PumpSpeed { get; set; }          // 泵速度(RPM)
    public Color ChannelColor { get; set; }        // 颜色
    public byte Address { get; set; }              // RS485地址
    public double TubeInnerDiameter { get; set; }  // 管内径(mm)
    public double WheelDiameter { get; set; }      // 辊轮直径(mm)
    public int DivpermL { get; set; }              // 每mL分度数
    
    public void DefaultSettings() { ... }
}
```

#### `MixedSolution` - 混合溶液
```csharp
public class MixedSolution
{
    public double TotalVol { get; set; }       // 总体积
    public double CurrentVol { get; set; }     // 当前体积
    public Color SolColor { get; set; }        // 溶液颜色
    public List<SingleSolution> SoluteList;    // 溶质列表
    public string Solvent;                     // 溶剂名
    
    public double SolventVol() { ... }         // 计算溶剂体积
}
```

### 静态字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `DefaultCombCount` | `int` | 默认组合实验数目 (10) |
| `AvailablePorts` | `List<string>` | 可用串口列表 |
| `Diluters` | `List<Diluter>` | 配液器列表 |
| `MixedSol` | `MixedSolution` | 当前混合溶液 |
| `WorkingElectrolyte` | `MixedSolution` | 工作电解液 |
| `LastExp` | `ExpProgram` | 上次实验程序 |
| `TheFlusher` | `Flusher` | 冲洗器实例 |
| `RS485Driver` | `MotorRS485` | RS485驱动实例 |
| `CHIConnected` | `bool` | CHI仪器连接状态 |
| `CHI` | `CHInstrument` | CHI仪器实例 |
| `VAPoints` | `List<PointF>` | 电压-电流数据点 |
| `DataFilePath` | `string` | 数据保存路径 |
| `ExpIDString` | `string` | 实验ID字符串 |
| `EngineeringMode` | `bool` | 工程模式标志 |
| `NamedStrings` | `Dictionary<string, string>` | 多语言字符串字典 |
| `ThePositioner` | `Positioner` | 定位器实例 |
| `CHs` | `BindingList<ChannelSettings>` | 通道设置列表 |
| `CHsettingsSource` | `BindingSource` | 通道设置数据源 |
| `PPs` | `BindingList<PeriPumpSettings>` | 蠕动泵设置列表 |
| `PPSettingsSource` | `BindingSource` | 蠕动泵设置数据源 |

### 静态方法

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `CreateDefalutPPs()` | `void` | 创建默认蠕动泵配置 |
| `CreateDefaultCHs()` | `void` | 创建默认通道配置 |
| `DispatchPumpMessage(byte[] message)` | `void` | 分发电机响应消息 |
| `GetDescription(this Enum currentEnum)` | `string` | 枚举描述扩展方法 |
| `Clone<T>(T source)` | `T` | 深拷贝辅助方法 |

### 辅助类

#### `LogMsgBuffer` - 日志消息缓冲

```csharp
public static class LogMsgBuffer
{
    public static string MsgBuffer = "";
    
    public static void AddEntry(string LogType, string Message);
    public static string GetContent();
    public static bool HasContent();
}
```

日志格式：`[{LogType}] {DateTime.Now} {Message}\r\n`

---

## 7. Experiment.cs - 实验引擎

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `Experiment` |
| **功能** | 实验执行引擎，驱动程序步骤执行 |

### 公开属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `CurrentStep` | `int` | 当前步骤索引 |
| `Running` | `bool` | 单次实验是否运行中 |
| `ComboRunning` | `bool` | 组合实验是否运行中 |
| `Interim` | `bool` | 组合实验程序切换标志 |
| `ElapsedTime` | `TimeSpan` | 总运行时间 |
| `ElapsedStepTime` | `TimeSpan` | 当前步骤运行时间 |
| `ElapsedComboTime` | `TimeSpan` | 组合实验运行时间 |
| `StepStart` | `DateTime` | 步骤开始时间 |
| `Duration` | `double` | 总时长（秒） |

### 公开字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Program` | `ExpProgram` | 实验程序 |
| `ActiveSteps` | `List<ProgStep>` | 当前活动步骤列表 |

### 构造函数

```csharp
public Experiment()
// 创建1秒间隔的时钟定时器
```

### 公开方法

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `PrepareSteps()` | `void` | 准备步骤，计算总时长 |
| `ResetStates()` | `void` | 重置所有状态 |
| `ResetComboStates()` | `void` | 重置组合实验状态 |
| `LoadProgram(ExpProgram ep)` | `void` | 加载程序 |
| `RunProgram(bool freshStart)` | `void` | 运行程序 |
| `RunProgram(ExpProgram ep, bool freshStart)` | `void` | 加载并运行程序 |
| `RunComboProgram(ExpProgram ep, bool freshStart)` | `void` | 运行组合实验 |
| `RunComboProgram(bool freshStart)` | `void` | 运行组合实验 |

### 核心驱动逻辑 - ClockTick

1秒定时器驱动，主要逻辑：

```
if (Running) {
    更新时间计数
    
    if (当前步骤是配液) {
        计算混合溶液体积和颜色
    }
    
    if (当前步骤是冲洗/移液) {
        根据泵状态更新溶液体积和颜色
    }
    
    获取步骤状态 stepState = ActiveSteps[CurrentStep].GetState(elapsed)
    
    if (stepState == idle) {
        初始化配液器
        执行步骤 ExecuteStep()
    }
    else if (stepState.HasFlag(nextsol)) {
        ExecuteStep()  // 多步注入继续调用
    }
    else if (stepState == end) {
        CurrentStep++
    }
    
    if (CurrentStep >= ActiveSteps.Count) {
        Running = false
        if (ComboRunning) {
            NextComboParams()
            RunComboProgram(true)
        }
    }
}
```

### ExecuteStep 步骤执行

根据 `OperType` 执行不同操作：

| 操作类型 | 执行内容 |
|----------|----------|
| `PrepSol` | 计算注射量，调用 Diluter.Infuse() |
| `Flush` | 调用 Flusher.Flush() 或 Evacuate() |
| `Transfer` | 调用 Flusher.Transfer() |
| `EChem` | 调用 CHI.RunExperiment() |
| `Change` | 调用 Positioner 移动 |

### 溶液颜色混合算法

```csharp
// 根据各溶质浓度比例混合颜色
for each diluter:
    dilution = infusedVol / totalVol
    r = (int)(diluter.Color.R * dilution + 255 * (1 - dilution))
    g = (int)(diluter.Color.G * dilution + 255 * (1 - dilution))
    b = (int)(diluter.Color.B * dilution + 255 * (1 - dilution))
    fraction = infusedVol * LowConc / totalIons
    R += (int)(r * fraction)
    G += (int)(g * fraction)
    B += (int)(b * fraction)
```

### 依赖关系

| 依赖模块 | 用途 |
|----------|------|
| `ExpProgram` | 程序定义 |
| `ProgStep` | 步骤定义 |
| `LIB.Diluters` | 配液器列表 |
| `LIB.TheFlusher` | 冲洗器 |
| `LIB.CHI` | CHI仪器 |
| `LIB.ThePositioner` | 定位器 |
| `LIB.MixedSol` | 混合溶液 |
| `LIB.WorkingElectrolyte` | 工作电解液 |
| `LIB.PPs` | 蠕动泵列表 |

---

## 8. ProgStep.cs - 程序步骤

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `ProgStep` |
| **功能** | 定义单个程序步骤的参数和状态 |

### 枚举类型

#### `Operation` - 操作类型
```csharp
public enum Operation
{
    [Description("空白")] Blank,
    [Description("配液")] PrepSol,
    [Description("电化学")] EChem,
    [Description("冲洗")] Flush,
    [Description("移液")] Transfer,
    [Description("换样")] Change
}
```

#### `StepState` - 步骤状态（Flags）
```csharp
public enum StepState
{
    idle = 0,      // 空闲
    busy = 1,      // 忙碌
    nextsol = 2,   // 需要下一批溶液
    end = 4        // 结束
}
```

### 公开属性

#### 通用属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `OperType` | `Operation` | 操作类型 |
| `Duration` | `double` | 持续时间（秒） |
| `DurUnit` | `string` | 时间单位 |
| `State` | `StepState` | 步骤状态 |
| `Started` | `bool` | 是否已开始 |

#### 配液参数

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `Comps` | `List<SingleSolution>` | 溶液组分列表 |
| `TotalVol` | `double` | 总体积 |
| `TotalConc` | `double` | 总浓度 |
| `ConstTotalConc` | `bool` | 是否恒定总浓度 |

#### 电化学参数

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `CHITechnique` | `string` | 技术名称 ("CV", "LSV", "i-t") |
| `E0` | `float` | 初始电位 |
| `EH` | `float` | 高电位 |
| `EL` | `float` | 低电位 |
| `EF` | `float` | 终止电位 |
| `ScanRate` | `float` | 扫描速率 |
| `Sensitivity` | `float` | 灵敏度 |
| `AutoSensibility` | `float` | 自动灵敏度 |
| `SamplingInterval` | `float` | 采样间隔 |
| `ScanDir` | `float` | 扫描方向 |
| `SegNum` | `float` | 段数 |
| `QuietTime` | `float` | 静止时间 |
| `RunTime` | `float` | 运行时间 |

#### 冲洗/移液参数

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `FlushCycleNum` | `int` | 冲洗周期数 |
| `EvacuateOnly` | `bool` | 是否仅排空 |
| `PumpDirection` | `bool` | 泵方向 |
| `PumpRPM` | `ushort` | 泵转速 |
| `PumpAddress` | `byte` | 泵地址 |

#### 换样参数

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `SimpleChange` | `bool` | 是否简单换样 |
| `PickandPlace` | `bool` | 是否取放模式 |
| `IncX` | `int` | X增量 |
| `IncY` | `int` | Y增量 |
| `IncZ` | `int` | Z增量 |

### 公开方法

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `GetDesc()` | `string` | 获取步骤描述字符串 |
| `GetState(TimeSpan elapsed)` | `StepState` | 获取步骤状态 |
| `PreptoExcute()` | `void` | 准备执行（计算参数和时间） |

### GetState 状态判断逻辑

```csharp
if (Started) {
    if (OperType == PrepSol) {
        for each diluter:
            if (isInfusing) running = true
            if (!hasInfused) nextsol = true
        
        if (running) State = busy
        else if (nextsol) State = busy | nextsol
        else State = end
    }
    else if (OperType == EChem) {
        State = CHI.CHIRunning ? busy : end
    }
    else if (OperType == Change) {
        if (elapsed > Duration && (!Live || !Busy && !Pending))
            State = end
        else
            State = busy
    }
    else {
        // 基于时间判断
        State = elapsed > Duration ? end : busy
    }
}
else {
    State = idle
}
```

### PreptoExcute 时间计算

| 操作类型 | 时间计算方式 |
|----------|--------------|
| `PrepSol` | 各通道注射时间之和（按注入顺序分批） |
| `EChem CV` | QuietTime + (EH-EL) * (SegNum-1) / ScanRate |
| `EChem LSV` | QuietTime + (EF-E0) / ScanRate |
| `EChem i-t` | QuietTime + RunTime |
| `Flush` | 周期时间 * 周期数 + 出水泵时间 |
| `Change` | 最大距离 / 速度 |
| `其他` | 直接使用Duration |

---

## 9. ExpProgram.cs - 实验程序

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `ExpProgram` |
| **功能** | 管理实验步骤列表和组合实验参数 |

### 公开字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Steps` | `List<ProgStep>` | 基础步骤列表 |
| `ParamEndValues` | `List<ProgStep>` | 参数终值列表 |
| `ParamCurValues` | `List<ProgStep>` | 参数当前值列表 |
| `ParamIntervals` | `List<ProgStep>` | 参数步长列表 |
| `ConstConcExpCount` | `int` | 恒定浓度实验数 |

### 私有字段（JSON序列化）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `ParamMatrix` | `List<List<double>>` | 参数值矩阵 |
| `ParamIndex` | `List<int>` | 参数下标列表 |
| `ConstConcIndex` | `List<int>` | 恒定浓度实验索引 |
| `UserSkipList` | `List<int>` | 用户跳过列表 |
| `ComboExpToggle` | `List<bool>` | 实验开关列表 |
| `CurrentExpIndex` | `int` | 当前实验索引 |
| `TotalExpCount` | `int` | 总实验数 |

### 公开方法

#### 步骤管理

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `AddStep(ProgStep ps)` | `void` | 添加步骤 |
| `DeleteStep(int index)` | `void` | 删除步骤 |
| `InsertStep(int index, ProgStep ps)` | `void` | 插入步骤 |
| `UpdateStep(int index)` | `void` | 更新步骤 |
| `InitializeCombo()` | `void` | 初始化组合实验 |

#### 组合实验控制

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `FillParamMatrix()` | `void` | 填充参数矩阵 |
| `ComboParamsValid()` | `bool` | 参数是否有效 |
| `ComboCompleted()` | `bool` | 是否完成 |
| `ComboProgress()` | `int` | 当前进度 (1-based) |
| `ComboExpCount()` | `int` | 总实验数 |
| `LoadParamValues()` | `void` | 载入当前参数值 |

#### 导航方法

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `NextComboParams()` | `void` | 下一个实验 |
| `PreviousComboParams()` | `void` | 上一个实验 |
| `ResetComboParams()` | `void` | 重置到第一个 |
| `ComboSeekNLoad(int expindex)` | `void` | 跳转到指定实验 |
| `SelectCombParams()` | `bool` | 选择当前参数组 |

#### 恒定浓度实验

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `SetConstConcExp()` | `List<int>` | 设置恒定浓度实验 |
| `NextSelectComboParams()` | `void` | 下一个选中实验 |
| `PreviousSelectComboParams()` | `void` | 上一个选中实验 |
| `SelectComboSeekNLoad(int selectindex)` | `void` | 跳转到选中实验 |
| `SelectComboProgress()` | `int` | 选中实验进度 |
| `ListSelectParams()` | `string` | 列出选中参数 |
| `RefreshParams()` | `void` | 刷新参数 |

#### 跳过控制

| 方法签名 | 返回类型 | 说明 |
|----------|----------|------|
| `UserSkip(int SelectComboIndex)` | `bool` | 是否跳过指定实验 |
| `UpdateUserSkipList(List<int> list)` | `void` | 更新跳过列表 |

### 静态方法

```csharp
public static List<double> CalParamValues(double startvalue, double endvalue, double interval)
// 计算从startvalue到endvalue，步长为interval的参数值列表
// 如果interval=0，自动计算为 (end-start)/DefaultCombCount
```

### 参数矩阵数据结构

```
ParamMatrix示例：
[
    [0.3, 0.2, 0.1],   // 参数1的可能值
    [0, 0.1, 0.2],     // 参数2的可能值
    [0, 0.1],          // 参数3的可能值
    [0],               // 参数4的可能值
    [0],               // 参数5的可能值
    [2]                // 参数6的可能值
]

ParamIndex示例：
[0, 2, 1, 0, 0, 0]  // 表示取 [0.3, 0.2, 0.1, 0, 0, 2]

TotalExpCount = 3 × 3 × 2 × 1 × 1 × 1 = 18
```

### 组合实验遍历算法

```csharp
void NextComboParamIndexes() {
    LoopParamIndex = ParamMatrix.Count - 1;  // 从最后一个参数开始
    while (LoopParamChanged && LoopParamIndex >= 0) {
        if (++ParamIndex[LoopParamIndex] > ParamMatrix[LoopParamIndex].Count - 1) {
            ParamIndex[LoopParamIndex] = 0;  // 进位
            LoopParamChanged = true;
        } else {
            LoopParamChanged = false;  // 不进位则退出
        }
        LoopParamIndex--;
    }
    CurrentExpIndex++;
}
```

---

## 10. ECTechs.cs - 电化学技术枚举

### 基本信息

| 项目 | 内容 |
|------|------|
| **命名空间** | `eChemSDL` |
| **类名** | `ECTechs` (静态类) |
| **功能** | 定义CHI仪器支持的电化学技术代码 |

### 技术代码常量

| 常量名 | 值 | 技术名称 |
|--------|-----|----------|
| `M_CV` | 0 | 循环伏安法 (Cyclic Voltammetry) |
| `M_LSV` | 1 | 线性扫描伏安法 (Linear Sweep Voltammetry) |
| `M_SCV` | 2 | 阶梯循环伏安法 |
| `M_TAFEL` | 3 | Tafel曲线 |
| `M_CA` | 4 | 计时安培法 (Chronoamperometry) |
| `M_CC` | 5 | 计时库仑法 (Chronocoulometry) |
| `M_DPV` | 6 | 差分脉冲伏安法 (Differential Pulse Voltammetry) |
| `M_NPV` | 7 | 正常脉冲伏安法 (Normal Pulse Voltammetry) |
| `M_SWV` | 8 | 方波伏安法 (Square Wave Voltammetry) |
| `M_ACV` | 9 | 交流伏安法 (AC Voltammetry) |
| `M_SHACV` | 10 | 二次谐波交流伏安法 |
| `M_IT` | 11 | 计时电流法 (i-t) |
| `M_BE` | 12 | 体相电解 (Bulk Electrolysis) |
| `M_HMV` | 13 | 悬汞电极伏安法 |
| `M_IMP` | 14 | 电化学阻抗谱 (Impedance) |
| `M_CP` | 15 | 计时电位法 (Chronopotentiometry) |
| `M_PSA` | 16 | 电位溶出分析 |
| `M_IMPT` | 17 | 阻抗-时间 |
| `M_DPA` | 18 | 差分脉冲安培法 |
| `M_TPA` | 19 | 三脉冲安培法 |
| `M_DDPA` | 20 | 双差分脉冲安培法 |
| `M_CPCR` | 21 | CP电流逆转 |
| `M_DNPV` | 22 | 差分正常脉冲伏安法 |
| `M_SECM` | 23 | 扫描电化学显微镜 |
| `M_PAC` | 24 | 脉冲安培电流 |
| `M_PSC` | 25 | 脉冲阶梯库仑 |
| `M_OCPT` | 26 | 开路电位-时间 |
| `M_SSF` | 27 | SSF |
| `M_IMPE` | 28 | 阻抗-电位 |
| `M_STEP` | 29 | 多电位阶跃 |
| `M_QCM` | 30 | 石英晶体微天平 |
| `M_SSTEP` | 31 | 单电位阶跃 |
| `M_CPCS` | 32 | CP电流阶跃 |
| `M_IPAD` | 33 | 集成脉冲安培检测 |
| `M_SPC` | 34 | 光谱电化学 |
| `M_SWG` | 35 | 方波发生器 |
| `M_SONIC` | 36 | 超声 |
| `M_ECN` | 37 | 电化学噪声 |
| `M_SMPL` | 38 | 采样 |
| `M_SISECM` | 39 | SI-SECM |
| `M_LVDT` | 40 | LVDT |
| `M_FTACV` | 41 | 傅里叶变换交流伏安 |
| `M_ZCCC` | 42 | 零电流计时电位 |
| `M_ICHRG` | 43 | 电流充电 |
| `M_ACTB` | 44 | 交流塔菲尔 |

### 技术名称映射

```csharp
public static Dictionary<string, int> Map = new Dictionary<string, int>
{
    {"CV", M_CV},
    {"LSV", M_LSV},
    {"i-t", M_IT}
};
```

> **注意：** 当前程序只实现了 CV, LSV, i-t 三种技术的完整支持。

---

## 总结

### 模块依赖关系图

```
                    ┌─────────────┐
                    │   LIB.cs    │
                    │ (全局上下文) │
                    └──────┬──────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ MotorRS485.cs│   │CHInstrument.cs│  │Positioner.cs │
│ (RS485驱动) │   │ (CHI仪器)    │   │  (定位器)    │
└──────┬───────┘   └──────────────┘   └──────────────┘
       │
       ├──────────────────┐
       ▼                  ▼
┌──────────────┐   ┌──────────────┐
│  Diluter.cs  │   │  Flusher.cs  │
│   (配液器)   │   │   (冲洗器)   │
└──────────────┘   └──────────────┘
       │                  │
       └────────┬─────────┘
                ▼
         ┌──────────────┐
         │Experiment.cs │
         │ (实验引擎)   │
         └──────┬───────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│  ProgStep.cs │  │ExpProgram.cs │
│ (程序步骤)   │  │ (实验程序)   │
└──────────────┘  └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  ECTechs.cs  │
                  │(技术枚举)    │
                  └──────────────┘
```

### Python迁移关键点

1. **异步处理：** C#使用 `async/await` 和 `Task`，Python可用 `asyncio`
2. **线程同步：** C#使用 `SemaphoreSlim`，Python可用 `asyncio.Lock`
3. **串口通讯：** C#使用 `System.IO.Ports.SerialPort`，Python使用 `pyserial`
4. **定时器：** C#使用 `System.Timers.Timer`，Python可用 `asyncio.create_task` + `await asyncio.sleep`
5. **事件机制：** C#使用 `event`，Python可用回调函数或 `PySignal`
6. **JSON序列化：** C#使用 `Newtonsoft.Json`，Python使用 `json` 或 `pydantic`
7. **数据绑定：** C#使用 `BindingList/BindingSource`，Python/PySide6可用 Model/View
8. **DLL调用：** C#使用 `DllImport`，Python使用 `ctypes` 或 `cffi`

### 协议规范总结

| 设备 | 通讯方式 | 波特率 | 帧格式 |
|------|----------|--------|--------|
| RS485电机 | 串口RS485 | 38400 | 0xFA开头，校验和 |
| 定位平台 | 串口 | 115200 | 文本命令 (CJX...) |
| CHI仪器 | DLL调用 | - | 参数ID+浮点值 |
