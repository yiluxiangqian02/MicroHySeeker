# CHI 660F GUI 自动化控制器 使用手册

## 概述

`chi660f_gui_controller.py` 是一个基于 **pywinauto + Win32 API** 的 CHI 660F 电化学工作站 GUI 自动化控制模块。通过操控 CHI 660F 软件的 **Macro Command 对话框**，填写宏命令并自动执行电化学实验，实现无需人工干预的全自动化测量。

### 设计背景

CHI 660F 是 CH Instruments 生产的高端电化学工作站，但其软件（`chi660f.exe`）存在以下自动化难点：

| 方案 | 可行性 | 原因 |
|------|--------|------|
| libec.dll (ctypes) | ❌ 不可用 | libec.dll 只支持 660E，与 660F 协议不兼容 |
| 32位桥进程 | ❌ 不可用 | 同上，底层 DLL 不支持 |
| /runmacro 命令行 | ⚠️ 不稳定 | 可执行但无法可靠生成 CSV 文件 |
| **GUI 自动化** | ✅ **稳定可靠** | 通过 Macro Command 对话框直接控制 |

### 技术原理

```
Python 脚本
    ↓ Win32 API (PostMessage/SendMessage)
chi660f.exe 主窗口
    ↓ WM_COMMAND 32799
Macro Command 对话框
    ↓ 填入 Edit(id=308), 点击 Run Macro(id=312)
CHI 660F 执行宏命令
    ↓ 宏命令包含 tech/参数/run/csvsave
CSV 数据文件
    ↓ Python 解析
返回结构化数据
```

---

## 安装依赖

```bash
pip install pywinauto pywin32
```

> **注意**: 当前使用 64 位 Python 控制 32 位 chi660f.exe。pywinauto 的部分功能（如读取工具栏按钮文字）因 32/64 位不匹配受限，但本模块通过 Win32 API 直接发送消息，绕过了此限制。

---

## 快速开始

### 最简用法

```python
from src.echem_sdl.hardware.chi660f_gui_controller import quick_cv

# 运行一次 Dummy Cell CV 实验
result = quick_cv(e_init=0, e_high=0.5, e_low=-0.5, scan_rate=0.1, dummy=True)

if result.success:
    print(f"数据点数: {len(result.data_points)}")
    print(f"数据文件: {result.data_file}")
```

### 标准用法

```python
from src.echem_sdl.hardware.chi660f_gui_controller import (
    CHI660FController, ExperimentConfig, CVParams
)

# 1. 创建配置
config = ExperimentConfig(
    chi_exe_path=r"D:\CHI660F\chi660f.exe",  # CHI 660F 安装路径
    output_dir=r"D:\CHI660F\data",             # 数据输出目录
    use_dummy_cell=False,                      # 实际实验设为 False
    timeout=300,                               # 最大等待时间 (秒)
)

# 2. 创建控制器并启动
ctrl = CHI660FController(config)
ctrl.launch()  # 启动或连接到 CHI 660F

# 3. 设置参数并运行实验
params = CVParams(
    e_init=0.0,      # 初始电位 (V)
    e_high=0.5,      # 高电位 (V)
    e_low=-0.5,      # 低电位 (V)
    scan_rate=0.05,   # 扫描速率 (V/s)
    segments=4,       # 扫描段数
)

result = ctrl.run_cv(params)

# 4. 处理结果
if result.success:
    print(f"数据列: {result.headers}")  # ['Potential/V', 'Current/A']
    print(f"数据点: {len(result.data_points)}")
    for point in result.data_points[:5]:
        print(f"  E={point[0]:.3f}V, I={point[1]:.6e}A")

# 5. 关闭 (可选)
ctrl.close()
```

---

## 支持的技术

### 1. CV - 循环伏安法 (Cyclic Voltammetry)

