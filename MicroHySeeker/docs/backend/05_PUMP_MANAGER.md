# 05 - PumpManager 模块规范

> **文件路径**: `src/echem_sdl/hardware/pump_manager.py`  
> **优先级**: P1 (硬件驱动) - **核心模块**  
> **依赖**: `rs485_driver.py`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\LIB.cs` (泵管理部分)

---

## ⚠️ 核心架构说明：统一泵管理

> **PumpManager 是泵管理的唯一入口**
> 
> 在当前 Python 实现中，所有泵统一通过 PumpManager 管理：
> 
> ```
> ┌─────────────────────────────────────────────────────────────┐
> │                      PumpManager                            │
> │  ┌─────────────────────────────────────────────────────┐   │
> │  │          所有泵 (1-12号) 通过同一 COM 口            │   │
> │  │                    RS485Driver                       │   │
> │  └─────────────────────────────────────────────────────┘   │
> │                           │                                 │
> │     ┌─────────────────────┼─────────────────────┐          │
> │     ▼                     ▼                     ▼          │
> │  ┌──────┐            ┌──────┐            ┌──────┐         │
> │  │泵 1-8│            │泵 9  │            │泵10-12│         │
> │  │配液泵│            │移液泵│            │冲洗泵 │         │
> │  └──────┘            └──────┘            └──────┘         │
> │     ▲                     ▲                     ▲          │
> │     │                     │                     │          │
> │  DilutionChannel      FlushChannel         FlushChannel    │
> │  (pump_address)       (pump_address)       (pump_address)  │
> └─────────────────────────────────────────────────────────────┘
> ```
> 
> **前端数据模型**（见 `src/models.py`）：
> - `DilutionChannel.pump_address`: 配液通道引用的泵地址
> - `FlushChannel.pump_address` + `work_type`: 冲洗通道引用的泵地址和类型
> - 配置界面使用统一的泵地址下拉框（1-12）
> 
> **后端实现要求**：
> - Diluter 和 Flusher 不直接创建泵，而是从 PumpManager 获取
> - 使用 `PumpManager.get_pump(address)` 获取泵实例
> - 泵的创建/销毁由 PumpManager 统一管理

---

## 一、模块职责

PumpManager 是泵统一管理器，负责：
1. 动态创建和管理 Diluter 实例（数量由配置决定）
2. 管理 Flusher 实例
3. 根据地址路由 RS485 响应帧
4. 提供统一的泵访问接口
5. 泵状态聚合与查询

**核心原则**: 泵数量由配置决定，严禁写死

---

## 二、类设计

### 2.1 类定义

```python
from typing import Dict, List, Optional, Callable
from threading import RLock

class PumpManager:
    """泵统一管理器
    
    动态管理配液泵（Diluter）和冲洗泵（Flusher），
    路由 RS485 响应到对应设备。
    
    Attributes:
        diluters: 配液泵字典 {address: Diluter}
        flusher: 冲洗器实例
        driver: RS485 驱动
        
    Example:
        >>> manager = PumpManager(driver, config)
        >>> diluter = manager.get_diluter(1)
        >>> diluter.prepare(0.1, 1000)
        >>> diluter.infuse()
    """
```

### 2.2 构造函数

```python
def __init__(
    self,
    driver: "RS485Driver",
    config: "PumpManagerConfig",
    logger: Optional["LoggerService"] = None
) -> None:
    """初始化 PumpManager
    
    Args:
        driver: RS485 驱动实例
        config: 泵管理器配置（包含所有泵配置）
        logger: 日志服务
    """
```

### 2.3 配置类

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class PumpManagerConfig:
    """泵管理器配置"""
    diluter_configs: List[DiluterConfig] = field(default_factory=list)
    flusher_config: Optional[FlusherConfig] = None
    
    @staticmethod
    def from_settings(settings: dict) -> "PumpManagerConfig":
        """从设置字典构建配置"""
        ...
```

