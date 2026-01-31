# MicroHySeeker 后端接口文档

本文档详细描述了 MicroHySeeker 系统中所有后端接口、服务端口和通信协议，用于后续硬件开发和后端搭建。

---

## 目录

1. [RS485 通信接口](#1-rs485-通信接口)
2. [CHI 电化学工作站接口](#2-chi-电化学工作站接口)
3. [实验运行服务接口](#3-实验运行服务接口)
4. [数据模型接口](#4-数据模型接口)
5. [UI 后端交互接口](#5-ui-后端交互接口)

---

## 1. RS485 通信接口

### 1.1 类: `RS485Wrapper`

**文件位置**: `src/services/rs485_wrapper.py`

**功能**: 封装 RS485 串口通信，控制蠕动泵（地址 1-12）

#### 初始化参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `port` | str | "COM3" | RS485 串口端口号 |
| `baudrate` | int | 9600 | 波特率 |
| `timeout` | float | 0.5 | 读取超时时间（秒） |

#### 公共方法

| 方法签名 | 返回值 | 描述 |
|----------|--------|------|
| `open_port(port: str, baudrate: int) -> bool` | bool | 打开串口连接 |
| `close_port() -> None` | None | 关闭串口连接 |
| `is_connected() -> bool` | bool | 检查连接状态 |
| `scan_pumps() -> List[int]` | List[int] | 扫描可用泵地址 |
| `start_pump(addr: int, direction: str, rpm: int) -> bool` | bool | 启动泵 |
| `stop_pump(addr: int) -> bool` | bool | 停止泵 |
| `stop_all() -> bool` | bool | 停止所有泵（急停） |
| `set_pump_speed(addr: int, rpm: int) -> bool` | bool | 设置泵转速 |
| `get_pump_status(addr: int) -> dict` | dict | 获取泵状态 |

#### UI 调用点

| UI 位置 | 调用方法 | 说明 |
|---------|----------|------|
| 配置对话框 - 连接按钮 | `open_port()`, `close_port()` | 连接/断开 RS485 |
| 配置对话框 - 扫描按钮 | `scan_pumps()` | 扫描可用泵 |
| 手动控制 - 正转按钮 | `start_pump(addr, "FWD", rpm)` | 正向启动泵 |
| 手动控制 - 反转按钮 | `start_pump(addr, "REV", rpm)` | 反向启动泵 |
| 手动控制 - 停止按钮 | `stop_pump(addr)` | 停止单个泵 |
| 手动控制 - 全部停止 | `stop_all()` | 停止所有泵 |
| 手动控制 - 关闭对话框 | `stop_all()` | 安全停止 |
| 配制溶液 - 开始配制 | `start_pump()`, `stop_pump()` | 配液过程控制 |
| 实验运行 - 配液步骤 | `start_pump()`, `stop_pump()` | 按注液顺序启停泵 |
| 实验运行 - 冲洗步骤 | `start_pump()`, `stop_pump()` | 冲洗泵控制 |
| 实验运行 - 移液步骤 | `start_pump()`, `stop_pump()` | 移液泵控制 |

---

## 2. CHI 电化学工作站接口

### 2.1 类: `CHIWrapper`

**文件位置**: `src/services/chi_wrapper.py`

**功能**: 封装 CHI 电化学工作站的控制接口

#### 公共方法

| 方法签名 | 返回值 | 描述 |
|----------|--------|------|
| `connect() -> bool` | bool | 连接 CHI 工作站 |
| `disconnect() -> None` | None | 断开连接 |
| `is_connected() -> bool` | bool | 检查连接状态 |
| `run_cv(params: dict) -> dict` | dict | 执行循环伏安法 |
| `run_lsv(params: dict) -> dict` | dict | 执行线性扫描伏安法 |
| `run_it(params: dict) -> dict` | dict | 执行计时电流法 |
| `stop() -> None` | None | 停止当前实验 |
| `get_data() -> np.ndarray` | ndarray | 获取实验数据 |

#### CV 参数结构

```python
cv_params = {
    "e0": 0.0,           # 初始电位 (V)
    "eh": 0.8,           # 上限电位 (V)
    "el": -0.2,          # 下限电位 (V)
    "ef": 0.0,           # 终止电位 (V)
    "scan_rate": 0.05,   # 扫描速率 (V/s)
    "seg_num": 2,        # 扫描段数
    "scan_dir": "FWD",   # 扫描方向
    "sensitivity": 1.0,  # 灵敏度 (V)
    "autosensitivity": True,  # 自动灵敏度
    "quiet_time": 2.0,   # 静置时间 (秒)
    "sample_interval": 1.0,  # 记录间隔 (mV)
}
```

#### LSV 参数结构

```python
lsv_params = {
    "e0": 0.0,           # 初始电位 (V)
    "ef": 0.8,           # 终止电位 (V)
    "scan_rate": 0.05,   # 扫描速率 (V/s)
    "sensitivity": 1.0,  # 灵敏度 (V)
    "quiet_time": 2.0,   # 静置时间 (秒)
    "sample_interval": 1.0,  # 记录间隔 (mV)
}
```

#### i-t 参数结构

```python
it_params = {
    "e0": 0.0,           # 初始电位 (V)
    "run_time": 60.0,    # 运行时间 (秒)
    "sensitivity": 1.0,  # 灵敏度 (V)
    "quiet_time": 2.0,   # 静置时间 (秒)
    "sample_interval": 0.1,  # 采样间隔 (秒)
}
```

#### UI 调用点

| UI 位置 | 调用方法 | 说明 |
|---------|----------|------|
| 实验运行 - 电化学步骤 | `run_cv()` / `run_lsv()` / `run_it()` | 根据技术类型调用 |
| 停止实验 | `stop()` | 中止电化学实验 |

---

## 3. 实验运行服务接口

### 3.1 类: `ExperimentRunner`

**文件位置**: `src/engine/runner.py`

**功能**: 协调执行实验步骤

#### 信号 (Qt Signals)

| 信号名 | 参数类型 | 描述 |
|--------|----------|------|
| `step_started` | (int, str) | 步骤开始 (索引, ID) |
| `step_finished` | (int, str, bool) | 步骤完成 (索引, ID, 成功) |
| `experiment_finished` | (bool,) | 实验完成 (成功) |
| `log_message` | (str,) | 日志消息 |

#### 公共方法

| 方法签名 | 返回值 | 描述 |
|----------|--------|------|
| `run_experiment(exp: Experiment) -> None` | None | 运行单次实验 |
| `stop() -> None` | None | 停止实验 |
| `pause() -> None` | None | 暂停实验 |
| `resume() -> None` | None | 继续实验 |

#### 步骤执行流程

##### 配液步骤 (PREP_SOL)

```
1. 读取配液参数: target_concentration, total_volume_ml, injection_order
2. 计算各溶液注入量 (基于原浓度和校准数据)
3. 按 injection_order 顺序启动泵
4. 等待注液完成
5. 停止泵
```

**后端接口调用**:
- `RS485Wrapper.start_pump(pump_address, direction, rpm)`
- `RS485Wrapper.stop_pump(pump_address)`

##### 电化学步骤 (EChem)

```
1. 读取电化学参数: technique, e0, eh, el, ef, scan_rate, ...
2. 根据 technique 类型调用对应 CHI 方法
3. 等待实验完成
4. 获取数据
5. 如果启用 OCPT 检测，监控反向电流
```

**后端接口调用**:
- `CHIWrapper.run_cv(params)` / `run_lsv(params)` / `run_it(params)`
- `CHIWrapper.get_data()`

##### 冲洗步骤 (FLUSH)

```
1. 读取冲洗参数: pump_address, direction, rpm, duration, cycles
2. 循环 cycles 次:
   a. 启动泵
   b. 等待 duration 秒
   c. 停止泵
```

**后端接口调用**:
- `RS485Wrapper.start_pump(pump_address, direction, rpm)`
- `RS485Wrapper.stop_pump(pump_address)`

##### 移液步骤 (TRANSFER)

```
1. 读取移液参数: pump_address, direction, rpm, transfer_duration, transfer_duration_unit
2. 根据单位转换为实际秒数:
   - ms: duration / 1000
   - s: duration
   - min: duration * 60
   - hr: duration * 3600
   - cycle: 根据校准数据计算
3. 启动泵
4. 等待运行时间
5. 停止泵
```

**参数说明**:
- `transfer_duration`: 持续时间数值
- `transfer_duration_unit`: 时间单位 (ms/s/min/hr/cycle)

**后端接口调用**:
- `RS485Wrapper.start_pump(pump_address, direction, rpm)`
- `RS485Wrapper.stop_pump(pump_address)`

##### 排空步骤 (EVACUATE)

```
1. 读取排空参数: pump_address, direction, rpm, transfer_duration, transfer_duration_unit, flush_cycles
2. 排空是Flusher的Outlet阶段，用于清空管路
3. 循环 flush_cycles 次:
   a. 启动Outlet泵
   b. 等待 duration (按单位转换)
   c. 停止泵
```

**参数说明**:
- `pump_address`: Outlet泵地址
- `direction`: 泵方向 (FWD/REV)
- `rpm`: 转速
- `transfer_duration`: 持续时间数值
- `transfer_duration_unit`: 时间单位 (ms/s/min/hr/cycle)
- `flush_cycles`: 循环次数

**后端接口调用**:
- `RS485Wrapper.start_pump(pump_address, direction, rpm)`
- `RS485Wrapper.stop_pump(pump_address)`

---

## 4. 数据模型接口

### 4.1 配液通道 `DilutionChannel`

**文件位置**: `src/models.py`

```python
@dataclass
class DilutionChannel:
    channel_id: str           # 通道序号 (自动分配: 1, 2, 3...)
    solution_name: str        # 溶液名称
    stock_concentration: float  # 原浓度 (mol/L, 保留两位小数)
    pump_address: int         # 泵地址 (1-12)
    direction: str = "FWD"    # 方向 (FWD/REV)
    default_rpm: int = 120    # 默认转速 (RPM)
    color: str = "#00FF00"    # 显示颜色
```

### 4.2 冲洗通道 `FlushChannel`

```python
@dataclass
class FlushChannel:
    channel_id: str           # 通道序号
    pump_address: int         # 泵地址 (1-12)
    direction: str = "FWD"    # 方向
    work_type: str = "Transfer"  # 工作类型: Inlet, Transfer, Outlet
    rpm: int = 100            # 转速
    cycle_duration_s: float = 30.0  # 循环时长（秒，保留两位小数）
```

### 4.3 程序步骤 `ProgStep`

```python
@dataclass
class ProgStep:
    step_type: ProgramStepType  # 步骤类型 (见枚举)
    step_id: str                # 步骤ID
    pump_address: Optional[int] = None  # 泵地址
    pump_direction: Optional[str] = None  # 泵方向 (FWD/REV)
    pump_rpm: Optional[int] = None  # 泵转速
    
    # 移液/排空 - 持续时间
    transfer_duration: Optional[float] = None  # 持续时间数值
    transfer_duration_unit: str = "s"  # 单位 (ms/s/min/hr/cycle)
    
    # 冲洗/排空 - 循环
    flush_cycles: Optional[int] = None  # 循环次数
    flush_cycle_duration_s: Optional[float] = None  # 每循环时长(秒)
    
    # 空白 - 持续时间
    duration_s: Optional[float] = None  # 持续时间(秒)
    notes: Optional[str] = None  # 备注
    
    # 配液参数
    prep_sol_params: Optional[PrepSolStep] = None
    
    # 电化学参数
    ec_settings: Optional[ECSettings] = None
```

### 4.4 步骤类型枚举 `ProgramStepType`

```python
class ProgramStepType(Enum):
    TRANSFER = "transfer"    # 移液
    PREP_SOL = "prep_sol"    # 配液
    FLUSH = "flush"          # 冲洗 (Inlet阶段)
    EChem = "echem"          # 电化学
    BLANK = "blank"          # 空白 (等待/无操作)
    EVACUATE = "evacuate"    # 排空 (Outlet阶段)
```

### 4.5 电化学设置 `ECSettings`

```python
@dataclass
class ECSettings:
    technique: ECTechnique = ECTechnique.CV  # CV, LSV, I_T
    e0: float = 0.0           # 初始电位 (V)
    eh: float = 0.8           # 上限电位 (V)
    el: float = -0.2          # 下限电位 (V)
    ef: float = 0.0           # 终止电位 (V)
    scan_rate: float = 0.05   # 扫描速率 (V/s)
    seg_num: int = 2          # 扫描段数
    scan_dir: str = "FWD"     # 扫描方向
    sensitivity: float = 1.0  # 灵敏度 (V)
    autosensitivity: bool = True  # 自动灵敏度
    quiet_time_s: float = 2.0  # 静置时间 (秒)
    run_time_s: float = 60.0  # 运行时间 (秒, i-t用)
    
    # OCPT 反向电流检测
    ocpt_enabled: bool = False
    ocpt_threshold_uA: float = -50.0  # 阈值电流 (μA)
    ocpt_duration_s: float = 5.0  # 持续时间 (秒)
    ocpt_action: OCPTAction = OCPTAction.LOG  # 触发动作
```

### 4.4 配液步骤参数 `PrepSolStep`

```python
@dataclass
class PrepSolStep:
    target_concentration: float  # 目标浓度 (mol/L, 保留两位小数)
    total_volume_ul: float  # 总体积 (μL, 内部存储; UI显示为mL)
    is_solvent: bool = False  # 是否溶剂
    injection_order: List[str] = []  # 注液顺序 (溶液名称列表)
```

---

## 5. UI 后端交互接口

### 5.1 配置对话框 `ConfigDialog`

**文件**: `src/dialogs/config_dialog.py`

| UI 操作 | 后端接口 | 数据格式 |
|---------|----------|----------|
| 连接 RS485 | `RS485Wrapper.open_port(port, baudrate)` | port: str, baudrate: int |
| 断开 RS485 | `RS485Wrapper.close_port()` | - |
| 扫描泵 | `RS485Wrapper.scan_pumps()` | 返回 List[int] |
| 保存配置 | `SystemConfig.save_to_file(path)` | path: str |

**通道参数格式**:
- 所有浓度: 保留两位小数 (mol/L)
- 所有时长: 保留两位小数 (秒)
- 通道ID: 自动分配序号 (1, 2, 3...)

---

### 5.2 程序编辑器 `ProgramEditorDialog`

**文件**: `src/dialogs/program_editor.py`

| UI 操作 | 后端接口 | 说明 |
|---------|----------|------|
| 保存程序 | `Experiment.to_json_str()` | 序列化实验对象 |
| 加载程序 | `Experiment.from_json_str()` | 反序列化实验对象 |

**配液参数**:
- 溶液配方来自 `SystemConfig.dilution_channels`
- 显示格式: [溶液名称, 原浓度(mol/L), 泵端口, 是否溶剂, 注液顺序]
- 总体积单位: mL (内部转换为 μL 存储)

**电化学参数根据技术类型**:
| 技术 | 可用参数 | 禁用参数 |
|------|----------|----------|
| CV | E0, EH, EL, EF, 扫速, 方向, 段数, 灵敏度, 记录间隔, 自动灵敏度, 静置时间 | 运行时间 |
| LSV | E0, EF, 扫速, 灵敏度, 记录间隔, 静置时间 | EH, EL, 方向, 段数, 运行时间, 自动灵敏度 |
| i-t | E0, 灵敏度, 记录间隔, 静置时间, 运行时间 | EH, EL, EF, 扫速, 方向, 段数, 自动灵敏度 |

---

### 5.3 组合实验编辑器 `ComboExpEditorDialog`

**文件**: `src/dialogs/combo_exp_editor.py`

| UI 操作 | 数据格式 | 说明 |
|---------|----------|------|
| 加载步骤 | 从 `Experiment.steps` | 读取单次实验步骤 |
| 生成组合 | `List[Dict[str, float]]` | 参数组合列表 |

**参数显示规则**:
- 配液: 每个溶液有独立的目标浓度(mol/L)行，溶液类型列显示溶液名称
- 电化学 CV: 静置时间, E0, EH, EL, EF, 扫速
- 电化学 LSV: 静置时间, E0, EF, 扫速
- 电化学 i-t: 静置时间, E0, 运行时间
- 冲洗: 持续时间(s), 循环次数
- 移液: 持续时间, 转速
- 排空: 持续时间(s), 循环次数
- 空白: 持续时间(s)

---

### 5.4 手动控制 `ManualControlDialog`

**文件**: `src/dialogs/manual_control.py`

| UI 操作 | 后端接口 | 参数 |
|---------|----------|------|
| 选择泵 | - | pump_address: 1-12 |
| 正转 | `RS485Wrapper.start_pump(addr, "FWD", rpm)` | rpm: 1-600 |
| 反转 | `RS485Wrapper.start_pump(addr, "REV", rpm)` | rpm: 1-600 |
| 停止 | `RS485Wrapper.stop_pump(addr)` | - |
| 全部停止 | `RS485Wrapper.stop_all()` | - |
| 关闭对话框 | `RS485Wrapper.stop_all()` | 安全措施 |

---

### 5.5 配制溶液 `PrepSolutionDialog`

**文件**: `src/dialogs/prep_solution.py`

| UI 操作 | 后端接口 | 说明 |
|---------|----------|------|
| 加载溶液 | 从 `SystemConfig.dilution_channels` | 读取配液通道配置 |
| 开始配制 | `RS485Wrapper.start_pump()` | 按注液顺序启动泵 |
| 完成配制 | `RS485Wrapper.stop_pump()` | 停止所有相关泵 |

---

### 5.6 主窗口 `MainWindow`

**文件**: `src/ui/main_window.py`

| UI 组件 | 后端接口 | 说明 |
|---------|----------|------|
| 泵状态指示 | 读取 `SystemConfig.dilution_channels` 和 `flush_channels` | 2列6行显示12个泵状态 |
| 实验过程区 | 读取 `SystemConfig.flush_channels` | 显示 Inlet/Transfer/Outlet 泵 |
| 开始单次实验 | `ExperimentRunner.run_experiment()` | 运行单次实验 |
| 开始组合实验 | 循环调用 `run_experiment()` | 运行组合实验 |
| 停止实验 | `ExperimentRunner.stop()` | 停止实验 |
| 复位组合进程 | 重置 `current_combo_index` | 复位到第1组 |
| 列出参数 | 读取 `combo_params[current_index]` | 显示当前参数 |

---

## 附录 A: 泵地址分配表

| 地址 | 典型用途 | 工作类型 | 方向 |
|------|----------|----------|------|
| 1 | 配液泵 1 | - | FWD |
| 2 | 配液泵 2 | - | FWD |
| 3 | 配液泵 3 | - | FWD |
| 4 | 配液泵 4 | - | FWD |
| 5 | 冲洗泵 | Inlet | FWD |
| 6 | 冲洗泵 | Transfer | FWD |
| 7 | 冲洗泵 | Outlet | FWD |
| 8 | 移液泵 | - | FWD |
| 9-12 | 备用 | - | - |

---

## 附录 B: 数值精度规范

| 数据类型 | 小数位数 | 单位 |
|----------|----------|------|
| 浓度 | 2 位 | mol/L |
| 体积 (UI) | 2 位 | mL |
| 体积 (内部) | 2 位 | μL |
| 时间 | 2 位 | 秒 |
| 电位 | 2 位 | V |
| 扫描速率 | 4 位 | V/s |
| 电流 | 2 位 | μA |
| 转速 | 0 位 | RPM |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0 | 2026-01-30 | 全面更新接口文档 |
| 2.1 | 2026-01-30 | 添加配液注液顺序、电化学参数变化规则 |
| 2.2 | 2026-01-30 | 添加体积单位mL、小数精度规范 |
