# C# 源代码详细分析报告

> 针对 Python 实现改进的技术分析文档  
> 生成日期：2026年2月4日

---

## 目录

1. [Program.cs - 主程序入口分析](#1-programcs---主程序入口)
2. [ExperimentEngine.cs - 实验引擎核心逻辑](#2-experimentenginecs---实验引擎核心逻辑)
3. [CHInstrument.cs - CHI电化学工作站通信](#3-chinstrumentcs---chi电化学工作站通信)
4. [Python实现对比与改进建议](#4-python实现对比与改进建议)
5. [关键差异总结](#5-关键差异总结)

---

## 1. Program.cs - 主程序入口

### 1.1 类结构

```
Program.cs (静态类)
├── Main() - 程序入口点
├── Application配置
│   ├── EnableVisualStyles()
│   ├── SetCompatibleTextRenderingDefault()
│   └── Run(new MainWin())
└── 全局异常处理
```

### 1.2 主要流程

| 步骤 | 功能 | 说明 |
|------|------|------|
| 1 | 初始化可视化样式 | Windows Forms 样式配置 |
| 2 | 设置文本渲染 | 使用GDI+渲染 |
| 3 | 加载语言资源 | 根据Culture设置加载中/英文 |
| 4 | 创建主窗口 | 实例化 MainWin |
| 5 | 初始化全局资源 | LIB.CreateDefaultCHs(), LIB.CreateDefalutPPs() |
| 6 | 扫描串口 | 填充 LIB.AvailablePorts |
| 7 | 启动消息循环 | Application.Run() |

### 1.3 初始化顺序

```
1. 语言设置加载 (Properties.Settings.Default.Culture)
2. 资源字符串加载 (UserStrings.resx)
3. 默认通道配置创建 (6通道)
4. 默认蠕动泵配置创建 (Inlet/Outlet/Transfer)
5. 串口扫描
6. 上次实验程序恢复 (如有)
```

### 1.4 Python实现现状

Python 版本使用 PySide6 的 QApplication，启动流程在 `run_ui.py`:

```python
# 当前Python实现
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
```

**改进建议**：
- 添加全局异常处理机制
- 实现配置恢复（上次实验程序）
- 添加语言切换支持
- 实现启动时的硬件扫描流程

---

## 2. ExperimentEngine.cs - 实验引擎核心逻辑

### 2.1 类结构

```
Experiment (实验引擎)
├── 属性
│   ├── Program: ExpProgram         # 实验程序
│   ├── ActiveSteps: List<ProgStep> # 活动步骤列表
│   ├── CurrentStep: int            # 当前步骤索引
│   ├── Running: bool               # 单次运行状态
│   ├── ComboRunning: bool          # 组合运行状态
│   ├── Interim: bool               # 程序切换标志
│   ├── ElapsedTime: TimeSpan       # 总运行时间
│   ├── ElapsedStepTime: TimeSpan   # 步骤运行时间
│   ├── ElapsedComboTime: TimeSpan  # 组合运行时间
│   ├── StepStart: DateTime         # 步骤开始时间
│   └── Duration: double            # 总时长(秒)
│
├── 核心方法
│   ├── PrepareSteps()              # 准备步骤
│   ├── ResetStates()               # 重置状态
│   ├── ResetComboStates()          # 重置组合状态
│   ├── LoadProgram()               # 加载程序
│   ├── RunProgram()                # 运行单次实验
│   ├── RunComboProgram()           # 运行组合实验
│   ├── ExecuteStep()               # 执行当前步骤
│   └── ClockTick()                 # 1秒定时回调
│
└── 内部定时器
    └── Timer clock (1秒间隔)
```

### 2.2 状态机设计

```
StepState (位标志枚举):
┌──────────────────────────────────────────────────┐
│  idle (0)   → 步骤未开始                          │
│  busy (1)   → 步骤执行中                          │
│  nextsol (2) → 多批次注入，需要下一批             │
│  end (4)    → 步骤完成                            │
│                                                  │
│  组合: busy | nextsol (3) = 执行中且需要继续注入  │
└──────────────────────────────────────────────────┘

引擎状态流转:
                    ┌─────────┐
                    │  IDLE   │
                    └────┬────┘
                         │ LoadProgram()
                         ▼
                    ┌─────────┐
                    │  READY  │
                    └────┬────┘
                         │ RunProgram()/RunComboProgram()
                         ▼
                    ┌─────────┐ ◄────── ClockTick()
        ┌───────────│ RUNNING │────────┐
        │           └────┬────┘        │
        │                │             │
   暂停 │                │ 完成       │ 错误
        ▼                ▼             ▼
   ┌─────────┐    ┌───────────┐   ┌─────────┐
   │ PAUSED  │    │ COMPLETED │   │  ERROR  │
   └─────────┘    └───────────┘   └─────────┘
```

### 2.3 ClockTick 核心逻辑

```csharp
void ClockTick(Object source, ElapsedEventArgs e)
{
    if (Running) {
        // 1. 更新时间计数
        ElapsedTime = DateTime.Now - StartTime;
        ElapsedStepTime = DateTime.Now - StepStart;
        
        // 2. 配液步骤：更新混合溶液状态
        if (ActiveSteps[CurrentStep].OperType == PrepSol) {
            UpdateMixedSolutionVolume();
            UpdateMixedSolutionColor();
        }
        
        // 3. 冲洗/移液步骤：更新体积
        if (ActiveSteps[CurrentStep].OperType == Flush || Transfer) {
            UpdateFlushVolume();
        }
        
        // 4. 获取步骤状态
        StepState state = ActiveSteps[CurrentStep].GetState(ElapsedStepTime);
        
        // 5. 状态分派
        switch (state) {
            case idle:
                // 首次启动步骤
                InitializeDiluters();
                ExecuteStep();
                break;
                
            case busy | nextsol:
                // 多批次注入继续
                ExecuteStep();
                break;
                
            case end:
                // 步骤完成，进入下一步
                CurrentStep++;
                StepStart = DateTime.Now;
                break;
        }
        
        // 6. 检查实验完成
        if (CurrentStep >= ActiveSteps.Count) {
            Running = false;
            
            // 组合实验：继续下一组
            if (ComboRunning) {
                Program.NextComboParams();
                if (!Program.ComboCompleted()) {
                    RunComboProgram(freshStart: true);
                } else {
                    ComboRunning = false;
                }
            }
        }
    }
}
```

### 2.4 ExecuteStep 步骤执行

```csharp
void ExecuteStep()
{
    ProgStep step = ActiveSteps[CurrentStep];
    step.Started = true;
    
    switch (step.OperType) {
        case PrepSol:
            // 配液：计算注射量，启动配液器
            for each (comp in step.Comps) {
                if (comp.InjectOrder == currentBatch) {
                    Diluter diluter = LIB.Diluters[comp.ChannelIndex];
                    diluter.Prepare(comp.LowConc, comp.IsSolvent, solventVol);
                    diluter.Infuse();  // 发送RS485命令
                }
            }
            break;
            
        case Flush:
            // 冲洗
            LIB.TheFlusher.SetCycle(step.FlushCycleNum);
            if (step.EvacuateOnly) {
                LIB.TheFlusher.Evacuate();
            } else {
                LIB.TheFlusher.Flush();
            }
            break;
            
        case Transfer:
            // 移液
            LIB.TheFlusher.Transfer(step.PumpAddress, step.PumpRPM, 
                                    step.PumpDirection, step.Duration);
            break;
            
        case EChem:
            // 电化学测试
            LIB.CHI.RunExperiment(step);
            break;
            
        case Change:
            // 换样
            if (step.SimpleChange) {
                LIB.ThePositioner.Next();
            } else if (step.PickandPlace) {
                LIB.ThePositioner.NextPickAndPlace();
            } else {
                LIB.ThePositioner.IncPosition(step.IncX, step.IncY, step.IncZ);
            }
            break;
            
        case Blank:
            // 空白等待：无操作，仅等待Duration秒
            break;
    }
}
```

### 2.5 多批次注入机制

配液步骤支持按 `InjectOrder` 分批注入：

```
InjectOrder 机制:
┌────────────────────────────────────────────────────┐
│ 溶质A (InjectOrder=1) ───┐                         │
│ 溶质B (InjectOrder=1) ───┤──► 第1批同时注入        │
│ 溶质C (InjectOrder=2) ───┼──► 第2批                │
│ 溶剂  (InjectOrder=3) ───┴──► 第3批 (最后注入)     │
└────────────────────────────────────────────────────┘

GetState() 判断逻辑:
- 扫描所有配液器，检查 isInfusing() 和 hasInfused()
- 如果有正在注入的 → busy
- 如果有未完成的批次 → busy | nextsol
- 全部完成 → end
```

### 2.6 组合实验控制

```csharp
void RunComboProgram(bool freshStart)
{
    ComboRunning = true;
    
    if (freshStart) {
        // 加载当前组合参数
        Program.LoadParamValues();
        
        // 准备步骤（重新计算时长）
        PrepareSteps();
        
        // 重置状态
        ResetStates();
        CurrentStep = 0;
    }
    
    Running = true;
}

// 在 ClockTick 中完成一次实验后:
if (!Program.ComboCompleted()) {
    Program.NextComboParams();  // 切换到下一组参数
    RunComboProgram(freshStart: true);
}
```

### 2.7 Python实现对比

**当前Python实现** ([experiment_engine.py](../MicroHySeeker/src/echem_sdl/core/experiment_engine.py)):

| 特性 | C# | Python现状 | 差异 |
|------|-----|------------|------|
| 定时器 | System.Timers.Timer (1秒) | threading.Thread + sleep | Python缺少精确定时 |
| 状态机 | 位标志枚举 | Enum类 | Python已实现类似 |
| 多批次注入 | InjectOrder分批 | 未实现 | **需要添加** |
| 溶液颜色混合 | 实时计算 | 未实现 | **需要添加** |
| 暂停/恢复 | 完整支持 | 已实现 | ✓ |
| 组合实验 | 参数矩阵遍历 | 基础实现 | 需要完善 |

---

## 3. CHInstrument.cs - CHI电化学工作站通信

### 3.1 类结构

```
CHInstrument
├── DLL导入 (libec.dll)
│   ├── CHI_hasTechnique(int)        # 检查技术支持
│   ├── CHI_setTechnique(int)        # 设置技术类型
│   ├── CHI_setParameter(byte[], float)  # 设置参数
│   ├── CHI_getParameter(byte[])     # 获取参数
│   ├── CHI_runExperiment()          # 运行实验
│   ├── CHI_experimentIsRunning()    # 检查运行状态
│   ├── CHI_getExperimentData(float[], float[], int)  # 获取数据
│   ├── CHI_getErrorStatus(byte[], int)  # 获取错误
│   └── CHI_showErrorStatus()        # 显示错误
│
├── 公开字段
│   ├── Sensitivity: float           # 灵敏度 (默认 1e-6)
│   ├── x[], y[]: float[]           # 数据缓冲区 (65536点)
│   ├── n: int                      # 缓冲区大小
│   ├── duration: int               # 持续时间
│   ├── StartTime: DateTime         # 开始时间
│   ├── StepSeconds: double         # 步骤秒数
│   ├── CHIRunning: bool            # 运行状态
│   ├── Description: string         # 描述
│   ├── Technique: string           # 技术名称
│   └── Techniques: List<int>       # 支持的技术列表
│
├── 公开方法
│   ├── CHIInitialize()             # 初始化仪器
│   ├── SetExperiment(ProgStep)     # 设置实验参数
│   ├── RunExperiment(ProgStep)     # 设置并运行
│   ├── RunExperiment()             # 运行当前实验
│   └── CancelSimulation()          # 取消模拟
│
└── BackgroundWorker
    ├── DoWork → 实验运行循环
    ├── ProgressChanged → 数据更新回调
    └── RunWorkerCompleted → 完成处理
```

### 3.2 CHI参数ID映射

| 参数ID字符串 | 含义 | 数据类型 | 适用技术 |
|-------------|------|----------|----------|
| `m_iSens` | 灵敏度 (V/A) | float | 全部 |
| `m_ei` | 初始电位 E0 | float | CV, LSV, i-t |
| `m_eh` | 高电位 EH | float | CV |
| `m_el` | 低电位 EL | float | CV |
| `m_ef` | 终止电位 EF | float | CV, LSV |
| `m_vv` | 扫描速率 (V/s) | float | CV, LSV |
| `m_qt` | 静止时间 (s) | float | 全部 |
| `m_inpcl` | 段数/循环数 | float | CV |
| `m_pn` | 扫描方向 (1=正,-1=负) | float | CV, LSV |
| `m_inpsi` | 采样间隔 (V) | float | CV, LSV |
| `m_bAutoSens` | 自动灵敏度 | float | 全部 |
| `m_st` | 运行时间 (s) | float | i-t |

### 3.3 SetExperiment 参数设置

```csharp
void SetExperiment(ProgStep ps)
{
    // 设置技术类型
    int techCode = ECTechs.Map[ps.CHITechnique];
    CHI_setTechnique(techCode);
    
    // 设置通用参数
    CHI_setParameter("m_iSens", ps.Sensitivity);
    CHI_setParameter("m_qt", ps.QuietTime);
    CHI_setParameter("m_bAutoSens", ps.AutoSensibility);
    
    // 根据技术类型设置特定参数
    switch (ps.CHITechnique) {
        case "CV":
            CHI_setParameter("m_ei", ps.E0);
            CHI_setParameter("m_eh", ps.EH);
            CHI_setParameter("m_el", ps.EL);
            CHI_setParameter("m_ef", ps.EF);
            CHI_setParameter("m_vv", ps.ScanRate);
            CHI_setParameter("m_inpcl", ps.SegNum);
            CHI_setParameter("m_pn", ps.ScanDir);
            CHI_setParameter("m_inpsi", ps.SamplingInterval);
            break;
            
        case "LSV":
            CHI_setParameter("m_ei", ps.E0);
            CHI_setParameter("m_ef", ps.EF);
            CHI_setParameter("m_vv", ps.ScanRate);
            CHI_setParameter("m_pn", ps.ScanDir);
            CHI_setParameter("m_inpsi", ps.SamplingInterval);
            break;
            
        case "i-t":
            CHI_setParameter("m_ei", ps.E0);
            CHI_setParameter("m_st", ps.RunTime);
            break;
    }
    
    // 计算预期时长
    CalculateStepSeconds(ps);
}
```

### 3.4 数据采集流程

```
BackgroundWorker 工作流程:
┌─────────────────────────────────────────────────────┐
│                                                     │
│  DoWork:                                            │
│  ┌─────────────────────────────────────────────┐    │
│  │ 1. CHI_runExperiment()                      │    │
│  │ 2. while (CHI_experimentIsRunning()) {      │    │
│  │      Thread.Sleep(250);  // 250ms轮询      │    │
│  │      CHI_getExperimentData(x, y, n);        │    │
│  │      ReportProgress(currentData);           │    │
│  │    }                                        │    │
│  │ 3. 最终数据获取                              │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  ProgressChanged:                                   │
│  ┌─────────────────────────────────────────────┐    │
│  │ 更新 LIB.VAPoints 列表                       │    │
│  │ 触发UI重绘                                   │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  RunWorkerCompleted:                                │
│  ┌─────────────────────────────────────────────┐    │
│  │ 1. CHIRunning = false                       │    │
│  │ 2. 生成CSV文件名                             │    │
│  │ 3. 保存数据到CSV                             │    │
│  │ 4. 记录日志                                  │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3.5 Mock模式

当 DLL 不可用或仪器未连接时：

```csharp
// 模拟数据生成
Random random = new Random();
for (int i = 0; i < expectedPoints; i++) {
    x[i] = startPotential + i * stepVoltage;
    y[i] = (float)random.NextDouble() * scale;
    
    Thread.Sleep(10);  // 模拟采样间隔
    ReportProgress(i);
}
```

### 3.6 错误处理

```csharp
void HandleCHIError()
{
    byte[] buffer = new byte[256];
    CHI_getErrorStatus(buffer, 256);
    string errorMsg = Encoding.ASCII.GetString(buffer).TrimEnd('\0');
    
    LogMsgBuffer.AddEntry("CHI ERROR", errorMsg);
    CHI_showErrorStatus();  // 弹出错误对话框
    
    if (Properties.Settings.Default.StopOnPanic) {
        // 紧急停止实验
        AbortExperiment();
    }
}
```

### 3.7 Python实现对比

**当前Python实现** ([chi.py](../MicroHySeeker/src/echem_sdl/hardware/chi.py)):

| 特性 | C# | Python现状 | 差异 |
|------|-----|------------|------|
| DLL调用 | DllImport (libec.dll) | 纯Mock | **需要ctypes实现** |
| 参数设置 | CHI_setParameter() | 数据类存储 | **需要映射到DLL** |
| 数据采集 | BackgroundWorker轮询 | 线程模拟 | 结构类似 |
| 技术支持 | CV, LSV, i-t (完整) | CV, LSV, i-t, OCPT等 | Python更多 |
| 错误处理 | DLL错误回调 | 无 | **需要添加** |

### 3.8 需要添加的DLL接口

```python
# ctypes 实现示例
import ctypes
from ctypes import c_byte, c_float, c_int, POINTER

class CHIDll:
    """CHI DLL 封装"""
    
    def __init__(self, dll_path: str = "libec.dll"):
        self._dll = ctypes.CDLL(dll_path)
        self._setup_functions()
    
    def _setup_functions(self):
        # CHI_hasTechnique
        self._dll.CHI_hasTechnique.argtypes = [c_int]
        self._dll.CHI_hasTechnique.restype = c_byte
        
        # CHI_setTechnique
        self._dll.CHI_setTechnique.argtypes = [c_int]
        self._dll.CHI_setTechnique.restype = None
        
        # CHI_setParameter
        self._dll.CHI_setParameter.argtypes = [POINTER(c_byte), c_float]
        self._dll.CHI_setParameter.restype = None
        
        # CHI_runExperiment
        self._dll.CHI_runExperiment.argtypes = []
        self._dll.CHI_runExperiment.restype = c_byte
        
        # CHI_experimentIsRunning
        self._dll.CHI_experimentIsRunning.argtypes = []
        self._dll.CHI_experimentIsRunning.restype = c_byte
        
        # CHI_getExperimentData
        self._dll.CHI_getExperimentData.argtypes = [
            POINTER(c_float), POINTER(c_float), c_int
        ]
        self._dll.CHI_getExperimentData.restype = None
    
    def set_parameter(self, param_id: str, value: float):
        """设置参数"""
        param_bytes = (c_byte * len(param_id))(*[ord(c) for c in param_id])
        self._dll.CHI_setParameter(param_bytes, c_float(value))
```

---

## 4. Python实现对比与改进建议

### 4.1 ExperimentEngine 改进

#### 4.1.1 多批次注入支持

```python
# 需要在 ProgStep 中添加
@dataclass
class SolutionComponent:
    solute: str
    low_conc: float
    is_solvent: bool = False
    in_const_conc: bool = False
    inject_order: int = 1      # 新增：注入顺序
    channel_index: int = 0

# 在引擎中实现批次检查
def _check_prepsol_state(self, step: ProgStep) -> StepState:
    """检查配液步骤状态"""
    running = False
    has_next = False
    
    for comp in step.components:
        diluter = self._diluters.get(comp.channel_index)
        if diluter:
            if diluter.is_infusing():
                running = True
            if not diluter.has_infused() and comp.inject_order > self._current_batch:
                has_next = True
    
    if running:
        return StepState.BUSY
    elif has_next:
        self._current_batch += 1
        return StepState.BUSY | StepState.NEXT_SOL
    else:
        return StepState.END
```

#### 4.1.2 精确定时器

```python
import asyncio
from PySide6.QtCore import QTimer

class ExperimentEngine:
    def __init__(self):
        # 使用Qt定时器实现精确1秒回调
        self._clock = QTimer()
        self._clock.setInterval(1000)  # 1秒
        self._clock.timeout.connect(self._clock_tick)
    
    def _clock_tick(self):
        """每秒回调"""
        if not self._running:
            return
        
        # 更新时间
        self._elapsed_time = time.time() - self._start_time
        self._step_elapsed_time = time.time() - self._step_start_time
        
        # 更新步骤状态
        step = self.current_step
        if step:
            state = self._get_step_state(step)
            self._handle_state(state)
```

### 4.2 CHI驱动改进

#### 4.2.1 真实硬件支持架构

```python
from abc import ABC, abstractmethod

class CHIBackend(ABC):
    """CHI后端抽象基类"""
    
    @abstractmethod
    def connect(self) -> bool: ...
    
    @abstractmethod
    def set_technique(self, technique: int) -> bool: ...
    
    @abstractmethod
    def set_parameter(self, param_id: str, value: float) -> bool: ...
    
    @abstractmethod
    def run_experiment(self) -> bool: ...
    
    @abstractmethod
    def is_running(self) -> bool: ...
    
    @abstractmethod
    def get_data(self) -> tuple[list[float], list[float]]: ...


class CHIDllBackend(CHIBackend):
    """真实DLL后端"""
    
    def __init__(self, dll_path: str = "libec.dll"):
        self._dll = ctypes.CDLL(dll_path)
        self._setup_functions()


class CHIMockBackend(CHIBackend):
    """Mock后端"""
    pass


class CHIInstrument:
    """CHI仪器驱动"""
    
    def __init__(self, backend: CHIBackend = None):
        self._backend = backend or CHIMockBackend()
```

### 4.3 全局上下文改进

```python
# lib_context.py 需要添加的功能

class LibContext:
    """全局上下文"""
    
    def __init__(self):
        # 硬件实例（单例）
        self._rs485_driver: Optional[RS485Driver] = None
        self._chi: Optional[CHIInstrument] = None
        self._flusher: Optional[Flusher] = None
        self._positioner: Optional[Positioner] = None
        self._diluters: Dict[int, Diluter] = {}
        
        # 状态数据
        self._chi_connected: bool = False
        self._va_points: List[tuple] = []
        self._mixed_solution: Optional[MixedSolution] = None
        
        # 配置
        self._channels: List[ChannelSettings] = []
        self._peri_pumps: List[PeriPumpSettings] = []
    
    def dispatch_pump_message(self, message: bytes):
        """分发泵响应消息到对应的配液器"""
        if len(message) < 2:
            return
        
        address = message[1]
        for diluter in self._diluters.values():
            if diluter.address == address:
                diluter.handle_response(message)
                break
```

---

## 5. 关键差异总结

### 5.1 架构差异

| 方面 | C# 实现 | Python 现状 | 改进优先级 |
|------|---------|------------|-----------|
| 定时器机制 | System.Timers.Timer (精确) | threading.sleep (不精确) | 🔴 高 |
| 多批次注入 | InjectOrder 完整支持 | 未实现 | 🔴 高 |
| CHI DLL | DllImport 原生调用 | 纯Mock | 🟡 中 |
| 溶液颜色计算 | 实时混合算法 | 未实现 | 🟢 低 |
| 定位器 | 完整串口控制 | 基础实现 | 🟡 中 |

### 5.2 协议差异

| 协议 | C# | Python | 状态 |
|------|-----|--------|------|
| RS485帧格式 | 0xFA/0xFB头 + 校验和 | 完全一致 | ✅ 兼容 |
| 电机编码 | 16384分度/圈 | 完全一致 | ✅ 兼容 |
| CHI参数ID | ASCII字符串 | 待实现 | ⚠️ 需添加 |

### 5.3 事件机制差异

| 机制 | C# | Python | 建议 |
|------|-----|--------|------|
| 电机响应 | event Action<byte[]> | 回调函数 | ✅ 可接受 |
| 进度报告 | BackgroundWorker.ReportProgress | Qt信号 | ✅ 更好 |
| 实验完成 | event EventHandler | 自定义事件系统 | ✅ 已实现 |

### 5.4 改进任务清单

1. **高优先级**
   - [ ] 实现精确的定时器机制（QTimer 或 asyncio）
   - [ ] 添加多批次注入支持（InjectOrder）
   - [ ] 完善步骤状态机（位标志枚举）

2. **中优先级**
   - [ ] 实现CHI DLL接口（ctypes）
   - [ ] 添加真实/Mock后端切换
   - [ ] 完善定位器控制

3. **低优先级**
   - [ ] 实现溶液颜色混合算法
   - [ ] 添加Kafka消息服务
   - [ ] Excel导出功能

---

## 附录：技术代码对照表

| 技术 | C# 代码 | Python 枚举 | 说明 |
|------|--------|------------|------|
| CV | M_CV = 0 | ECTechnique.CV = 0 | ✅ 一致 |
| LSV | M_LSV = 1 | ECTechnique.LSV = 1 | ✅ 一致 |
| i-t | M_IT = 11 | ECTechnique.IT = 9 | ⚠️ 值不同 |
| CA | M_CA = 4 | ECTechnique.CA = 2 | ⚠️ 值不同 |
| CP | M_CP = 15 | ECTechnique.CP = 4 | ⚠️ 值不同 |
| OCPT | M_OCPT = 26 | ECTechnique.OCPT = 5 | ⚠️ 值不同 |

> ⚠️ **注意**：Python实现中的技术代码与C#原版不一致，如果需要与真实CHI仪器通信，必须使用C#中的原始值。

---

*报告生成时间：2026年2月4日*  
*分析版本：eChemSDL C# 原版 → Python MicroHySeeker*