### 2.4 属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `diluters` | `Dict[int, Diluter]` | 配液泵字典 {地址: 实例} |
| `flusher` | `Optional[Flusher]` | 冲洗器实例 |
| `driver` | `RS485Driver` | RS485 驱动 |
| `pump_count` | `int` | 泵总数（只读） |
| `online_pumps` | `List[int]` | 在线泵地址列表（只读） |

### 2.5 公开方法

#### build_from_config()
```python
def build_from_config(self, config: PumpManagerConfig) -> None:
    """根据配置构建泵实例
    
    Args:
        config: 泵管理器配置
        
    Note:
        此方法会清除现有泵实例并重建
    """
```

#### get_diluter()
```python
def get_diluter(self, address: int) -> Optional[Diluter]:
    """获取指定地址的配液泵
    
    Args:
        address: RS485 地址
        
    Returns:
        Diluter 实例，不存在返回 None
    """
```

#### get_all_diluters()
```python
def get_all_diluters(self) -> List[Diluter]:
    """获取所有配液泵列表"""
```

#### add_diluter()
```python
def add_diluter(self, config: DiluterConfig) -> Diluter:
    """添加配液泵
    
    Args:
        config: 配液泵配置
        
    Returns:
        创建的 Diluter 实例
        
    Raises:
        ValueError: 地址已存在
    """
```

#### remove_diluter()
```python
def remove_diluter(self, address: int) -> bool:
    """移除配液泵
    
    Args:
        address: RS485 地址
        
    Returns:
        是否成功移除
    """
```

#### dispatch_response()
```python
def dispatch_response(self, addr: int, cmd: int, payload: bytes) -> None:
    """分发 RS485 响应到对应设备
    
    Args:
        addr: 设备地址
        cmd: 命令字节
        payload: 响应数据
        
    Note:
        此方法由 RS485Driver 回调调用
    """
```

#### scan_pumps()
```python
def scan_pumps(self, addresses: Optional[List[int]] = None) -> List[int]:
    """扫描在线泵
    
    Args:
        addresses: 要扫描的地址，默认 1-12
        
    Returns:
        在线泵地址列表
    """
```

#### stop_all()
```python
def stop_all(self) -> None:
    """紧急停止所有泵"""
```

#### get_status()
```python
def get_status(self) -> Dict[int, Dict]:
    """获取所有泵状态
    
    Returns:
        {address: {state, is_running, ...}}
    """
```

---

## 三、地址路由

### 3.1 地址映射表

```python
class PumpManager:
    def __init__(self, ...):
        self._address_map: Dict[int, object] = {}  # addr -> device
        self._lock = RLock()
    
    def _register_device(self, address: int, device: object) -> None:
        """注册设备到地址映射"""
        with self._lock:
            if address in self._address_map:
                raise ValueError(f"地址 {address} 已被占用")
            self._address_map[address] = device
    
    def _unregister_device(self, address: int) -> None:
        """取消设备注册"""
        with self._lock:
            self._address_map.pop(address, None)
```

### 3.2 响应分发

```python
def dispatch_response(self, addr: int, cmd: int, payload: bytes) -> None:
    """分发响应帧"""
    with self._lock:
        device = self._address_map.get(addr)
    
    if device is None:
        self._logger.warning(f"未知地址 {addr} 的响应")
        return
    
    # 分发到对应设备
    if hasattr(device, 'handle_response'):
        device.handle_response(cmd, payload)
```

### 3.3 回调注册

```python
def _setup_driver_callback(self) -> None:
    """设置 RS485 驱动回调"""
    self._driver.set_callback(self.dispatch_response)
```

---

## 四、动态泵管理

### 4.1 从配置构建

