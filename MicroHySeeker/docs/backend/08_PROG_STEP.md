# 08 - ProgStep 模块规范

> **文件路径**: `src/echem_sdl/core/prog_step.py`
> **优先级**: P0 (核心模块)
> **依赖**: 无
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\ProgStep.cs`

---

## 一、模块职责

ProgStep 是实验程序的基本执行单元，负责：

1. 定义单个实验步骤的类型和参数
2. 支持多种步骤类型（配液、转移、冲洗、电化学等）
3. 提供步骤验证
4. 支持 JSON 序列化/反序列化
5. 计算步骤预估时长

---

## 二、步骤类型

### 2.1 类型枚举

```python
from enum import Enum

class StepType(str, Enum):
    """步骤类型枚举"""
    PREP_SOL = "prep_sol"      # 配液
    TRANSFER = "transfer"       # 转移
    FLUSH = "flush"             # 冲洗
    ECHEM = "echem"             # 电化学
    BLANK = "blank"             # 空白/等待
    EVACUATE = "evacuate"       # 抽空
    POSITION = "position"       # 定位（可选）
```

### 2.2 各类型说明

| 类型         | 说明       | 主要参数               |
| ------------ | ---------- | ---------------------- |
| `PREP_SOL` | 配液操作   | 通道列表、浓度、总体积 |
| `TRANSFER` | 转移溶液   | 源位置、目标位置、体积 |
| `FLUSH`    | 冲洗管路   | 冲洗轮数               |
| `ECHEM`    | 电化学测量 | EC技术、参数           |
| `BLANK`    | 等待/延时  | 等待时间               |
| `EVACUATE` | 抽空池体   | 抽空时间               |
| `POSITION` | 移动位置   | 目标位置               |

---

## 三、配置数据类

### 3.1 配液配置

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class PrepSolConfig:
    """配液配置"""
    # 通道浓度映射 {"D1": 0.5, "D2": 0.3, ...}
    concentrations: Dict[str, float] = field(default_factory=dict)
    # 总体积 (uL)
    total_volume_ul: float = 100.0
    # 注液顺序（默认按配置顺序）
    injection_order: Optional[List[str]] = None
    # 混合次数
    mix_count: int = 0
    # 混合体积 (uL)
    mix_volume_ul: float = 50.0
  
    def get_concentration(self, channel_id: str) -> float:
        """获取通道浓度"""
        return self.concentrations.get(channel_id, 0.0)
  
    def get_injection_order(self) -> List[str]:
        """获取注液顺序"""
        if self.injection_order:
            return self.injection_order
        return list(self.concentrations.keys())
```

### 3.2 转移配置

```python
@dataclass
class TransferConfig:
    """转移配置"""
    # 源通道
    source_channel: str = ""
    # 目标位置
    target_position: str = "pool"
    # 转移体积 (uL)
    volume_ul: float = 100.0
    # 转移速度 (uL/s)
    speed_ul_per_s: float = 10.0
```

### 3.3 冲洗配置

```python
@dataclass
class FlushConfig:
    """冲洗配置"""
    # 冲洗轮数
    cycles: int = 3
    # 冲洗体积 (uL)
    volume_ul: float = 500.0
    # 使用的冲洗通道
    channels: List[str] = field(default_factory=lambda: ["wash", "dry"])
```

### 3.4 电化学配置

```python
@dataclass
class ECConfig:
    """电化学配置"""
    # 技术类型
    technique: str = "CV"
    # 初始电位 (V)
    e_init: float = 0.0
    # 最高电位 (V)
    e_high: float = 0.8
    # 最低电位 (V)
    e_low: float = -0.2
    # 终止电位 (V)
    e_final: float = 0.0
    # 扫描速率 (V/s)
    scan_rate: float = 0.1
    # 扫描段数
    segments: int = 2
    # 静置时间 (s)
    quiet_time: float = 2.0
    # 运行时间 (s) - 用于 i-t, OCPT
    run_time: float = 60.0
    # 采样间隔 (s)
    sample_interval: float = 0.1
    # 灵敏度
    sensitivity: float = 1e-5
```

### 3.5 空白配置

```python
@dataclass
class BlankConfig:
    """空白/等待配置"""
    # 等待时间 (s)
    wait_time: float = 5.0
    # 描述
    description: str = ""
```

### 3.6 抽空配置

```python
@dataclass
class EvacuateConfig:
    """抽空配置"""
    # 抽空时间 (s)
    evacuate_time: float = 10.0
    # 抽空速度
    speed: int = 3
```

---

## 四、主类设计

### 4.1 类定义

