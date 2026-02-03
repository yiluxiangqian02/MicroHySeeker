# 04 - Flusher 模块规范

> **文件路径**: `src/echem_sdl/hardware/flusher.py`  
> **优先级**: P1 (硬件驱动)  
> **依赖**: `rs485_driver.py`, `lib_context.py`, `pump_manager.py`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\Flusher.cs`

---

## ⚠️ 重要架构变更

> **与原 C# 设计的差异：统一泵管理**
> 
> 在 Python 实现中，**冲洗泵和配液泵统一通过 PumpManager 管理**：
> - 所有泵（1-12号）通过同一个 RS485 COM 口通信
> - `FlushChannel` 仅存储 `pump_address`（泵地址）和 `work_type`（工作类型）
> - 实际泵控制需通过 `PumpManager.get_pump(address)` 获取泵实例
> - 配置界面使用统一的泵地址下拉框（1-12）
> 
> 请参考 [05_PUMP_MANAGER.md](05_PUMP_MANAGER.md) 了解统一泵管理架构。
> 
> **前端当前实现**（见 `src/models.py`）：
> ```python
> @dataclass
> class FlushChannel:
>     pump_address: int  # 泵地址 (1-12)
>     work_type: FlushWorkType  # Inlet / Transfer / Outlet
>     ...
> ```

---

## 一、模块职责

Flusher（冲洗器）负责管理三泵冲洗系统，执行：
1. **Inlet (进水泵)**: 将溶液抽入反应池
2. **Outlet (出水泵)**: 将溶液从反应池排出
3. **Transfer (移液泵)**: 在两个池之间转移溶液

**核心功能**:
- 执行完整的冲洗循环（多周期）
- 执行排空操作（evacuate）
- 执行单次移液操作（transfer）
- 管理冲洗阶段状态机

---

## 二、类设计

### 2.1 枚举定义

```python
from enum import Enum

class FlusherPhase(Enum):
    """冲洗阶段"""
    IDLE = "idle"           # 空闲
    INLET = "inlet"         # 进水阶段
    TRANSFER = "transfer"   # 移液阶段
    OUTLET = "outlet"       # 出水阶段
    COMPLETED = "completed" # 完成

class FlusherState(Enum):
    """冲洗器整体状态"""
    IDLE = "idle"
    RUNNING = "running"     # 冲洗中
    PAUSED = "paused"       # 暂停
    ERROR = "error"
```

### 2.2 配置类

```python
from dataclasses import dataclass

@dataclass
class FlusherPumpConfig:
    """单个冲洗泵配置"""
    address: int              # RS485 地址
    name: str                 # 泵名称
    rpm: int = 200            # 默认转速
    direction: str = "FWD"    # 默认方向
    duration_s: float = 10.0  # 默认运行时间（秒）

@dataclass
class FlusherConfig:
    """冲洗器完整配置"""
    inlet: FlusherPumpConfig      # 进水泵
    outlet: FlusherPumpConfig     # 出水泵
    transfer: FlusherPumpConfig   # 移液泵
    default_cycles: int = 3       # 默认冲洗循环数
```

### 2.3 主类定义

```python
class Flusher:
    """冲洗器控制器
    
    管理三泵（Inlet/Outlet/Transfer）的冲洗流程。
    
    Attributes:
        config: 冲洗器配置
        state: 当前状态
        phase: 当前阶段
        current_cycle: 当前循环数 (从1开始)
        total_cycles: 总循环数
        
    Example:
        >>> flusher = Flusher(config, rs485_driver)
        >>> flusher.set_cycles(3)
        >>> flusher.start()
        >>> while flusher.is_running:
        ...     print(f"Cycle {flusher.current_cycle}, Phase: {flusher.phase}")
        ...     time.sleep(1)
    """
```

### 2.4 构造函数

```python
def __init__(
    self,
    config: FlusherConfig,
    driver: "RS485Driver",
    logger: Optional["LoggerService"] = None
) -> None:
    """初始化 Flusher
    
    Args:
        config: 冲洗器配置
        driver: RS485 驱动实例
        logger: 日志服务
    """