```python
from src.echem_sdl.hardware.chi660f_gui_controller import CVParams

params = CVParams(
    e_init=0.0,           # 初始电位 (V), 范围: -10 ~ +10
    e_high=0.5,           # 高电位 (V), 范围: -10 ~ +10
    e_low=-0.5,           # 低电位 (V), 范围: -10 ~ +10
    e_final=0.0,          # 终止电位 (V), 默认等于 e_init
    scan_rate=0.1,        # 扫描速率 (V/s), 范围: 1e-6 ~ 10000
    segments=2,           # 扫描段数, 范围: 1 ~ 10000
    sample_interval=0.001, # 采样间隔 (V), 范围: 0.001 ~ 0.064
    quiet_time=2.0,       # 静默时间 (s), 范围: 0 ~ 100000
    sensitivity=0.0,      # 灵敏度 (A/V), 0 = 自动
    polarity='p',         # 扫描极性: 'p' = 正向先, 'n' = 负向先
)

result = ctrl.run_cv(params)
# 输出数据列: Potential/V, Current/A
```

**典型应用**: 电极表面修饰表征、氧化还原峰分析、电活性面积计算

### 2. LSV - 线性扫描伏安法 (Linear Sweep Voltammetry)

```python
from src.echem_sdl.hardware.chi660f_gui_controller import LSVParams

params = LSVParams(
    e_init=0.0,           # 初始电位 (V)
    e_final=1.0,          # 终止电位 (V)
    scan_rate=0.01,       # 扫描速率 (V/s), 范围: 1e-6 ~ 10000
    sample_interval=0.001, # 采样间隔 (V)
    quiet_time=2.0,       # 静默时间 (s)
    sensitivity=0.0,      # 灵敏度, 0 = 自动
)

result = ctrl.run_lsv(params)
# 输出数据列: Potential/V, Current/A
```

**典型应用**: Tafel 分析、析氧/析氢极化曲线、腐蚀电位测定

### 3. i-t - 安培-时间曲线 (Amperometric i-t)

```python
from src.echem_sdl.hardware.chi660f_gui_controller import ITParams

params = ITParams(
    e_init=0.3,           # 恒定电位 (V), 范围: -10 ~ +10
    sample_interval=0.1,  # 采样间隔 (s), 范围: 4e-7 ~ 50
    run_time=60.0,        # 运行时间 (s), 范围: 0.001 ~ 500000
    quiet_time=2.0,       # 静默时间 (s)
    sensitivity=0.0,      # 灵敏度, 0 = 自动
)

result = ctrl.run_it(params)
# 输出数据列: Time/sec, Current/A
```

**典型应用**: 传感器响应、电沉积监控、电流稳定性测试

### 4. IMP/EIS - 交流阻抗谱 (Electrochemical Impedance Spectroscopy)

```python
from src.echem_sdl.hardware.chi660f_gui_controller import IMPParams

params = IMPParams(
    e_init=0.0,           # DC 偏置电位 (V), 范围: -10 ~ +10
    freq_low=0.01,        # 最低频率 (Hz), 范围: 1e-5 ~ 100000
    freq_high=100000.0,   # 最高频率 (Hz), 范围: 1e-4 ~ 3000000
    amplitude=0.005,      # AC 振幅 (V), 范围: 0.001 ~ 0.7
    quiet_time=2.0,       # 静默时间 (s)
    auto_sensitivity=True, # 自动灵敏度
    bias_mode=0,          # 偏置模式: 0=vs Eref, 1=vs Eoc
)

result = ctrl.run_imp(params)
# 输出数据列: Freq/Hz, Z'/ohm, Z''/ohm
```

**典型应用**: 电极界面电阻、涂层评价、电池内阻测量

### 5. OCPT - 开路电位-时间 (Open Circuit Potential vs Time)

```python
from src.echem_sdl.hardware.chi660f_gui_controller import OCPTParams

params = OCPTParams(
    sample_interval=1.0,  # 采样间隔 (s), 范围: 1e-6 ~ 50
    run_time=300.0,       # 运行时间 (s), 范围: 0.1 ~ 500000
    e_high=10.0,          # 高电位限制 (V)
    e_low=-10.0,          # 低电位限制 (V)
)

result = ctrl.run_ocpt(params)
# 输出数据列: Time/sec, Potential/V
```

