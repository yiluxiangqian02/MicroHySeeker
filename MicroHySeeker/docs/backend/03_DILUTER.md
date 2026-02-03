# 03 - Diluter 模块规范

> **文件路径**: `src/echem_sdl/hardware/diluter.py`  
> **优先级**: P1 (硬件驱动)  
> **依赖**: `rs485_driver.py`, `lib_context.py`, `pump_manager.py`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\Diluter.cs`

---

## ⚠️ 重要架构变更

> **与原 C# 设计的差异：统一泵管理**
> 
> 在 Python 实现中，**配液泵和冲洗泵统一通过 PumpManager 管理**：
> - 所有泵（1-12号）通过同一个 RS485 COM 口通信
> - `DilutionChannel` 和 `FlushChannel` 仅存储 `pump_address`（泵地址）
> - 实际泵控制需通过 `PumpManager.get_pump(address)` 获取泵实例
> - 配置界面使用统一的泵地址下拉框（1-12）
> 
> 请参考 [05_PUMP_MANAGER.md](05_PUMP_MANAGER.md) 了解统一泵管理架构。
> 
> **前端当前实现**（见 `src/models.py` 和 `src/dialogs/config_dialog.py`）：
> ```python
> @dataclass
> class DilutionChannel:
>     pump_address: int  # 泵地址 (1-12)，通过此地址从 PumpManager 获取泵
>     solution_name: str
>     ...
> ```

---

## 一、模块职责

Diluter（配液器）是单通道配液泵的控制器，负责：
1. 管理单个蠕动泵的运行状态
2. 计算目标浓度所需的注液量
3. 执行精确体积的注液操作
4. 跟踪注液进度和完成状态
5. 处理 RS485 响应帧

**核心概念**:
- 每个 Diluter 实例对应一个物理泵
- 通过 RS485 地址与泵通信
- 支持体积到分度的转换（基于标定因子）

---

## 二、类设计

### 2.1 类定义

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable
import threading
import time

class DiluterState(Enum):
    """Diluter 状态枚举"""
    IDLE = "idle"           # 空闲
    INFUSING = "infusing"   # 注液中
    COMPLETED = "completed" # 已完成
    ERROR = "error"         # 错误

@dataclass
class DiluterConfig:
    """Diluter 配置"""
    address: int                    # RS485 地址 (1-12)
    name: str                       # 溶液名称
    stock_concentration: float      # 储备浓度 (mol/L)
    ul_per_division: float = 0.1    # 每分度对应的微升数（标定因子）
    default_rpm: int = 120          # 默认转速
    default_direction: str = "FWD"  # 默认方向

class Diluter:
    """配液器驱动
    
    控制单通道蠕动泵进行精确体积注液。
    
    Attributes:
        config: 配置参数
        state: 当前状态
        target_volume_ul: 目标体积（微升）
        infused_volume_ul: 已注入体积（微升）
        
    Example:
        >>> diluter = Diluter(config, rs485_driver)
        >>> diluter.prepare(target_conc=0.1, total_volume=1000)
        >>> diluter.infuse()
        >>> while diluter.is_infusing:
        ...     time.sleep(0.1)
    """
```

### 2.2 构造函数

```python
def __init__(
    self,
    config: DiluterConfig,
    driver: "RS485Driver",
    logger: Optional["LoggerService"] = None
) -> None:
    """初始化 Diluter
    
    Args:
        config: 配液器配置
        driver: RS485 驱动实例
        logger: 日志服务
    """
```

### 2.3 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `config` | `DiluterConfig` | 配置参数 |
| `state` | `DiluterState` | 当前状态 |
| `target_volume_ul` | `float` | 目标体积（微升） |
| `infused_volume_ul` | `float` | 已注入体积（微升） |
| `is_infusing` | `bool` | 是否正在注液（只读） |
| `has_infused` | `bool` | 是否已完成注液（只读） |
| `progress` | `float` | 注液进度 0-1（只读） |
| `estimated_duration` | `float` | 预计持续时间（秒，只读） |

