# MicroHySeeker 后端接口文档

本文档记录了 UI 层与后端硬件/服务层的所有接口定义，便于后续后端开发与对接。

---

## 1. RS485 通信接口 (RS485Wrapper)

位置: `src/services/rs485_wrapper.py`

### 1.1 连接管理

| 接口方法 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `open_port(port: str, baudrate: int)` | 串口号 (如 "COM3"), 波特率 (9600/115200) | `bool` | 打开串口连接 |
| `close_port()` | 无 | `None` | 关闭串口连接 |
| `is_connected()` | 无 | `bool` | 检查连接状态 |

### 1.2 泵控制

| 接口方法 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `start_pump(addr: int, direction: str, rpm: int)` | 泵地址(1-12), 方向("FWD"/"REV"), 转速 | `bool` | 启动指定泵 |
| `stop_pump(addr: int)` | 泵地址(1-12) | `bool` | 停止指定泵 |
| `stop_all()` | 无 | `bool` | 停止所有泵 |
| `scan_pumps()` | 无 | `List[int]` | 扫描在线泵，返回地址列表 |
| `set_pump_rpm(addr: int, rpm: int)` | 泵地址, 转速 | `bool` | 设置泵转速 |
| `get_pump_status(addr: int)` | 泵地址 | `dict` | 获取泵状态 {running, rpm, direction} |

### 1.3 帧发送/响应

| 接口方法 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `send_frame(frame: bytes)` | RS485帧数据 | `bool` | 发送原始帧 |
| `register_callback(addr: int, callback: Callable)` | 泵地址, 回调函数 | `None` | 注册响应回调 |
| `dispatch_frame(frame: bytes)` | 接收到的帧 | `None` | 路由帧到对应设备 |

---

## 2. 电化学仪接口 (CHIWrapper)

位置: `src/services/chi_wrapper.py`

### 2.1 连接管理

| 接口方法 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `connect()` | 无 | `bool` | 连接电化学仪 |
| `disconnect()` | 无 | `None` | 断开连接 |
| `is_connected()` | 无 | `bool` | 检查连接状态 |

### 2.2 电化学技术执行

| 接口方法 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `run_cv(params: CVParams)` | CV参数对象 | `bool` | 执行循环伏安法 |
| `run_lsv(params: LSVParams)` | LSV参数对象 | `bool` | 执行线性扫描伏安法 |
| `run_it(params: ITParams)` | i-t参数对象 | `bool` | 执行计时电流法 |
| `stop()` | 无 | `bool` | 停止当前实验 |

#### CVParams 结构
```python
class CVParams:
    e0: float           # 初始电位 (V)
    eh: float           # 上限电位 (V)
    el: float           # 下限电位 (V)
    ef: float           # 终止电位 (V)
    scan_rate: float    # 扫描速率 (V/s)
    seg_num: int        # 扫描段数
    quiet_time_s: float # 静置时间 (s)
    sensitivity: float  # 灵敏度 (V)
    autosensitivity: bool
    sample_interval: float  # 采样间隔 (mV)
```

#### LSVParams 结构
```python
class LSVParams:
    e0: float           # 初始电位 (V)
    ef: float           # 终止电位 (V)
    scan_rate: float    # 扫描速率 (V/s)
    quiet_time_s: float # 静置时间 (s)
    sensitivity: float
    sample_interval: float
```

#### ITParams 结构
```python
class ITParams:
    e0: float           # 恒定电位 (V)
    run_time_s: float   # 运行时间 (s)
    quiet_time_s: float # 静置时间 (s)
    sensitivity: float
    sample_interval: float
```

### 2.3 数据获取

| 接口方法 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `get_data()` | 无 | `ECData` | 获取实验数据 |
| `export_data(path: str, format: str)` | 路径, 格式("csv"/"txt") | `bool` | 导出数据 |

### 2.4 OCPT 检测回调

| 信号/回调 | 参数 | 说明 |
|----------|------|------|
| `on_ocpt_triggered(current_uA: float)` | 检测到的电流值 | OCPT触发时回调 |

---

## 3. 实验运行引擎 (ExperimentRunner)

位置: `src/engine/runner.py`

### 3.1 实验控制

| 接口方法 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `run_experiment(exp: Experiment)` | 实验对象 | `None` | 开始运行实验 |
| `stop()` | 无 | `None` | 停止实验 |
| `pause()` | 无 | `None` | 暂停实验 |
| `resume()` | 无 | `None` | 恢复实验 |

