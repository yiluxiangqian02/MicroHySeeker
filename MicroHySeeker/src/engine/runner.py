"""
实验运行引擎 - 按步骤执行实验
"""
import time
import threading
from typing import List, Optional, Callable, Dict
from PySide6.QtCore import QObject, Signal, QThread

from src.models import Experiment, ProgStep, ProgramStepType, ECSettings, SystemConfig
from src.services.rs485_wrapper import get_rs485_instance


class ExperimentWorker(QObject):
    """实验执行Worker - 运行在独立线程中"""
    
    step_started = Signal(int, str)  # step_index, step_id
    step_finished = Signal(int, str, bool)  # step_index, step_id, success
    log_message = Signal(str)
    experiment_finished = Signal(bool)  # success
    
    # 默认流速配置 (未校准时使用)
    # 假设管径 1.6mm，100 RPM 约 50 uL/s (基于常见蠕动泵规格)
    DEFAULT_UL_PER_SEC_AT_100RPM = 50.0  
    
    def __init__(self, experiment: Experiment, rs485, config: Optional[SystemConfig] = None):
        super().__init__()
        self.experiment = experiment
        self.rs485 = rs485
        self.config = config
        self._stop_flag = False
        
        # 构建通道查找表
        self._dilution_channels: Dict[str, dict] = {}
        self._pump_calibration: Dict[int, float] = {}  # pump_address -> ul_per_sec_at_100rpm
        
        if config:
            # 加载泵校准数据
            for pump in config.pumps:
                if pump.calibration and "ul_per_sec" in pump.calibration:
                    # 校准数据存的是 100 RPM 下的流速
                    self._pump_calibration[pump.address] = pump.calibration["ul_per_sec"]
            
            # 也从全局校准数据加载
            for addr_str, cal_data in config.calibration_data.items():
                addr = int(addr_str) if isinstance(addr_str, str) else addr_str
                if "ul_per_sec" in cal_data:
                    self._pump_calibration[addr] = cal_data["ul_per_sec"]
            
            # 构建配液通道信息
            for ch in config.dilution_channels:
                self._dilution_channels[ch.solution_name] = {
                    "pump_address": ch.pump_address,
                    "direction": ch.direction,
                    "stock_concentration": ch.stock_concentration,
                    "default_rpm": ch.default_rpm,
                }
    
    def stop(self):
        self._stop_flag = True
    
    def _get_flush_pump_addresses(self) -> set:
        """获取 Inlet/Transfer/Outlet 泵的地址集合（这些泵不需要流速校准）"""
        addrs = set()
        if self.config:
            for ch in self.config.flush_channels:
                addrs.add(ch.pump_address)
        return addrs
    
    def pre_check(self) -> list:
        """运行前预检查，返回错误消息列表（空列表表示通过）
        
        检查项目：
        1. 实验是否有步骤
        2. RS485 端口连接状态（非 Mock 模式下）
        3. 配液泵是否已校准（Inlet/Transfer/Outlet 泵不需要）
        4. 配液参数完整性（浓度、体积、泵地址）
        5. 泵地址有效性
        """
        errors = []
        warnings = []
        
        if not self.experiment or not self.experiment.steps:
            errors.append("实验没有任何步骤")
            return errors
        
        # --- 检查 RS485 连接 ---
        is_mock = self.config.mock_mode if self.config else True
        if not is_mock and not self.rs485.is_connected():
            errors.append("RS485 端口未连接。请先在配置中打开串口连接，或切换到 Mock 模式")
        
        # --- 获取不需要校准的泵地址 (Inlet/Transfer/Outlet) ---
        flush_pump_addrs = self._get_flush_pump_addresses()
        
        for i, step in enumerate(self.experiment.steps):
            step_num = i + 1
            stype = step.step_type
            
            # --- 配液步骤检查 ---
            if stype == ProgramStepType.PREP_SOL:
                if not step.prep_sol_params:
                    errors.append(f"步骤 {step_num} [配液]: 缺少配液参数")
                    continue
                
                params = step.prep_sol_params
                if params.total_volume_ul <= 0:
                    errors.append(f"步骤 {step_num} [配液]: 总体积必须大于 0")
                
                has_any_selected = False
                total_solute_vol = 0
                
                for sol_name in params.injection_order:
                    if not params.selected_solutions.get(sol_name, False):
                        continue
                    has_any_selected = True
                    is_solvent = params.solvent_flags.get(sol_name, False)
                    
                    # 检查泵配置
                    ch_info = self._dilution_channels.get(sol_name, {})
                    pump_addr = ch_info.get("pump_address", 0)
                    if pump_addr <= 0:
                        errors.append(f"步骤 {step_num} [配液]: 溶液 '{sol_name}' 没有对应的泵配置")
                        continue
                    
                    # 配液泵必须校准（不是 Inlet/Transfer/Outlet 泵）
                    if pump_addr not in flush_pump_addrs:
                        if pump_addr not in self._pump_calibration:
                            errors.append(
                                f"步骤 {step_num} [配液]: 泵 {pump_addr} ({sol_name}) 未校准流速。"
                                f"请先在配置中完成泵流速校准，否则无法准确控制注液量"
                            )
                    
                    if not is_solvent:
                        target_conc = params.target_concentrations.get(sol_name, 0)
                        stock_conc = ch_info.get("stock_concentration", 0)
                        
                        if target_conc > 0 and stock_conc > 0:
                            if target_conc > stock_conc:
                                errors.append(
                                    f"步骤 {step_num} [配液]: {sol_name} 目标浓度 "
                                    f"({target_conc}M) 超过母液浓度 ({stock_conc}M)"
                                )
                            else:
                                vol = (target_conc * params.total_volume_ul) / stock_conc
                                total_solute_vol += vol
                
                if not has_any_selected:
                    errors.append(f"步骤 {step_num} [配液]: 没有选择任何溶液")
                elif total_solute_vol > params.total_volume_ul:
                    errors.append(
                        f"步骤 {step_num} [配液]: 溶质总体积 ({total_solute_vol:,.0f}μL) "
                        f"超过总体积 ({params.total_volume_ul:,.0f}μL)"
                    )
            
            # --- 移液/冲洗/排空 步骤检查 ---
            elif stype in [ProgramStepType.TRANSFER, ProgramStepType.FLUSH, ProgramStepType.EVACUATE]:
                type_name = {ProgramStepType.TRANSFER: "移液", 
                             ProgramStepType.FLUSH: "冲洗", 
                             ProgramStepType.EVACUATE: "排空"}.get(stype, "")
                if not step.pump_address:
                    errors.append(f"步骤 {step_num} [{type_name}]: 未指定泵地址")
                elif step.pump_address < 1 or step.pump_address > 12:
                    errors.append(f"步骤 {step_num} [{type_name}]: 泵地址 {step.pump_address} 超出有效范围 (1-12)")
                
                if stype == ProgramStepType.TRANSFER:
                    if not step.transfer_duration or step.transfer_duration <= 0:
                        errors.append(f"步骤 {step_num} [移液]: 持续时间必须大于 0")
                elif stype == ProgramStepType.FLUSH:
                    if not step.flush_cycle_duration_s or step.flush_cycle_duration_s <= 0:
                        errors.append(f"步骤 {step_num} [冲洗]: 单次冲洗时长必须大于 0")
                    if not step.flush_cycles or step.flush_cycles <= 0:
                        errors.append(f"步骤 {step_num} [冲洗]: 循环次数必须大于 0")
            
            # --- 电化学步骤检查 ---
            elif stype == ProgramStepType.ECHEM:
                if not step.ec_settings:
                    errors.append(f"步骤 {step_num} [电化学]: 缺少电化学参数")
                else:
                    ec = step.ec_settings
                    tech = ec.technique
                    if hasattr(tech, 'value'):
                        tech_val = tech.value
                    else:
                        tech_val = str(tech)
                    
                    if tech_val in ["CV", "LSV"]:
                        if ec.eh is not None and ec.el is not None and ec.eh <= ec.el:
                            errors.append(
                                f"步骤 {step_num} [电化学 {tech_val}]: "
                                f"上限电位 ({ec.eh}V) 必须大于下限电位 ({ec.el}V)"
                            )
                        if not ec.scan_rate or ec.scan_rate <= 0:
                            errors.append(f"步骤 {step_num} [电化学 {tech_val}]: 扫描速率必须大于 0")
        
        return errors
    
    def _check_pump_connection(self, pump_addr: int, context: str) -> bool:
        """泵操作前检查连接状态
        
        Args:
            pump_addr: 泵地址
            context: 操作上下文（用于错误消息）
        Returns:
            True 可以继续, False 应该中止
        """
        is_mock = self.config.mock_mode if self.config else True
        if is_mock:
            return True  # Mock 模式下跳过连接检查
        
        if not self.rs485.is_connected():
            self.log_message.emit(
                f"  ❌ 错误: RS485 端口未连接，无法操作泵 {pump_addr} ({context})。"
                f"请检查串口连接后重试。"
            )
            return False
        return True
    
    def run(self):
        """执行实验步骤"""
        if not self.experiment:
            self.experiment_finished.emit(False)
            return
        
        # --- 运行前预检查 ---
        errors = self.pre_check()
        if errors:
            for err in errors:
                self.log_message.emit(f"[预检查失败] {err}")
            self.log_message.emit(f"[实验] 预检查发现 {len(errors)} 个错误，实验无法启动")
            self.experiment_finished.emit(False)
            return
        
        self.log_message.emit(f"[实验] 预检查通过，开始执行 {len(self.experiment.steps)} 个步骤")
        
        for i, step in enumerate(self.experiment.steps):
            if self._stop_flag:
                self.log_message.emit(f"[实验] 实验已停止")
                break
            
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
                elif step.step_type == ProgramStepType.ECHEM:
                    success = self._execute_echem(step)
                elif step.step_type == ProgramStepType.BLANK:
                    success = self._execute_blank(step)
                elif step.step_type == ProgramStepType.EVACUATE:
                    success = self._execute_evacuate(step)
            except Exception as e:
                self.log_message.emit(f"[错误] {str(e)}")
                success = False
            
            self.step_finished.emit(i, step.step_id, success)
            
            if not success:
                self.log_message.emit(f"[步骤{i}] 执行失败")
                break
            
            time.sleep(0.1)
        
        self.experiment_finished.emit(True)
        self.log_message.emit(f"[实验] 完成")
    
    def _execute_transfer(self, step: ProgStep) -> bool:
        """执行移液"""
        pump_addr = step.pump_address
        if not pump_addr:
            self.log_message.emit("  移液: 未指定泵地址")
            return False
        
        if not self._check_pump_connection(pump_addr, "移液"):
            return False
        
        direction = step.pump_direction or "FWD"
        rpm = step.pump_rpm or 100
        duration = step.transfer_duration or 10.0
        
        self.log_message.emit(f"  移液: 泵{pump_addr} {direction} {rpm}RPM, 持续{duration}s")
        
        if not self.rs485.start_pump(pump_addr, direction, rpm):
            self.log_message.emit(f"  ❌ 启动泵 {pump_addr} 失败，请检查硬件连接")
            return False
        
        time.sleep(duration)
        return self.rs485.stop_pump(pump_addr)
    
    def _execute_prep_sol(self, step: ProgStep) -> bool:
        """执行配液 - 根据目标浓度计算各溶液体积并依次注入"""
        if not step.prep_sol_params:
            return False
        
        params = step.prep_sol_params
        total_volume_ul = params.total_volume_ul
        
        # 构建浓度信息用于日志
        conc_info = []
        for sol_name in params.injection_order:
            if sol_name in params.selected_solutions and params.selected_solutions[sol_name]:
                conc = params.target_concentrations.get(sol_name, 0.0)
                is_solvent = params.solvent_flags.get(sol_name, False)
                if is_solvent:
                    conc_info.append(f"{sol_name}(溶剂)")
                elif conc > 0:
                    conc_info.append(f"{sol_name}:{conc:.3f}M")
        
        vol_formatted = f"{params.total_volume_ul:,.2f}uL"
        conc_str = ", ".join(conc_info) if conc_info else "无配液"
        
        self.log_message.emit(
            f"  配液: {conc_str}, "
            f"注液顺序{params.injection_order}, 总体积{vol_formatted}"
        )
        
        # 计算各溶液需要的体积
        volumes_to_inject = {}  # {溶液名: 体积(uL)}
        remaining_volume = total_volume_ul
        
        for sol_name in params.injection_order:
            if self._stop_flag:
                return False
            
            if not params.selected_solutions.get(sol_name, False):
                continue
            
            is_solvent = params.solvent_flags.get(sol_name, False)
            
            if is_solvent:
                # 溶剂：剩余体积
                volumes_to_inject[sol_name] = remaining_volume
            else:
                # 计算稀释体积: C1*V1 = C2*V2 => V1 = C2*V2/C1
                target_conc = params.target_concentrations.get(sol_name, 0.0)
                if target_conc <= 0:
                    continue
                
                # 获取母液浓度
                channel_info = self._dilution_channels.get(sol_name, {})
                stock_conc = channel_info.get("stock_concentration", target_conc)
                
                if stock_conc <= 0:
                    self.log_message.emit(f"    警告: {sol_name} 母液浓度为0，跳过")
                    continue
                
                # 计算需要的体积
                vol_needed = (target_conc * total_volume_ul) / stock_conc
                volumes_to_inject[sol_name] = vol_needed
                remaining_volume -= vol_needed
        
        # 按注液顺序依次注入
        flush_pump_addrs = self._get_flush_pump_addresses()
        
        for sol_name in params.injection_order:
            if self._stop_flag:
                return False
            
            if sol_name not in volumes_to_inject:
                continue
            
            vol = volumes_to_inject[sol_name]
            if vol <= 0:
                continue
            
            # 获取泵信息
            channel_info = self._dilution_channels.get(sol_name, {})
            pump_addr = channel_info.get("pump_address", 0)
            direction = channel_info.get("direction", "FWD")
            rpm = channel_info.get("default_rpm", 100)
            
            if pump_addr <= 0:
                self.log_message.emit(f"    ❌ {sol_name} 无对应泵配置，跳过")
                continue
            
            # 连接检查
            if not self._check_pump_connection(pump_addr, f"配液-{sol_name}"):
                return False
            
            # 校准检查（Inlet/Transfer/Outlet 泵不需要校准）
            is_calibrated = pump_addr in self._pump_calibration
            if not is_calibrated and pump_addr not in flush_pump_addrs:
                self.log_message.emit(
                    f"    ❌ 泵 {pump_addr} ({sol_name}) 未校准流速，无法准确控制注液量。"
                    f"请先完成泵流速校准。"
                )
                return False
            
            # 计算注入时间 (基于流速标定)
            ul_per_sec_at_100rpm = self._pump_calibration.get(
                pump_addr, 
                self.DEFAULT_UL_PER_SEC_AT_100RPM
            )
            # 流速与转速成正比
            ul_per_sec = ul_per_sec_at_100rpm * (rpm / 100.0)
            duration_s = vol / ul_per_sec
            
            is_solvent = params.solvent_flags.get(sol_name, False)
            role = "(溶剂)" if is_solvent else ""
            self.log_message.emit(
                f"    注入 {sol_name}{role}: "
                f"{vol:,.2f}uL, 泵{pump_addr} {direction} {rpm}RPM, "
                f"流速{ul_per_sec:.1f}uL/s, 预计{duration_s:.1f}s"
            )
            
            # 启动泵
            if not self.rs485.start_pump(pump_addr, direction, rpm):
                self.log_message.emit(f"    ❌ 启动泵 {pump_addr} ({sol_name}) 失败，请检查硬件连接")
                return False
            
            # 等待注入完成
            time.sleep(duration_s)
            
            # 停止泵
            if not self.rs485.stop_pump(pump_addr):
                self.log_message.emit(f"    警告: 停止泵{pump_addr}失败")
            
            # 注入间隔
            time.sleep(0.5)
        
        self.log_message.emit(f"  配液完成")
        return True
    
    def _execute_flush(self, step: ProgStep) -> bool:
        """执行冲洗"""
        pump_addr = step.pump_address
        if not pump_addr:
            self.log_message.emit("  冲洗: 未指定泵地址")
            return False
        
        if not self._check_pump_connection(pump_addr, "冲洗"):
            return False
        
        direction = step.pump_direction or "FWD"
        rpm = step.flush_rpm or 100
        cycle_duration = step.flush_cycle_duration_s or 30
        cycles = step.flush_cycles or 1
        
        self.log_message.emit(f"  冲洗: 泵{pump_addr} {direction} {rpm}RPM, {cycles}次, 每次{cycle_duration}s")
        
        for c in range(cycles):
            if self._stop_flag:
                return False
            
            self.log_message.emit(f"    冲洗第{c+1}次...")
            
            if not self.rs485.start_pump(pump_addr, direction, rpm):
                self.log_message.emit(f"    ❌ 启动泵 {pump_addr} 失败，请检查硬件连接")
                return False
            
            time.sleep(cycle_duration)
            
            if not self.rs485.stop_pump(pump_addr):
                return False
            
            time.sleep(0.5)
        
        return True
    
    def _execute_echem(self, step: ProgStep) -> bool:
        """执行电化学测量
        
        支持的技术:
        - CV: 循环伏安法
        - LSV: 线性扫描伏安法
        - i-t: 安培-时间曲线
        - OCPT: 开路电位测量
        """
        if not step.ec_settings:
            self.log_message.emit("  电化学: 缺少参数配置")
            return False
        
        ec = step.ec_settings
        technique = ec.technique.value if hasattr(ec.technique, 'value') else str(ec.technique)
        
        # 构建参数信息
        if technique in ["CV", "LSV"]:
            params_str = (
                f"E0={ec.e0:.2f}V, Eh={ec.eh:.2f}V, El={ec.el:.2f}V, "
                f"扫描速率={ec.scan_rate}V/s, 段数={ec.seg_num}"
            )
        elif technique in ["i-t", "IT"]:
            params_str = f"E0={ec.e0:.2f}V, 运行时间={ec.run_time_s}s"
        elif technique == "OCPT":
            params_str = f"运行时间={ec.run_time_s}s"
        else:
            params_str = f"采样间隔={ec.sample_interval_ms}ms"
        
        self.log_message.emit(f"  电化学: {technique.upper()}, {params_str}")
        
        # OCPT 监控信息
        if ec.ocpt_enabled:
            self.log_message.emit(
                f"    OCPT 监控已启用: 阈值={ec.ocpt_threshold_uA}μA, "
                f"动作={ec.ocpt_action.value if hasattr(ec.ocpt_action, 'value') else ec.ocpt_action}"
            )
        
        # 静置时间
        quiet_time = ec.quiet_time_s or 0
        if quiet_time > 0:
            self.log_message.emit(f"    静置时间: {quiet_time}s")
            start_time = time.time()
            while time.time() - start_time < quiet_time:
                if self._stop_flag:
                    return False
                time.sleep(0.5)
        
        # 计算运行时间
        if technique in ["CV", "LSV"]:
            # 基于电位范围和扫描速率计算
            e_range = abs(ec.eh - ec.el) if ec.eh and ec.el else 1.0
            run_time = (e_range * (ec.seg_num or 2)) / (ec.scan_rate or 0.1)
        else:
            run_time = ec.run_time_s or 60
        
        # 限制模拟时间（实际运行时移除此限制）
        actual_run_time = min(run_time, 10)  # Mock 模式最多运行10秒
        
        self.log_message.emit(f"    开始测量 (预计 {run_time:.1f}s, 模拟 {actual_run_time:.1f}s)...")
        
        # 模拟数据采集
        sample_interval = (ec.sample_interval_ms or 100) / 1000.0
        start_time = time.time()
        data_points = []
        
        while time.time() - start_time < actual_run_time:
            if self._stop_flag:
                self.log_message.emit(f"    测量被中止")
                return False
            
            elapsed = time.time() - start_time
            
            # 模拟数据点（实际应从 CHI 仪器读取）
            if technique == "CV":
                # 模拟 CV 波形
                cycle_time = e_range / (ec.scan_rate or 0.1)
                t_in_cycle = elapsed % cycle_time
                segment = int(elapsed / cycle_time) % 2
                if segment == 0:
                    potential = (ec.el or -0.2) + (t_in_cycle / cycle_time) * e_range
                else:
                    potential = (ec.eh or 0.8) - (t_in_cycle / cycle_time) * e_range
                current = 1e-6 * (potential - 0.3) + 1e-7  # 简化的电流响应
            elif technique == "OCPT":
                potential = 0.2 + 0.01 * elapsed  # 模拟开路电位漂移
                current = 0
            else:
                potential = ec.e0 or 0
                current = 1e-6 * (1 - 2.718 ** (-elapsed / 5))  # 衰减曲线
            
            data_points.append((elapsed, potential, current))
            
            # 定期报告进度
            if len(data_points) % 20 == 0:
                progress = (elapsed / actual_run_time) * 100
                self.log_message.emit(f"    进度: {progress:.0f}% ({len(data_points)} 点)")
            
            time.sleep(sample_interval)
        
        self.log_message.emit(f"  电化学完成: 采集 {len(data_points)} 个数据点")
        return True
    
    def _execute_blank(self, step: ProgStep) -> bool:
        """执行空白步骤"""
        duration = step.duration_s or 5.0
        self.log_message.emit(f"  空白: 等待 {duration}s")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._stop_flag:
                return False
            time.sleep(0.5)
        
        return True
    
    def _execute_evacuate(self, step: ProgStep) -> bool:
        """执行排空"""
        pump_addr = step.pump_address
        if not pump_addr:
            self.log_message.emit("  排空: 未指定泵地址")
            return False
        
        if not self._check_pump_connection(pump_addr, "排空"):
            return False
        
        direction = step.pump_direction or "FWD"
        rpm = step.pump_rpm or 100
        duration = step.transfer_duration or 30.0
        cycles = step.flush_cycles or 1
        
        self.log_message.emit(f"  排空: 泵{pump_addr} {direction} {rpm}RPM, {cycles}次, 每次{duration}s")
        
        for c in range(cycles):
            if self._stop_flag:
                return False
            
            self.log_message.emit(f"    排空第{c+1}次...")
            
            if not self.rs485.start_pump(pump_addr, direction, rpm):
                self.log_message.emit(f"    ❌ 启动泵 {pump_addr} 失败，请检查硬件连接")
                return False
            
            time.sleep(duration)
            
            if not self.rs485.stop_pump(pump_addr):
                return False
            
            time.sleep(0.5)
        
        return True