### 2.4 公开方法

#### prepare()
```python
def prepare(
    self,
    target_conc: float,
    total_volume_ul: float,
    is_solvent: bool = False
) -> float:
    """准备注液参数
    
    根据目标浓度计算需要注入的体积。
    
    Args:
        target_conc: 目标浓度 (mol/L)
        total_volume_ul: 总体积 (μL)
        is_solvent: 是否为溶剂（溶剂用于补齐体积）
        
    Returns:
        float: 需要注入的体积 (μL)
        
    Formula:
        V_stock = (target_conc / stock_conc) * total_volume
        V_solvent = total_volume - sum(V_stock_i)
    """
```

#### infuse()
```python
def infuse(
    self,
    rpm: Optional[int] = None,
    forward: bool = True
) -> bool:
    """开始注液
    
    Args:
        rpm: 转速，默认使用配置值
        forward: 方向，True为正转
        
    Returns:
        bool: 是否成功启动
        
    Note:
        此方法非阻塞，注液在后台进行
        使用 is_infusing 属性检查状态
    """
```

#### stop()
```python
def stop(self) -> bool:
    """停止注液
    
    Returns:
        bool: 是否成功停止
    """
```

#### reset()
```python
def reset(self) -> None:
    """重置状态
    
    清除目标体积、已注入体积，状态归零
    """
```

#### handle_response()
```python
def handle_response(self, cmd: int, payload: bytes) -> None:
    """处理 RS485 响应
    
    由 RS485Driver 回调调用，更新内部状态。
    
    Args:
        cmd: 命令字节
        payload: 响应数据
    """
```

#### get_duration()
```python
def get_duration(self, volume_ul: Optional[float] = None) -> float:
    """计算注液持续时间
    
    Args:
        volume_ul: 体积，默认使用 target_volume_ul
        
    Returns:
        float: 预计秒数
    """
```

---

## 三、状态机

### 3.1 状态转移图

```
          prepare()
IDLE ─────────────────► IDLE (target_volume set)
  │                         │
  │                         │ infuse()
  │                         ▼
  │                     INFUSING
  │                         │
  │        ┌────────────────┼────────────────┐
  │        │                │                │
  │   timer完成        stop()调用        错误发生
  │        │                │                │
  │        ▼                ▼                ▼
  │    COMPLETED          IDLE            ERROR
  │        │                                 │
  │        │ reset()                  reset()│
  └────────┴─────────────────────────────────┘
```

### 3.2 状态说明

| 状态 | 说明 | 允许的操作 |
|------|------|------------|
| `IDLE` | 空闲，可配置 | prepare, infuse |
| `INFUSING` | 注液中 | stop |
| `COMPLETED` | 注液完成 | reset |
| `ERROR` | 发生错误 | reset |

---

## 四、体积计算

### 4.1 浓度配比计算

```python
def calculate_volume(
    target_conc: float,
    stock_conc: float,
    total_volume_ul: float
) -> float:
    """计算需要的储备液体积
    
    基于 C1*V1 = C2*V2
    V1 = (C2/C1) * V2
    
    Args:
        target_conc: 目标浓度
        stock_conc: 储备浓度
        total_volume_ul: 目标总体积
        
    Returns:
        float: 需要的储备液体积 (μL)
    """
    if stock_conc <= 0:
        return 0.0
    ratio = target_conc / stock_conc
    return ratio * total_volume_ul
```

### 4.2 体积到分度转换

```python
def volume_to_divisions(
    volume_ul: float,
    ul_per_division: float
) -> int:
    """体积转换为编码器分度
    
    Args:
        volume_ul: 体积 (μL)
        ul_per_division: 每分度微升数
        
    Returns:
        int: 编码器分度数
    """
    return int(volume_ul / ul_per_division)
```

### 4.3 时间计算