```python
def build_from_config(self, config: PumpManagerConfig) -> None:
    """根据配置构建泵"""
    # 清除现有
    self._clear_all()
    
    # 创建 Diluters
    for diluter_cfg in config.diluter_configs:
        diluter = Diluter(diluter_cfg, self._driver, self._logger)
        self._register_device(diluter_cfg.address, diluter)
        self.diluters[diluter_cfg.address] = diluter
    
    # 创建 Flusher
    if config.flusher_config:
        self.flusher = Flusher(config.flusher_config, self._driver, self._logger)
        # 注册冲洗泵地址
        self._register_device(config.flusher_config.inlet.address, self.flusher)
        self._register_device(config.flusher_config.outlet.address, self.flusher)
        self._register_device(config.flusher_config.transfer.address, self.flusher)
    
    self._logger.info(f"已创建 {len(self.diluters)} 个配液泵")
```

### 4.2 动态添加/移除

```python
def add_diluter(self, config: DiluterConfig) -> Diluter:
    """动态添加配液泵"""
    if config.address in self.diluters:
        raise ValueError(f"地址 {config.address} 已存在")
    
    diluter = Diluter(config, self._driver, self._logger)
    self._register_device(config.address, diluter)
    self.diluters[config.address] = diluter
    
    self._logger.info(f"添加配液泵: 地址 {config.address}, 名称 {config.name}")
    return diluter

def remove_diluter(self, address: int) -> bool:
    """动态移除配液泵"""
    if address not in self.diluters:
        return False
    
    diluter = self.diluters.pop(address)
    self._unregister_device(address)
    
    # 确保停止
    if diluter.is_infusing:
        diluter.stop()
    
    self._logger.info(f"移除配液泵: 地址 {address}")
    return True
```

---

## 五、状态聚合

### 5.1 获取全局状态

```python
def get_status(self) -> Dict[int, Dict]:
    """获取所有泵状态"""
    status = {}
    
    for addr, diluter in self.diluters.items():
        status[addr] = {
            "type": "diluter",
            "name": diluter.config.name,
            "state": diluter.state.value,
            "is_running": diluter.is_infusing,
            "progress": diluter.progress,
            "target_volume": diluter.target_volume_ul,
            "infused_volume": diluter.infused_volume_ul,
        }
    
    if self.flusher:
        # 添加冲洗泵状态
        for pump_type in ["inlet", "outlet", "transfer"]:
            pump_cfg = getattr(self.flusher.config, pump_type)
            is_active = (
                self.flusher.is_running and 
                self.flusher.phase.value == pump_type
            )
            status[pump_cfg.address] = {
                "type": "flusher",
                "name": pump_cfg.name,
                "role": pump_type,
                "is_running": is_active,
            }
    
    return status
```

### 5.2 运行中的泵

```python
@property
def running_pumps(self) -> List[int]:
    """获取当前运行中的泵地址"""
    running = []
    
    for addr, diluter in self.diluters.items():
        if diluter.is_infusing:
            running.append(addr)
    
    if self.flusher and self.flusher.is_running:
        # 根据阶段确定运行的冲洗泵
        phase = self.flusher.phase.value
        if phase in ["inlet", "outlet", "transfer"]:
            pump_cfg = getattr(self.flusher.config, phase)
            running.append(pump_cfg.address)
    
    return running
```

---

## 六、错误处理

### 6.1 异常定义

```python
class PumpManagerError(Exception):
    """PumpManager 错误基类"""
    pass

class AddressConflictError(PumpManagerError):
    """地址冲突"""
    pass

class DeviceNotFoundError(PumpManagerError):
    """设备未找到"""
    pass
```

### 6.2 紧急停止

```python
def stop_all(self) -> None:
    """紧急停止所有泵"""
    self._logger.warning("执行紧急停止")
    
    # 停止所有 Diluters
    for diluter in self.diluters.values():
        try:
            diluter.stop()
        except Exception as e:
            self._logger.error(f"停止 Diluter {diluter.config.address} 失败: {e}")
    
    # 停止 Flusher
    if self.flusher:
        try:
            self.flusher.stop()
        except Exception as e:
            self._logger.error(f"停止 Flusher 失败: {e}")
    
    # 直接发送停止命令到所有已知地址
    for addr in self._address_map.keys():
        try:
            self._driver.run_speed(addr=addr, rpm=0, forward=True)
        except:
            pass
```

