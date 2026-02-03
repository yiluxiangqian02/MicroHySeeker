# 09 - ExpProgram 模块规范

> **文件路径**: `src/echem_sdl/core/exp_program.py`  
> **优先级**: P0 (核心模块)  
> **依赖**: `prog_step.py`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\ExpProgram.cs`

---

## 一、模块职责

ExpProgram 是实验程序管理模块，负责：
1. 管理步骤集合（有序列表）
2. 定义组合参数（Combo Parameters）
3. 生成参数组合矩阵
4. 提供程序验证
5. JSON 序列化/反序列化
6. 计算总时长和统计信息

---

## 二、组合参数设计

### 2.1 参数定义

```python
from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class ComboParameter:
    """组合参数定义
    
    定义一个可变参数及其取值范围。
    
    Attributes:
        name: 参数名称（显示用）
        target_path: 参数路径（如 "steps[0].ec_config.scan_rate"）
        values: 参数值列表
        unit: 单位（显示用）
    """
    name: str
    target_path: str
    values: List[Any] = field(default_factory=list)
    unit: str = ""
    
    @property
    def count(self) -> int:
        """值的数量"""
        return len(self.values)
    
    def get_value(self, index: int) -> Any:
        """获取指定索引的值"""
        if 0 <= index < len(self.values):
            return self.values[index]
        return None
```

### 2.2 参数路径格式

参数路径使用点分表示法，支持数组索引：

```
steps[0].ec_config.scan_rate    # 第1步EC配置的扫描速率
steps[1].prep_sol_config.concentrations.D1  # 第2步配液D1浓度
steps[2].flush_config.cycles    # 第3步冲洗轮数
```

### 2.3 参数矩阵

```python
@dataclass
class ParamMatrix:
    """参数组合矩阵"""
    parameters: List[ComboParameter]
    combinations: List[List[Any]] = field(default_factory=list)
    
    @property
    def combo_count(self) -> int:
        """组合总数"""
        return len(self.combinations)
    
    def get_values_at(self, combo_index: int) -> dict:
        """获取指定组合的参数值
        
        Args:
            combo_index: 组合索引
            
        Returns:
            dict: {参数路径: 值}
        """
        if combo_index >= len(self.combinations):
            return {}
        
        combo = self.combinations[combo_index]
        return {
            param.target_path: combo[i]
            for i, param in enumerate(self.parameters)
        }
```

---

## 三、主类设计

### 3.1 类定义

```python
from typing import Optional
import json
from pathlib import Path

class ExpProgram:
    """实验程序
    
    管理实验步骤和组合参数，支持保存/加载。
    
    Attributes:
        name: 程序名称
        description: 程序描述
        steps: 步骤列表
        combo_params: 组合参数列表
        
    Example:
        >>> program = ExpProgram("CV扫描")
        >>> program.add_step(ProgStepFactory.create_cv())
        >>> program.add_combo_param(ComboParameter(
        ...     name="扫描速率",
        ...     target_path="steps[0].ec_config.scan_rate",
        ...     values=[0.05, 0.1, 0.2]
        ... ))
        >>> program.fill_param_matrix()
        >>> print(f"组合数: {program.combo_count}")
    """
```

### 3.2 构造函数

```python
def __init__(
    self,
    name: str = "",
    description: str = ""
) -> None:
    """初始化实验程序
    
    Args:
        name: 程序名称
        description: 描述
    """
    self.name = name
    self.description = description
    self.steps: List[ProgStep] = []
    self.combo_params: List[ComboParameter] = []
    self._param_matrix: Optional[ParamMatrix] = None
    self._original_values: dict = {}  # 保存原始值用于恢复
```

### 3.3 步骤管理

```python
def add_step(self, step: "ProgStep", index: int = -1) -> None:
    """添加步骤
    
    Args:
        step: 步骤对象
        index: 插入位置（-1 表示末尾）
    """
    if index < 0 or index >= len(self.steps):
        self.steps.append(step)
    else:
        self.steps.insert(index, step)

def remove_step(self, index: int) -> Optional["ProgStep"]:
    """移除步骤
    
    Args:
        index: 步骤索引
        
    Returns:
        被移除的步骤
    """
    if 0 <= index < len(self.steps):
        return self.steps.pop(index)
    return None