```python
def calculate_duration(
    volume_ul: float,
    rpm: int,
    ul_per_rev: float = 100.0  # 每转微升数
) -> float:
    """计算注液时间
    
    Args:
        volume_ul: 体积 (μL)
        rpm: 转速
        ul_per_rev: 每转微升数
        
    Returns:
        float: 时间 (秒)
    """
    revolutions = volume_ul / ul_per_rev
    minutes = revolutions / rpm
    return minutes * 60
```

---

## 五、与 RS485 交互

### 5.1 发送命令

```python
def _send_run_speed(self, rpm: int, forward: bool) -> bool:
    """发送转速命令"""
    return self._driver.run_speed(
        addr=self.config.address,
        rpm=rpm,
        forward=forward
    )

def _send_turn_to(self, divisions: int, speed: int) -> bool:
    """发送位置命令"""
    return self._driver.turn_to(
        addr=self.config.address,
        divisions=divisions,
        speed=speed
    )

def _send_stop(self) -> bool:
    """发送停止命令"""
    return self._driver.run_speed(
        addr=self.config.address,
        rpm=0,
        forward=True
    )
```

### 5.2 响应处理

```python
def handle_response(self, cmd: int, payload: bytes) -> None:
    """处理响应帧"""
    from .rs485_protocol import CMD_READ_ENCODER, decode_position
    
    if cmd == CMD_READ_ENCODER:
        current_pos = decode_position(payload)
        self._update_infused_volume(current_pos)
    elif cmd == 0xF6:  # 速度确认
        self._on_speed_confirmed()
```

---

## 六、线程模型

### 6.1 定时器更新

```python
def _start_progress_timer(self) -> None:
    """启动进度更新定时器"""
    self._progress_timer = threading.Timer(
        interval=0.5,
        function=self._update_progress
    )
    self._progress_timer.start()

def _update_progress(self) -> None:
    """更新进度"""
    if self.state != DiluterState.INFUSING:
        return
    
    elapsed = time.time() - self._start_time
    if elapsed >= self.estimated_duration:
        self._complete_infusion()
    else:
        self.infused_volume_ul = (
            elapsed / self.estimated_duration
        ) * self.target_volume_ul
        self._start_progress_timer()  # 重新调度
```

---

## 七、错误处理

### 7.1 异常类型

```python
class DiluterError(Exception):
    """Diluter 错误基类"""
    pass

class InvalidConfigError(DiluterError):
    """配置无效"""
    pass

class InfusionError(DiluterError):
    """注液错误"""
    pass
```

### 7.2 错误恢复

```python
def _handle_error(self, error: Exception) -> None:
    """处理错误"""
    self.state = DiluterState.ERROR
    self._logger.error(f"Diluter {self.config.address} 错误: {error}")
    self._send_stop()  # 确保电机停止
```

---

## 八、测试要求

### 8.1 单元测试