---

## 七、测试要求

### 7.1 单元测试

```python
# tests/test_pump_manager.py

import pytest
from unittest.mock import Mock
from echem_sdl.hardware.pump_manager import PumpManager, PumpManagerConfig
from echem_sdl.hardware.diluter import DiluterConfig

class TestPumpManager:
    @pytest.fixture
    def mock_driver(self):
        driver = Mock()
        driver.run_speed.return_value = True
        driver.set_callback = Mock()
        return driver
    
    @pytest.fixture
    def config(self):
        return PumpManagerConfig(
            diluter_configs=[
                DiluterConfig(address=1, name="A", stock_concentration=1.0),
                DiluterConfig(address=2, name="B", stock_concentration=0.5),
            ]
        )
    
    @pytest.fixture
    def manager(self, mock_driver, config):
        manager = PumpManager(mock_driver, config)
        return manager
    
    def test_build_from_config(self, manager):
        """测试从配置构建"""
        assert len(manager.diluters) == 2
        assert 1 in manager.diluters
        assert 2 in manager.diluters
    
    def test_get_diluter(self, manager):
        """测试获取 Diluter"""
        diluter = manager.get_diluter(1)
        assert diluter is not None
        assert diluter.config.name == "A"
        
        # 不存在的地址
        assert manager.get_diluter(99) is None
    
    def test_add_diluter(self, manager):
        """测试添加 Diluter"""
        config = DiluterConfig(address=3, name="C", stock_concentration=0.8)
        diluter = manager.add_diluter(config)
        
        assert 3 in manager.diluters
        assert diluter.config.name == "C"
    
    def test_add_duplicate_address(self, manager):
        """测试添加重复地址"""
        config = DiluterConfig(address=1, name="X", stock_concentration=1.0)
        with pytest.raises(ValueError):
            manager.add_diluter(config)
    
    def test_remove_diluter(self, manager):
        """测试移除 Diluter"""
        result = manager.remove_diluter(1)
        assert result == True
        assert 1 not in manager.diluters
        
        # 移除不存在的
        result = manager.remove_diluter(99)
        assert result == False
    
    def test_dispatch_response(self, manager):
        """测试响应分发"""
        # 模拟响应
        manager.dispatch_response(addr=1, cmd=0xF6, payload=b'\x01')
        # 验证 Diluter 收到响应
    
    def test_stop_all(self, manager, mock_driver):
        """测试紧急停止"""
        manager.stop_all()
        # 验证发送了停止命令
        assert mock_driver.run_speed.called
    
    def test_get_status(self, manager):
        """测试状态获取"""
        status = manager.get_status()
        assert 1 in status
        assert 2 in status
        assert status[1]["type"] == "diluter"

class TestPumpManagerConfig:
    def test_from_settings(self):
        """测试从设置构建配置"""
        settings = {
            "diluter_channels": [
                {"address": 1, "name": "A", "stock_concentration": 1.0},
                {"address": 2, "name": "B", "stock_concentration": 0.5},
            ]
        }
        config = PumpManagerConfig.from_settings(settings)
        assert len(config.diluter_configs) == 2
```

---

## 八、使用示例

### 8.1 基本使用

```python
from echem_sdl.hardware.pump_manager import PumpManager, PumpManagerConfig
from echem_sdl.hardware.diluter import DiluterConfig
from echem_sdl.hardware.rs485_driver import RS485Driver

# 创建驱动
driver = RS485Driver(port='COM3', mock_mode=True)
driver.open()

# 配置泵
config = PumpManagerConfig(
    diluter_configs=[
        DiluterConfig(address=1, name="HCl", stock_concentration=1.0),
        DiluterConfig(address=2, name="NaOH", stock_concentration=0.5),
        DiluterConfig(address=3, name="H2O", stock_concentration=0.0),
    ]
)

# 创建管理器
manager = PumpManager(driver, config)

# 获取并使用 Diluter
hcl = manager.get_diluter(1)
hcl.prepare(target_conc=0.1, total_volume_ul=1000)
hcl.infuse()

# 查看状态
print(manager.get_status())

# 紧急停止
manager.stop_all()

driver.close()
```