### 3.2 信号 (Qt Signals)

| 信号名 | 参数 | 说明 |
|-------|------|------|
| `step_started` | `(int, str)` - (步骤索引, 步骤ID) | 步骤开始 |
| `step_finished` | `(int, str, bool)` - (索引, ID, 是否成功) | 步骤完成 |
| `log_message` | `str` | 日志消息 |
| `experiment_finished` | `bool` | 实验完成 (是否成功) |

---

## 4. 步骤类型与参数

位置: `src/models.py`

### 4.1 ProgramStepType 枚举

```python
class ProgramStepType(Enum):
    TRANSFER = "transfer"     # 移液
    PREP_SOL = "prep_sol"     # 配液
    FLUSH = "flush"           # 冲洗
    EChem = "echem"           # 电化学
    BLANK = "blank"           # 空白/等待
    EVACUATE = "evacuate"     # 排空
```

### 4.2 各步骤类型参数

#### TRANSFER (移液)
| 参数 | 类型 | 说明 |
|-----|------|------|
| `pump_address` | int | 泵地址 (1-12) |
| `pump_direction` | str | 方向 ("FWD"/"REV") |
| `pump_rpm` | int | 转速 |
| `transfer_duration` | float | 持续时间 |
| `transfer_duration_unit` | str | 单位 ("ms"/"s"/"min"/"hr"/"cycle") |

#### PREP_SOL (配液)
| 参数 | 类型 | 说明 |
|-----|------|------|
| `prep_sol_params.total_volume_ul` | float | 总体积 (μL, UI显示为mL) |
| `prep_sol_params.target_concentration` | float | 目标浓度 (mol/L) |
| `prep_sol_params.injection_order` | List[str] | 注液顺序 |
| `prep_sol_params.is_solvent` | bool | 是否为溶剂 |

#### FLUSH (冲洗)
| 参数 | 类型 | 说明 |
|-----|------|------|
| `pump_address` | int | 泵地址 |
| `pump_direction` | str | 方向 |
| `flush_rpm` | int | 转速 |
| `flush_cycle_duration_s` | float | 循环时长 (s) |
| `flush_cycles` | int | 循环次数 |

#### EVACUATE (排空)
| 参数 | 类型 | 说明 |
|-----|------|------|
| `pump_address` | int | Outlet泵地址 |
| `pump_direction` | str | 方向 |
| `pump_rpm` | int | 转速 |
| `transfer_duration` | float | 持续时间 |
| `transfer_duration_unit` | str | 单位 |
| `flush_cycles` | int | 循环次数 |

#### EChem (电化学)
| 参数 | 类型 | 说明 |
|-----|------|------|
| `ec_settings.technique` | ECTechnique | CV/LSV/I_T |
| `ec_settings.e0` | float | 初始电位 (V) |
| `ec_settings.eh` | float | 上限电位 (V) |
| `ec_settings.el` | float | 下限电位 (V) |
| `ec_settings.ef` | float | 终止电位 (V) |
| `ec_settings.scan_rate` | float | 扫描速率 (V/s) |
| `ec_settings.seg_num` | int | 扫描段数 |
| `ec_settings.quiet_time_s` | float | 静置时间 (s) |
| `ec_settings.run_time_s` | float | 运行时间 (s, i-t用) |
| `ec_settings.autosensitivity` | bool | 自动灵敏度 |
| `ec_settings.ocpt_enabled` | bool | 启用OCPT检测 |
| `ec_settings.ocpt_threshold_uA` | float | 阈值电流 (μA) |
| `ec_settings.ocpt_duration_s` | float | 持续时间 (s) |
| `ec_settings.ocpt_action` | OCPTAction | 触发动作 |

#### BLANK (空白)
| 参数 | 类型 | 说明 |
|-----|------|------|
| `duration_s` | float | 持续时间 (s) |
| `notes` | str | 备注 |

---

## 5. 配置数据结构

位置: `src/models.py`

### 5.1 SystemConfig

```python
class SystemConfig:
    rs485_port: str             # RS485端口
    rs485_baudrate: int         # 波特率
    chi_dll_path: str           # CHI DLL路径
    dilution_channels: List[DilutionChannel]  # 配液通道
    flush_channels: List[FlushChannel]        # 冲洗通道
    pumps: List[PumpConfig]                   # 泵配置
```

### 5.2 DilutionChannel (配液通道)

