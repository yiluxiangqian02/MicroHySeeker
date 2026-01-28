"""Program and step data models."""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json


@dataclass
class ProgStep:
    """单个程序步骤的数据模型。"""
    step_id: int
    step_type: str  # "配液", "电化学", "冲洗", "移液", "空白"
    step_name: str
    
    # 配液参数
    solution_type: Optional[str] = None
    high_concentration: Optional[float] = None
    target_volume: Optional[float] = None
    volume_unit: Optional[str] = None
    pump_address: Optional[int] = None
    pump_speed: Optional[float] = None
    
    # 电化学参数
    potential: Optional[float] = None
    current_limit: Optional[float] = None
    duration: Optional[float] = None
    ocpt_enabled: bool = False
    
    # 冲洗参数
    flush_pump_address: Optional[int] = None
    flush_volume: Optional[float] = None
    flush_cycles: Optional[int] = None
    flush_direction: Optional[str] = None
    
    # 移液参数
    source_well: Optional[str] = None
    target_well: Optional[str] = None
    transfer_volume: Optional[float] = None
    transfer_speed: Optional[float] = None
    
    # 空白参数
    delay_time: Optional[float] = None
    
    # 元数据
    enabled: bool = True
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgStep":
        """从字典创建实例。"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExpProgram:
    """实验程序数据模型。"""
    program_id: str
    program_name: str
    steps: List[ProgStep] = field(default_factory=list)
    ocpt_enabled: bool = False
    notes: str = ""
    created_at: str = ""
    modified_at: str = ""
    
    def add_step(self, step: ProgStep) -> None:
        """添加步骤。"""
        self.steps.append(step)
    
    def remove_step(self, step_id: int) -> None:
        """删除步骤。"""
        self.steps = [s for s in self.steps if s.step_id != step_id]
    
    def get_step(self, step_id: int) -> Optional[ProgStep]:
        """获取步骤。"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "program_id": self.program_id,
            "program_name": self.program_name,
            "ocpt_enabled": self.ocpt_enabled,
            "notes": self.notes,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "steps": [step.to_dict() for step in self.steps]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExpProgram":
        """从字典创建实例。"""
        program = cls(
            program_id=data.get("program_id", ""),
            program_name=data.get("program_name", ""),
            ocpt_enabled=data.get("ocpt_enabled", False),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", "")
        )
        for step_data in data.get("steps", []):
            program.add_step(ProgStep.from_dict(step_data))
        return program
    
    def to_json(self) -> str:
        """转换为 JSON 字符串。"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ExpProgram":
        """从 JSON 字符串创建实例。"""
        data = json.loads(json_str)
        return cls.from_dict(data)