```

### 2.5 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `config` | `FlusherConfig` | 配置参数 |
| `state` | `FlusherState` | 整体状态 |
| `phase` | `FlusherPhase` | 当前阶段 |
| `current_cycle` | `int` | 当前循环数 |
| `total_cycles` | `int` | 总循环数 |
| `is_running` | `bool` | 是否运行中（只读） |
| `progress` | `float` | 总进度 0-1（只读） |
| `phase_progress` | `float` | 阶段进度 0-1（只读） |

### 2.6 公开方法

#### set_cycles()
```python
def set_cycles(self, cycles: int) -> None:
    """设置冲洗循环数
    
    Args:
        cycles: 循环次数 (1-99)
    """
```

#### start()
```python
def start(self) -> bool:
    """开始冲洗
    
    Returns:
        bool: 是否成功启动
        
    Note:
        此方法非阻塞，冲洗在后台进行
    """
```

#### stop()
```python
def stop(self) -> bool:
    """停止冲洗
    
    Returns:
        bool: 是否成功停止
        
    Note:
        会立即停止所有泵
    """
```

#### pause() / resume()
```python
def pause(self) -> bool:
    """暂停冲洗"""

def resume(self) -> bool:
    """恢复冲洗"""
```

#### evacuate()
```python
def evacuate(
    self,
    duration_s: Optional[float] = None
) -> bool:
    """执行排空操作（仅 Outlet 泵）
    
    Args:
        duration_s: 排空时间，默认使用配置值
        
    Returns:
        bool: 是否成功启动
    """
```

#### transfer()
```python
def transfer(
    self,
    volume_ul: Optional[float] = None,
    duration_s: Optional[float] = None,
    forward: bool = True
) -> bool:
    """执行单次移液
    
    Args:
        volume_ul: 体积（与 duration_s 二选一）
        duration_s: 持续时间
        forward: 方向
        
    Returns:
        bool: 是否成功启动
    """
```

#### reset()
```python
def reset(self) -> None:
    """重置状态"""
```

---

## 三、冲洗流程

### 3.1 完整循环时序

```
每个循环:
┌──────────────┐
│ 1. INLET     │ ← 进水泵运行 duration_s 秒
├──────────────┤
│ 2. TRANSFER  │ ← 移液泵运行 duration_s 秒
├──────────────┤
│ 3. OUTLET    │ ← 出水泵运行 duration_s 秒
└──────────────┘
      ↓ 循环结束
  判断是否达到 total_cycles
      ↓
  是 → COMPLETED
  否 → 回到 1. INLET，cycle++
```

### 3.2 阶段状态机

```
        start()
IDLE ─────────────► INLET
  ▲                    │
  │                    │ inlet完成
  │                    ▼
  │               TRANSFER
  │                    │
  │                    │ transfer完成
  │                    ▼
  │                OUTLET
  │                    │
  │      ┌─────────────┼─────────────┐
  │      │             │             │
  │  stop()调用    cycle < total   cycle >= total
  │      │             │             │
  │      ▼             ▼             ▼
  └──── IDLE         INLET      COMPLETED
                   (cycle++)         │
                                     │ reset()
                                     ▼
                                   IDLE
```

---

## 四、内部实现

### 4.1 阶段执行器

```python
def _execute_phase(self, phase: FlusherPhase) -> None:
    """执行单个阶段"""
    pump_config = self._get_pump_config(phase)
    if pump_config is None:
        return
    
    self.phase = phase
    self._phase_start_time = time.time()
    
    # 启动泵
    self._driver.run_speed(
        addr=pump_config.address,
        rpm=pump_config.rpm,
        forward=(pump_config.direction == "FWD")
    )
    
    # 设置阶段完成定时器
    self._phase_timer = threading.Timer(
        pump_config.duration_s,
        self._on_phase_complete
    )
    self._phase_timer.start()

def _on_phase_complete(self) -> None:
    """阶段完成回调"""
    # 停止当前泵
    pump_config = self._get_pump_config(self.phase)
    self._driver.run_speed(addr=pump_config.address, rpm=0, forward=True)
    
    # 切换到下一阶段
    self._advance_phase()