```python
class DilutionChannel:
    channel_id: int             # 通道号 (自动编号1,2,3...)
    solution_name: str          # 溶液名称
    stock_concentration: float  # 原浓度 (mol/L)
    pump_address: int           # 泵地址 (1-12)
    pump_direction: str         # 方向 ("FWD"/"REV")
    default_rpm: int            # 默认转速
    calibration_factor: float   # 校准系数
```

### 5.3 FlushChannel (冲洗通道)

```python
class FlushChannel:
    channel_id: int             # 通道号 (自动编号)
    work_type: str              # 工作类型 ("Inlet"/"Transfer"/"Outlet")
    pump_address: int           # 泵地址
    pump_direction: str         # 方向
    default_rpm: int            # 默认转速
    cycle_duration_s: float     # 循环时长
```

---

## 6. UI 调用后端的位置标记

以下是 UI 代码中调用后端接口的关键位置，用 `=== 后端接口 ===` 注释标记：

### 6.1 手动控制 (manual_control.py)

```python
# PumpControlWidget._on_run()
success = self.rs485.start_pump(self.pump_address, direction, rpm)

# PumpControlWidget._on_stop()
success = self.rs485.stop_pump(self.pump_address)

# ManualControlDialog._on_stop_all()
self.rs485.stop_all()
```

### 6.2 配置对话框 (config_dialog.py)

```python
# ConfigDialog._on_connect()
success = self.rs485.open_port(port, baudrate)

# ConfigDialog._on_scan()
addrs = self.rs485.scan_pumps()
```

### 6.3 配制溶液 (prep_solution.py)

```python
# PrepSolutionWorker.run()
self.rs485.start_pump(ch.pump_address, ch.direction, ch.default_rpm)
# 计算注入时间（基于校准参数）
time.sleep(inject_time)
self.rs485.stop_pump(ch.pump_address)
```

### 6.4 程序编辑器 (program_editor.py)

后端接口通过 ExperimentRunner 间接调用：
- 移液: `RS485Wrapper.start_pump/stop_pump`
- 配液: 多泵协调配液
- 冲洗: `RS485Wrapper.start_pump`
- 电化学: `CHIWrapper.run_cv/lsv/it`
- 排空: `RS485Wrapper.start_pump` (Outlet泵)

### 6.5 主窗口 (main_window.py)

```python
# MainWindow._on_run_single()
self.runner.run_experiment(self.single_experiment)

# MainWindow._on_stop()
self.runner.stop()
```

---

## 7. 数据流示意

```
UI Layer                    Engine Layer              Hardware Layer
---------                   ------------              --------------
MainWindow                  ExperimentRunner          RS485Wrapper
  │                              │                         │
  ├─ run_experiment() ──────────>│                         │
  │                              │                         │
  │                        for step in steps:              │
  │                              │                         │
  │                        ├─ TRANSFER ──────────────────>│ start_pump()
  │                        │                               │ stop_pump()
  │                        │                               │
  │                        ├─ PREP_SOL ──────────────────>│ (多泵协调)
  │                        │                               │
  │                        ├─ FLUSH ─────────────────────>│ start_pump()
  │                        │                               │
  │                        ├─ EVACUATE ──────────────────>│ start_pump() (Outlet)
  │                        │                               │
  │                        └─ EChem ─────────────────────>│ CHIWrapper.run_*()
  │                                                        │
  │<──── step_started, step_finished, log_message ────────│
```

---

## 8. 组合实验编辑器接口

位置: `src/dialogs/combo_exp_editor.py`

### 8.1 ComboExpEditorDialog

组合实验编辑器 - 紧凑版，采用单一表格显示所有步骤的所有变量参数。

#### 设计特点
- **左侧**: 步骤列表（只读），显示步骤序号、类型、简短描述
- **右侧**: 参数表格，每行一个变量（步骤、变量名、初值、终值、间隔）
- **底部**: 组合预览和保存按钮
- **字体**: 8pt 紧凑字体，一次显示所有变量

#### 信号

```python
combo_saved = Signal(list)  # 组合实验参数列表 [dict, dict, ...]
```

#### 构造函数

```python
def __init__(self, experiment: Experiment, config: SystemConfig = None, parent=None):
    """
    创建组合实验编辑器
    
    Args:
        experiment: 单次实验模板
        config: 系统配置（包含配液通道信息）
        parent: 父窗口
    """
```

### 8.2 参数表格格式

表格每行显示一个可调参数：

