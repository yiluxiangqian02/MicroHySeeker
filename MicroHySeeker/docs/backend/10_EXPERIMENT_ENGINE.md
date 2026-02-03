# 10 - ExperimentEngine 模块规范

> **文件路径**: `src/echem_sdl/core/experiment_engine.py`  
> **优先级**: P0 (核心模块)  
> **依赖**: `prog_step.py`, `exp_program.py`, `lib_context.py`, `hardware/*`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\Experiment.cs`

---

## 一、模块职责

ExperimentEngine 是实验执行引擎，负责：
1. 加载和管理实验程序（ExpProgram）
2. 驱动实验生命周期（准备→启动→执行→完成）
3. 按步骤调度硬件操作
4. 管理组合实验的参数迭代
5. 发出状态变更事件供 UI 订阅
6. 处理暂停/恢复/中止

**核心设计**: 状态机 + 定时器驱动

---

## 二、状态机设计

### 2.1 引擎状态

```python
from enum import Enum

class EngineState(Enum):
    """引擎状态"""
    IDLE = "idle"              # 空闲
    LOADING = "loading"        # 加载程序中
    READY = "ready"            # 已就绪
    RUNNING = "running"        # 运行中
    STEP_EXECUTING = "step_executing"  # 步骤执行中
    PAUSED = "paused"          # 已暂停
    STOPPING = "stopping"      # 停止中
    COMPLETED = "completed"    # 已完成
    ERROR = "error"            # 错误
```

### 2.2 状态转移图

```
                    load_program()
     IDLE ─────────────────────────► LOADING
       ▲                                 │
       │                                 │ 成功
       │                                 ▼
       │                              READY
       │                                 │
       │                                 │ start()
       │                                 ▼
       │     ┌───────────────────── RUNNING ◄─────────────┐
       │     │                          │                 │
       │     │ pause()                  │ tick()          │ resume()
       │     ▼                          ▼                 │
       │  PAUSED ──────────────► STEP_EXECUTING ──────────┘
       │     │                          │
       │     │ stop()                   │ step完成
       │     ▼                          ▼
       │  STOPPING             advance_step()
       │     │                          │
       │     │               ┌──────────┴──────────┐
       │     │               │                     │
       │     │          有下一步              无下一步
       │     │               │                     │
       │     │               ▼                     ▼
       │     │           RUNNING              COMPLETED
       │     │                                     │
       └─────┴─────────────────────────────────────┘
                          reset()
```

---

## 三、类设计

### 3.1 主类定义

```python
from typing import Optional, Callable, List
from threading import RLock
import time

class ExperimentEngine:
    """实验执行引擎
    
    驱动实验程序执行，协调硬件操作，管理组合实验迭代。
    
    Attributes:
        state: 当前引擎状态
        program: 当前加载的实验程序
        current_step_index: 当前步骤索引
        current_combo_index: 当前组合索引
        elapsed_time: 实验已运行时间（秒）
        
    Example:
        >>> engine = ExperimentEngine(context)
        >>> engine.load_program(program)
        >>> engine.start()
        >>> while engine.is_running:
        ...     print(f"Step {engine.current_step_index}, Progress: {engine.progress}")
        ...     time.sleep(1)
    """
```

### 3.2 构造函数

```python
def __init__(
    self,
    context: "LibContext",
    tick_interval: float = 1.0
) -> None:
    """初始化实验引擎
    
    Args:
        context: 全局上下文（包含硬件和服务实例）
        tick_interval: 心跳间隔（秒）
    """
```

### 3.3 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `state` | `EngineState` | 当前状态 |
| `program` | `Optional[ExpProgram]` | 实验程序 |
| `current_step_index` | `int` | 当前步骤索引 |
| `current_step` | `Optional[ProgStep]` | 当前步骤 |
| `current_combo_index` | `int` | 当前组合索引 |
| `is_running` | `bool` | 是否运行中 |
| `is_paused` | `bool` | 是否暂停 |
| `elapsed_time` | `float` | 已运行时间（秒） |
| `step_elapsed_time` | `float` | 当前步骤已运行时间 |
| `progress` | `float` | 总进度 0-1 |
| `step_progress` | `float` | 步骤进度 0-1 |

### 3.4 公开方法

#### load_program()
```python
def load_program(self, program: "ExpProgram") -> bool:
    """加载实验程序
    
    Args:
        program: 实验程序
        
    Returns:
        bool: 加载是否成功
        
    Raises:
        ValueError: 程序无效
    """
```

#### prepare_steps()
```python
def prepare_steps(self) -> bool:
    """准备步骤（预计算参数）
    
    Returns:
        bool: 准备是否成功
    """