**典型应用**: 腐蚀电位监测、电极稳定性评估、界面电位变化追踪

---

## 自定义宏命令

对于更复杂的实验，可以直接编写宏命令文本：

```python
macro_text = """folder: D:\\CHI660F\\data
fileoverride
dummyon
tech: cv
ei = -0.2
eh = 0.8
el = -0.2
pn = p
v = 0.05
cl = 4
si = 0.001
qt = 5
autosens
run
csvsave: my_custom_cv
dummyoff"""

result = ctrl.run_custom_macro(macro_text)
```

### 常用宏命令参考

| 命令 | 说明 | 示例 |
|------|------|------|
| `tech: xxx` | 选择技术 | `tech: cv` |
| `ei = x` | 初始电位 (V) | `ei = 0.0` |
| `eh = x` | 高电位 (V) | `eh = 0.5` |
| `el = x` | 低电位 (V) | `el = -0.5` |
| `ef = x` | 终止电位 (V) | `ef = 0.0` |
| `v = x` | 扫描速率 (V/s) | `v = 0.1` |
| `cl = n` | 扫描段数 | `cl = 2` |
| `si = x` | 采样间隔 | `si = 0.001` |
| `st = x` | 运行时间 (s) | `st = 60` |
| `qt = x` | 静默时间 (s) | `qt = 2` |
| `fl = x` | 最低频率 (Hz) | `fl = 0.01` |
| `fh = x` | 最高频率 (Hz) | `fh = 100000` |
| `amp = x` | AC 振幅 (V) | `amp = 0.005` |
| `pn = p/n` | 极性 | `pn = p` |
| `sens = x` | 灵敏度 (A/V) | `sens = 1e-6` |
| `autosens` | 自动灵敏度 | |
| `impautosens` | IMP 自动灵敏度 | |
| `dummyon` | 开启 Dummy Cell | |
| `dummyoff` | 关闭 Dummy Cell | |
| `run` | 执行实验 | |
| `csvsave: name` | 保存 CSV 文件 | `csvsave: test01` |
| `tsave: name` | 保存文本文件 | `tsave: test01` |
| `folder: path` | 设置输出目录 | `folder: D:\data` |
| `fileoverride` | 覆盖同名文件 | |
| `ibias = n` | EIS 偏置模式 (0-4) | `ibias = 1` |

---

## 配置说明

### ExperimentConfig 参数

```python
@dataclass
class ExperimentConfig:
    chi_exe_path: str = r"D:\CHI660F\chi660f.exe"  # CHI 660F 安装路径
    output_dir: str = ""            # 数据输出目录 (空=自动: chi660f目录/data)
    output_format: str = "csv"      # 输出格式: "csv" | "txt"
    use_dummy_cell: bool = False    # 使用内置 Dummy Cell (测试用)
    file_override: bool = True      # 自动覆盖同名文件
    timeout: float = 600.0          # 实验最大等待时间 (秒)
    auto_close_macro: bool = True   # 实验完成后自动关闭 Macro 对话框
    startup_wait: float = 5.0       # 启动等待时间 (秒)
```

### ExperimentResult 结构

```python
@dataclass
class ExperimentResult:
    success: bool          # 是否成功
    technique: str         # 使用的技术名 (如 "cv", "i-t")
    data_file: str         # 数据文件完整路径
    data_points: list      # 二维数据 [[x, y, ...], ...]
    headers: list          # 列名 ["Potential/V", "Current/A"]
    elapsed_time: float    # 实验总耗时 (秒)
    error_message: str     # 错误信息 (成功时为空)
```

---

## API 参考

### CHI660FController 类

#### 生命周期方法

| 方法 | 说明 |
|------|------|
| `launch(force_restart=False)` | 启动或连接到 CHI 660F。`force_restart=True` 会先杀掉旧进程 |
| `close()` | 关闭 CHI 660F |
| `is_connected()` | 检查是否已连接 |

