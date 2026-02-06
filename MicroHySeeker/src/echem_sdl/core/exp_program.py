"""
ExpProgram - 实验程序模块

管理实验步骤集合和组合参数。
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import json
import re
from itertools import product

from .prog_step import ProgStep, StepType


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
    name: str = ""
    target_path: str = ""
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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "target_path": self.target_path,
            "values": self.values,
            "unit": self.unit,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComboParameter":
        return cls(
            name=data.get("name", ""),
            target_path=data.get("target_path", ""),
            values=data.get("values", []),
            unit=data.get("unit", ""),
        )


@dataclass
class ParamMatrix:
    """参数组合矩阵"""
    parameters: List[ComboParameter] = field(default_factory=list)
    combinations: List[List[Any]] = field(default_factory=list)
    
    @property
    def combo_count(self) -> int:
        """组合总数"""
        return len(self.combinations)
    
    def get_values_at(self, combo_index: int) -> Dict[str, Any]:
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
        self._original_values: Dict[str, Any] = {}  # 保存原始值用于恢复
        
        # 元数据
        self.created_at: str = ""
        self.modified_at: str = ""
        self.version: str = "1.0"
    
    # ========================
    # 步骤管理
    # ========================
    
    def add_step(self, step: ProgStep, index: int = -1) -> None:
        """添加步骤
        
        Args:
            step: 步骤对象
            index: 插入位置（-1 表示末尾）
        """
        if index < 0 or index >= len(self.steps):
            self.steps.append(step)
        else:
            self.steps.insert(index, step)
        self._param_matrix = None  # 清除缓存
    
    def remove_step(self, index: int) -> Optional[ProgStep]:
        """移除步骤
        
        Args:
            index: 步骤索引
            
        Returns:
            被移除的步骤
        """
        if 0 <= index < len(self.steps):
            self._param_matrix = None
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
        self._param_matrix = None
        return True
    
    def get_step(self, index: int) -> Optional[ProgStep]:
        """获取步骤"""
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None
    
    @property
    def step_count(self) -> int:
        """步骤数量"""
        return len(self.steps)
    
    @property
    def enabled_steps(self) -> List[ProgStep]:
        """获取启用的步骤"""
        return [s for s in self.steps if s.enabled]
    
    @property
    def enabled_step_count(self) -> int:
        """启用的步骤数量"""
        return len(self.enabled_steps)
    
    # ========================
    # 组合参数管理
    # ========================
    
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
    
    def fill_param_matrix(self) -> None:
        """生成参数组合矩阵
        
        使用笛卡尔积生成所有参数组合。
        """
        if not self.combo_params:
            self._param_matrix = ParamMatrix(parameters=[])
            return
        
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
        return max(1, self._param_matrix.combo_count)
    
    def get_param_values(self, combo_index: int) -> Dict[str, Any]:
        """获取指定组合的参数值"""
        if self._param_matrix is None:
            self.fill_param_matrix()
        return self._param_matrix.get_values_at(combo_index)
    
    def load_param_values(self, combo_index: int) -> bool:
        """加载指定组合的参数值到步骤中
        
        Args:
            combo_index: 组合索引
            
        Returns:
            是否成功
        """
        if self._param_matrix is None:
            self.fill_param_matrix()
        
        if not self.combo_params:
            return True  # 没有组合参数，直接返回成功
        
        if combo_index >= self.combo_count:
            return False
        
        values = self.get_param_values(combo_index)
        
        for path, value in values.items():
            try:
                self._set_value_by_path(path, value)
            except Exception:
                pass  # 忽略设置失败的参数
        
        return True
    
    def _set_value_by_path(self, path: str, value: Any) -> None:
        """通过路径设置值
        
        Args:
            path: 参数路径（如 "steps[0].ec_config.scan_rate"）
            value: 值
        """
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p]  # 移除空字符串
        
        obj: Any = self
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
    
    def _get_value_by_path(self, path: str) -> Any:
        """通过路径获取值"""
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p]
        
        obj: Any = self
        for part in parts:
            if part.isdigit():
                obj = obj[int(part)]
            else:
                obj = getattr(obj, part)
        
        return obj
    
    def _save_original_values(self) -> None:
        """保存原始参数值"""
        self._original_values.clear()
        for param in self.combo_params:
            try:
                self._original_values[param.target_path] = self._get_value_by_path(param.target_path)
            except Exception:
                pass
    
    def restore_original_values(self) -> None:
        """恢复原始参数值"""
        for path, value in self._original_values.items():
            try:
                self._set_value_by_path(path, value)
            except Exception:
                pass
    
    def get_current_params(self) -> Dict[str, Any]:
        """获取当前参数值"""
        result = {}
        for param in self.combo_params:
            try:
                result[param.name] = self._get_value_by_path(param.target_path)
            except Exception:
                result[param.name] = None
        return result
    
    # ========================
    # 统计与验证
    # ========================
    
    @property
    def total_duration(self) -> float:
        """计算总时长（单个组合）"""
        return sum(step.get_duration() for step in self.steps if step.enabled)
    
    @property
    def total_experiment_duration(self) -> float:
        """计算全部实验时长（含所有组合）"""
        return self.total_duration * self.combo_count
    
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
                errors.append(f"步骤 {i + 1}: {err}")
        
        # 验证组合参数路径
        for param in self.combo_params:
            try:
                self._get_value_by_path(param.target_path)
            except Exception:
                errors.append(f"参数路径无效: {param.target_path}")
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """获取程序摘要"""
        step_types = {}
        for step in self.steps:
            st = step.step_type.value
            step_types[st] = step_types.get(st, 0) + 1
        
        return {
            "name": self.name,
            "description": self.description,
            "step_count": self.step_count,
            "enabled_step_count": self.enabled_step_count,
            "step_types": step_types,
            "combo_param_count": len(self.combo_params),
            "combo_count": self.combo_count if self.combo_params else 1,
            "single_duration_s": self.total_duration,
            "total_duration_s": self.total_experiment_duration,
        }
    
    # ========================
    # 序列化
    # ========================
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "steps": [step.to_dict() for step in self.steps],
            "combo_params": [p.to_dict() for p in self.combo_params],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExpProgram":
        """从字典创建"""
        program = cls(
            name=data.get("name", ""),
            description=data.get("description", "")
        )
        
        program.version = data.get("version", "1.0")
        program.created_at = data.get("created_at", "")
        program.modified_at = data.get("modified_at", "")
        
        # 加载步骤
        for step_data in data.get("steps", []):
            step = ProgStep.from_dict(step_data)
            program.add_step(step)
        
        # 加载组合参数
        for param_data in data.get("combo_params", []):
            param = ComboParameter.from_dict(param_data)
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
        from datetime import datetime
        self.modified_at = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = self.modified_at
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
    
    @classmethod
    def load(cls, file_path: str | Path) -> "ExpProgram":
        """从文件加载"""
        path = Path(file_path)
        json_str = path.read_text(encoding="utf-8")
        return cls.from_json(json_str)
    
    def copy(self) -> "ExpProgram":
        """创建副本"""
        return ExpProgram.from_dict(self.to_dict())
    
    # ========================
    # 兼容前端接口
    # ========================
    
    @classmethod
    def from_frontend_experiment(cls, experiment: "Experiment") -> "ExpProgram":
        """从前端 Experiment 对象创建
        
        用于兼容现有前端数据模型
        
        Args:
            experiment: 前端 Experiment 对象
            
        Returns:
            ExpProgram 实例
        """
        program = cls(
            name=experiment.exp_name,
            description=experiment.notes
        )
        
        # 转换步骤
        for fe_step in experiment.steps:
            step = cls._convert_frontend_step(fe_step)
            program.add_step(step)
        
        return program
    
    @staticmethod
    def _convert_frontend_step(fe_step) -> ProgStep:
        """转换前端步骤到后端格式"""
        from .prog_step import (
            ProgStep, StepType, PrepSolConfig, TransferConfig,
            FlushConfig, ECConfig, BlankConfig, EvacuateConfig
        )
        
        # 映射步骤类型
        type_map = {
            "transfer": StepType.TRANSFER,
            "prep_sol": StepType.PREP_SOL,
            "flush": StepType.FLUSH,
            "echem": StepType.ECHEM,
            "blank": StepType.BLANK,
            "evacuate": StepType.EVACUATE,
        }
        
        step_type_value = fe_step.step_type.value if hasattr(fe_step.step_type, 'value') else str(fe_step.step_type)
        step_type = type_map.get(step_type_value.lower(), StepType.BLANK)
        
        step = ProgStep(
            step_type=step_type,
            name=fe_step.step_id,
            notes=fe_step.notes if hasattr(fe_step, 'notes') else "",
        )
        
        # 根据类型转换配置
        if step_type == StepType.TRANSFER:
            step.transfer_config = TransferConfig(
                pump_address=fe_step.pump_address or 1,
                volume_ul=fe_step.volume_ul or 0,
                speed_rpm=fe_step.pump_rpm or 100,
                direction=fe_step.pump_direction or "FWD",
                duration_s=fe_step.transfer_duration,
            )
        
        elif step_type == StepType.PREP_SOL and fe_step.prep_sol_params:
            params = fe_step.prep_sol_params
            # 简化：只记录目标浓度
            step.prep_sol_config = PrepSolConfig(
                concentrations={},  # 需要从通道配置获取
                total_volume_ul=params.total_volume_ul,
                injection_order=params.injection_order,
            )
        
        elif step_type == StepType.FLUSH:
            step.flush_config = FlushConfig(
                cycles=fe_step.flush_cycles or 1,
                phase_duration_s=fe_step.flush_cycle_duration_s or 10.0,
                speed_rpm=fe_step.flush_rpm or 200,
            )
        
        elif step_type == StepType.ECHEM and fe_step.ec_settings:
            ec = fe_step.ec_settings
            technique = ec.technique.value if hasattr(ec.technique, 'value') else str(ec.technique)
            step.ec_config = ECConfig(
                technique=technique,
                e_init=ec.e0 or 0.0,
                e_high=ec.eh or 0.8,
                e_low=ec.el or -0.2,
                e_final=ec.ef or 0.0,
                scan_rate=ec.scan_rate or 0.1,
                segments=ec.seg_num or 2,
                quiet_time=ec.quiet_time_s or 2.0,
                run_time=ec.run_time_s or 60.0,
                sample_interval=ec.sample_interval_ms / 1000.0 if ec.sample_interval_ms else 0.1,
                ocpt_enabled=ec.ocpt_enabled,
                ocpt_threshold_uA=ec.ocpt_threshold_uA,
                ocpt_action=ec.ocpt_action.value if hasattr(ec.ocpt_action, 'value') else "log",
            )
        
        elif step_type == StepType.BLANK:
            step.blank_config = BlankConfig(
                wait_time=fe_step.duration_s or 5.0,
            )
        
        elif step_type == StepType.EVACUATE:
            step.evacuate_config = EvacuateConfig(
                evacuate_time=fe_step.duration_s or 10.0,
                pump_address=fe_step.pump_address or 3,
            )
        
        return step