```

### 4.2 阶段推进

```python
PHASE_SEQUENCE = [
    FlusherPhase.INLET,
    FlusherPhase.TRANSFER,
    FlusherPhase.OUTLET,
]

def _advance_phase(self) -> None:
    """推进到下一阶段"""
    current_idx = PHASE_SEQUENCE.index(self.phase)
    
    if current_idx < len(PHASE_SEQUENCE) - 1:
        # 切换到下一阶段
        next_phase = PHASE_SEQUENCE[current_idx + 1]
        self._execute_phase(next_phase)
    else:
        # 当前循环完成
        if self.current_cycle < self.total_cycles:
            self.current_cycle += 1
            self._execute_phase(PHASE_SEQUENCE[0])
        else:
            # 全部完成
            self.phase = FlusherPhase.COMPLETED
            self.state = FlusherState.IDLE
            self._on_complete()
```

### 4.3 进度计算

```python
@property
def progress(self) -> float:
    """计算总进度"""
    if self.total_cycles == 0:
        return 0.0
    
    phases_per_cycle = len(PHASE_SEQUENCE)
    total_phases = self.total_cycles * phases_per_cycle
    
    completed_cycles = self.current_cycle - 1
    completed_phases = completed_cycles * phases_per_cycle
    
    if self.phase in PHASE_SEQUENCE:
        current_phase_idx = PHASE_SEQUENCE.index(self.phase)
        completed_phases += current_phase_idx + self.phase_progress
    
    return completed_phases / total_phases

@property
def phase_progress(self) -> float:
    """计算阶段进度"""
    if not hasattr(self, '_phase_start_time'):
        return 0.0
    
    pump_config = self._get_pump_config(self.phase)
    if pump_config is None:
        return 0.0
    
    elapsed = time.time() - self._phase_start_time
    return min(1.0, elapsed / pump_config.duration_s)
```

---

## 五、事件回调

### 5.1 事件类型

```python
from typing import Callable, TypeAlias

# 事件回调类型
OnPhaseChange: TypeAlias = Callable[[FlusherPhase], None]
OnCycleComplete: TypeAlias = Callable[[int], None]  # 循环号
OnComplete: TypeAlias = Callable[[], None]
OnError: TypeAlias = Callable[[Exception], None]
```

### 5.2 注册回调

```python
def on_phase_change(self, callback: OnPhaseChange) -> None:
    """注册阶段变化回调"""
    self._phase_callbacks.append(callback)

def on_cycle_complete(self, callback: OnCycleComplete) -> None:
    """注册循环完成回调"""
    self._cycle_callbacks.append(callback)

def on_complete(self, callback: OnComplete) -> None:
    """注册全部完成回调"""
    self._complete_callbacks.append(callback)
```

---

## 六、线程安全

### 6.1 锁保护

```python
def __init__(self, ...):
    self._lock = threading.RLock()
    self._phase_timer: Optional[threading.Timer] = None

def start(self) -> bool:
    with self._lock:
        if self.state == FlusherState.RUNNING:
            return False
        self.state = FlusherState.RUNNING
        self.current_cycle = 1
        self._execute_phase(PHASE_SEQUENCE[0])
        return True

def stop(self) -> bool:
    with self._lock:
        if self._phase_timer:
            self._phase_timer.cancel()
        # 停止所有泵
        for pump in [self.config.inlet, self.config.outlet, self.config.transfer]:
            self._driver.run_speed(addr=pump.address, rpm=0, forward=True)
        self.state = FlusherState.IDLE
        self.phase = FlusherPhase.IDLE
        return True
```

---

## 七、错误处理

### 7.1 异常定义

```python
class FlusherError(Exception):
    """Flusher 错误基类"""
    pass

class PumpCommunicationError(FlusherError):
    """泵通信错误"""
    pass

class InvalidStateError(FlusherError):
    """状态无效"""
    pass