#### 实验方法

| 方法 | 说明 | 返回 |
|------|------|------|
| `run_cv(params, output_name="")` | 循环伏安法 | `ExperimentResult` |
| `run_lsv(params, output_name="")` | 线性扫描伏安法 | `ExperimentResult` |
| `run_it(params, output_name="")` | 安培-时间曲线 | `ExperimentResult` |
| `run_imp(params, output_name="")` | 交流阻抗谱 | `ExperimentResult` |
| `run_ocpt(params, output_name="")` | 开路电位-时间 | `ExperimentResult` |
| `run_custom_macro(macro_text)` | 执行自定义宏命令 | `ExperimentResult` |

#### 控制方法

| 方法 | 说明 |
|------|------|
| `stop_experiment()` | 停止正在进行的实验 |
| `get_open_circuit_potential()` | 获取开路电位 |
| `send_command(cmd_id)` | 发送任意 WM_COMMAND |
| `get_window_title()` | 获取当前窗口标题 |

#### 便捷函数

```python
quick_cv(e_init=0, e_high=0.5, e_low=-0.5, scan_rate=0.1, segments=2, dummy=True)
quick_it(e_init=0, run_time=10, sample_interval=0.1, dummy=True)
quick_imp(e_init=0, freq_low=1, freq_high=100000, amplitude=0.005, dummy=True)
```

---

## WM_COMMAND 速查表

以下是从 `chi660f.exe` 二进制资源中提取的完整菜单命令 ID：

### File 菜单
| ID | 命令 |
|----|------|
| 57600 | New |
| 57601 | Open |
| 57602 | Close |
| 57604 | Save As |
| 57665 | Exit |

### Setup 菜单
| ID | 命令 |
|----|------|
| 32789 | Technique... |
| 32790 | Parameters... |
| 32791 | System... |
| 32792 | Hardware Test |

### Control 菜单
| ID | 命令 |
|----|------|
| 32793 | Run Experiment |
| 32794 | Pause / Resume |
| 32795 | Stop Run |
| 32796 | Reverse Scan |
| 32797 | Repetitive Runs... |
| 32798 | Run Status... |
| **32799** | **Macro Command...** ⭐ |
| 32800 | Open Circuit Potential |
| 32803 | Cell... |
| 32804 | Preconditioning... |

### Graphics 菜单
| ID | 命令 |
|----|------|
| 32807 | Present Data Plot |
| 32813 | Zoom In |
| 32819 | Graph Options... |

---

## 故障排除

### 1. "无法打开 Macro Command 对话框"

**原因**: CHI 660F 可能处于异常状态（有残留对话框）。

**解决方案**: 使用 `force_restart=True` 强制重启：
```python
ctrl.launch(force_restart=True)
```

### 2. 实验超时

**原因**: 实验时间过长或仪器未连接。

**解决方案**:
- 增大 `timeout` 值
- 确认仪器已连接并开机
- 使用 `use_dummy_cell=True` 先测试流程

### 3. "CH Instruments Electrochemical Software" 错误对话框

**原因**: 软件启动时的非致命错误 (`CEcDoc::OnGraphicsTestvtk`)。

**解决方案**: 控制器会自动关闭此对话框，无需手动处理。

### 4. CSV 文件未生成

**可能原因**:
- `output_dir` 路径不存在 → 控制器会自动创建
- 宏命令中没有 `csvsave:` → 检查宏文本
- 仪器未连接且未使用 dummy cell → 设置 `use_dummy_cell=True`

### 5. 32 位/64 位不匹配

**现象**: pywinauto 无法读取某些控件文本。

**原因**: chi660f.exe 是 32 位 MFC 应用，而 Python 通常是 64 位。

**解决方案**: 本模块使用 Win32 API 直接消息通信，不受此限制影响。如需完全兼容，安装 32 位 Python。

---

## 数据文件格式

CHI 660F 生成的 CSV 文件格式如下：