```python
@dataclass
class ProgStep:
    """程序步骤
  
    表示实验程序中的单个执行步骤。
  
    Attributes:
        step_type: 步骤类型
        name: 步骤名称
        enabled: 是否启用
        prep_sol_config: 配液配置
        transfer_config: 转移配置
        flush_config: 冲洗配置
        ec_config: 电化学配置
        blank_config: 空白配置
        evacuate_config: 抽空配置
      
    Example:
        >>> step = ProgStep(
        ...     step_type=StepType.ECHEM,
        ...     name="CV测量",
        ...     ec_config=ECConfig(technique="CV", scan_rate=0.1)
        ... )
    """
    # 基本信息
    step_type: StepType
    name: str = ""
    enabled: bool = True
  
    # 各类型配置（仅对应类型有效）
    prep_sol_config: Optional[PrepSolConfig] = None
    transfer_config: Optional[TransferConfig] = None
    flush_config: Optional[FlushConfig] = None
    ec_config: Optional[ECConfig] = None
    blank_config: Optional[BlankConfig] = None
    evacuate_config: Optional[EvacuateConfig] = None
```

### 4.2 方法

#### 获取当前配置

```python
def get_config(self) -> Optional[object]:
    """获取当前步骤类型的配置"""
    config_map = {
        StepType.PREP_SOL: self.prep_sol_config,
        StepType.TRANSFER: self.transfer_config,
        StepType.FLUSH: self.flush_config,
        StepType.ECHEM: self.ec_config,
        StepType.BLANK: self.blank_config,
        StepType.EVACUATE: self.evacuate_config,
    }
    return config_map.get(self.step_type)
```

#### 计算时长

```python
def get_duration(self) -> float:
    """获取步骤预估时长（秒）
  
    Returns:
        float: 预估执行时间
    """
    if self.step_type == StepType.PREP_SOL:
        config = self.prep_sol_config
        if config is None:
            return 0.0
        # 每个通道约 10 秒
        return len(config.concentrations) * 10.0
  
    elif self.step_type == StepType.FLUSH:
        config = self.flush_config
        if config is None:
            return 0.0
        # 每轮约 15 秒
        return config.cycles * 15.0
  
    elif self.step_type == StepType.ECHEM:
        config = self.ec_config
        if config is None:
            return 0.0
        if config.technique in ["CV", "LSV"]:
            # 基于电位范围和扫描速率
            e_range = config.e_high - config.e_low
            return config.quiet_time + (e_range * config.segments / config.scan_rate)
        elif config.technique in ["i-t", "CA"]:
            return config.quiet_time + config.run_time
        elif config.technique == "OCPT":
            return config.quiet_time + config.run_time
        return 60.0
  
    elif self.step_type == StepType.BLANK:
        config = self.blank_config
        return config.wait_time if config else 5.0
  
    elif self.step_type == StepType.EVACUATE:
        config = self.evacuate_config
        return config.evacuate_time if config else 10.0
  
    elif self.step_type == StepType.TRANSFER:
        config = self.transfer_config
        if config is None:
            return 0.0
        return config.volume_ul / config.speed_ul_per_s
  
    return 0.0
```

#### 验证

```python
def validate(self) -> List[str]:
    """验证步骤配置
  
    Returns:
        List[str]: 错误消息列表（空表示有效）
    """
    errors = []
  
    config = self.get_config()
    if config is None:
        errors.append(f"步骤类型 {self.step_type} 缺少配置")
        return errors
  
    if self.step_type == StepType.PREP_SOL:
        if not config.concentrations:
            errors.append("配液配置缺少通道")
        if config.total_volume_ul <= 0:
            errors.append("总体积必须大于0")
  
    elif self.step_type == StepType.ECHEM:
        if config.e_high <= config.e_low:
            errors.append("最高电位必须大于最低电位")
        if config.scan_rate <= 0:
            errors.append("扫描速率必须大于0")
  
    elif self.step_type == StepType.FLUSH:
        if config.cycles <= 0:
            errors.append("冲洗轮数必须大于0")
  
    return errors
```

### 4.3 序列化

```python
def to_dict(self) -> dict:
    """转换为字典"""
    result = {
        "step_type": self.step_type.value,
        "name": self.name,
        "enabled": self.enabled,
    }
  
    config = self.get_config()
    if config:
        result[f"{self.step_type.value}_config"] = asdict(config)
  
    return result

@classmethod
def from_dict(cls, data: dict) -> "ProgStep":
    """从字典创建"""
    step_type = StepType(data.get("step_type", "blank"))
  
    step = cls(
        step_type=step_type,
        name=data.get("name", ""),
        enabled=data.get("enabled", True),
    )
  
    # 加载对应配置
    config_key = f"{step_type.value}_config"
    if config_key in data:
        config_data = data[config_key]
        if step_type == StepType.PREP_SOL:
            step.prep_sol_config = PrepSolConfig(**config_data)
        elif step_type == StepType.ECHEM:
            step.ec_config = ECConfig(**config_data)
        # ... 其他类型
  
    return step
```

---

## 五、工厂方法

