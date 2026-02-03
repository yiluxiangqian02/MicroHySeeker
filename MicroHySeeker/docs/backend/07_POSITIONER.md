# 07 - Positioner 模块规范

> ⚠️ **重要提示**: 本模块**不需要实现**！当前项目不使用三轴定位平台。  
> 此文档仅作为参考保留，请跳过此模块的开发。

---

> **文件路径**: `src/echem_sdl/hardware/positioner.py`  
> **优先级**: ~~P3 (可选模块)~~ → **不需要实现**  
> **依赖**: `rs485_driver.py`, `rs485_protocol.py`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\Positioner.cs`

---

## 一、模块职责

~~Positioner 是 XYZ 三轴定位平台驱动模块，负责：~~
~~1. 控制三轴运动（X、Y、Z）~~
~~2. 管理多个预设位置点~~
~~3. 提供回零和相对/绝对定位~~
~~4. 状态监测与运动完成检测~~

**⚠️ 当前项目不需要此功能**

~~**使用场景**: 自动更换电极位置、多孔板扫描~~

---

## 二、协议规范

### 2.1 通讯参数

| 参数 | 值 |
|------|-----|
| 默认地址 | 0x10 (16) |
| 波特率 | 38400 |
| 数据帧 | 8N2 |

### 2.2 命令定义

| 命令 | 码值 | 数据长度 | 说明 |
|------|------|----------|------|
| HOME | 0x01 | 0 | 三轴回零 |
| MOVE_ABS | 0x02 | 12 | 绝对定位 (X, Y, Z 各4字节) |
| MOVE_REL | 0x03 | 12 | 相对定位 |
| GET_POS | 0x04 | 0 | 查询位置 |
| SET_SPEED | 0x05 | 6 | 设置速度 (X, Y, Z 各2字节) |
| GET_STATUS | 0x06 | 0 | 查询状态 |
| STOP | 0x07 | 0 | 紧急停止 |
| GOTO_PRESET | 0x08 | 1 | 移动到预设点 |

### 2.3 状态字节

```
位7: X轴到位
位6: Y轴到位
位5: Z轴到位
位4: 运动中
位3: 错误
位2-0: 保留
```

---

## 三、类设计

### 3.1 位置结构

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Position:
    """三维位置"""
    x: float = 0.0  # mm
    y: float = 0.0  # mm
    z: float = 0.0  # mm
    
    def to_steps(self, steps_per_mm: float = 100.0) -> tuple:
        """转换为步数"""
        return (
            int(self.x * steps_per_mm),
            int(self.y * steps_per_mm),
            int(self.z * steps_per_mm)
        )

@dataclass
class PresetPosition:
    """预设位置点"""
    index: int
    name: str
    position: Position
    description: str = ""
```

### 3.2 主类定义

```python
class Positioner:
    """XYZ 三轴定位器驱动
    
    控制 XYZ 定位平台，支持绝对/相对定位和预设位置。
    
    Attributes:
        address: 设备地址
        current_position: 当前位置
        is_moving: 是否运动中
        is_homed: 是否已回零
        
    Example:
        >>> pos = Positioner(driver, address=0x10)
        >>> await pos.home()
        >>> await pos.move_to(Position(10.0, 20.0, 5.0))
    """
```

### 3.3 构造函数

```python
def __init__(
    self,
    driver: "RS485Driver",
    address: int = 0x10,
    steps_per_mm: float = 100.0,
    mock_mode: bool = False
) -> None:
    """初始化定位器
    
    Args:
        driver: RS485 驱动实例
        address: 设备地址
        steps_per_mm: 每毫米步数
        mock_mode: 模拟模式
    """
```

### 3.4 公开方法

#### 回零

```python
async def home(self) -> bool:
    """三轴回零
    
    Returns:
        bool: 回零是否成功
        
    Raises:
        PositionerError: 回零失败
    """
```

#### 绝对定位

```python
async def move_to(
    self,
    position: Position,
    wait: bool = True
) -> bool:
    """移动到绝对位置
    
    Args:
        position: 目标位置
        wait: 是否等待到位
        
    Returns:
        bool: 移动是否成功
    """
```

#### 相对定位

```python
async def move_relative(
    self,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
    wait: bool = True
) -> bool:
    """相对移动
    
    Args:
        dx: X方向偏移 (mm)
        dy: Y方向偏移 (mm)
        dz: Z方向偏移 (mm)
        wait: 是否等待到位
    """
```

#### 单轴移动

```python
async def move_x(self, x: float, wait: bool = True) -> bool:
    """移动X轴"""

async def move_y(self, y: float, wait: bool = True) -> bool:
    """移动Y轴"""

async def move_z(self, z: float, wait: bool = True) -> bool:
    """移动Z轴"""
```

#### 预设位置