```

#### start()
```python
def start(self, combo_mode: bool = False) -> bool:
    """启动实验
    
    Args:
        combo_mode: 是否启用组合实验模式
        
    Returns:
        bool: 是否成功启动
    """
```

#### stop()
```python
def stop(self) -> bool:
    """停止实验
    
    Returns:
        bool: 是否成功停止
    """
```

#### pause() / resume()
```python
def pause(self) -> bool:
    """暂停实验"""

def resume(self) -> bool:
    """恢复实验"""
```

#### reset()
```python
def reset(self) -> None:
    """重置引擎状态"""
```

#### tick()
```python
def tick(self) -> None:
    """心跳函数（由定时器调用）
    
    更新时间计数，检查步骤状态，推进步骤。
    """
```

---

## 四、步骤执行

### 4.1 执行分发

```python
def _execute_step(self, step: "ProgStep") -> None:
    """执行单个步骤"""
    self.state = EngineState.STEP_EXECUTING
    self._step_start_time = time.time()
    
    step_type = step.step_type
    
    if step_type == StepType.PREP_SOL:
        self._execute_prep_sol(step)
    elif step_type == StepType.TRANSFER:
        self._execute_transfer(step)
    elif step_type == StepType.FLUSH:
        self._execute_flush(step)
    elif step_type == StepType.ECHEM:
        self._execute_echem(step)
    elif step_type == StepType.BLANK:
        self._execute_blank(step)
    elif step_type == StepType.EVACUATE:
        self._execute_evacuate(step)
    else:
        self._logger.warning(f"未知步骤类型: {step_type}")
```

### 4.2 配液步骤

```python
def _execute_prep_sol(self, step: "ProgStep") -> None:
    """执行配液步骤"""
    prep_config = step.prep_sol_config
    total_volume = prep_config.total_volume_ul
    
    # 获取配液顺序
    channels = prep_config.injection_order
    
    for channel_id in channels:
        diluter = self._context.pump_manager.get_diluter_by_name(channel_id)
        if diluter is None:
            self._logger.warning(f"未找到通道: {channel_id}")
            continue
        
        # 计算注液量并准备
        target_conc = prep_config.get_concentration(channel_id)
        diluter.prepare(
            target_conc=target_conc,
            total_volume_ul=total_volume,
            is_solvent=(target_conc == 0)
        )
        
        # 注液
        diluter.infuse()
        
        # 等待完成
        while diluter.is_infusing:
            if self._stop_requested:
                diluter.stop()
                return
            time.sleep(0.1)
        
        diluter.reset()
```

### 4.3 电化学步骤

```python
def _execute_echem(self, step: "ProgStep") -> None:
    """执行电化学步骤"""
    ec_config = step.ec_config
    chi = self._context.chi
    
    if chi is None:
        self._logger.error("CHI 仪器未连接")
        return
    
    # 设置参数
    params = ECParameters(
        technique=ec_config.technique,
        e_init=ec_config.e_init,
        e_high=ec_config.e_high,
        e_low=ec_config.e_low,
        e_final=ec_config.e_final,
        scan_rate=ec_config.scan_rate,
        segments=ec_config.segments,
        quiet_time=ec_config.quiet_time,
        run_time=ec_config.run_time,
    )
    
    chi.set_parameters(params)
    
    # 设置数据回调
    chi.on_data(lambda p: self._on_echem_data(p))
    
    # 运行
    chi.run()
    
    # 等待完成
    while chi.is_running:
        if self._stop_requested:
            chi.stop()
            return
        time.sleep(0.1)
```

### 4.4 冲洗步骤

```python
def _execute_flush(self, step: "ProgStep") -> None:
    """执行冲洗步骤"""
    flush_config = step.flush_config
    flusher = self._context.flusher
    
    if flusher is None:
        self._logger.error("Flusher 未配置")
        return
    
    flusher.set_cycles(flush_config.cycles)
    flusher.start()
    
    # 等待完成
    while flusher.is_running:
        if self._stop_requested:
            flusher.stop()
            return
        time.sleep(0.1)
```

---

## 五、组合实验

### 5.1 组合模式启动

```python
def start(self, combo_mode: bool = False) -> bool:
    """启动实验"""
    if self.state not in [EngineState.READY, EngineState.IDLE]:
        return False
    
    self._combo_mode = combo_mode
    self._stop_requested = False
    
    if combo_mode:
        # 生成组合参数矩阵
        self.program.fill_param_matrix()
        self._total_combos = self.program.combo_count
        self.current_combo_index = 0
        
        # 加载第一组参数
        self.program.load_param_values(0)
    
    self.state = EngineState.RUNNING
    self.current_step_index = 0
    self._start_time = time.time()
    
    self._emit_event("experiment_started")
    self._execute_step(self.program.steps[0])
    
    return True