| 列 | 说明 | 是否可编辑 |
|----|------|-----------|
| 步骤 | 格式: `{序号:02d}:{类型}` 如 "01:配液" | 只读 |
| 变量 | 参数名称，配液显示 `{溶液名}/{参数名}` | 只读 |
| 初值 | 当前值，保留2位小数 | 只读 |
| 终值 | 扫描终止值 | 可编辑 (QDoubleSpinBox) |
| 间隔 | 扫描步长 | 可编辑 (QDoubleSpinBox) |

### 8.3 各步骤类型的可扫描参数

#### BLANK (空白)
| 参数名 | 说明 |
|--------|------|
| 持续时间(s) | 空白等待时间 |

#### FLUSH (冲洗)
| 参数名 | 说明 |
|--------|------|
| 持续时间(s) | 每次冲洗时长 |
| 循环次数 | 冲洗循环次数 |

#### EVACUATE (排空)
| 参数名 | 说明 |
|--------|------|
| 持续时间(s) | 排空时长 |
| 循环次数 | 排空循环次数 |

#### TRANSFER (移液)
| 参数名 | 说明 |
|--------|------|
| 持续时间(s) | 移液时长 |
| 转速(RPM) | 泵转速 |

#### PREP_SOL (配液)
| 参数名 | 说明 |
|--------|------|
| {溶液名}/浓度(M) | 各溶液目标浓度 (每个配液通道一行) |
| 配液/总体积(mL) | 总配液体积 |

#### EChem (电化学)
根据技术类型显示不同参数：

**CV (循环伏安法)**
| 参数名 | 说明 |
|--------|------|
| 静置时间(s) | 测量前静置 |
| E0(V) | 初始电位 |
| EH(V) | 上限电位 |
| EL(V) | 下限电位 |
| EF(V) | 终止电位 |
| 扫速(V/s) | 扫描速率 |

**LSV (线性扫描伏安法)**
| 参数名 | 说明 |
|--------|------|
| 静置时间(s) | 测量前静置 |
| E0(V) | 初始电位 |
| EF(V) | 终止电位 |
| 扫速(V/s) | 扫描速率 |

**i-t (计时电流法)**
| 参数名 | 说明 |
|--------|------|
| 静置时间(s) | 测量前静置 |
| E0(V) | 工作电位 |
| 运行时间(s) | 测量时长 |

### 8.4 组合参数输出格式

`combo_saved` 信号发射的数据格式：

```python
# 输出: List[dict]
# 每个 dict 包含一组参数值，key 格式为 "step_{index}_{param_name}"
[
    {"step_0_E0(V)": 0.00, "step_0_EH(V)": 0.80, "step_1_浓度(M)": 0.01},
    {"step_0_E0(V)": 0.10, "step_0_EH(V)": 0.80, "step_1_浓度(M)": 0.01},
    {"step_0_E0(V)": 0.20, "step_0_EH(V)": 0.80, "step_1_浓度(M)": 0.01},
    # ... 所有组合
]
```

对于配液溶液，key 格式为 `"step_{index}_{solution_type}_{param_name}"`

### 8.5 后端执行接口

```python
class ExperimentRunner:
    # 新增信号
    combo_progress = Signal(int, int, dict)  # (当前次数, 总次数, 当前变量值)
    
    def run_combo_experiment(self, combo_params: List[dict], base_experiment: Experiment):
        """
        执行组合实验
        
        Args:
            combo_params: 组合参数列表，由 combo_saved 信号提供
            base_experiment: 基础实验模板
        """
        total_runs = len(combo_params)
        
        for run_idx, params in enumerate(combo_params):
            # 1. 应用当前参数值到实验副本
            current_exp = self._apply_params(base_experiment, params)
            
            # 2. 发送进度信号
            self.combo_progress.emit(run_idx + 1, total_runs, params)
            
            # 3. 执行当前实验
            self.run_experiment(current_exp)
            
            # 4. 检查是否需要中止
            if self._stop_requested:
                break
```

---


## 9. 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| 1.0 | 2026-01-31 | 初始版本 |
| 1.1 | 2026-01-31 | 添加组合实验编辑器接口文档 |
| 1.2 | 2026-01-31 | 重构组合实验编辑器为紧凑版，单表格显示所有参数 |

---

**注意**: 此文档为 UI 与后端对接的接口约定，后端开发时请严格按照接口定义实现。接口变更需同步更新此文档。
