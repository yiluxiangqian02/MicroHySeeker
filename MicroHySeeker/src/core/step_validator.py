"""
步骤验证器 - 提供统一的步骤参数验证功能

参考 C# 源项目的验证机制，提供：
1. 实时参数验证
2. 错误和警告消息
3. 验证状态图标
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from src.models import (
    ProgStep, ProgramStepType, PrepSolStep, ECSettings, ECTechnique,
    SystemConfig, DilutionChannel
)


class ValidationLevel(Enum):
    """验证级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationMessage:
    """验证消息"""
    level: ValidationLevel
    field: str  # 相关字段
    message: str
    
    def __str__(self) -> str:
        prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(self.level.value, "")
        return f"{prefix} {self.message}"


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool = True
    messages: List[ValidationMessage] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return any(m.level == ValidationLevel.ERROR for m in self.messages)
    
    @property
    def has_warnings(self) -> bool:
        return any(m.level == ValidationLevel.WARNING for m in self.messages)
    
    @property
    def error_messages(self) -> List[str]:
        return [str(m) for m in self.messages if m.level == ValidationLevel.ERROR]
    
    @property
    def warning_messages(self) -> List[str]:
        return [str(m) for m in self.messages if m.level == ValidationLevel.WARNING]
    
    def add_error(self, field: str, message: str):
        self.messages.append(ValidationMessage(ValidationLevel.ERROR, field, message))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str):
        self.messages.append(ValidationMessage(ValidationLevel.WARNING, field, message))
    
    def add_info(self, field: str, message: str):
        self.messages.append(ValidationMessage(ValidationLevel.INFO, field, message))
    
    def merge(self, other: "ValidationResult"):
        self.messages.extend(other.messages)
        if other.has_errors:
            self.is_valid = False