```python
class ProgStepFactory:
    """步骤工厂"""
  
    @staticmethod
    def create_prep_sol(
        name: str,
        concentrations: Dict[str, float],
        total_volume_ul: float = 100.0
    ) -> ProgStep:
        """创建配液步骤"""
        return ProgStep(
            step_type=StepType.PREP_SOL,
            name=name,
            prep_sol_config=PrepSolConfig(
                concentrations=concentrations,
                total_volume_ul=total_volume_ul
            )
        )
  
    @staticmethod
    def create_cv(
        name: str = "CV",
        e_low: float = -0.2,
        e_high: float = 0.8,
        scan_rate: float = 0.1,
        segments: int = 2
    ) -> ProgStep:
        """创建CV步骤"""
        return ProgStep(
            step_type=StepType.ECHEM,
            name=name,
            ec_config=ECConfig(
                technique="CV",
                e_init=e_low,
                e_low=e_low,
                e_high=e_high,
                e_final=e_low,
                scan_rate=scan_rate,
                segments=segments
            )
        )
  
    @staticmethod
    def create_flush(
        name: str = "冲洗",
        cycles: int = 3
    ) -> ProgStep:
        """创建冲洗步骤"""
        return ProgStep(
            step_type=StepType.FLUSH,
            name=name,
            flush_config=FlushConfig(cycles=cycles)
        )
  
    @staticmethod
    def create_blank(
        name: str = "等待",
        wait_time: float = 5.0
    ) -> ProgStep:
        """创建空白步骤"""
        return ProgStep(
            step_type=StepType.BLANK,
            name=name,
            blank_config=BlankConfig(wait_time=wait_time)
        )
  
    @staticmethod
    def create_evacuate(
        name: str = "抽空",
        evacuate_time: float = 10.0
    ) -> ProgStep:
        """创建抽空步骤"""
        return ProgStep(
            step_type=StepType.EVACUATE,
            name=name,
            evacuate_config=EvacuateConfig(evacuate_time=evacuate_time)
        )
```

---

## 六、测试要求

### 6.1 单元测试

```python
# tests/test_prog_step.py

import pytest
from echem_sdl.core.prog_step import (
    ProgStep, StepType, PrepSolConfig, ECConfig, ProgStepFactory
)

class TestProgStep:
    def test_create_step(self):
        """测试创建步骤"""
        step = ProgStep(
            step_type=StepType.BLANK,
            name="测试步骤"
        )
        assert step.step_type == StepType.BLANK
        assert step.name == "测试步骤"
        assert step.enabled == True
  
    def test_get_config(self):
        """测试获取配置"""
        step = ProgStep(
            step_type=StepType.ECHEM,
            ec_config=ECConfig(technique="CV")
        )
        config = step.get_config()
        assert config is not None
        assert config.technique == "CV"
  
    def test_duration_cv(self):
        """测试CV时长计算"""
        step = ProgStep(
            step_type=StepType.ECHEM,
            ec_config=ECConfig(
                technique="CV",
                e_low=-0.2,
                e_high=0.8,
                scan_rate=0.1,
                segments=2,
                quiet_time=2.0
            )
        )
        duration = step.get_duration()
        # 2 + (1.0 * 2 / 0.1) = 2 + 20 = 22
        assert duration == pytest.approx(22.0)
  
    def test_validate_valid_step(self):
        """测试验证有效步骤"""
        step = ProgStepFactory.create_cv()
        errors = step.validate()
        assert len(errors) == 0
  
    def test_validate_invalid_step(self):
        """测试验证无效步骤"""
        step = ProgStep(
            step_type=StepType.ECHEM,
            ec_config=ECConfig(e_high=0.0, e_low=0.5)  # 错误：high < low
        )
        errors = step.validate()
        assert len(errors) > 0
  
    def test_serialization(self):
        """测试序列化"""
        step = ProgStepFactory.create_cv("测试CV")
        data = step.to_dict()
      
        restored = ProgStep.from_dict(data)
        assert restored.step_type == StepType.ECHEM
        assert restored.name == "测试CV"
        assert restored.ec_config.technique == "CV"

class TestProgStepFactory:
    def test_create_prep_sol(self):
        """测试创建配液步骤"""
        step = ProgStepFactory.create_prep_sol(
            name="配液",
            concentrations={"D1": 0.5, "D2": 0.3},
            total_volume_ul=100.0
        )
        assert step.step_type == StepType.PREP_SOL
        assert step.prep_sol_config.concentrations["D1"] == 0.5
  
    def test_create_flush(self):
        """测试创建冲洗步骤"""
        step = ProgStepFactory.create_flush(cycles=5)
        assert step.step_type == StepType.FLUSH
        assert step.flush_config.cycles == 5
```

---

## 七、验收标准

- [ ] StepType 枚举完整
- [ ] 所有配置数据类正确实现
- [ ] ProgStep 主类正确实现
- [ ] get_config() 返回正确配置
- [ ] get_duration() 计算准确
- [ ] validate() 检查完整
- [ ] JSON 序列化/反序列化正确
- [ ] 工厂方法覆盖所有类型
- [ ] 单元测试覆盖率 > 90%
- [ ] 类型注解完整
