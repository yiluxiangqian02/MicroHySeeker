"""
echem_sdl.core - 实验引擎核心模块

包含：
- ProgStep: 程序步骤
- ExpProgram: 实验程序
- ExperimentEngine: 实验执行引擎
"""

from .prog_step import (
    StepType,
    ECTechnique,
    PrepSolConfig,
    TransferConfig,
    FlushConfig,
    ECConfig,
    BlankConfig,
    EvacuateConfig,
    ProgStep,
    ProgStepFactory,
)

from .exp_program import (
    ComboParameter,
    ParamMatrix,
    ExpProgram,
)

from .experiment_engine import (
    EngineState,
    EngineStatus,
    ExperimentResult,
    ExperimentEngine,
    EVENT_EXPERIMENT_STARTED,
    EVENT_EXPERIMENT_COMPLETED,
    EVENT_EXPERIMENT_STOPPED,
    EVENT_EXPERIMENT_ERROR,
    EVENT_STEP_STARTED,
    EVENT_STEP_COMPLETED,
    EVENT_STEP_PROGRESS,
    EVENT_COMBO_ADVANCED,
    EVENT_ECHEM_DATA,
    EVENT_STATE_CHANGED,
)

__all__ = [
    # prog_step
    "StepType",
    "ECTechnique",
    "PrepSolConfig",
    "TransferConfig",
    "FlushConfig",
    "ECConfig",
    "BlankConfig",
    "EvacuateConfig",
    "ProgStep",
    "ProgStepFactory",
    # exp_program
    "ComboParameter",
    "ParamMatrix",
    "ExpProgram",
    # experiment_engine
    "EngineState",
    "EngineStatus",
    "ExperimentResult",
    "ExperimentEngine",
    "EVENT_EXPERIMENT_STARTED",
    "EVENT_EXPERIMENT_COMPLETED",
    "EVENT_EXPERIMENT_STOPPED",
    "EVENT_EXPERIMENT_ERROR",
    "EVENT_STEP_STARTED",
    "EVENT_STEP_COMPLETED",
    "EVENT_STEP_PROGRESS",
    "EVENT_COMBO_ADVANCED",
    "EVENT_ECHEM_DATA",
    "EVENT_STATE_CHANGED",
]