```

### 5.2 组合推进

```python
def _advance_combo(self) -> bool:
    """推进到下一个组合
    
    Returns:
        bool: 是否有下一个组合
    """
    if not self._combo_mode:
        return False
    
    next_index = self.current_combo_index + 1
    
    if next_index >= self._total_combos:
        return False
    
    self.current_combo_index = next_index
    self.program.load_param_values(next_index)
    
    self._emit_event("combo_advanced", {
        "index": next_index,
        "total": self._total_combos,
        "params": self.program.get_current_params()
    })
    
    return True
```

### 5.3 步骤推进

```python
def _advance_step(self) -> None:
    """推进到下一步骤"""
    self._emit_event("step_completed", {
        "index": self.current_step_index,
        "step": self.current_step
    })
    
    next_index = self.current_step_index + 1
    
    if next_index >= len(self.program.steps):
        # 当前组合完成
        if self._combo_mode and self._advance_combo():
            # 重置步骤索引，开始新组合
            self.current_step_index = 0
            self._execute_step(self.program.steps[0])
        else:
            # 全部完成
            self._complete()
    else:
        # 执行下一步
        self.current_step_index = next_index
        self._execute_step(self.program.steps[next_index])
```

---

## 六、事件系统

### 6.1 事件类型

```python
from typing import TypeAlias, Dict, Any

EventData: TypeAlias = Dict[str, Any]
EventCallback: TypeAlias = Callable[[str, EventData], None]

# 事件类型常量
EVENT_EXPERIMENT_STARTED = "experiment_started"
EVENT_EXPERIMENT_COMPLETED = "experiment_completed"
EVENT_EXPERIMENT_STOPPED = "experiment_stopped"
EVENT_EXPERIMENT_ERROR = "experiment_error"
EVENT_STEP_STARTED = "step_started"
EVENT_STEP_COMPLETED = "step_completed"
EVENT_STEP_PROGRESS = "step_progress"
EVENT_COMBO_ADVANCED = "combo_advanced"
EVENT_ECHEM_DATA = "echem_data"
```

### 6.2 事件订阅

```python
def on_event(self, callback: EventCallback) -> None:
    """订阅所有事件"""
    self._event_callbacks.append(callback)

def on(self, event_type: str, callback: Callable) -> None:
    """订阅特定事件"""
    if event_type not in self._specific_callbacks:
        self._specific_callbacks[event_type] = []
    self._specific_callbacks[event_type].append(callback)

def _emit_event(self, event_type: str, data: EventData = None) -> None:
    """发出事件"""
    data = data or {}
    data["timestamp"] = time.time()
    data["state"] = self.state.value
    
    # 通用回调
    for cb in self._event_callbacks:
        try:
            cb(event_type, data)
        except Exception as e:
            self._logger.error(f"事件回调错误: {e}")
    
    # 特定回调
    for cb in self._specific_callbacks.get(event_type, []):
        try:
            cb(data)
        except Exception as e:
            self._logger.error(f"事件回调错误: {e}")
```

---

## 七、心跳与进度

### 7.1 心跳函数

```python
def tick(self) -> None:
    """心跳函数"""
    if self.state not in [EngineState.RUNNING, EngineState.STEP_EXECUTING]:
        return
    
    with self._lock:
        # 更新时间
        now = time.time()
        self.elapsed_time = now - self._start_time
        self.step_elapsed_time = now - self._step_start_time
        
        # 检查步骤状态
        if self._check_step_completed():
            self._advance_step()
        else:
            # 发送进度事件
            self._emit_event("step_progress", {
                "step_index": self.current_step_index,
                "step_progress": self.step_progress,
                "total_progress": self.progress
            })
```

### 7.2 进度计算

```python
@property
def progress(self) -> float:
    """计算总进度"""
    if not self.program or not self.program.steps:
        return 0.0
    
    total_steps = len(self.program.steps)
    
    if self._combo_mode:
        combo_progress = self.current_combo_index / self._total_combos
        step_progress = self.current_step_index / total_steps
        return combo_progress + step_progress / self._total_combos
    else:
        base = self.current_step_index / total_steps
        step_contrib = self.step_progress / total_steps
        return base + step_contrib

@property
def step_progress(self) -> float:
    """计算步骤进度"""
    if self.current_step is None:
        return 0.0
    
    duration = self.current_step.get_duration()
    if duration <= 0:
        return 0.0
    
    return min(1.0, self.step_elapsed_time / duration)
```

---

## 八、错误处理

### 8.1 异常类型

```python
class EngineError(Exception):
    """引擎错误基类"""
    pass

class ProgramInvalidError(EngineError):
    """程序无效"""
    pass

class StepExecutionError(EngineError):
    """步骤执行错误"""
    pass