```
Feb. 10, 2026   13:13:18          ← 日期时间
Cyclic Voltammetry                ← 技术名称
File: run unsaved                 ← 文件信息
Data Source:  Int Dummy            ← 数据来源 (Dummy/Real)
Instrument Model:  CHI660F        ← 仪器型号
Header:                           ← 用户自定义头
Note:                             ← 备注

Init E (V) = 0                    ← 实验参数
High E (V) = 0.5
Low E (V) = -0.5
...                               ← 更多参数

Potential/V, Current/A            ← 列名行 ← 数据起始标记

0.000, 7.091e-8                   ← 数据行
-0.001, 7.823e-7
-0.002, 1.716e-6
...                               ← 约 1000-2000 个数据点
```

控制器的 `_parse_csv()` 方法会自动跳过头信息，提取列名和数据。

---

## 完整示例：批量实验

```python
from src.echem_sdl.hardware.chi660f_gui_controller import (
    CHI660FController, ExperimentConfig,
    CVParams, ITParams, IMPParams, OCPTParams
)

config = ExperimentConfig(
    output_dir=r"D:\experiments\2026_02_10",
    use_dummy_cell=False,  # 实际实验
    timeout=600,
)

ctrl = CHI660FController(config)
ctrl.launch()

# 1. 先测量 OCP
ocp_result = ctrl.run_ocpt(
    OCPTParams(sample_interval=1, run_time=60),
    output_name="step1_ocp"
)

# 2. CV 表征
cv_result = ctrl.run_cv(
    CVParams(e_init=0, e_high=0.8, e_low=-0.2, scan_rate=0.05, segments=4),
    output_name="step2_cv"
)

# 3. EIS 测量
eis_result = ctrl.run_imp(
    IMPParams(e_init=0, freq_low=0.01, freq_high=100000, amplitude=0.005),
    output_name="step3_eis"
)

# 4. i-t 稳定性测试
it_result = ctrl.run_it(
    ITParams(e_init=0.5, run_time=300, sample_interval=1),
    output_name="step4_it"
)

# 汇总结果
for name, result in [("OCP", ocp_result), ("CV", cv_result), 
                      ("EIS", eis_result), ("i-t", it_result)]:
    status = "✅" if result.success else "❌"
    print(f"{status} {name}: {len(result.data_points)} 点, {result.elapsed_time:.1f}s")

ctrl.close()
```

---

## 文件结构

```
src/echem_sdl/hardware/
├── chi660f_gui_controller.py   ← 本模块 (GUI 自动化)
├── chi_macro.py                ← 老模块 (/runmacro 命令行方式)
└── chi.py                      ← CHIInstrument 抽象层
```

---

## 技术参数范围速查

| 参数 | CV | LSV | i-t | IMP | OCPT |
|------|----|----|------|-----|------|
| 初始电位 ei | -10~+10V | -10~+10V | -10~+10V | -10~+10V | — |
| 高电位 eh | -10~+10V | — | — | — | -10~+10V |
| 低电位 el | -10~+10V | — | — | — | -10~+10V |
| 终止电位 ef | -10~+10V | -10~+10V | — | — | — |
| 扫描速率 v | 1e-6~10kV/s | 1e-6~10kV/s | — | — | — |
| 采样间隔 si | 0.001~0.064V | 0.001~0.064V | 4e-7~50s | — | 1e-6~50s |
| 运行时间 st | — | — | 0.001~5e5s | — | 0.1~5e5s |
| 低频 fl | — | — | — | 1e-5~1e5Hz | — |
| 高频 fh | — | — | — | 1e-4~3e6Hz | — |
| AC振幅 amp | — | — | — | 0.001~0.7V | — |
| 灵敏度 sens | 1e-12~0.1 | 1e-12~0.1 | 1e-12~0.1 | auto | — |

---

*最后更新: 2026-02-10*
*模块版本: 1.0*
*依赖: pywinauto >= 0.6.9, pywin32 >= 311*
