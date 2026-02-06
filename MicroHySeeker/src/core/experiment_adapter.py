"""
实验模型适配器 - 桥接 src/models.py 和 src/echem_sdl/core/ 两套模型

将 UI 层使用的 Experiment/ProgStep 转换为 engine 层使用的 ExpProgram/ProgStep
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# UI 层模型
from src.models import (
    Experiment as UIExperiment,
    ProgStep as UIProgStep,
    ProgramStepType as UIStepType,
    PrepSolStep as UIPrepSolStep,
    ECSettings as UIECSettings,
    ECTechnique as UIECTechnique,
    SystemConfig,
)

# Engine 层模型
from src.echem_sdl.core.prog_step import (
    ProgStep as EngineProgStep,
    StepType as EngineStepType,
    PrepSolConfig,
    TransferConfig,
    FlushConfig,
    ECConfig,
    BlankConfig,
    EvacuateConfig,
)
from src.echem_sdl.core.exp_program import ExpProgram


class ModelAdapter:
    """模型适配器 - 在两套模型之间转换"""
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Args:
            config: 系统配置，用于获取通道信息
        """
        self.config = config
    
    # ========================
    # UI -> Engine 转换
    # ========================
    
    def ui_to_engine_experiment(self, ui_exp: UIExperiment) -> ExpProgram:
        """将 UI Experiment 转换为 Engine ExpProgram"""
        program = ExpProgram(
            name=ui_exp.exp_name,
            description=ui_exp.notes,
        )
        
        for ui_step in ui_exp.steps:
            engine_step = self.ui_to_engine_step(ui_step)
            program.add_step(engine_step)
        
        return program
    
    def ui_to_engine_step(self, ui_step: UIProgStep) -> EngineProgStep:
        """将 UI ProgStep 转换为 Engine ProgStep"""
        step_type = self._convert_step_type_to_engine(ui_step.step_type)
        
        engine_step = EngineProgStep(
            step_type=step_type,
            name=ui_step.step_id,
            enabled=True,
            notes=ui_step.notes,
        )
        
        # 根据类型设置配置
        if step_type == EngineStepType.PREP_SOL and ui_step.prep_sol_params:
            engine_step.prep_sol_config = self._convert_prep_sol_config(ui_step.prep_sol_params)
        
        elif step_type == EngineStepType.TRANSFER:
            engine_step.transfer_config = TransferConfig(
                pump_address=ui_step.pump_address or 1,
                direction=ui_step.pump_direction or "FWD",
                speed_rpm=ui_step.pump_rpm or 100,
                duration_s=ui_step.transfer_duration,
            )
        
        elif step_type == EngineStepType.FLUSH:
            engine_step.flush_config = FlushConfig(
                cycles=ui_step.flush_cycles or 1,
                phase_duration_s=ui_step.flush_cycle_duration_s or 30.0,
                speed_rpm=ui_step.flush_rpm or 100,
            )
        
        elif step_type == EngineStepType.ECHEM and ui_step.ec_settings:
            engine_step.ec_config = self._convert_ec_config(ui_step.ec_settings)
        
        elif step_type == EngineStepType.BLANK:
            engine_step.blank_config = BlankConfig(
                wait_time=ui_step.duration_s or 5.0,
                description=ui_step.notes,
            )
        
        elif step_type == EngineStepType.EVACUATE:
            engine_step.evacuate_config = EvacuateConfig(
                evacuate_time=ui_step.transfer_duration or 30.0,
                speed_rpm=ui_step.pump_rpm or 200,
                pump_address=ui_step.pump_address or 3,
            )
        
        return engine_step
    
    def _convert_step_type_to_engine(self, ui_type: UIStepType) -> EngineStepType:
        """步骤类型转换"""
        mapping = {
            UIStepType.PREP_SOL: EngineStepType.PREP_SOL,
            UIStepType.TRANSFER: EngineStepType.TRANSFER,
            UIStepType.FLUSH: EngineStepType.FLUSH,
            UIStepType.ECHEM: EngineStepType.ECHEM,
            UIStepType.BLANK: EngineStepType.BLANK,
            UIStepType.EVACUATE: EngineStepType.EVACUATE,
        }
        return mapping.get(ui_type, EngineStepType.BLANK)
    
    def _convert_prep_sol_config(self, ui_params: UIPrepSolStep) -> PrepSolConfig:
        """转换配液配置"""
        # 构建浓度映射
        concentrations = {}
        for sol_name, is_selected in ui_params.selected_solutions.items():
            if is_selected:
                conc = ui_params.target_concentrations.get(sol_name, 0.0)
                # 跳过溶剂（浓度为0或标记为溶剂）
                if not ui_params.solvent_flags.get(sol_name, False):
                    concentrations[sol_name] = conc
        
        return PrepSolConfig(
            concentrations=concentrations,
            total_volume_ul=ui_params.total_volume_ul,
            injection_order=ui_params.injection_order if ui_params.injection_order else None,
        )
    
    def _convert_ec_config(self, ui_ec: UIECSettings) -> ECConfig:
        """转换电化学配置"""
        technique_mapping = {
            UIECTechnique.CV: "CV",
            UIECTechnique.LSV: "LSV",
            UIECTechnique.I_T: "i-t",
            UIECTechnique.OCPT: "OCPT",
        }
        
        return ECConfig(
            technique=technique_mapping.get(ui_ec.technique, "CV"),
            e_init=ui_ec.e0 or 0.0,
            e_high=ui_ec.eh or 0.8,
            e_low=ui_ec.el or -0.2,
            e_final=ui_ec.ef or 0.0,
            scan_rate=ui_ec.scan_rate or 0.1,
            segments=ui_ec.seg_num or 2,
            quiet_time=ui_ec.quiet_time_s or 2.0,
            run_time=ui_ec.run_time_s or 60.0,
            sample_interval=ui_ec.sample_interval_ms / 1000.0 if ui_ec.sample_interval_ms else 0.001,
            ocpt_enabled=ui_ec.ocpt_enabled,
            ocpt_threshold_uA=ui_ec.ocpt_threshold_uA,
            ocpt_action=ui_ec.ocpt_action.value if ui_ec.ocpt_action else "log",
        )
    
    # ========================
    # Engine -> UI 转换
    # ========================
    
    def engine_to_ui_experiment(self, program: ExpProgram) -> UIExperiment:
        """将 Engine ExpProgram 转换为 UI Experiment"""
        ui_exp = UIExperiment(
            exp_id=program.name.replace(" ", "_").lower(),
            exp_name=program.name,
            notes=program.description,
        )
        
        for i, engine_step in enumerate(program.steps):
            ui_step = self.engine_to_ui_step(engine_step, i)
            ui_exp.steps.append(ui_step)
        
        return ui_exp
    
    def engine_to_ui_step(self, engine_step: EngineProgStep, index: int = 0) -> UIProgStep:
        """将 Engine ProgStep 转换为 UI ProgStep"""
        step_type = self._convert_step_type_to_ui(engine_step.step_type)
        
        ui_step = UIProgStep(
            step_id=engine_step.name or f"step_{index + 1}",
            step_type=step_type,
            notes=engine_step.notes,
        )
        
        # 根据类型设置参数
        if step_type == UIStepType.PREP_SOL and engine_step.prep_sol_config:
            ui_step.prep_sol_params = self._convert_prep_sol_to_ui(engine_step.prep_sol_config)
        
        elif step_type == UIStepType.TRANSFER and engine_step.transfer_config:
            cfg = engine_step.transfer_config
            ui_step.pump_address = cfg.pump_address
            ui_step.pump_direction = cfg.direction
            ui_step.pump_rpm = cfg.speed_rpm
            ui_step.transfer_duration = cfg.duration_s
            ui_step.volume_ul = cfg.volume_ul
        
        elif step_type == UIStepType.FLUSH and engine_step.flush_config:
            cfg = engine_step.flush_config
            ui_step.flush_cycles = cfg.cycles
            ui_step.flush_cycle_duration_s = cfg.phase_duration_s
            ui_step.flush_rpm = cfg.speed_rpm
        
        elif step_type == UIStepType.ECHEM and engine_step.ec_config:
            ui_step.ec_settings = self._convert_ec_to_ui(engine_step.ec_config)
        
        elif step_type == UIStepType.BLANK and engine_step.blank_config:
            ui_step.duration_s = engine_step.blank_config.wait_time
        
        elif step_type == UIStepType.EVACUATE and engine_step.evacuate_config:
            cfg = engine_step.evacuate_config
            ui_step.transfer_duration = cfg.evacuate_time
            ui_step.pump_rpm = cfg.speed_rpm
            ui_step.pump_address = cfg.pump_address
        
        return ui_step
    
    def _convert_step_type_to_ui(self, engine_type: EngineStepType) -> UIStepType:
        """步骤类型转换（反向）"""
        mapping = {
            EngineStepType.PREP_SOL: UIStepType.PREP_SOL,
            EngineStepType.TRANSFER: UIStepType.TRANSFER,
            EngineStepType.FLUSH: UIStepType.FLUSH,
            EngineStepType.ECHEM: UIStepType.ECHEM,
            EngineStepType.BLANK: UIStepType.BLANK,
            EngineStepType.EVACUATE: UIStepType.EVACUATE,
        }
        return mapping.get(engine_type, UIStepType.BLANK)
    
    def _convert_prep_sol_to_ui(self, config: PrepSolConfig) -> UIPrepSolStep:
        """转换配液配置到 UI 格式"""
        params = UIPrepSolStep(
            total_volume_ul=config.total_volume_ul,
            injection_order=config.get_injection_order(),
        )
        
        for channel_id, conc in config.concentrations.items():
            params.target_concentrations[channel_id] = conc
            params.selected_solutions[channel_id] = True
            params.solvent_flags[channel_id] = False
        
        return params
    
    def _convert_ec_to_ui(self, config: ECConfig) -> UIECSettings:
        """转换电化学配置到 UI 格式"""
        technique_mapping = {
            "CV": UIECTechnique.CV,
            "LSV": UIECTechnique.LSV,
            "i-t": UIECTechnique.I_T,
            "IT": UIECTechnique.I_T,
            "OCPT": UIECTechnique.OCPT,
        }
        
        return UIECSettings(
            technique=technique_mapping.get(config.technique, UIECTechnique.CV),
            e0=config.e_init,
            eh=config.e_high,
            el=config.e_low,
            ef=config.e_final,
            scan_rate=config.scan_rate,
            seg_num=config.segments,
            quiet_time_s=config.quiet_time,
            run_time_s=config.run_time,
            sample_interval_ms=int(config.sample_interval * 1000),
            ocpt_enabled=config.ocpt_enabled,
            ocpt_threshold_uA=config.ocpt_threshold_uA,
        )


# 单例实例
_adapter_instance: Optional[ModelAdapter] = None


def get_adapter(config: Optional[SystemConfig] = None) -> ModelAdapter:
    """获取适配器单例"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = ModelAdapter(config)
    elif config:
        _adapter_instance.config = config
    return _adapter_instance
