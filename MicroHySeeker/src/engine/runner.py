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
    echem_result = Signal(str, list, list)  # technique, data_points, headers
    pump_batch_update = Signal(list, list)  # running_pump_addrs, waiting_pump_addrs
    
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
        self._position_calibration: Dict[int, dict] = {}  # pump_address -> {slope_k, intercept_b, ul_per_encoder_count}
        
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
                # 加载位置校准数据 (线性回归: Volume = k * revolutions + b)
                if "slope_k" in cal_data:
                    self._position_calibration[addr] = {
                        "slope_k": cal_data["slope_k"],
                        "intercept_b": cal_data.get("intercept_b", 0.0),
                        "ul_per_encoder_count": cal_data.get("ul_per_encoder_count", 0.0),
                    }
            
            # 构建配液通道信息
            for ch in config.dilution_channels:
                self._dilution_channels[ch.solution_name] = {
                    "pump_address": ch.pump_address,
                    "direction": ch.direction,
                    "stock_concentration": ch.stock_concentration,
                    "default_rpm": ch.default_rpm,
                }
            
            # 将 Inlet 泵作为 H2O 溶剂通道加入
            for ch in config.flush_channels:
                if ch.work_type == "Inlet":
                    self._dilution_channels["H2O"] = {
                        "pump_address": ch.pump_address,
                        "direction": ch.direction,
                        "stock_concentration": 0.0,
                        "default_rpm": ch.rpm,
                    }
                    break
    
    def stop(self):
        self._stop_flag = True
    
    def _emergency_stop_all_pumps(self):
        """紧急停止所有泵 — 实验中断/失败时的安全清理"""
        try:
            if self.rs485 and self.rs485.is_connected():
                self.log_message.emit("[安全] 正在停止所有泵...")
                self.rs485.stop_all()
                self.log_message.emit("[安全] 所有泵已停止")
        except Exception as e:
            self.log_message.emit(f"[安全] 停止泵异常: {e}")
    
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
        
        all_success = True
        for i, step in enumerate(self.experiment.steps):
            if self._stop_flag:
                self.log_message.emit(f"[实验] 实验已停止")
                all_success = False
                break
            
            self.step_started.emit(i, step.step_id)
            step_type_str = step.step_type.value if hasattr(step.step_type, 'value') else str(step.step_type)
            self.log_message.emit(f"[步骤{i}] 开始执行: {step_type_str}")
            
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
                all_success = False
                break
            
            time.sleep(0.1)
        
        self.experiment_finished.emit(all_success)
        status_text = "成功完成" if all_success else "执行失败"
        self.log_message.emit(f"[实验] {status_text}")
        
        # 安全清理: 实验结束/中断时停止所有泵
        if not all_success:
            self._emergency_stop_all_pumps()
    
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
        
        # 分段等待，支持中断
        if not self._interruptible_sleep(duration):
            self.rs485.stop_pump(pump_addr)
            return False
        return self.rs485.stop_pump(pump_addr)
    
    def _interruptible_sleep(self, total_seconds: float, interval: float = 0.5) -> bool:
        """可中断的等待 — 每interval秒检查一次_stop_flag
        
        Returns:
            True: 正常等完
            False: 被中断
        """
        waited = 0.0
        while waited < total_seconds:
            if self._stop_flag:
                return False
            step_wait = min(interval, total_seconds - waited)
            time.sleep(step_wait)
            waited += step_wait
        return True
    
    def _execute_prep_sol(self, step: ProgStep) -> bool:
        """执行配液 - 根据目标浓度计算各溶液体积，按注液顺序号分批注入
        
        相同注液顺序号的泵同时启动（同批次），不同顺序号按升序依次执行。
        """
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
        
        # 编码器常量
        ENCODER_DIVISIONS_PER_REV = 16384
        
        # 构建注入任务列表
        inject_tasks = []
        
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
            
            # 位置校准检查 - 优先使用位置模式，无校准时回退RPM时间模式
            pos_cal = self._position_calibration.get(pump_addr)
            use_position_mode = pos_cal and pos_cal.get("slope_k", 0) > 0
            
            encoder_counts = 0
            revolutions = 0.0
            estimated_seconds = 0.0
            
            if use_position_mode:
                # 使用位置校准计算编码器计数: Volume = k * revolutions + b
                # => revolutions = (Volume - b) / k
                slope_k = pos_cal["slope_k"]
                intercept_b = pos_cal.get("intercept_b", 0.0)
                
                revolutions = (vol - intercept_b) / slope_k
                if revolutions < 0:
                    revolutions = 0
                encoder_counts = int(revolutions * ENCODER_DIVISIONS_PER_REV)
                
                # 反向泵使用负编码器值
                if direction == "REV":
                    encoder_counts = -encoder_counts
                
                # 估算运行时间 (用于同步等待)
                estimated_seconds = (abs(revolutions) / (rpm / 60.0)) + 2.0
            else:
                # 回退: RPM 时间模式
                ul_per_sec = self._pump_calibration.get(pump_addr, 0)
                if ul_per_sec > 0:
                    run_seconds = vol / ul_per_sec
                else:
                    # 无任何校准数据，使用保守的估算 (100RPM约1.5uL/s)
                    run_seconds = vol / 1.5
                estimated_seconds = run_seconds + 2.0
                self.log_message.emit(
                    f"    ⚠ 泵 {pump_addr} ({sol_name}) 无位置校准，"
                    f"回退 RPM 时间模式 ({run_seconds:.1f}s @ {rpm}RPM)"
                )
            
            # 获取注液顺序号
            order_num = params.injection_order_numbers.get(sol_name, 1)
            
            inject_tasks.append({
                "sol_name": sol_name,
                "vol": vol,
                "pump_addr": pump_addr,
                "direction": direction,
                "rpm": rpm,
                "encoder_counts": encoder_counts,
                "revolutions": revolutions,
                "estimated_seconds": estimated_seconds,
                "order_num": order_num,
                "is_solvent": params.solvent_flags.get(sol_name, False),
                "use_position_mode": use_position_mode,
            })
        
        # 按注液顺序号分批
        batches = {}  # {order_num: [task, ...]}
        for task in inject_tasks:
            order = task["order_num"]
            if order not in batches:
                batches[order] = []
            batches[order].append(task)
        
        sorted_orders = sorted(batches.keys())
        
        # 日志：显示分批信息
        if len(sorted_orders) > 1:
            for order in sorted_orders:
                names = [t["sol_name"] for t in batches[order]]
                self.log_message.emit(f"    批次 {order}: {', '.join(names)} (同时注入)")
        
        # 逐批次执行 - 使用位置模式(位移控制)
        for batch_idx, order_num in enumerate(sorted_orders):
            if self._stop_flag:
                return False
            
            batch = batches[order_num]
            
            # 计算当前运行和等待中的泵地址
            running_addrs = [t["pump_addr"] for t in batch]
            waiting_addrs = []
            for future_order in sorted_orders[batch_idx + 1:]:
                for t in batches[future_order]:
                    waiting_addrs.append(t["pump_addr"])
            
            # 发送泵状态更新信号（运行中=绿色，等待中=黄色）
            self.pump_batch_update.emit(running_addrs, waiting_addrs)
            
            # 逐泵启动，支持位置模式或RPM时间模式
            max_wait = 0.0
            rpm_tasks = []  # 需要手动停止的RPM任务
            for task in batch:
                role = "(溶剂)" if task["is_solvent"] else ""
                
                if task.get("use_position_mode", True):
                    # 位置模式 (run_position_rel)
                    self.log_message.emit(
                        f"    注入 {task['sol_name']}{role}: "
                        f"{task['vol']:,.2f}uL, 泵{task['pump_addr']} 位移模式, "
                        f"{task['revolutions']:.2f}圈, 编码器={task['encoder_counts']}, "
                        f"{task['rpm']}RPM, 预计{task['estimated_seconds']:.1f}s"
                    )
                    
                    result = self.rs485.run_position_rel(
                        task["pump_addr"],
                        task["encoder_counts"],
                        task["rpm"],
                        acceleration=2
                    )
                    if not result:
                        self.log_message.emit(
                            f"    ❌ 泵 {task['pump_addr']} ({task['sol_name']}) 位置命令发送失败"
                        )
                        return False
                else:
                    # RPM 时间模式回退
                    self.log_message.emit(
                        f"    注入 {task['sol_name']}{role}: "
                        f"{task['vol']:,.2f}uL, 泵{task['pump_addr']} RPM时间模式, "
                        f"{task['rpm']}RPM, 预计{task['estimated_seconds']:.1f}s"
                    )
                    
                    result = self.rs485.start_pump(
                        task["pump_addr"],
                        task["direction"],
                        task["rpm"]
                    )
                    if not result:
                        self.log_message.emit(
                            f"    ❌ 泵 {task['pump_addr']} ({task['sol_name']}) 启动失败"
                        )
                        return False
                    rpm_tasks.append(task)
                
                if task["estimated_seconds"] > max_wait:
                    max_wait = task["estimated_seconds"]
            
            # 等待本批次中最长的泵完成
            if max_wait > 0:
                self.log_message.emit(f"    等待批次 {order_num} 完成... ({max_wait:.1f}s)")
                # 分段等待以支持中途停止
                waited = 0.0
                while waited < max_wait:
                    if self._stop_flag:
                        for t in batch:
                            self.rs485.stop_pump(t["pump_addr"])
                        return False
                    step_wait = min(0.5, max_wait - waited)
                    time.sleep(step_wait)
                    waited += step_wait
            
            # 停止RPM时间模式的泵
            for t in rpm_tasks:
                self.rs485.stop_pump(t["pump_addr"])
                time.sleep(0.2)
            
            for task in batch:
                self.log_message.emit(
                    f"    ✓ {task['sol_name']} 注入完成 ({task['vol']:,.2f}uL)"
                )
            
            # 批次间间隔
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
            
            if not self._interruptible_sleep(cycle_duration):
                self.rs485.stop_pump(pump_addr)
                return False
            
            if not self.rs485.stop_pump(pump_addr):
                return False
            
            time.sleep(0.5)
        
        return True
    
    def _execute_echem(self, step: ProgStep) -> bool:
        """执行电化学测量 (通过 CHI 660F GUI 控制器)
        
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
        
        # 通过 CHIBridge 调用真实 CHI 660F 仪器
        try:
            from src.echem_sdl.hardware.chi_echem_bridge import CHIBridge, CHIBridgeConfig
            
            # 从系统配置获取 CHI 路径（如有），否则使用默认
            chi_exe = r"D:\CHI660F\chi660f.exe"
            output_dir = r"D:\CHI660F\data"
            if self.config:
                chi_exe = getattr(self.config, 'chi_exe_path', chi_exe)
                output_dir = getattr(self.config, 'chi_output_dir', output_dir)
            
            # 确保输出目录存在
            import os
            os.makedirs(output_dir, exist_ok=True)
            
            # 创建或复用 Bridge
            if not hasattr(self, '_chi_bridge') or self._chi_bridge is None:
                bridge_config = CHIBridgeConfig(
                    chi_exe_path=chi_exe,
                    output_dir=output_dir,
                    use_dummy_cell=getattr(ec, 'use_dummy_cell', True),
                )
                self._chi_bridge = CHIBridge(bridge_config)
            
            if not self._chi_bridge.is_connected:
                self.log_message.emit("    正在连接 CHI 660F...")
                if not self._chi_bridge.connect():
                    self.log_message.emit("    ❌ CHI 660F 连接失败")
                    return False
                self.log_message.emit("    ✅ CHI 660F 已连接")
            
            self.log_message.emit(f"    开始 {technique.upper()} 测量...")
            result = self._chi_bridge.run(ec)
            
            if self._stop_flag:
                self._chi_bridge.stop()
                self.log_message.emit("    测量被中止")
                return False
            
            if result.success:
                self.log_message.emit(
                    f"  电化学完成: 采集 {len(result.data_points)} 个数据点, "
                    f"耗时 {result.elapsed_time:.1f}s"
                )
                if result.data_file:
                    self.log_message.emit(f"    数据文件: {result.data_file}")
                # 发射电化学结果信号，供UI显示图像
                self.echem_result.emit(
                    technique, result.data_points, result.headers
                )
                # 关闭 CHI 660F 窗口，释放资源
                try:
                    if self._chi_bridge:
                        self._chi_bridge.disconnect()
                        self._chi_bridge = None
                        self.log_message.emit("    CHI 660F 已关闭")
                except Exception as e:
                    self.log_message.emit(f"    ⚠ 关闭 CHI 660F 时出错: {e}")
                return True
            else:
                self.log_message.emit(f"    ❌ 电化学测量失败: {result.error_message}")
                return False
                
        except ImportError:
            self.log_message.emit("    ⚠ CHI Bridge 模块不可用，使用 Mock 模式")
            return self._execute_echem_mock(ec, technique)
        except Exception as e:
            self.log_message.emit(f"    ❌ 电化学异常: {e}")
            return False
    
    def _execute_echem_mock(self, ec: ECSettings, technique: str) -> bool:
        """电化学 Mock 模式 (CHI 不可用时的模拟数据采集)"""
        # 计算运行时间
        if technique in ["CV", "LSV"]:
            e_range = abs(ec.eh - ec.el) if ec.eh and ec.el else 1.0
            run_time = (e_range * (ec.seg_num or 2)) / (ec.scan_rate or 0.1)
        else:
            run_time = ec.run_time_s or 60
        
        actual_run_time = min(run_time, 10)  # Mock 模式最多运行10秒
        self.log_message.emit(f"    [Mock] 开始模拟 (预计 {run_time:.1f}s, 模拟 {actual_run_time:.1f}s)...")
        
        sample_interval = (ec.sample_interval_ms or 100) / 1000.0
        start_time = time.time()
        data_points = []
        
        while time.time() - start_time < actual_run_time:
            if self._stop_flag:
                self.log_message.emit("    [Mock] 测量被中止")
                return False
            
            elapsed = time.time() - start_time
            
            if technique == "CV":
                e_range = abs(ec.eh - ec.el) if ec.eh and ec.el else 1.0
                cycle_time = e_range / (ec.scan_rate or 0.1)
                t_in_cycle = elapsed % cycle_time
                segment = int(elapsed / cycle_time) % 2
                if segment == 0:
                    potential = (ec.el or -0.2) + (t_in_cycle / cycle_time) * e_range
                else:
                    potential = (ec.eh or 0.8) - (t_in_cycle / cycle_time) * e_range
                current = 1e-6 * (potential - 0.3) + 1e-7
            elif technique == "OCPT":
                potential = 0.2 + 0.01 * elapsed
                current = 0
            else:
                potential = ec.e0 or 0
                current = 1e-6 * (1 - 2.718 ** (-elapsed / 5))
            
            data_points.append((elapsed, potential, current))
            
            if len(data_points) % 20 == 0:
                progress = (elapsed / actual_run_time) * 100
                self.log_message.emit(f"    [Mock] 进度: {progress:.0f}% ({len(data_points)} 点)")
            
            time.sleep(sample_interval)
        
        self.log_message.emit(f"  [Mock] 电化学完成: 采集 {len(data_points)} 个数据点")
        # 发射结果信号供UI显示
        headers = ["Time/s", "Potential/V", "Current/A"]
        self.echem_result.emit(technique, data_points, headers)
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
            
            if not self._interruptible_sleep(duration):
                self.rs485.stop_pump(pump_addr)
                return False
            
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
    echem_result = Signal(str, list, list)  # technique, data_points, headers
    pump_batch_update = Signal(list, list)  # running_pump_addrs, waiting_pump_addrs
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
        self._worker.echem_result.connect(self.echem_result.emit)
        self._worker.pump_batch_update.connect(self.pump_batch_update.emit)
        
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