def move_step(self, from_index: int, to_index: int) -> bool:
    """移动步骤
    
    Args:
        from_index: 源索引
        to_index: 目标索引
        
    Returns:
        是否成功
    """
    if not (0 <= from_index < len(self.steps)):
        return False
    if not (0 <= to_index < len(self.steps)):
        return False
    
    step = self.steps.pop(from_index)
    self.steps.insert(to_index, step)
    return True

def get_step(self, index: int) -> Optional["ProgStep"]:
    """获取步骤"""
    if 0 <= index < len(self.steps):
        return self.steps[index]
    return None

@property
def step_count(self) -> int:
    """步骤数量"""
    return len(self.steps)
```

### 3.4 组合参数管理

```python
def add_combo_param(self, param: ComboParameter) -> None:
    """添加组合参数"""
    self.combo_params.append(param)
    self._param_matrix = None  # 清除缓存

def remove_combo_param(self, index: int) -> Optional[ComboParameter]:
    """移除组合参数"""
    if 0 <= index < len(self.combo_params):
        self._param_matrix = None
        return self.combo_params.pop(index)
    return None

def clear_combo_params(self) -> None:
    """清空组合参数"""
    self.combo_params.clear()
    self._param_matrix = None
```

### 3.5 参数矩阵生成

```python
def fill_param_matrix(self) -> None:
    """生成参数组合矩阵
    
    使用笛卡尔积生成所有参数组合。
    """
    if not self.combo_params:
        self._param_matrix = ParamMatrix(parameters=[])
        return
    
    from itertools import product
    
    # 保存原始值
    self._save_original_values()
    
    # 生成所有组合
    value_lists = [p.values for p in self.combo_params]
    combinations = list(product(*value_lists))
    
    self._param_matrix = ParamMatrix(
        parameters=self.combo_params,
        combinations=[list(c) for c in combinations]
    )

@property
def combo_count(self) -> int:
    """组合总数"""
    if self._param_matrix is None:
        self.fill_param_matrix()
    return self._param_matrix.combo_count

def get_param_values(self, combo_index: int) -> dict:
    """获取指定组合的参数值"""
    if self._param_matrix is None:
        self.fill_param_matrix()
    return self._param_matrix.get_values_at(combo_index)
```

### 3.6 参数加载

```python
def load_param_values(self, combo_index: int) -> bool:
    """加载指定组合的参数值到步骤中
    
    Args:
        combo_index: 组合索引
        
    Returns:
        是否成功
    """
    if self._param_matrix is None:
        self.fill_param_matrix()
    
    if combo_index >= self.combo_count:
        return False
    
    values = self.get_param_values(combo_index)
    
    for path, value in values.items():
        self._set_value_by_path(path, value)
    
    return True

def _set_value_by_path(self, path: str, value: Any) -> None:
    """通过路径设置值
    
    Args:
        path: 参数路径（如 "steps[0].ec_config.scan_rate"）
        value: 值
    """
    import re
    
    parts = re.split(r'\.|\[|\]', path)
    parts = [p for p in parts if p]  # 移除空字符串
    
    obj = self
    for i, part in enumerate(parts[:-1]):
        if part.isdigit():
            obj = obj[int(part)]
        else:
            obj = getattr(obj, part)
    
    last_part = parts[-1]
    if isinstance(obj, dict):
        obj[last_part] = value
    else:
        setattr(obj, last_part, value)

def _save_original_values(self) -> None:
    """保存原始参数值"""
    self._original_values.clear()
    for param in self.combo_params:
        self._original_values[param.target_path] = self._get_value_by_path(param.target_path)

def restore_original_values(self) -> None:
    """恢复原始参数值"""
    for path, value in self._original_values.items():
        self._set_value_by_path(path, value)
```

### 3.7 统计与验证

```python
@property
def total_duration(self) -> float:
    """计算总时长（单个组合）"""
    return sum(step.get_duration() for step in self.steps if step.enabled)

@property
def total_experiment_duration(self) -> float:
    """计算全部实验时长（含所有组合）"""
    return self.total_duration * max(1, self.combo_count)

