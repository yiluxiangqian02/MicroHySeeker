"""
实验运行引擎 - 按步骤执行实验
"""
import time
import threading
from typing import List, Optional, Callable
from PySide6.QtCore import QObject, Signal, QThread

from src.models import Experiment, ProgStep, ProgramStepType, ECSettings
from src.services.rs485_wrapper import get_rs485_instance


class ExperimentRunner(QObject):
    """实验运行引擎"""
    
    # 信号
    step_started = Signal(int, str)  # step_index, step_id
    step_finished = Signal(int, str, bool)  # step_index, step_id, success
    log_message = Signal(str)
    experiment_finished = Signal(bool)  # success
    paused = Signal()
    resumed = Signal()
    
    def __init__(self):
        super().__init__()
        self.rs485 = get_rs485_instance()
        self.is_running = False
        self.is_paused = False
        self.experiment: Optional[Experiment] = None
        self.current_step_index = -1
        self._stop_flag = False
        self._pause_flag = False
        self._ocpt_triggered = False
    
    def run_experiment(self, experiment: Experiment):
        """在后台线程运行实验"""
        self.experiment = experiment
        self.current_step_index = -1
        self.is_running = True
        self._stop_flag = False
        
        thread = QThread()
        thread.run = self._run_steps
        thread.start()
    
    def _run_steps(self):
        """执行步骤"""
        if not self.experiment:
            return
        
        for i, step in enumerate(self.experiment.steps):
            if self._stop_flag:
                self.log_message.emit(f"[实验] 实验已停止")
                break
            
            self.current_step_index = i
            self.step_started.emit(i, step.step_id)
            self.log_message.emit(f"[步骤{i}] 开始执行: {step.step_type.value}")
            
            success = False
            try:
                if step.step_type == ProgramStepType.TRANSFER:
                    success = self._execute_transfer(step)
                elif step.step_type == ProgramStepType.PREP_SOL:
                    success = self._execute_prep_sol(step)
                elif step.step_type == ProgramStepType.FLUSH:
                    success = self._execute_flush(step)
                elif step.step_type == ProgramStepType.EChem:
                    success = self._execute_echem(step)
                elif step.step_type == ProgramStepType.BLANK:
                    success = True
            except Exception as e:
                self.log_message.emit(f"[错误] {str(e)}")
                success = False
            
            self.step_finished.emit(i, step.step_id, success)
            
            if not success:
                self.log_message.emit(f"[步骤{i}] 执行失败")
                break
            
            time.sleep(0.1)
        
        self.is_running = False
        self.experiment_finished.emit(True)
        self.log_message.emit(f"[实验] 完成")
    
    def _execute_transfer(self, step: ProgStep) -> bool:
        """执行移液"""
        if not step.pump_address or not step.volume_ul:
            return False
        
        pump_addr = step.pump_address
        direction = step.pump_direction or "FWD"
        rpm = step.pump_rpm or 100
        volume = step.volume_ul
        
        # 根据标定因子计算运行时间
        ul_per_sec = self.rs485._pump_states.get(pump_addr, 0.5)  # 默认 0.5 uL/s
        run_time = volume / ul_per_sec
        
        self.log_message.emit(f"  移液: {pump_addr} {direction} {rpm}RPM, 体积{volume}uL (~{run_time:.1f}s)")
        
        if not self.rs485.start_pump(pump_addr, direction, rpm):
            return False
        
        time.sleep(run_time)
        return self.rs485.stop_pump(pump_addr)
    
    def _execute_prep_sol(self, step: ProgStep) -> bool:
        """执行配液"""
        if not step.prep_sol_params:
            return False
        
        params = step.prep_sol_params
        self.log_message.emit(
            f"  配液: 目标浓度{params.target_concentration}mol/L, "
            f"注液顺序{params.injection_order}, 总体积{params.total_volume_ul}uL"
        )
        
        # 简化：只记录信息，实际配液需要根据通道配置逐一调用泵
        return True
    
    def _execute_flush(self, step: ProgStep) -> bool:
        """执行冲洗"""
        pump_addr = step.pump_address or 2
        rpm = step.flush_rpm or 100
        cycle_duration = step.flush_cycle_duration_s or 30
        cycles = step.flush_cycles or 1
        
        self.log_message.emit(f"  冲洗: 泵{pump_addr} {cycles}次, 每次{cycle_duration}s")
        
        for c in range(cycles):
            if self._stop_flag:
                return False
            
            if not self.rs485.start_pump(pump_addr, "FWD", rpm):
                return False
            
            time.sleep(cycle_duration)
            
            if not self.rs485.stop_pump(pump_addr):
                return False
            
            time.sleep(0.5)
        
        return True
    
    def _execute_echem(self, step: ProgStep) -> bool:
        """执行电化学"""
        if not step.ec_settings:
            return False
        
        ec = step.ec_settings
        self.log_message.emit(
            f"  电化学: {ec.technique.value}, E0={ec.e0}V, 采样间隔{ec.sample_interval_ms}ms"
        )
        
        if ec.ocpt_enabled:
            self.log_message.emit(f"    OCPT 已启用: 阈值={ec.ocpt_threshold_uA}μA, 动作={ec.ocpt_action.value}")
        
        # 模拟运行
        run_time = ec.run_time_s or 60
        start_time = time.time()
        sample_count = 0
        
        while time.time() - start_time < run_time:
            if self._stop_flag:
                return False
            
            # 模拟采样
            elapsed = time.time() - start_time
            sample_count += 1
            
            # 模拟 OCPT 检测
            if ec.ocpt_enabled and sample_count % 10 == 0:  # 每 10 次采样检测一次
                # 这里应该读取实际电流，现在仅模拟
                simulated_current = -30.0  # 模拟反向电流
                if simulated_current < ec.ocpt_threshold_uA:
                    self.log_message.emit(f"    [OCPT] 触发! 电流={simulated_current}μA")
                    if ec.ocpt_action.value == "abort":
                        self.log_message.emit(f"    [OCPT] 中止实验")
                        return False
                    elif ec.ocpt_action.value == "pause":
                        self.log_message.emit(f"    [OCPT] 暂停步骤")
                        # 可实现暂停对话
            
            time.sleep(ec.sample_interval_ms / 1000.0)
        
        self.log_message.emit(f"  电化学完成, 采样{sample_count}次")
        return True
    
    def stop(self):
        """停止运行"""
        self._stop_flag = True
        self.is_running = False
    
    def pause(self):
        """暂停"""
        self._pause_flag = True
        self.is_paused = True
        self.paused.emit()
    
    def resume(self):
        """恢复"""
        self._pause_flag = False
        self.is_paused = False
        self.resumed.emit()