```python
# tests/test_diluter.py

import pytest
from echem_sdl.hardware.diluter import Diluter, DiluterConfig, DiluterState
from unittest.mock import Mock

class TestDiluter:
    @pytest.fixture
    def mock_driver(self):
        driver = Mock()
        driver.run_speed.return_value = True
        driver.turn_to.return_value = True
        return driver
    
    @pytest.fixture
    def diluter(self, mock_driver):
        config = DiluterConfig(
            address=1,
            name="HCl",
            stock_concentration=1.0,
            ul_per_division=0.1
        )
        return Diluter(config, mock_driver)
    
    def test_prepare_volume(self, diluter):
        """测试体积计算"""
        volume = diluter.prepare(
            target_conc=0.1,
            total_volume_ul=1000.0
        )
        assert volume == 100.0  # 0.1/1.0 * 1000
    
    def test_prepare_solvent(self, diluter):
        """测试溶剂计算"""
        volume = diluter.prepare(
            target_conc=0.0,
            total_volume_ul=1000.0,
            is_solvent=True
        )
        # 溶剂量应该根据其他溶液计算
    
    def test_infuse_starts(self, diluter, mock_driver):
        """测试注液启动"""
        diluter.prepare(target_conc=0.1, total_volume_ul=1000.0)
        result = diluter.infuse()
        assert result == True
        assert diluter.state == DiluterState.INFUSING
        mock_driver.run_speed.assert_called()
    
    def test_stop(self, diluter, mock_driver):
        """测试停止"""
        diluter.prepare(target_conc=0.1, total_volume_ul=1000.0)
        diluter.infuse()
        diluter.stop()
        assert diluter.state == DiluterState.IDLE
    
    def test_reset(self, diluter):
        """测试重置"""
        diluter.prepare(target_conc=0.1, total_volume_ul=1000.0)
        diluter.reset()
        assert diluter.target_volume_ul == 0.0
        assert diluter.state == DiluterState.IDLE
    
    def test_duration_calculation(self, diluter):
        """测试时间计算"""
        diluter.prepare(target_conc=0.1, total_volume_ul=1000.0)
        duration = diluter.get_duration()
        assert duration > 0

class TestVolumeCalculation:
    def test_concentration_calculation(self):
        """测试浓度配比"""
        from echem_sdl.hardware.diluter import calculate_volume
        vol = calculate_volume(0.1, 1.0, 1000.0)
        assert vol == 100.0
    
    def test_zero_stock_concentration(self):
        """测试零储备浓度"""
        from echem_sdl.hardware.diluter import calculate_volume
        vol = calculate_volume(0.1, 0.0, 1000.0)
        assert vol == 0.0
```

---

## 九、使用示例

### 9.1 基本使用

```python
from echem_sdl.hardware.diluter import Diluter, DiluterConfig
from echem_sdl.hardware.rs485_driver import RS485Driver

# 创建驱动
driver = RS485Driver(port='COM3', mock_mode=True)
driver.open()

# 配置 Diluter
config = DiluterConfig(
    address=1,
    name="HCl",
    stock_concentration=1.0,  # 1 mol/L
    ul_per_division=0.1,
    default_rpm=120
)

diluter = Diluter(config, driver)

# 准备配液 (目标 0.1 mol/L，总体积 1000 μL)
required_volume = diluter.prepare(
    target_conc=0.1,
    total_volume_ul=1000.0
)
print(f"需要注入: {required_volume} μL")

# 开始注液
diluter.infuse()

# 等待完成
while diluter.is_infusing:
    print(f"进度: {diluter.progress * 100:.1f}%")
    time.sleep(0.5)

print("注液完成")
diluter.reset()
driver.close()
```

### 9.2 多通道配液

```python
# 多通道配液示例
diluters = [
    Diluter(DiluterConfig(addr=1, name="A", stock_concentration=1.0), driver),
    Diluter(DiluterConfig(addr=2, name="B", stock_concentration=0.5), driver),
    Diluter(DiluterConfig(addr=3, name="Solvent", stock_concentration=0.0), driver),
]

# 准备各通道
total_volume = 1000.0
target_concs = [0.1, 0.05, 0.0]  # 最后一个是溶剂

volumes = []
for d, conc in zip(diluters[:-1], target_concs[:-1]):
    vol = d.prepare(target_conc=conc, total_volume_ul=total_volume)
    volumes.append(vol)

# 溶剂补齐
solvent_vol = total_volume - sum(volumes)
diluters[-1].target_volume_ul = solvent_vol

# 按顺序注液
for d in diluters:
    d.infuse()
    while d.is_infusing:
        time.sleep(0.1)
    d.reset()
```

---

## 十、前端对接指南

### 10.1 前端数据模型

**文件**: `src/models.py`