class StepValidator:
    """步骤验证器"""
    
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config
        self._dilution_channels: Dict[str, DilutionChannel] = {}
        if config:
            for ch in config.dilution_channels:
                self._dilution_channels[ch.solution_name] = ch
    
    def validate_step(self, step: ProgStep) -> ValidationResult:
        """验证单个步骤"""
        validators = {
            ProgramStepType.TRANSFER: self._validate_transfer,
            ProgramStepType.PREP_SOL: self._validate_prep_sol,
            ProgramStepType.FLUSH: self._validate_flush,
            ProgramStepType.ECHEM: self._validate_echem,
            ProgramStepType.BLANK: self._validate_blank,
            ProgramStepType.EVACUATE: self._validate_evacuate,
        }
        
        validator = validators.get(step.step_type)
        if validator:
            return validator(step)
        
        result = ValidationResult()
        result.add_error("step_type", f"不支持的步骤类型: {step.step_type}")
        return result
    
    def validate_experiment(self, steps: List[ProgStep]) -> ValidationResult:
        """验证整个实验"""
        result = ValidationResult()
        
        if not steps:
            result.add_warning("steps", "实验没有任何步骤")
            return result
        
        for i, step in enumerate(steps):
            step_result = self.validate_step(step)
            for msg in step_result.messages:
                # 添加步骤索引前缀
                msg.message = f"步骤 {i+1}: {msg.message}"
            result.merge(step_result)
        
        # 检查步骤顺序逻辑
        self._validate_step_sequence(steps, result)
        
        return result
    
    def _validate_transfer(self, step: ProgStep) -> ValidationResult:
        """验证移液步骤"""
        result = ValidationResult()
        
        if not step.pump_address:
            result.add_error("pump_address", "未指定泵地址")
        elif step.pump_address < 1 or step.pump_address > 12:
            result.add_error("pump_address", f"泵地址 {step.pump_address} 超出范围 (1-12)")
        
        duration = step.transfer_duration or 0
        if duration <= 0:
            result.add_error("transfer_duration", "移液持续时间必须大于 0")
        elif duration > 3600:
            result.add_warning("transfer_duration", f"移液持续时间 {duration}s 较长，请确认")
        
        rpm = step.pump_rpm or 0
        if rpm <= 0:
            result.add_error("pump_rpm", "泵转速必须大于 0")
        elif rpm > 500:
            result.add_warning("pump_rpm", f"泵转速 {rpm} RPM 较高，请注意流速")
        
        return result
    
    def _validate_prep_sol(self, step: ProgStep) -> ValidationResult:
        """验证配液步骤"""
        result = ValidationResult()
        
        if not step.prep_sol_params:
            result.add_error("prep_sol_params", "缺少配液参数")
            return result
        
        params = step.prep_sol_params
        
        # 验证总体积
        if params.total_volume_ul <= 0:
            result.add_error("total_volume_ul", "总体积必须大于 0")
        elif params.total_volume_ul < 1000:
            result.add_warning("total_volume_ul", f"总体积 {params.total_volume_ul} μL 较小")
        
        # 验证溶液选择
        selected_count = sum(1 for v in params.selected_solutions.values() if v)
        if selected_count == 0:
            result.add_error("selected_solutions", "未选择任何溶液")
            return result
        
        # 验证溶剂
        solvent_count = sum(1 for name, is_solvent in params.solvent_flags.items()
                           if is_solvent and params.selected_solutions.get(name, False))
        if solvent_count == 0:
            result.add_warning("solvent_flags", "未指定溶剂，可能导致体积计算错误")
        elif solvent_count > 1:
            result.add_warning("solvent_flags", f"指定了 {solvent_count} 个溶剂，只有最后注入的会填充剩余体积")
        
        # 验证浓度
        total_calculated_volume = 0
        for sol_name in params.injection_order:
            if not params.selected_solutions.get(sol_name, False):
                continue
            
            if params.solvent_flags.get(sol_name, False):
                continue  # 溶剂不需要验证浓度
            
            target_conc = params.target_concentrations.get(sol_name, 0)
            if target_conc <= 0:
                result.add_warning("target_concentrations", 
                                   f"{sol_name} 目标浓度为 0，将不会注入")
                continue
            
            # 检查是否超过母液浓度
            channel = self._dilution_channels.get(sol_name)
            if channel:
                stock_conc = channel.stock_concentration
                if target_conc > stock_conc:
                    result.add_error("target_concentrations",
                                     f"{sol_name} 目标浓度 ({target_conc} M) 超过母液浓度 ({stock_conc} M)")
                
                # 计算体积
                if stock_conc > 0:
                    vol = (target_conc * params.total_volume_ul) / stock_conc
                    total_calculated_volume += vol
        
        # 检查总体积
        if total_calculated_volume > params.total_volume_ul:
            result.add_error("total_volume_ul",
                             f"计算体积 ({total_calculated_volume:.2f} μL) 超过总体积 ({params.total_volume_ul} μL)")
        
        # 检查注液顺序
        if not params.injection_order:
            result.add_error("injection_order", "注液顺序为空")
        
        return result
    
    def _validate_flush(self, step: ProgStep) -> ValidationResult:
        """验证冲洗步骤"""
        result = ValidationResult()
        
        if not step.pump_address:
            result.add_error("pump_address", "未指定泵地址")
        
        duration = step.flush_cycle_duration_s or 0
        if duration <= 0:
            result.add_error("flush_cycle_duration_s", "冲洗时长必须大于 0")
        
        cycles = step.flush_cycles or 0
        if cycles <= 0:
            result.add_error("flush_cycles", "冲洗次数必须大于 0")
        elif cycles > 10:
            result.add_warning("flush_cycles", f"冲洗 {cycles} 次可能耗时较长")
        
        return result
    
    def _validate_echem(self, step: ProgStep) -> ValidationResult:
        """验证电化学步骤"""
        result = ValidationResult()
        
        if not step.ec_settings:
            result.add_error("ec_settings", "缺少电化学参数")
            return result
        
        ec = step.ec_settings
        technique = ec.technique
        
        if not technique:
            result.add_error("technique", "未选择电化学技术")
            return result
        
        # CV/LSV 特有验证
        if technique in [ECTechnique.CV, ECTechnique.LSV]:
            if ec.eh is not None and ec.el is not None:
                if ec.eh <= ec.el:
                    result.add_error("eh/el", f"上限电位 ({ec.eh} V) 必须大于下限电位 ({ec.el} V)")
                
                # 检查电位范围
                e_range = abs(ec.eh - ec.el)
                if e_range > 3.0:
                    result.add_warning("eh/el", f"电位范围 {e_range:.2f} V 较大")
            
            if ec.scan_rate and ec.scan_rate <= 0:
                result.add_error("scan_rate", "扫描速率必须大于 0")
            elif ec.scan_rate and ec.scan_rate > 1:
                result.add_warning("scan_rate", f"扫描速率 {ec.scan_rate} V/s 较快")
            
            if ec.seg_num and ec.seg_num <= 0:
                result.add_error("seg_num", "扫描段数必须大于 0")
        
        # i-t 特有验证
        if technique == ECTechnique.I_T:
            if not ec.run_time_s or ec.run_time_s <= 0:
                result.add_error("run_time_s", "运行时间必须大于 0")
            elif ec.run_time_s > 3600:
                result.add_warning("run_time_s", f"运行时间 {ec.run_time_s} s 较长")
        
        # OCPT 验证
        if ec.ocpt_enabled:
            if ec.ocpt_threshold_uA >= 0:
                result.add_warning("ocpt_threshold_uA", 
                                   f"OCPT 阈值 {ec.ocpt_threshold_uA} μA 为正值，通常使用负值检测反向电流")
        
        return result
    
    def _validate_blank(self, step: ProgStep) -> ValidationResult:
        """验证空白步骤"""
        result = ValidationResult()
        
        duration = step.duration_s or 0
        if duration <= 0:
            result.add_warning("duration_s", "空白步骤持续时间为 0")
        elif duration > 600:
            result.add_warning("duration_s", f"空白步骤 {duration} s 较长")
        
        return result
    
    def _validate_evacuate(self, step: ProgStep) -> ValidationResult:
        """验证排空步骤"""
        result = ValidationResult()
        
        if not step.pump_address:
            result.add_error("pump_address", "未指定泵地址")
        
        duration = step.transfer_duration or 0
        if duration <= 0:
            result.add_error("transfer_duration", "排空时长必须大于 0")
        
        cycles = step.flush_cycles or 0
        if cycles <= 0:
            result.add_error("flush_cycles", "排空次数必须大于 0")
        
        return result
    
    def _validate_step_sequence(self, steps: List[ProgStep], result: ValidationResult):
        """验证步骤顺序逻辑"""
        # 检查是否有电化学步骤
        has_echem = any(s.step_type == ProgramStepType.ECHEM for s in steps)
        has_prep_sol = any(s.step_type == ProgramStepType.PREP_SOL for s in steps)
        
        if has_echem and not has_prep_sol:
            result.add_warning("sequence", "有电化学步骤但没有配液步骤")
        
        # 检查配液是否在电化学之前
        prep_sol_indices = [i for i, s in enumerate(steps) if s.step_type == ProgramStepType.PREP_SOL]
        echem_indices = [i for i, s in enumerate(steps) if s.step_type == ProgramStepType.ECHEM]
        
        if prep_sol_indices and echem_indices:
            if min(echem_indices) < min(prep_sol_indices):
                result.add_warning("sequence", "电化学步骤在配液步骤之前，可能需要先配液")
        
        # 检查连续的相同步骤
        prev_type = None
        for i, step in enumerate(steps):
            if step.step_type == prev_type and step.step_type != ProgramStepType.BLANK:
                result.add_info("sequence", f"步骤 {i} 和 {i+1} 是连续的 {step.step_type.value} 步骤")
            prev_type = step.step_type