### 8.2 与 LibContext 集成

```python
class LibContext:
    def __init__(self, ...):
        self.pump_manager = PumpManager(self.rs485_driver, config)
        
        # 设置响应路由
        self.rs485_driver.set_callback(self.pump_manager.dispatch_response)
    
    @property
    def diluters(self) -> List[Diluter]:
        return self.pump_manager.get_all_diluters()
```

---

## 九、前端对接指南

### 9.1 前端调用路径

**前端** → **RS485Wrapper** → **PumpManager** → **泵实例**

```python
# 前端通过RS485Wrapper间接使用PumpManager

# RS485Wrapper初始化（src/services/rs485_wrapper.py）
class RS485Wrapper:
    def __init__(self):
        self.ctx = LibContext(mock_mode=False)
        # ctx.pump_manager 已经初始化
        self.pump_manager = self.ctx.pump_manager
    
    def start_pump(self, address: int, speed: int, direction: str):
        """前端调用此方法启动泵"""
        pump = self.pump_manager.get_pump(address)
        if pump:
            pump.set_speed(speed)
            pump.set_direction(direction)
            pump.set_enable(True)
```

### 9.2 必须实现的前端接口

**RS485Wrapper中与PumpManager相关的方法**：

```python
# src/services/rs485_wrapper.py

class RS485Wrapper:
    def scan_pumps(self, start_addr: int = 1, end_addr: int = 12) -> List[int]:
        """扫描泵地址
        
        Returns:
            发现的泵地址列表
        """
        return self.pump_manager.scan_pumps(start_addr, end_addr)
    
    def start_pump(self, address: int, speed: int, direction: str = "FWD") -> bool:
        """启动泵
        
        Args:
            address: 泵地址 (1-12)
            speed: 速度 (0-255 RPM)
            direction: 方向 ("FWD" or "REV")
        """
        pump = self.pump_manager.get_pump(address)
        if pump:
            pump.set_speed(speed)
            pump.set_direction(direction)
            return pump.set_enable(True)
        return False
    
    def stop_pump(self, address: int) -> bool:
        """停止泵"""
        pump = self.pump_manager.get_pump(address)
        return pump.set_enable(False) if pump else False
    
    def get_pump_state(self, address: int) -> Optional[dict]:
        """获取泵状态"""
        pump = self.pump_manager.get_pump(address)
        if pump:
            return {
                "enabled": pump.enabled,
                "speed": pump.speed,
                "direction": pump.direction,
                "position": pump.position
            }
        return None
```

### 9.3 前端验证流程

**测试步骤**（阶段2已验证）：
1. 启动UI: `python run_ui.py`
2. 点击"手动控制"按钮
3. 扫描泵（Mock模式下应显示1-12号泵）
4. 选择泵地址: 1
5. 设置速度: 100 RPM
6. 点击"启动"

**预期结果**：
- Mock模式下，控制台输出泵启动日志
- UI显示泵状态
- 点击"停止"能正常停止

### 9.4 源项目参考

**C# 文件**: `D:\AI4S\eChemSDL\eChemSDL\MotorRS485.cs`

**重点参考**：
- 泵地址管理（1-12号）
- 请求/响应队列模式
- 状态查询逻辑

**关键差异**：
- C#直接在MotorRS485类中管理泵
- Python单独抽取PumpManager统一管理
- 使用LibContext进行依赖注入

---

## 十、验收标准

- [ ] 类与接口按规范实现
- [ ] 动态泵数量管理（无写死）
- [ ] 地址路由正确
- [ ] 响应分发正确
- [ ] 状态聚合正确
- [ ] 紧急停止功能正常
- [ ] 线程安全（锁保护）
- [ ] RS485Wrapper接口实现完整
- [ ] 前端"手动控制"功能正常工作
- [ ] Mock模式能模拟所有泵操作
- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] docstring 规范