```python
@dataclass
class DilutionChannel:
    pump_address: int              # 泵地址 (1-12)
    solution_name: str             # 溶液名称
    stock_concentration: float      # 储备浓度 (mol/L)
    target_concentration: float     # 目标浓度 (mol/L)
    target_volume_ml: float        # 目标体积 (mL)
    ul_per_division: float = 0.1   # 标定因子 (µL/分度)
    enabled: bool = True           # 是否启用
```

**后端需求**：Diluter类必须接受这些参数进行初始化。

### 10.2 前端调用路径

**配置对话框** → **RS485Wrapper** → **Diluter**

```python
# 前端调用（src/dialogs/config_dialog.py）
def apply_config(self):
    for ch in self.channels:
        wrapper.configure_dilution_channels([ch])

# RS485Wrapper（src/services/rs485_wrapper.py）
def configure_dilution_channels(self, channels: List[DilutionChannel]):
    for ch in channels:
        diluter = Diluter(
            address=ch.pump_address,
            name=ch.solution_name,
            stock_concentration=ch.stock_concentration,
            pump_manager=self.ctx.pump_manager,
            logger=self.ctx.logger
        )
        self.diluters[ch.pump_address] = diluter

def start_dilution(self, channel_id: int, volume_ul: float) -> bool:
    diluter = self.diluters.get(channel_id)
    return diluter.infuse_volume(volume_ul) if diluter else False
```

### 10.3 必须实现的前端接口

**RS485Wrapper需要添加的方法**：

```python
# src/services/rs485_wrapper.py

class RS485Wrapper:
    def configure_dilution_channels(
        self,
        channels: List[DilutionChannel]
    ) -> None:
        """配置配液通道
        
        Args:
            channels: 配液通道列表
        """
        ...
    
    def start_dilution(
        self,
        channel_id: int,
        volume_ul: float
    ) -> bool:
        """开始配液
        
        Args:
            channel_id: 通道ID（泵地址）
            volume_ul: 注液体积（微升）
            
        Returns:
            是否成功启动
        """
        ...
    
    def get_dilution_progress(
        self,
        channel_id: int
    ) -> float:
        """获取配液进度
        
        Args:
            channel_id: 通道ID
            
        Returns:
            进度百分比 (0-100)
        """
        ...
    
    def stop_dilution(
        self,
        channel_id: int
    ) -> bool:
        """停止配液
        
        Args:
            channel_id: 通道ID
            
        Returns:
            是否成功停止
        """
        ...
```

### 10.4 前端验证流程

**测试步骤**：
1. 启动UI: `python run_ui.py`
2. 点击"配置溶液"按钮
3. 配置一个通道：
   - 泵地址: 1
   - 溶液名称: H2SO4
   - 储备浓度: 1.0 M
   - 目标浓度: 0.1 M
   - 标定因子: 0.1 µL/div
4. 点击"应用"按钮
5. 点击"开始配液"按钮

**预期结果**：
- Mock模式下，控制台输出配液日志
- UI显示进度（如果实现）
- 配液完成后自动停止
- 无异常抛出

### 10.5 源项目参考

**C# 文件**: `D:\AI4S\eChemSDL\eChemSDL\Diluter.cs`

**重点参考**：
- `InfuseVolume()` 方法的实现逻辑
- 体积到分度的转换公式
- 状态机设计（IDLE → INFUSING → COMPLETED）
- 与泵通信的方式

**关键差异**：
- C#有单独的 `DilutionPump` 类
- Python使用 `PumpManager` 统一管理
- 需要通过 `pump_manager.get_pump(address)` 获取泵实例

---

## 十一、验收标准

- [ ] 类与接口按规范实现
- [ ] 体积计算正确（浓度配比公式）
- [ ] 状态机转换正确
- [ ] 通过PumpManager正确控制泵
- [ ] 响应处理正确
- [ ] 进度跟踪准确
- [ ] 错误处理健壮
- [ ] RS485Wrapper接口实现完整
- [ ] 前端"配置溶液"功能正常工作
- [ ] Mock模式能模拟完整流程
- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] docstring 规范