def get_step_summary(step: ProgStep) -> str:
    """获取步骤的详细摘要"""
    if step.step_type == ProgramStepType.TRANSFER:
        duration = step.transfer_duration or 0
        rpm = step.pump_rpm or 0
        addr = step.pump_address or "?"
        direction = "正向" if step.pump_direction == "FWD" else "反向"
        return f"泵{addr} {direction} {rpm}RPM, {duration:.1f}s"
    
    elif step.step_type == ProgramStepType.PREP_SOL:
        if step.prep_sol_params:
            return step.prep_sol_params.get_summary()
        return "未配置"
    
    elif step.step_type == ProgramStepType.FLUSH:
        duration = step.flush_cycle_duration_s or 0
        cycles = step.flush_cycles or 1
        addr = step.pump_address or "?"
        return f"泵{addr}, {duration:.1f}s × {cycles}次"
    
    elif step.step_type == ProgramStepType.ECHEM:
        if step.ec_settings:
            tech = step.ec_settings.technique
            tech_name = tech.value if hasattr(tech, 'value') else str(tech)
            
            if tech in [ECTechnique.CV, ECTechnique.LSV]:
                return f"{tech_name.upper()}: {step.ec_settings.el:.2f}~{step.ec_settings.eh:.2f}V, {step.ec_settings.scan_rate}V/s"
            elif tech == ECTechnique.I_T:
                return f"i-t: E0={step.ec_settings.e0:.2f}V, {step.ec_settings.run_time_s}s"
            else:
                return tech_name.upper()
        return "未配置"
    
    elif step.step_type == ProgramStepType.BLANK:
        duration = step.duration_s or 0
        notes = step.notes or ""
        if notes:
            return f"{duration:.1f}s ({notes[:20]}...)" if len(notes) > 20 else f"{duration:.1f}s ({notes})"
        return f"{duration:.1f}s"
    
    elif step.step_type == ProgramStepType.EVACUATE:
        duration = step.transfer_duration or 0
        cycles = step.flush_cycles or 1
        addr = step.pump_address or "?"
        return f"泵{addr}, {duration:.1f}s × {cycles}次"
    
    return ""