```

### 7.2 错误恢复

```python
def _handle_error(self, error: Exception) -> None:
    """处理错误"""
    self.state = FlusherState.ERROR
    self._logger.error(f"Flusher 错误: {error}")
    
    # 紧急停止所有泵
    for pump in [self.config.inlet, self.config.outlet, self.config.transfer]:
        try:
            self._driver.run_speed(addr=pump.address, rpm=0, forward=True)
        except:
            pass
    
    # 触发错误回调
    for cb in self._error_callbacks:
        cb(error)
```

---

## 八、测试要求

### 8.1 单元测试

```python
# tests/test_flusher.py

import pytest
import time
from unittest.mock import Mock
from echem_sdl.hardware.flusher import (
    Flusher, FlusherConfig, FlusherPumpConfig,
    FlusherState, FlusherPhase
)

class TestFlusher:
    @pytest.fixture
    def mock_driver(self):
        driver = Mock()
        driver.run_speed.return_value = True
        return driver
    
    @pytest.fixture
    def config(self):
        return FlusherConfig(
            inlet=FlusherPumpConfig(address=1, name="Inlet", duration_s=0.1),
            outlet=FlusherPumpConfig(address=2, name="Outlet", duration_s=0.1),
            transfer=FlusherPumpConfig(address=3, name="Transfer", duration_s=0.1),
            default_cycles=2
        )
    
    @pytest.fixture
    def flusher(self, config, mock_driver):
        return Flusher(config, mock_driver)
    
    def test_initial_state(self, flusher):
        """测试初始状态"""
        assert flusher.state == FlusherState.IDLE
        assert flusher.phase == FlusherPhase.IDLE
        assert flusher.current_cycle == 0
    
    def test_set_cycles(self, flusher):
        """测试设置循环数"""
        flusher.set_cycles(5)
        assert flusher.total_cycles == 5
    
    def test_start_stop(self, flusher, mock_driver):
        """测试启停"""
        flusher.set_cycles(1)
        assert flusher.start() == True
        assert flusher.state == FlusherState.RUNNING
        
        flusher.stop()
        assert flusher.state == FlusherState.IDLE
        # 验证停止命令发送
        assert mock_driver.run_speed.call_count >= 3
    
    def test_full_cycle(self, flusher, mock_driver):
        """测试完整循环"""
        flusher.set_cycles(1)
        flusher.start()
        
        # 等待完成（每阶段0.1秒，共3阶段）
        time.sleep(0.5)
        
        assert flusher.phase == FlusherPhase.COMPLETED
        assert flusher.current_cycle == 1
    
    def test_evacuate(self, flusher, mock_driver):
        """测试排空"""
        result = flusher.evacuate(duration_s=0.1)
        assert result == True
        mock_driver.run_speed.assert_called()
    
    def test_transfer(self, flusher, mock_driver):
        """测试移液"""
        result = flusher.transfer(duration_s=0.1, forward=True)
        assert result == True
    
    def test_progress(self, flusher):
        """测试进度计算"""
        flusher.set_cycles(2)
        flusher.start()
        
        # 初始进度接近0
        assert flusher.progress >= 0.0
        assert flusher.progress <= 1.0
        
        flusher.stop()

class TestFlusherCallbacks:
    def test_phase_change_callback(self, flusher):
        """测试阶段变化回调"""
        phases = []
        flusher.on_phase_change(lambda p: phases.append(p))
        
        flusher.set_cycles(1)
        flusher.start()
        time.sleep(0.5)
        
        assert FlusherPhase.INLET in phases
        assert FlusherPhase.TRANSFER in phases
        assert FlusherPhase.OUTLET in phases
```

---

## 九、使用示例

### 9.1 基本冲洗

```python
from echem_sdl.hardware.flusher import Flusher, FlusherConfig, FlusherPumpConfig
from echem_sdl.hardware.rs485_driver import RS485Driver

driver = RS485Driver(port='COM3', mock_mode=True)
driver.open()

config = FlusherConfig(
    inlet=FlusherPumpConfig(address=1, name="Inlet", rpm=200, duration_s=10),
    outlet=FlusherPumpConfig(address=2, name="Outlet", rpm=200, duration_s=10),
    transfer=FlusherPumpConfig(address=3, name="Transfer", rpm=150, duration_s=15),
    default_cycles=3
)