class HardwareError(EngineError):
    """硬件错误"""
    pass
```

### 8.2 错误恢复

```python
def _handle_error(self, error: Exception) -> None:
    """处理错误"""
    self._logger.error(f"实验错误: {error}")
    
    # 紧急停止所有硬件
    self._context.pump_manager.stop_all()
    if self._context.chi:
        self._context.chi.stop()
    if self._context.flusher:
        self._context.flusher.stop()
    
    self.state = EngineState.ERROR
    self._emit_event("experiment_error", {"error": str(error)})
```

---

## 九、测试要求

### 9.1 单元测试

```python
# tests/test_experiment_engine.py

import pytest
import time
from unittest.mock import Mock, MagicMock
from echem_sdl.core.experiment_engine import ExperimentEngine, EngineState

class TestExperimentEngine:
    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.pump_manager = Mock()
        context.flusher = Mock()
        context.chi = Mock()
        context.logger = Mock()
        return context
    
    @pytest.fixture
    def mock_program(self):
        program = Mock()
        program.steps = [Mock(), Mock(), Mock()]
        for i, step in enumerate(program.steps):
            step.step_type = "blank"
            step.get_duration.return_value = 0.1
        return program
    
    @pytest.fixture
    def engine(self, mock_context):
        return ExperimentEngine(mock_context, tick_interval=0.1)
    
    def test_initial_state(self, engine):
        """测试初始状态"""
        assert engine.state == EngineState.IDLE
        assert engine.program is None
    
    def test_load_program(self, engine, mock_program):
        """测试加载程序"""
        result = engine.load_program(mock_program)
        assert result == True
        assert engine.state == EngineState.READY
        assert engine.program == mock_program
    
    def test_start_stop(self, engine, mock_program):
        """测试启停"""
        engine.load_program(mock_program)
        
        result = engine.start()
        assert result == True
        assert engine.state in [EngineState.RUNNING, EngineState.STEP_EXECUTING]
        
        engine.stop()
        assert engine.state in [EngineState.IDLE, EngineState.STOPPING]
    
    def test_pause_resume(self, engine, mock_program):
        """测试暂停恢复"""
        engine.load_program(mock_program)
        engine.start()
        
        engine.pause()
        assert engine.state == EngineState.PAUSED
        
        engine.resume()
        assert engine.is_running
    
    def test_step_progression(self, engine, mock_program):
        """测试步骤推进"""
        engine.load_program(mock_program)
        engine.start()
        
        # 等待几个步骤
        time.sleep(0.5)
        
        assert engine.current_step_index > 0
    
    def test_event_emission(self, engine, mock_program):
        """测试事件发出"""
        events = []
        engine.on_event(lambda e, d: events.append(e))
        
        engine.load_program(mock_program)
        engine.start()
        time.sleep(0.3)
        engine.stop()
        
        assert "experiment_started" in events

class TestComboMode:
    def test_combo_progression(self, engine, mock_program):
        """测试组合推进"""
        mock_program.fill_param_matrix = Mock()
        mock_program.combo_count = 3
        mock_program.load_param_values = Mock()
        
        engine.load_program(mock_program)
        engine.start(combo_mode=True)
        
        # 验证组合模式启动
        assert engine._combo_mode == True
        mock_program.fill_param_matrix.assert_called_once()
```

---

## 十、使用示例

### 10.1 基本使用

```python
from echem_sdl.core.experiment_engine import ExperimentEngine
from echem_sdl.core.exp_program import ExpProgram
from echem_sdl.lib_context import LibContext

# 初始化上下文
context = LibContext(...)

# 创建引擎
engine = ExperimentEngine(context, tick_interval=1.0)

# 加载程序
program = ExpProgram.load_from_json("experiment.json")
engine.load_program(program)

# 订阅事件
def on_event(event_type, data):
    print(f"[{event_type}] {data}")

engine.on_event(on_event)

# 启动实验
engine.start()

# 监控进度
while engine.is_running:
    print(f"Progress: {engine.progress * 100:.1f}%")
    time.sleep(1)

print("实验完成")
```

### 10.2 组合实验

```python
# 启用组合模式
engine.start(combo_mode=True)

# 组合事件监听
engine.on("combo_advanced", lambda d: print(f"组合 {d['index']}/{d['total']}"))
```

---

## 十一、验收标准

- [ ] 类与接口按规范实现
- [ ] 状态机转换正确
- [ ] 所有步骤类型执行正确
- [ ] 组合实验迭代正确
- [ ] 事件系统正常工作
- [ ] 暂停/恢复功能正常
- [ ] 紧急停止功能正常
- [ ] 进度计算准确
- [ ] 错误处理健壮
- [ ] 线程安全（锁保护）
- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] docstring 规范