def calculate_prep_sol_volumes(params: PrepSolStep, config: SystemConfig) -> Dict[str, Tuple[float, str]]:
    """计算配液各溶液体积
    
    Args:
        params: 配液参数
        config: 系统配置
        
    Returns:
        Dict[溶液名, (体积μL, 角色说明)]
    """
    # 构建通道查找表
    channels = {ch.solution_name: ch for ch in config.dilution_channels}
    
    volumes = {}
    total_volume_ul = params.total_volume_ul
    remaining_volume = total_volume_ul
    
    for sol_name in params.injection_order:
        if not params.selected_solutions.get(sol_name, False):
            continue
        
        is_solvent = params.solvent_flags.get(sol_name, False)
        
        if is_solvent:
            volumes[sol_name] = (remaining_volume, "溶剂-填充剩余")
        else:
            target_conc = params.target_concentrations.get(sol_name, 0.0)
            if target_conc <= 0:
                volumes[sol_name] = (0, "浓度为0")
                continue
            
            channel = channels.get(sol_name)
            if not channel:
                volumes[sol_name] = (0, "无通道配置")
                continue
            
            stock_conc = channel.stock_concentration
            if stock_conc <= 0:
                volumes[sol_name] = (0, "母液浓度为0")
                continue
            
            # C1*V1 = C2*V2 => V1 = C2*V2/C1
            vol_needed = (target_conc * total_volume_ul) / stock_conc
            volumes[sol_name] = (vol_needed, f"{target_conc}M")
            remaining_volume -= vol_needed
    
    return volumes