class ExperimentRunner(QObject):
    """实验运行引擎"""
    
    # 信号
    step_started = Signal(int, str)  # step_index, step_id
    step_finished = Signal(int, str, bool)  # step_index, step_id, success
    log_message = Signal(str)
    experiment_finished = Signal(bool)  # success
    paused = Signal()
    resumed = Signal()
    
    def __init__(self, config: Optional[SystemConfig] = None):
        super().__init__()
        self.rs485 = get_rs485_instance()
        self.config = config
        self.is_running = False
        self.is_paused = False
        self.experiment: Optional[Experiment] = None
        self.current_step_index = -1
        self._stop_flag = False
        self._pause_flag = False
        self._ocpt_triggered = False
        self._thread: Optional[QThread] = None
        self._worker: Optional[ExperimentWorker] = None
    
    def set_config(self, config: SystemConfig):
        """设置系统配置"""
        self.config = config
    
    def pre_check_experiment(self, experiment: Experiment) -> list:
        """在 UI 线程中运行预检查（不启动线程），返回错误列表"""
        worker = ExperimentWorker(experiment, self.rs485, self.config)
        return worker.pre_check()
    
    def run_experiment(self, experiment: Experiment):
        """在后台线程运行实验"""
        # 如果有正在运行的线程，先停止
        if self._thread and self._thread.isRunning():
            self.stop()
            self._thread.wait()
        
        self.experiment = experiment
        self.current_step_index = -1
        self.is_running = True
        self._stop_flag = False
        
        # 创建线程和worker (传入配置)
        self._thread = QThread()
        self._worker = ExperimentWorker(experiment, self.rs485, self.config)
        self._worker.moveToThread(self._thread)
        
        # 连接信号
        self._thread.started.connect(self._worker.run)
        self._worker.step_started.connect(self._on_step_started)
        self._worker.step_finished.connect(self._on_step_finished)
        self._worker.log_message.connect(self._on_log_message)
        self._worker.experiment_finished.connect(self._on_experiment_finished)
        
        # 启动线程
        self._thread.start()
    
    def _on_step_started(self, step_index: int, step_id: str):
        self.current_step_index = step_index
        self.step_started.emit(step_index, step_id)
    
    def _on_step_finished(self, step_index: int, step_id: str, success: bool):
        self.step_finished.emit(step_index, step_id, success)
    
    def _on_log_message(self, message: str):
        self.log_message.emit(message)
    
    def _on_experiment_finished(self, success: bool):
        self.is_running = False
        self.experiment_finished.emit(success)
        # 安全清理线程
        if self._thread:
            self._thread.quit()
            self._thread.wait()
    
    def stop(self):
        """停止运行"""
        self._stop_flag = True
        self.is_running = False
        if self._worker:
            self._worker.stop()
    
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