def validate(self) -> List[str]:
    """验证程序
    
    Returns:
        错误消息列表
    """
    errors = []
    
    if not self.steps:
        errors.append("程序至少需要一个步骤")
    
    for i, step in enumerate(self.steps):
        step_errors = step.validate()
        for err in step_errors:
            errors.append(f"步骤 {i+1}: {err}")
    
    # 验证组合参数路径
    for param in self.combo_params:
        try:
            self._get_value_by_path(param.target_path)
        except Exception:
            errors.append(f"参数路径无效: {param.target_path}")
    
    return errors

def get_summary(self) -> dict:
    """获取程序摘要"""
    return {
        "name": self.name,
        "step_count": self.step_count,
        "combo_param_count": len(self.combo_params),
        "combo_count": self.combo_count if self.combo_params else 1,
        "single_duration": self.total_duration,
        "total_duration": self.total_experiment_duration,
    }
```

### 3.8 序列化

```python
def to_dict(self) -> dict:
    """转换为字典"""
    return {
        "name": self.name,
        "description": self.description,
        "steps": [step.to_dict() for step in self.steps],
        "combo_params": [
            {
                "name": p.name,
                "target_path": p.target_path,
                "values": p.values,
                "unit": p.unit,
            }
            for p in self.combo_params
        ]
    }

@classmethod
def from_dict(cls, data: dict) -> "ExpProgram":
    """从字典创建"""
    program = cls(
        name=data.get("name", ""),
        description=data.get("description", "")
    )
    
    # 加载步骤
    for step_data in data.get("steps", []):
        step = ProgStep.from_dict(step_data)
        program.add_step(step)
    
    # 加载组合参数
    for param_data in data.get("combo_params", []):
        param = ComboParameter(
            name=param_data.get("name", ""),
            target_path=param_data.get("target_path", ""),
            values=param_data.get("values", []),
            unit=param_data.get("unit", ""),
        )
        program.add_combo_param(param)
    
    return program

def to_json(self, indent: int = 2) -> str:
    """转换为 JSON 字符串"""
    return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

@classmethod
def from_json(cls, json_str: str) -> "ExpProgram":
    """从 JSON 字符串创建"""
    data = json.loads(json_str)
    return cls.from_dict(data)

def save(self, file_path: str | Path) -> None:
    """保存到文件"""
    path = Path(file_path)
    path.write_text(self.to_json(), encoding="utf-8")

@classmethod
def load(cls, file_path: str | Path) -> "ExpProgram":
    """从文件加载"""
    path = Path(file_path)
    json_str = path.read_text(encoding="utf-8")
    return cls.from_json(json_str)
```

---

## 四、测试要求

### 4.1 单元测试

```python
# tests/test_exp_program.py

import pytest
import tempfile
from pathlib import Path
from echem_sdl.core.exp_program import ExpProgram, ComboParameter
from echem_sdl.core.prog_step import ProgStepFactory

class TestExpProgram:
    @pytest.fixture
    def sample_program(self):
        program = ExpProgram("测试程序", "描述")
        program.add_step(ProgStepFactory.create_flush(cycles=3))
        program.add_step(ProgStepFactory.create_cv())
        return program
    
    def test_create_program(self):
        """测试创建程序"""
        program = ExpProgram("Test", "Desc")
        assert program.name == "Test"
        assert program.step_count == 0
    
    def test_add_step(self, sample_program):
        """测试添加步骤"""
        initial_count = sample_program.step_count
        sample_program.add_step(ProgStepFactory.create_blank())
        assert sample_program.step_count == initial_count + 1
    
    def test_remove_step(self, sample_program):
        """测试移除步骤"""
        removed = sample_program.remove_step(0)
        assert removed is not None
        assert sample_program.step_count == 1
    
    def test_move_step(self, sample_program):
        """测试移动步骤"""
        first_step = sample_program.get_step(0)
        sample_program.move_step(0, 1)
        assert sample_program.get_step(1) == first_step
    
    def test_total_duration(self, sample_program):
        """测试时长计算"""
        duration = sample_program.total_duration
        assert duration > 0

