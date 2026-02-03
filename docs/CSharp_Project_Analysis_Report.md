# eChemSDL C# 项目结构详细分析报告

## 1. 项目概述

**项目名称**: eChemSDL  
**项目类型**: Windows Forms 应用程序  
**框架**: .NET Framework (C#)  
**命名空间**: `eChemSDL`, `KafkaMessage`, `HTPSolution`  
**入口文件**: `Program.cs`  
**主窗口**: `MainWin.cs`

---

## 2. 项目目录结构

```
D:\AI4S\eChemSDL\eChemSDL\
├── .vscode/                      # VS Code 配置
│   ├── launch.json
│   └── settings.json
├── bin/                          # 编译输出
│   ├── Debug/                    # 调试版本
│   │   ├── en/                   # 英文资源
│   │   ├── librdkafka/          # Kafka 原生库
│   │   ├── eChemSDL.exe         # 主程序
│   │   ├── libec.dll            # CHI电化学仪SDK
│   │   └── ...                   # 其他依赖DLL
│   └── Release/                  # 发布版本
├── obj/                          # 编译中间文件
├── packages/                     # NuGet 包
├── Properties/                   # 项目属性
├── Resources/                    # 资源文件
│
├── 【核心源代码文件】
├── Program.cs                    # 程序入口点
├── MainWin.cs                    # 主窗口 (+ Designer.cs, .resx)
├── LIB.cs                        # 全局库和上下文
├── Experiment.cs                 # 实验引擎
├── ExpProgram.cs                 # 实验程序管理
├── ProgStep.cs                   # 程序步骤定义
│
├── 【硬件控制模块】
├── CHInstrument.cs               # CHI电化学仪控制
├── MotorRS485.cs                 # RS485电机驱动 (新版)
├── MotorsOnRS485.cs              # RS485电机驱动 (旧版/Modbus)
├── Diluter.cs                    # 稀释器/配液泵控制
├── Flusher.cs                    # 冲洗器控制
├── Positioner.cs                 # 三轴定位平台控制
│
├── 【服务模块】
├── ECTechs.cs                    # 电化学技术常量
├── KafkaMsg.cs                   # Kafka消息服务
├── SaveAsExcel.cs                # Excel数据导出
│
├── 【UI对话框】
├── AboutBox.cs                   # 关于对话框
├── Calibrate.cs                  # 校准对话框
├── ComboExpEditor.cs             # 组合实验编辑器
├── Configurations.cs             # 系统配置对话框
├── Degas.cs                      # 排气对话框
├── EChem.cs                      # 电化学设置
├── EnterSelected.cs              # 选择输入对话框
├── JumptoCmbExp.cs               # 跳转到组合实验
├── ManMotorsOnRS485.cs           # RS485电机手动控制
├── ManPositioner.cs              # 定位器手动控制
├── Manual.cs                     # 手动控制 (注射泵)
├── PrepSolution.cs               # 溶液配制对话框
├── ProgramEditor.cs              # 程序编辑器
├── RS485TestForm.cs              # RS485测试对话框
├── Tester.cs                     # 测试工具
│
├── 【资源文件】
├── UserStrings.resx              # 中文字符串资源
├── UserStrings.en.resx           # 英文字符串资源
│
├── 【配置文件】
├── app.config                    # 应用配置
├── packages.config               # NuGet包配置
├── eChemSDL.csproj               # 项目文件
└── eChemSDL.sln                  # 解决方案文件
```

---

## 3. 核心模块详细分析

### 3.1 全局上下文模块 - LIB.cs

**命名空间**: `eChemSDL`  
**类型**: 静态类  
**职责**: 全局状态管理、共享资源、设备实例

#### 3.1.1 内部类定义

```csharp
// 单一溶液组分
public class SingleSolution {
    string Solute           // 溶质名称
    double LowConc          // 目标浓度
    bool IsSolvent          // 是否是溶剂
    bool InConstConc        // 是否参与恒定浓度计算
    int InjectOrder         // 注入顺序
    int ChannelIndex        // 对应通道索引
}

// 蠕动泵设置
public class PeriPumpSettings {
    string PumpName         // 泵名称 (Inlet/Outlet/Transfer)
    byte Address            // RS485地址
    ushort PumpRPM          // 转速
    PumpDirection Direction // 方向 (idle/forward/reverse)
    MotorState PumpStatus   // 运行状态
    int CycleDuration       // 周期时长(秒)
    
    enum PumpDirection { idle, forward, reverse }
}

// 通道设置
public class ChannelSettings {
    string ChannelName      // 通道名称
    double HighConc         // 源浓度
    ushort PumpSpeed        // 泵速(RPM)
    Color ChannelColor      // 显示颜色
    byte Address            // RS485地址
    double TubeInnerDiameter // 管内径(mm)
    double WheelDiameter    // 辊轮直径(mm)
    int DivpermL            // 每毫升编码值
}

// 混合溶液
public class MixedSolution {
    double TotalVol         // 总体积
    double CurrentVol       // 当前体积
    Color SolColor          // 溶液颜色
    List<SingleSolution> SoluteList  // 溶质列表
    string Solvent          // 溶剂名称
    double SolventVol()     // 计算溶剂体积
}
```

#### 3.1.2 静态成员

```csharp
// 设备实例
static MotorRS485 RS485Driver           // RS485驱动(唯一实例)
static CHInstrument CHI                 // 电化学仪
static Flusher TheFlusher              // 冲洗器
static Positioner ThePositioner        // 定位器
static List<Diluter> Diluters          // 稀释器列表

// 状态数据
static bool CHIConnected               // 电化学仪连接状态
static List<PointF> VAPoints           // 电化学数据点
static string DataFilePath             // 数据保存路径
static string ExpIDString              // 实验ID字符串
static bool EngineeringMode            // 工程模式

// 配置数据
static BindingList<ChannelSettings> CHs    // 通道配置列表
static BindingList<PeriPumpSettings> PPs   // 蠕动泵配置列表
static Dictionary<string, string> NamedStrings  // 多语言字符串
static List<string> AvailablePorts     // 可用串口列表

// 运行时数据
static ExpProgram LastExp              // 当前实验程序
static MixedSolution MixedSol          // 混合溶液状态
static MixedSolution WorkingElectrolyte // 工作电解液

// 辅助方法
static T Clone<T>(T source)            // 深拷贝(JSON序列化)
static string GetDescription(Enum)     // 获取枚举描述
static void DispatchPumpMessage(byte[]) // 分发泵消息
static void CreateDefaultCHs()         // 创建默认通道
static void CreateDefalutPPs()         // 创建默认蠕动泵
```

#### 3.1.3 日志缓冲类

```csharp
public static class LogMsgBuffer {
    static string MsgBuffer
    static void AddEntry(string LogType, string Message)
    static string GetContent()
    static bool HasContent()
}
```

---

### 3.2 硬件控制层

#### 3.2.1 RS485电机驱动 - MotorRS485.cs

**命名空间**: `eChemSDL`  
**类型**: 类 (IDisposable)  
**职责**: RS485总线通信、步进电机控制

```csharp
public class MotorRS485 : IDisposable {
    // 内部类
    public class MotorState {
        bool IsRunning          // 运行状态
        DateTime LastSeen       // 最后通信时间
        byte[] LastResponse     // 最后响应数据
    }
    
    // 属性
    bool IsReady               // 串口就绪
    bool IsOpen                // 串口打开
    bool MotorsOnline          // 电机在线
    ReadOnlyDictionary<byte, MotorState> MotorList  // 电机列表
    
    // 事件
    event Action<byte[]> OnMessageReceived  // 消息接收事件
    
    // 核心方法
    Task InitializeAsync()     // 初始化并发现设备
    Task DiscoverMotorsAsync() // 扫描在线电机
    void Open()                // 打开串口
    void Close()               // 关闭串口
    
    // 速度模式控制
    Task<byte[]> RunSpeedModeAsync(byte addr, ushort speed, bool forward, byte acceleration)
    Task<byte[]> StopSpeedModeAsync(byte addr, byte deceleration)
    
    // 相对位置模式控制
    Task<byte[]> RunRelativePositionModeAsync(byte addr, int divisions, ushort speed, bool forward, byte acceleration)
    Task<byte[]> StopRelativePositionModeAsync(byte addr, byte deceleration)
    
    // 便捷方法
    Task<byte[]> Run(byte addr)                      // 默认速度运行
    Task<byte[]> Run(byte addr, ushort speed, bool dir)
    Task<byte[]> CWRun(byte addr, ushort speed)      // 顺时针运行
    Task<byte[]> CCWRun(byte addr, ushort speed)     // 逆时针运行
    Task<byte[]> Stop(byte addr)                     // 停止速度模式
    Task<byte[]> Turn(byte addr, int degrees, ushort speed, bool forward, byte acceleration)
    Task<byte[]> TurnTo(byte addr, int divisions)    // 转到指定编码值
    Task<byte[]> TurnTo(byte addr, float degrees)    // 转到指定角度
    Task<byte[]> Break(byte addr)                    // 停止位置模式
    
    // 查询方法
    Task<byte[]> GetVersionAsync(byte addr)
    Task<byte[]> GetRunStatusAsync(byte addr)
    Task<byte[]> ReadAllSettingsAsync(byte addr)
    Task<byte[]> ReadAllStatusAsync(byte addr)
    
    // 工具方法
    string[] GetAddressStr()    // 获取地址字符串数组
    byte[] GetAddressBytes()    // 获取地址字节数组
    void DetachDataReader()     // 分离数据接收器
}
```

**通信协议**:
- 帧头: 0xFA (发送), 0xFB (接收)
- 波特率: 38400
- 数据位: 8, 停止位: 2, 无校验
- 编码器分辨率: 16384/圈

---

#### 3.2.2 稀释器控制 - Diluter.cs

**命名空间**: `eChemSDL`  
**类型**: 类  
**职责**: 单通道配液控制

```csharp
public class Diluter {
    // 属性
    string Name                 // 通道名称
    byte Address               // RS485地址
    double HighConc            // 源浓度
    double LowConc             // 目标浓度
    double TotalVol            // 总体积
    double PartVol             // 注入体积
    Color ChannelColor         // 显示颜色
    
    // 构造函数
    Diluter(LIB.ChannelSettings ch)
    
    // 核心方法
    void Initialize(LIB.ChannelSettings ch)  // 初始化配置
    void Prepare(double targetconc, bool issolvent, double solventvolt)  // 准备注入
    void Infuse()                            // 执行注入
    double GetDuration()                     // 获取预计时长
    
    // 状态查询
    double GetRemainingVol()                 // 剩余体积
    double GetInfusedVol()                   // 已注入体积
    bool isInfusing()                        // 是否正在注入
    bool hasInfused()                        // 是否已完成
    
    // 回调处理
    void HandleResponse(byte[] message)      // 处理设备响应
}
```

---

#### 3.2.3 冲洗器控制 - Flusher.cs

**命名空间**: `eChemSDL`  
**类型**: 类  
**职责**: 三泵冲洗系统控制

```csharp
public class Flusher {
    // 属性
    bool Bidirectional          // 双向冲洗模式
    PumpDirection CurrentDirection  // 当前方向
    int CycleNumber             // 剩余周期数
    
    // 定时器
    Timer InletTimer            // 进液定时器
    Timer OutletTimer           // 排液定时器
    Timer TrsfTimer             // 移液定时器
    Timer DelayTimer            // 延迟定时器
    
    // 构造和初始化
    Flusher()
    void Initialize()
    void UpdateFlusherPumps()
    
    // 冲洗控制
    void SetCycle(int cycleNum)              // 设置周期数
    void Flush()                             // 开始冲洗
    void Evacuate()                          // 排空
    void Transfer(byte address, ushort rpm, bool direction, double runtime)  // 移液
    
    // 定时器回调
    void Fill(Object source, ElapsedEventArgs e)         // 注入
    void StopFill(Object source, ElapsedEventArgs e)     // 停止注入
    void FlushTrsf(Object source, ElapsedEventArgs e)    // 冲洗移液
    void StopTransfer(Object source, ElapsedEventArgs e) // 停止移液
    void StopEvacuate(Object source, ElapsedEventArgs e) // 停止排空
}
```

**三泵模式流程**:
```
Evacuate =(DelayTimer)=> Fill =(InletTimer)=> StopFill 
    =(DelayTimer)=> Transfer =(TrsfTimer)=> StopTransfer 
    =(DelayTimer)=> Evacuate (循环)
    =(OutletTimer)=> StopEvacuate
```

---

#### 3.2.4 电化学仪控制 - CHInstrument.cs

**命名空间**: `eChemSDL`  
**类型**: 类  
**职责**: CHI电化学工作站控制

```csharp
public class CHInstrument {
    // DLL导入 (libec.dll)
    [DllImport] static extern byte CHI_hasTechnique(int x)
    [DllImport] static extern void CHI_setTechnique(int x)
    [DllImport] static extern void CHI_setParameter(byte[] id, float newValue)
    [DllImport] static extern bool CHI_runExperiment()
    [DllImport] static extern byte CHI_experimentIsRunning()
    [DllImport] static extern void CHI_showErrorStatus()
    [DllImport] static extern void CHI_getExperimentData(float[] x, float[] y, int n)
    [DllImport] static extern void CHI_getErrorStatus(byte[] buffer, int length)
    [DllImport] static extern float CHI_getParameter(byte[] id)
    
    // 属性
    float Sensitivity           // 灵敏度 (V/A)
    float[] x, y               // 数据缓冲
    int n                      // 缓冲大小 (65536)
    int duration               // 时长
    DateTime StartTime         // 开始时间
    double StepSeconds         // 步骤秒数
    bool CHIRunning            // 运行状态
    string Description         // 描述
    string Technique           // 技术类型
    List<int> Techniques       // 支持的技术列表
    
    // 构造和初始化
    CHInstrument()
    void CHIInitialize()
    
    // 核心方法
    void SetExperiment(ProgStep ps)          // 设置实验参数
    void RunExperiment(ProgStep ps)          // 运行实验
    void RunExperiment()                     // 运行当前实验
    void CancelSimulation()                  // 取消模拟
    
    // 后台工作
    void ReadData_DoWork(...)                // 数据读取
    void ReadData_ProgressChanged(...)       // 进度更新
    void ReadData_RunWorkerCompleted(...)    // 完成处理
}
```

**支持的技术类型** (ECTechs.cs):
```csharp
static class ECTechs {
    const int M_CV = 0      // 循环伏安
    const int M_LSV = 1     // 线性扫描伏安
    const int M_IT = 11     // 计时电流
    // ... 共45种技术
    
    static Dictionary<string, int> Map = {
        {"CV", M_CV},
        {"LSV", M_LSV},
        {"i-t", M_IT}
    }
}
```

---

#### 3.2.5 三轴定位器 - Positioner.cs

**命名空间**: `eChemSDL`  
**类型**: 类  
**职责**: XYZ三轴平台控制

```csharp
public class Positioner {
    // 底层参数
    string Port                 // 串口名称
    int Speed                   // 移动速度
    int PulsepercmX/Y/Z        // 每厘米脉冲数
    double cmperRow/Col/Lay    // 每行/列/层厘米数
    int MaxRow/Col/Lay         // 最大行/列/层数
    int Row/Col/Lay            // 当前位置
    int PickHeight             // 拾取高度
    int Index                  // 当前索引
    bool Busy                  // 忙状态
    bool Live                  // 在线状态
    int QuiteTime              // 静默超时
    int OfflineTime            // 离线超时
    
    // 构造和初始化
    Positioner()
    void Initialize()
    void Connect()
    void ReadyPort()
    
    // 位置控制
    void ToPosition(int r, int c, int l)     // 移动到指定位置
    void IncPosition(int incr, int incc, int incl)  // 相对移动
    void PositionByAxis(string axis, int unit)      // 单轴移动
    void Next()                              // 下一个位置
    void NextPickAndPlace()                  // 下一个取放位置
    void PickAndPlace(int r, int c, int l)   // 取放操作
    
    // 归零
    bool ZeroAll()
    bool ZeroXY()
    bool ZeroX/Y/Z()
    
    // 底层移动
    void Movetocms(double x, double y, double z)
    void MovetoPulse(string axis, int pulse)
    void MovetoPulse(int px, int py, int pz)
    
    // 通信
    void SendCommand(string cmd)
    void CheckStatus(...)
    void CheckLink()
    void UpdateStatus()
    bool Pending()                           // 是否有待执行命令
    void DetachDataReader()
    
    // 事件
    event EventHandler<SerialCommunicationEventArgs> SerialCommunication
}
```

**协议**: CJX系列控制器 (波特率115200, GB2312编码)

---

### 3.3 核心业务层

#### 3.3.1 程序步骤 - ProgStep.cs

**命名空间**: `eChemSDL`  
**类型**: 类  
**职责**: 单个实验步骤定义

```csharp
public class ProgStep {
    // 枚举
    enum Operation {
        Blank,      // 空白等待
        PrepSol,    // 配制溶液
        EChem,      // 电化学测试
        Flush,      // 冲洗
        Transfer,   // 移液
        Change      // 换样
    }
    
    enum StepState {
        idle = 0,   // 空闲
        busy = 1,   // 运行中
        nextsol = 2,// 下一批溶液
        end = 4     // 结束
    }
    
    // 通用属性
    Operation OperType          // 操作类型
    double Duration             // 持续时间(秒)
    string DurUnit              // 时间单位
    StepState State             // 当前状态
    bool Started                // 已启动
    
    // 配液参数
    List<SingleSolution> Comps  // 溶液组分
    double TotalVol             // 总体积
    double TotalConc            // 总浓度(恒定浓度)
    bool ConstTotalConc         // 是否恒定总浓度
    
    // 电化学参数
    string CHITechnique         // 技术类型 (CV/LSV/i-t)
    float E0/EH/EL/EF           // 电位参数
    float ScanRate              // 扫描速率
    float Sensitivity           // 灵敏度
    float AutoSensibility       // 自动灵敏度
    float SamplingInterval      // 采样间隔
    float ScanDir               // 扫描方向
    float SegNum                // 段数
    float QuietTime             // 静置时间
    float RunTime               // 运行时间
    
    // 冲洗/移液参数
    int FlushCycleNum           // 冲洗周期数
    bool EvacuateOnly           // 仅排空
    bool PumpDirection          // 泵方向
    ushort PumpRPM              // 泵转速
    byte PumpAddress            // 泵地址
    
    // 换样参数
    bool SimpleChange           // 简单换样
    bool PickandPlace           // 取放模式
    int IncX/IncY/IncZ          // 各轴增量
    
    // 方法
    string GetDesc()            // 获取步骤描述
    StepState GetState(TimeSpan elapsed)  // 获取当前状态
    void PreptoExcute()         // 准备执行(计算时长等)
}
```

---

#### 3.3.2 实验程序 - ExpProgram.cs

**命名空间**: `eChemSDL`  
**类型**: 类  
**职责**: 实验程序管理、组合实验

```csharp
public class ExpProgram {
    // 步骤列表
    List<ProgStep> Steps                    // 基础步骤
    List<ProgStep> ParamEndValues           // 参数终值
    List<ProgStep> ParamCurValues           // 参数当前值
    List<ProgStep> ParamIntervals           // 参数步长
    
    // 组合实验
    List<List<double>> ParamMatrix          // 参数矩阵
    List<int> ParamIndex                    // 参数索引
    List<int> ConstConcIndex                // 恒定浓度索引
    List<int> UserSkipList                  // 用户跳过列表
    List<bool> ComboExpToggle               // 实验开关
    int ConstConcExpCount                   // 恒定浓度实验数
    int CurrentExpIndex                     // 当前实验索引
    int TotalExpCount                       // 总实验数
    
    // 步骤管理
    void AddStep(ProgStep ps)
    void DeleteStep(int index)
    void InsertStep(int index, ProgStep ps)
    void UpdateStep(int index)
    void InitializeCombo()
    
    // 参数矩阵
    static List<double> CalParamValues(double start, double end, double interval)
    void FillParamMatrix()
    void LoadParamValues()
    
    // 组合实验导航
    bool ComboParamsValid()
    bool ComboCompleted()
    int ComboProgress()
    int ComboExpCount()
    void NextComboParams()
    void PreviousComboParams()
    void ResetComboParams()
    void ComboSeekNLoad(int expindex)
    bool SelectCombParams()
    
    // 恒定浓度
    List<int> SetConstConcExp()
    int SelectComboProgress()
    void SelectComboSeekNLoad(int selectindex)
    string ListSelectParams()
    
    // 用户跳过
    bool UserSkip(int index)
    void UpdateUserSkipList(List<int> list)
}
```

---

#### 3.3.3 实验引擎 - Experiment.cs

**命名空间**: `eChemSDL`  
**类型**: 类  
**职责**: 实验执行控制

```csharp
public class Experiment {
    // 属性
    ExpProgram Program                      // 当前程序
    List<ProgStep> ActiveSteps              // 活动步骤
    int CurrentStep                         // 当前步骤索引
    bool Running                            // 单次运行状态
    bool ComboRunning                       // 组合运行状态
    bool Interim                            // 程序切换标志
    DateTime StartTime                      // 开始时间
    TimeSpan ElapsedTime                    // 已用时间
    TimeSpan ElapsedStepTime                // 步骤已用时间
    TimeSpan ElapsedComboTime               // 组合已用时间
    DateTime StepStart                      // 步骤开始时间
    double Duration                         // 总时长
    
    // 构造函数
    Experiment()                            // 启动时钟定时器
    
    // 程序管理
    void LoadProgram(ExpProgram ep)
    void PrepareSteps()
    void ResetStates()
    void ResetComboStates()
    
    // 运行控制
    void RunProgram(bool freshStart)
    void RunProgram(ExpProgram ep, bool freshStart)
    void RunComboProgram(ExpProgram ep, bool freshStart)
    void RunComboProgram(bool freshStart)
    
    // 时钟回调
    void ClockTick(Object source, ElapsedEventArgs e)  // 每秒触发
    
    // 步骤执行
    void ExecuteStep()                      // 执行当前步骤
}
```

**ClockTick 主循环逻辑**:
1. 更新时间变量
2. 根据步骤类型更新UI状态(溶液颜色、体积等)
3. 检查步骤状态 (idle → 启动, busy → 继续, end → 下一步)
4. 处理组合实验切换

---

### 3.4 服务层

#### 3.4.1 Kafka消息服务 - KafkaMsg.cs

**命名空间**: `KafkaMessage`  
**类型**: 静态类  
**职责**: 远程消息通信

```csharp
public static class KafkaMsg {
    // 成员
    static BackgroundWorker ReadThread
    static List<string> Topics
    static CancellationToken CnclToken
    static bool ReadOne
    static Action<ConsumeResult<string,string>> ReaderCallback
    static IProducer<string, string> Producer
    static IConsumer<string, string> Consumer
    
    // 发送
    static void SendMsg(string key, string value)
    static void SendMsg(string key, string value, Action<DeliveryReport> callback)
    
    // 接收
    static void StartRead(List<string> topics, CancellationToken token, 
                         bool readone, Action<ConsumeResult> callback)
    
    // 内部
    static void Loop_ReadMsg()
    static void HandleFeedback(DeliveryReport obj)
}
```

**配置**: CloudKafka SASL/SSL连接

---

#### 3.4.2 Excel导出 - SaveAsExcel.cs

**命名空间**: `HTPSolution`  
**类型**: 类  
**职责**: 数据导出为Excel

```csharp
public class SaveAsExcel {
    ExcelPackage DataExcel
    ExcelWorksheet DataSheet
    string FilePath
    Point Pointer               // 当前写入位置
    
    // 构造
    SaveAsExcel(string filepath)
    
    // 方法
    void Save()
    void AppendData(string datastring)
    void AppendData(List<PointF> pointF)
    void AppendData(PointF pointF)
    void NextDataColumn()
}
```

**依赖**: EPPlus库

---

### 3.5 UI层

#### 3.5.1 主窗口 - MainWin.cs

**命名空间**: `eChemSDL`  
**类型**: Form (Windows Forms)  
**职责**: 主界面、实验可视化、用户交互

```csharp
public partial class MainWin : Form {
    // 核心成员
    Experiment Exp                          // 实验引擎实例
    Timer timer                             // UI刷新定时器
    BindingList<ProgStep> Steps             // 步骤绑定列表
    List<PointF> ChartPoints                // 图表数据
    
    // UI状态
    int Heartbeat3/6/50                     // 心跳计数器
    bool SetRedraw                          // 重绘标志
    string ComboInfo                        // 组合实验信息
    
    // 绘图方法
    void DrawExpApparatus(PaintEventArgs e) // 绘制实验装置
    void DrawBeakers(PaintEventArgs e, Point dip)        // 烧杯
    void DrawFlusingLines(PaintEventArgs e, Point dip)   // 冲洗管路
    void DrawCHInstrument(PaintEventArgs e, Point dip)   // 电化学仪
    void DrawPositioner(PaintEventArgs e, Point dip)     // 定位器
    void DrawProgress(PaintEventArgs e)                  // 进度条
    void DrawInfo(...)                                   // 信息文字
    
    // Kafka通信
    void SendConstUpdate()                  // 发送实时状态
    void SendInitialStat()                  // 发送初始状态
    void SendExitStat()                     // 发送退出状态
    void SendExpStat()                      // 发送实验状态
    void SendHeartbeat()                    // 心跳包
    
    // 事件处理
    void MainWin_Load(...)
    void MainWin_Paint(...)
    void MainWin_FormClosing(...)
    void MainTimerEvent(...)
    void btnRunSingleExp_Click(...)
    void btnRunComboExp_Click(...)
    void btnStopstep_Click(...)
    // ... 更多按钮事件
}
```

---

#### 3.5.2 配置对话框 - Configurations.cs

**功能模块**:
- 语言设置 (中文/英文)
- 串口配置 (RS485端口、定位器端口)
- 通道设置 (名称、浓度、地址、颜色)
- 冲洗泵设置 (名称、地址、方向、转速)
- 定位器设置 (脉冲、间距、范围)
- 数据路径设置
- 错误处理设置

---

#### 3.5.3 程序编辑器 - ProgramEditor.cs

**功能模块**:
- 步骤列表 (添加、删除、移动、编辑)
- 操作类型选择 (配液、电化学、冲洗、移液、换样、空白)
- 配液参数 (溶质、浓度、溶剂、注入顺序)
- 电化学参数 (技术类型、电位、扫描参数)
- 冲洗参数 (时长、仅排空)
- 移液参数 (泵地址、方向、转速、时长)
- 换样参数 (简单/自定义、取放、轴增量)

---

## 4. 模块依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                        MainWin (UI)                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Experiment (引擎)                     │ │
│  │  ┌──────────────────────────────────────────────────┐   │ │
│  │  │              ExpProgram (程序)                    │   │ │
│  │  │  ┌────────────────────────────────────────────┐  │   │ │
│  │  │  │           ProgStep (步骤)                   │  │   │ │
│  │  │  └────────────────────────────────────────────┘  │   │ │
│  │  └──────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│     LIB       │   │   KafkaMsg    │   │  SaveAsExcel  │
│ (全局上下文)   │   │  (远程通信)   │   │  (数据导出)   │
└───────┬───────┘   └───────────────┘   └───────────────┘
        │
        ├──────────────────────────────────────────────┐
        │                     │                        │
        ▼                     ▼                        ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  MotorRS485   │   │ CHInstrument  │   │  Positioner   │
│ (RS485驱动)   │   │ (电化学仪)    │   │   (定位器)    │
└───────┬───────┘   └───────────────┘   └───────────────┘
        │
        ├──────────────────────┐
        │                      │
        ▼                      ▼
┌───────────────┐   ┌───────────────┐
│    Diluter    │   │    Flusher    │
│  (稀释器x N)  │   │   (冲洗器)    │
└───────────────┘   └───────────────┘
```

---

## 5. 数据流向

### 5.1 配液流程
```
用户设置浓度 → ProgStep.Comps 
    → Experiment.ExecuteStep() 
    → Diluter.Prepare() + Diluter.Infuse()
    → MotorRS485.TurnTo()
    → RS485总线 → 步进电机
```

### 5.2 电化学测试流程
```
用户设置参数 → ProgStep (CV/LSV/i-t参数)
    → CHInstrument.SetExperiment()
    → CHI_setParameter() (DLL)
    → CHInstrument.RunExperiment()
    → BackgroundWorker读取数据
    → LIB.VAPoints → 保存CSV
```

### 5.3 冲洗流程
```
ProgStep (周期数) → Flusher.SetCycle()
    → Flusher.Flush() → Timer链式调用
    → MotorRS485.CWRun()/CCWRun()/Stop()
```

---

## 6. 配置存储

### 6.1 Properties.Settings.Default
- `RS485Port` - RS485串口名
- `ChannelListJSON` - 通道配置JSON
- `FlushingPumpsJSON` - 冲洗泵配置JSON
- `PositionerJSON` - 定位器配置JSON
- `DataFilePath` - 数据保存路径
- `TotalVol` - 默认总体积
- `LastExp` - 上次实验程序JSON
- `Culture` - 语言设置
- `StopOnPanic` - 出错停止
- `DefaultFlusherRPM/Duration` - 默认冲洗参数
- `DefaultTubeDiameter/WheelDiameter/DivPerML` - 默认泵参数

### 6.2 资源文件
- `UserStrings.resx` - 中文UI字符串
- `UserStrings.en.resx` - 英文UI字符串

---

## 7. 外部依赖

### 7.1 NuGet包
- `Confluent.Kafka` - Kafka客户端
- `Newtonsoft.Json` - JSON序列化
- `EPPlus` - Excel操作
- `Microsoft.WindowsAPICodePack.Shell` - Windows Shell API

### 7.2 原生DLL
- `libec.dll` - CHI电化学仪SDK
- `QtCore4.dll`, `QtGui4.dll` 等 - Qt运行时
- `librdkafka` - Kafka原生库

---

## 8. Python迁移建议

### 8.1 模块对应
| C# 模块 | Python 模块建议 |
|---------|----------------|
| LIB.cs | `src/services/context.py` |
| MotorRS485.cs | `src/hardware/rs485_driver.py` |
| Diluter.cs | `src/hardware/diluter.py` |
| Flusher.cs | `src/hardware/flusher.py` |
| CHInstrument.cs | `src/hardware/chi_instrument.py` |
| Positioner.cs | `src/hardware/positioner.py` |
| ProgStep.cs | `src/core/prog_step.py` |
| ExpProgram.cs | `src/core/exp_program.py` |
| Experiment.cs | `src/engine/experiment_engine.py` |
| KafkaMsg.cs | `src/services/kafka_client.py` |
| SaveAsExcel.cs | `src/services/data_exporter.py` |
| MainWin.cs | `src/ui/main_window.py` |
| Configurations.cs | `src/ui/config_dialog.py` |
| ProgramEditor.cs | `src/ui/program_editor_dialog.py` |

### 8.2 技术栈映射
| C# 技术 | Python 替代 |
|---------|-------------|
| Windows Forms | PySide6/PyQt6 |
| BackgroundWorker | asyncio / threading |
| SerialPort | pyserial |
| Timer | asyncio.Timer / QTimer |
| BindingList | PyQt信号槽 |
| Properties.Settings | JSON配置文件 |
| DllImport | ctypes |
| Confluent.Kafka | confluent-kafka-python |
| EPPlus | openpyxl / pandas |

### 8.3 关键注意事项
1. **异步处理**: RS485通信需要使用asyncio
2. **线程安全**: UI更新需要通过信号槽机制
3. **协议兼容**: 保持完全相同的RS485通信协议
4. **配置迁移**: 使用JSON格式存储配置
5. **多语言**: 使用Qt的翻译系统

---

*报告生成时间: 2026年1月31日*  
*分析版本: eChemSDL C# 原版*