flusher = Flusher(config, driver)

# 设置并启动
flusher.set_cycles(3)
flusher.start()

# 监控进度
while flusher.is_running:
    print(f"Cycle {flusher.current_cycle}/{flusher.total_cycles}, "
          f"Phase: {flusher.phase.value}, "
          f"Progress: {flusher.progress * 100:.1f}%")
    time.sleep(1)

print("冲洗完成")
driver.close()
```

### 9.2 带回调的冲洗

```python
def on_phase(phase):
    print(f"进入阶段: {phase.value}")

def on_cycle(cycle):
    print(f"完成循环 {cycle}")

def on_complete():
    print("全部完成!")

flusher.on_phase_change(on_phase)
flusher.on_cycle_complete(on_cycle)
flusher.on_complete(on_complete)

flusher.set_cycles(3)
flusher.start()
```

---

## 十、前端对接指南

### 10.1 前端数据模型

**文件**: `src/models.py`

```python
@dataclass
class FlushChannel:
    pump_address: int       # 冲洗泵地址
    duration_s: float       # 冲洗时长（秒）
    flow_rate: int = 100    # 流速 (RPM)
    enabled: bool = True    # 是否启用
```

**后端需求**：Flusher类必须接受这些参数。

### 10.2 前端调用路径

**冲洗对话框** → **RS485Wrapper** → **Flusher**

```python
# 前端调用（src/dialogs/flusher_dialog.py）
def start_flush(self):
    wrapper.start_flush(channel_id=1, duration=10.0)

# RS485Wrapper（src/services/rs485_wrapper.py）
def configure_flush_channels(self, channels: List[FlushChannel]):
    for ch in channels:
        flusher = Flusher(
            address=ch.pump_address,
            pump_manager=self.ctx.pump_manager,
            logger=self.ctx.logger
        )
        self.flushers[ch.pump_address] = flusher

def start_flush(self, channel_id: int, duration: float) -> bool:
    flusher = self.flushers.get(channel_id)
    return flusher.start_flush(duration) if flusher else False
```

### 10.3 必须实现的前端接口

**RS485Wrapper需要添加的方法**：

```python
# src/services/rs485_wrapper.py

class RS485Wrapper:
    def configure_flush_channels(
        self,
        channels: List[FlushChannel]
    ) -> None:
        """配置冲洗通道"""
        ...
    
    def start_flush(
        self,
        channel_id: int,
        duration: float
    ) -> bool:
        """开始冲洗"""
        ...
    
    def stop_flush(self, channel_id: int) -> bool:
        """停止冲洗"""
        ...
    
    def get_flush_status(self, channel_id: int) -> dict:
        """获取冲洗状态"""
        ...
```

### 10.4 前端验证流程

**测试步骤**：
1. 启动UI: `python run_ui.py`
2. 点击"冲洗"按钮
3. 配置冲洗参数：
   - 泵地址: 1
   - 冲洗时长: 10秒
   - 流速: 100 RPM
4. 点击"开始冲洗"

**预期结果**：
- Mock模式下，控制台输出冲洗日志
- 倒计时显示
- 冲洗完成后自动停止

### 10.5 源项目参考

**C# 文件**: `D:\AI4S\eChemSDL\eChemSDL\Flusher.cs`

**重点参考**：
- 三阶段冲洗逻辑（Inlet/Transfer/Outlet）
- 计时控制
- 与泵通信方式

**关键差异**：
- Python使用PumpManager统一管理泵
- 简化为单阶段冲洗（可选）

---

## 十一、验收标准

- [ ] 类与接口按规范实现
- [ ] 三阶段（Inlet/Transfer/Outlet）执行正确
- [ ] 多循环执行正确
- [ ] 状态机转换正确
- [ ] 进度计算准确
- [ ] 事件回调正常触发
- [ ] 线程安全（锁保护）
- [ ] 紧急停止功能正常
- [ ] RS485Wrapper接口实现完整
- [ ] 前端"冲洗"功能正常工作
- [ ] Mock模式能模拟完整流程
- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] docstring 规范