class TestComboParameters:
    @pytest.fixture
    def program_with_combo(self):
        program = ExpProgram("Combo Test")
        program.add_step(ProgStepFactory.create_cv(scan_rate=0.1))
        program.add_combo_param(ComboParameter(
            name="扫描速率",
            target_path="steps[0].ec_config.scan_rate",
            values=[0.05, 0.1, 0.2]
        ))
        return program
    
    def test_combo_count(self, program_with_combo):
        """测试组合数"""
        program_with_combo.fill_param_matrix()
        assert program_with_combo.combo_count == 3
    
    def test_multi_param_combo(self):
        """测试多参数组合"""
        program = ExpProgram()
        program.add_step(ProgStepFactory.create_cv())
        program.add_combo_param(ComboParameter(
            name="P1", target_path="steps[0].ec_config.scan_rate",
            values=[0.1, 0.2]
        ))
        program.add_combo_param(ComboParameter(
            name="P2", target_path="steps[0].ec_config.segments",
            values=[1, 2, 3]
        ))
        program.fill_param_matrix()
        # 2 x 3 = 6
        assert program.combo_count == 6
    
    def test_load_param_values(self, program_with_combo):
        """测试加载参数值"""
        program_with_combo.fill_param_matrix()
        
        program_with_combo.load_param_values(0)
        assert program_with_combo.steps[0].ec_config.scan_rate == 0.05
        
        program_with_combo.load_param_values(2)
        assert program_with_combo.steps[0].ec_config.scan_rate == 0.2

class TestSerialization:
    def test_to_dict_from_dict(self):
        """测试字典序列化"""
        program = ExpProgram("Test")
        program.add_step(ProgStepFactory.create_cv())
        
        data = program.to_dict()
        restored = ExpProgram.from_dict(data)
        
        assert restored.name == "Test"
        assert restored.step_count == 1
    
    def test_save_load(self):
        """测试文件保存加载"""
        program = ExpProgram("SaveTest")
        program.add_step(ProgStepFactory.create_flush())
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        
        try:
            program.save(path)
            loaded = ExpProgram.load(path)
            assert loaded.name == "SaveTest"
        finally:
            path.unlink()
    
    def test_validate(self):
        """测试验证"""
        program = ExpProgram()
        errors = program.validate()
        assert len(errors) > 0  # 空程序应有错误
        
        program.add_step(ProgStepFactory.create_cv())
        errors = program.validate()
        assert len(errors) == 0
```

---

## 五、JSON 格式示例

```json
{
  "name": "CV扫描速率研究",
  "description": "测试不同扫描速率下的CV响应",
  "steps": [
    {
      "step_type": "flush",
      "name": "预冲洗",
      "enabled": true,
      "flush_config": {
        "cycles": 3,
        "volume_ul": 500
      }
    },
    {
      "step_type": "prep_sol",
      "name": "配液",
      "enabled": true,
      "prep_sol_config": {
        "concentrations": {"D1": 0.5, "D2": 0.3, "D3": 0.2},
        "total_volume_ul": 100
      }
    },
    {
      "step_type": "echem",
      "name": "CV测量",
      "enabled": true,
      "ec_config": {
        "technique": "CV",
        "e_init": 0.0,
        "e_high": 0.8,
        "e_low": -0.2,
        "e_final": 0.0,
        "scan_rate": 0.1,
        "segments": 2,
        "quiet_time": 2.0
      }
    }
  ],
  "combo_params": [
    {
      "name": "扫描速率",
      "target_path": "steps[2].ec_config.scan_rate",
      "values": [0.05, 0.1, 0.2, 0.5],
      "unit": "V/s"
    }
  ]
}
```

---

## 六、验收标准

- [ ] 步骤管理（增删改移动）正确
- [ ] ComboParameter 定义正确
- [ ] 参数矩阵生成正确
- [ ] 多参数笛卡尔积正确
- [ ] load_param_values 正确设置值
- [ ] 参数路径解析正确
- [ ] 时长计算正确
- [ ] validate() 检查完整
- [ ] JSON 序列化/反序列化正确
- [ ] 文件保存/加载正确
- [ ] 单元测试覆盖率 > 90%
