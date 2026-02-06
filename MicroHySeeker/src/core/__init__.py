"""
Core 核心模块

包含：
- exp_program: 实验程序模型
- schemas: JSON Schema 定义
- step_state: 步骤状态机 (位标志枚举)
- batch_injection: 多批次注入管理
- step_validator: 步骤验证器
- experiment_adapter: 模型适配器
"""

from .exp_program import ExpProgram, ProgStep
from .schemas import PROG_STEP_SCHEMA, EXP_PROGRAM_SCHEMA

from .step_state import (
    StepState,
    EngineState,
    StepTiming,
    BatchInfo,
    StepExecutionContext,
    estimate_step_duration,
    validate_step_params,
)

from .batch_injection import (
    InjectionChannel,
    InjectionBatch,
    BatchInjectionManager,
)

from .step_validator import (
    ValidationLevel,
    ValidationMessage,
    ValidationResult,
    StepValidator,
    get_step_summary,
    calculate_prep_sol_volumes,
)

__all__ = [
    # exp_program
    "ExpProgram",
    "ProgStep",
    "PROG_STEP_SCHEMA",
    "EXP_PROGRAM_SCHEMA",
    
    # step_state
    "StepState",
    "EngineState", 
    "StepTiming",
    "BatchInfo",
    "StepExecutionContext",
    "estimate_step_duration",
    "validate_step_params",
    
    # batch_injection
    "InjectionChannel",
    "InjectionBatch",
    "BatchInjectionManager",
    
    # step_validator
    "ValidationLevel",
    "ValidationMessage",
    "ValidationResult",
    "StepValidator",
    "get_step_summary",
    "calculate_prep_sol_volumes",
]