```python
async def goto_preset(self, index: int, wait: bool = True) -> bool:
    """移动到预设位置
    
    Args:
        index: 预设位置索引 (0-7)
        wait: 是否等待到位
    """

def add_preset(self, preset: PresetPosition) -> None:
    """添加预设位置"""

def get_presets(self) -> List[PresetPosition]:
    """获取所有预设位置"""
```

#### 速度控制

```python
async def set_speed(
    self,
    x_speed: float = None,
    y_speed: float = None,
    z_speed: float = None
) -> bool:
    """设置各轴速度 (mm/s)"""
```

#### 状态查询

```python
async def get_position(self) -> Position:
    """获取当前位置"""

async def get_status(self) -> int:
    """获取状态字节"""

async def wait_for_idle(self, timeout: float = 30.0) -> bool:
    """等待运动完成
    
    Args:
        timeout: 超时时间（秒）
    """
```

#### 停止

```python
async def stop(self) -> bool:
    """紧急停止"""
```

### 3.5 属性

```python
@property
def current_position(self) -> Position:
    """当前位置"""

@property
def is_moving(self) -> bool:
    """是否运动中"""

@property
def is_homed(self) -> bool:
    """是否已回零"""
```

---

## 四、协议实现

### 4.1 命令常量

```python
class PositionerCmd:
    """定位器命令码"""
    HOME = 0x01
    MOVE_ABS = 0x02
    MOVE_REL = 0x03
    GET_POS = 0x04
    SET_SPEED = 0x05
    GET_STATUS = 0x06
    STOP = 0x07
    GOTO_PRESET = 0x08
```

### 4.2 数据编码

```python
def _encode_position(self, position: Position) -> bytes:
    """编码位置数据"""
    steps = position.to_steps(self._steps_per_mm)
    data = bytearray()
    for s in steps:
        data.extend(struct.pack('>i', s))  # 大端有符号整数
    return bytes(data)

def _decode_position(self, data: bytes) -> Position:
    """解码位置数据"""
    x_steps = struct.unpack('>i', data[0:4])[0]
    y_steps = struct.unpack('>i', data[4:8])[0]
    z_steps = struct.unpack('>i', data[8:12])[0]
    
    return Position(
        x=x_steps / self._steps_per_mm,
        y=y_steps / self._steps_per_mm,
        z=z_steps / self._steps_per_mm
    )
```

---

## 五、模拟模式

```python
class MockPositioner(Positioner):
    """模拟定位器"""
    
    def __init__(self, **kwargs):
        super().__init__(mock_mode=True, **kwargs)
        self._mock_position = Position()
        self._mock_homed = False
        self._mock_moving = False
    
    async def home(self) -> bool:
        self._mock_moving = True
        await asyncio.sleep(2.0)  # 模拟回零时间
        self._mock_position = Position()
        self._mock_homed = True
        self._mock_moving = False
        return True
    
    async def move_to(self, position: Position, wait: bool = True) -> bool:
        if not self._mock_homed:
            raise PositionerError("未回零")
        
        self._mock_moving = True
        
        # 计算运动时间
        distance = self._calculate_distance(self._mock_position, position)
        move_time = distance / 10.0  # 假设 10 mm/s
        
        if wait:
            await asyncio.sleep(move_time)
        
        self._mock_position = position
        self._mock_moving = False
        return True
```

---

## 六、测试要求

### 6.1 单元测试

```python
# tests/test_positioner.py

import pytest
import asyncio
from echem_sdl.hardware.positioner import Positioner, Position, MockPositioner

class TestPosition:
    def test_to_steps(self):
        """测试位置转步数"""
        pos = Position(10.0, 20.0, 5.0)
        steps = pos.to_steps(100.0)
        assert steps == (1000, 2000, 500)

class TestPositioner:
    @pytest.fixture
    def mock_positioner(self):
        return MockPositioner(driver=None, address=0x10)
    
    @pytest.mark.asyncio
    async def test_home(self, mock_positioner):
        """测试回零"""
        result = await mock_positioner.home()
        assert result == True
        assert mock_positioner.is_homed
        assert mock_positioner.current_position.x == 0.0
    
    @pytest.mark.asyncio
    async def test_move_to(self, mock_positioner):
        """测试绝对定位"""
        await mock_positioner.home()
        
        target = Position(10.0, 20.0, 5.0)
        result = await mock_positioner.move_to(target)
        
        assert result == True
        assert mock_positioner.current_position.x == 10.0
    
    @pytest.mark.asyncio
    async def test_move_without_home_fails(self, mock_positioner):
        """测试未回零移动失败"""
        with pytest.raises(Exception):
            await mock_positioner.move_to(Position(10.0, 0, 0))
```

---

## 七、验收标准

- [ ] Position 数据类正确实现
- [ ] 回零功能正常
- [ ] 绝对/相对定位正确
- [ ] 预设位置管理正确
- [ ] 速度设置正确
- [ ] 状态查询正确
- [ ] 等待到位功能正常
- [ ] 紧急停止功能正常
- [ ] 模拟模式可用
- [ ] 异步接口正确
- [ ] 单元测试通过
