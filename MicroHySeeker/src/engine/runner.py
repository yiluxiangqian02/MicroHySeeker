"""
实验运行引擎 - 按步骤执行实验
"""
import logging
import time
import threading
from typing import List, Optional, Callable, Dict
from PySide6.QtCore import QObject, Signal, QThread

from src.models import Experiment, ProgStep, ProgramStepType, ECSettings, SystemConfig
from src.services.rs485_wrapper import get_rs485_instance
from src.services.experiment_data_manager import ExperimentDataManager
from src.services.app_logger import get_app_logger

_logger = get_app_logger("RUNNER")

_LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG, "INFO": logging.INFO,
    "WARNING": logging.WARNING, "ERROR": logging.ERROR,
}


class ExperimentWorker(QObject):
    """实验执行Worker - 运行在独立线程中"""
    
    step_started = Signal(int, str)  # step_index, step_id
    step_finished = Signal(int, str, bool)  # step_index, step_id, success
    log_message = Signal(str, str, str)  # message, level, source
    experiment_finished = Signal(bool)  # success
    echem_result = Signal(str, list, list)  # technique, data_points, headers
    pump_batch_update = Signal(list, list)  # running_pump_addrs, waiting_pump_addrs
    volume_updated = Signal()  # 溶液体积变更信号（扣减后通知UI刷新）
    liquid_level_update = Signal(float, float)  # (tank1_fraction, tank2_fraction) 0-1
    
    # 泵地址 → 烧杯映射：泵6 → 反应烧杯(tank2)，其余 → 混合烧杯(tank1)
    TANK2_PUMP_ADDRS = {6}
    
    # 默认流速配置 (未校准时使用)
    # 假设管径 1.6mm，100 RPM 约 50 uL/s (基于常见蠕动泵规格)
    DEFAULT_UL_PER_SEC_AT_100RPM = 50.0  
    
    def __init__(self, experiment: Experiment, rs485, config: Optional[SystemConfig] = None,
                 data_manager: Optional[ExperimentDataManager] = None):
        super().__init__()
        self.experiment = experiment
        self.rs485 = rs485
        self.config = config
        self.dm = data_manager  # 实验数据管理器
        self._stop_flag = False
        self._steps_already_finished: set = set()  # 已由内部调用 step_finished 的步骤索引
        
        # 液位动画状态 (0.0 ~ 1.0，1.0 = 虚线位置 = 完全注入)
        self._tank1_level = 0.0  # 混合烧杯 (fraction)
        self._tank2_level = 0.0  # 反应烧杯 (fraction)
        # 烧杯实际体积 (μL) — 用于 transfer/evacuate 时计算百分比上限
        self._tank1_volume_ul = 0.0  # 混合烧杯中当前溶液体积
        self._tank2_volume_ul = 0.0  # 反应烧杯中当前溶液体积
        
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
        # 尽快中断正在执行的电化学步骤，避免长时间等待超时
        try:
            if hasattr(self, '_chi_bridge') and self._chi_bridge:
                self._chi_bridge.stop()
        except Exception:
            pass
    
    def _emergency_stop_all_pumps(self):
        """紧急停止所有泵 — 实验中断/失败时的安全清理"""
        try:
            if self.rs485 and self.rs485.is_connected():
                self._emit_log("[安全] 正在停止所有泵...")
                self.rs485.stop_all()
                self._emit_log("[安全] 所有泵已停止")
        except Exception as e:
            self._emit_log(f"[安全] 停止泵异常: {e}", "ERROR")
    
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
                
                if not step.volume_ul or step.volume_ul <= 0:
                    errors.append(f"步骤 {step_num} [{type_name}]: 体积必须大于 0")
            
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
        
        # --- 溶液剩余量检查 ---
        # 累加所有 PREP_SOL 步骤中每种溶液需要的体积 (μL)
        total_needed_ul: Dict[str, float] = {}  # {sol_name: total_volume_ul}
        for step in self.experiment.steps:
            if step.step_type != ProgramStepType.PREP_SOL or not step.prep_sol_params:
                continue
            params = step.prep_sol_params
            remaining_ul = params.total_volume_ul
            for sol_name in params.injection_order:
                if not params.selected_solutions.get(sol_name, False):
                    continue
                is_solvent = params.solvent_flags.get(sol_name, False)
                if is_solvent:
                    vol = remaining_ul
                else:
                    target_conc = params.target_concentrations.get(sol_name, 0.0)
                    ch_info = self._dilution_channels.get(sol_name, {})
                    stock_conc = ch_info.get("stock_concentration", 0)
                    if target_conc > 0 and stock_conc > 0:
                        vol = (target_conc * params.total_volume_ul) / stock_conc
                        remaining_ul -= vol
                    else:
                        vol = 0
                if vol > 0:
                    total_needed_ul[sol_name] = total_needed_ul.get(sol_name, 0) + vol
        
        # 与配液通道的剩余量对比
        if self.config:
            for ch in self.config.dilution_channels:
                if ch.total_volume_ml > 0 and ch.solution_name in total_needed_ul:
                    needed_ml = total_needed_ul[ch.solution_name] / 1000.0
                    if needed_ml > ch.remaining_volume_ml:
                        errors.append(
                            f"溶液 '{ch.solution_name}' 液量不足: "
                            f"需要 {needed_ml:.2f} mL，剩余 {ch.remaining_volume_ml:.1f} mL。"
                            f"请加液后在泵状态区右键重置剩余量"
                        )
            # 也检查 Inlet 泵 (H2O溶剂) 的剩余量
            if "H2O" in total_needed_ul:
                for ch in self.config.flush_channels:
                    if ch.work_type == "Inlet" and ch.total_volume_ml not in (0, float('inf')):
                        needed_ml = total_needed_ul["H2O"] / 1000.0
                        if needed_ml > ch.remaining_volume_ml:
                            errors.append(
                                f"溶剂 'H2O'(Inlet) 液量不足: "
                                f"需要 {needed_ml:.2f} mL，剩余 {ch.remaining_volume_ml:.1f} mL。"
                                f"请加液后在泵状态区右键重置剩余量"
                            )
                        break
        
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
            self._emit_log(
                f"  ❌ 错误: RS485 端口未连接，无法操作泵 {pump_addr} ({context})。"
                f"请检查串口连接后重试。", "ERROR"
            )
            return False
        return True
    
    def _emit_log(self, msg: str, level: str = "INFO", source: str = "RUNNER"):
        """统一日志：同时发信号到UI + 写文件日志 + 写实验运行日志"""
        normalized = (level or "INFO").upper()
        self.log_message.emit(msg, normalized, source)
        _logger.log(_LOG_LEVEL_MAP.get(normalized, logging.INFO), msg)
        if self.dm:
            self.dm.log(normalized, source, msg)

    def _build_compact_snapshot(self) -> dict:
        """构建精简的系统快照（去除冗余泵配置，只保留关键信息）"""
        if not self.config:
            return {}
        snapshot = {
            "rs485_port": getattr(self.config, 'rs485_port', ''),
            "rs485_baudrate": getattr(self.config, 'rs485_baudrate', 38400),
            "mock_mode": getattr(self.config, 'mock_mode', True),
            "data_dir": getattr(self.config, 'data_dir', './data'),
            "chi_exe_path": getattr(self.config, 'chi_exe_path', ''),
        }
        # 泵配置精简：只保留 address/name/direction/calibration
        pumps_compact = []
        for p in getattr(self.config, 'pumps', []):
            p_dict = p.to_dict() if hasattr(p, 'to_dict') else (p if isinstance(p, dict) else {})
            pumps_compact.append({
                "address": p_dict.get("address", 0),
                "name": p_dict.get("name", ""),
                "direction": p_dict.get("direction", "FWD"),
                "default_rpm": p_dict.get("default_rpm", 100),
                "ul_per_sec": p_dict.get("calibration", {}).get("ul_per_sec", 0),
            })
        snapshot["pumps_summary"] = pumps_compact
        # 稀释通道配置
        dilution = getattr(self.config, 'dilution_channels', [])
        if dilution:
            snapshot["dilution_channels_count"] = len(dilution)
        # 冲洗通道配置
        flush = getattr(self.config, 'flush_channels', [])
        if flush:
            snapshot["flush_channels_count"] = len(flush)
        return snapshot

    # ----------------------------------------------------------
    # 时长预估
    # ----------------------------------------------------------

    def _estimate_pump_duration(self, pump_addr: int, volume_ul: float, rpm: int) -> float:
        """估算单泵运行时间（秒），基于校准数据或保守估算"""
        if volume_ul <= 0:
            return 0.0
        pos_cal = self._position_calibration.get(pump_addr)
        if pos_cal and pos_cal.get("slope_k", 0) > 0:
            revolutions = (volume_ul - pos_cal.get("intercept_b", 0.0)) / pos_cal["slope_k"]
            if revolutions < 0:
                revolutions = 0
            return abs(revolutions) / (rpm / 60.0) + 2.0
        ul_per_sec = self._pump_calibration.get(pump_addr, 0)
        if ul_per_sec > 0:
            return volume_ul / ul_per_sec + 2.0
        return volume_ul / self.DEFAULT_UL_PER_SEC_AT_100RPM * (100.0 / max(rpm, 1)) + 2.0

    def _estimate_step_duration(self, step) -> float:
        """估算单步骤执行时间（秒）"""
        st = step.step_type

        # BLANK
        if st == ProgramStepType.BLANK:
            return step.duration_s or 5.0

        # TRANSFER / EVACUATE
        if st in (ProgramStepType.TRANSFER, ProgramStepType.EVACUATE):
            vol = step.volume_ul or 0
            rpm = step.pump_rpm or 100
            addr = step.pump_address or 0
            return self._estimate_pump_duration(addr, vol, rpm) if vol > 0 else 5.0

        # FLUSH
        if st == ProgramStepType.FLUSH:
            vol = step.volume_ul or 0
            rpm = step.flush_rpm or step.pump_rpm or 100
            addr = step.pump_address or 0
            cycles = max(step.flush_cycles, 1) if step.flush_cycles else 1
            per_cycle = self._estimate_pump_duration(addr, vol, rpm) if vol > 0 else (step.flush_cycle_duration_s or 30.0)
            return per_cycle * cycles

        # PREP_SOL
        if st == ProgramStepType.PREP_SOL and step.prep_sol_params:
            return self._estimate_prep_sol_duration(step.prep_sol_params)

        # ECHEM
        if st == ProgramStepType.ECHEM and step.ec_settings:
            return self._estimate_echem_duration(step.ec_settings)

        return 10.0  # 未知步骤保守估计

    def _estimate_prep_sol_duration(self, params) -> float:
        """估算配液步骤总时长（考虑批次并行）"""
        total_volume_ul = params.total_volume_ul
        if total_volume_ul <= 0:
            return 0.0

        # 计算各溶液体积（简化版两遍扫描）
        remaining = total_volume_ul
        solvent_names = []
        tasks = {}  # {sol_name: (vol_ul, order_num)}

        for sol_name in params.injection_order:
            if not params.selected_solutions.get(sol_name, False):
                continue
            if params.solvent_flags.get(sol_name, False):
                solvent_names.append(sol_name)
                continue
            tc = params.target_concentrations.get(sol_name, 0.0)
            if tc <= 0:
                continue
            ch = self._dilution_channels.get(sol_name)
            sc = ch["stock_concentration"] if ch else 1.0
            vol = (tc / sc) * total_volume_ul if sc > 0 else 0
            remaining -= vol
            order_num = params.injection_order_numbers.get(sol_name, 1)
            pump_addr = ch["pump_address"] if ch else 0
            rpm = ch.get("default_rpm", 100) if ch else 100
            tasks[sol_name] = (vol, order_num, pump_addr, rpm)

        # 分配溶剂
        if remaining > 0 and solvent_names:
            per_solvent = remaining / len(solvent_names)
            for sn in solvent_names:
                order_num = params.injection_order_numbers.get(sn, 1)
                ch = self._dilution_channels.get(sn)
                pump_addr = ch["pump_address"] if ch else 0
                rpm = ch.get("default_rpm", 100) if ch else 100
                tasks[sn] = (per_solvent, order_num, pump_addr, rpm)

        # 按批次分组，每批取 max
        from collections import defaultdict
        batches = defaultdict(list)
        for sol_name, (vol, order_num, pump_addr, rpm) in tasks.items():
            est = self._estimate_pump_duration(pump_addr, vol, rpm)
            batches[order_num].append(est)

        return sum(max(durations) for durations in batches.values()) if batches else 0.0

    def _estimate_echem_duration(self, ec) -> float:
        """估算电化学步骤时长"""
        tech = ec.technique.value if hasattr(ec.technique, 'value') else str(ec.technique)

        if tech == "ADT":
            cyc = ec.adt_num_cycles or 100
            tc = ec.adt_cathodic_duration_s or 3.0
            ta = ec.adt_cp_anodic_time_s or 3.0
            return cyc * (tc + ta)

        if tech == "i-t" and ec.run_time_s:
            return ec.run_time_s + (ec.quiet_time_s or 0)

        scan_rate = ec.scan_rate or 0.1
        if tech == "CV":
            eh = ec.eh or 0.8
            el = ec.el or -0.2
            seg = ec.seg_num or 2
            return abs(eh - el) * seg / scan_rate + (ec.quiet_time_s or 0)

        if tech == "LSV":
            e0 = ec.e0 or 0.0
            ef = ec.ef or 0.8
            return abs(ef - e0) / scan_rate + (ec.quiet_time_s or 0)

        if tech == "EIS":
            return 60.0  # EIS duration hard to predict

        return 30.0  # fallback

    def _estimate_total_duration(self, experiment) -> float:
        """估算整个实验的总时长（秒）"""
        total = 0.0
        for step in experiment.steps:
            total += self._estimate_step_duration(step)
        return total

    def run(self):
        """执行实验步骤"""
        if not self.experiment:
            self.experiment_finished.emit(False)
            return
        
        # 液位归零
        self._tank1_level = 0.0
        self._tank2_level = 0.0
        self._tank1_volume_ul = 0.0
        self._tank2_volume_ul = 0.0
        self._emit_tank_levels()
        
        # --- 数据管理：开始运行 ---
        if self.dm:
            system_snapshot = self._build_compact_snapshot()
            self.dm.begin_run(
                exp_name=self.experiment.exp_name,
                exp_dict=self.experiment.to_dict(),
                system_snapshot=system_snapshot,
                operator=getattr(self.experiment, 'operator', ''),
            )
        
        # --- 运行前预检查 ---
        errors = self.pre_check()
        if errors:
            for err in errors:
                self._emit_log(f"[预检查失败] {err}", "ERROR")
            self._emit_log(f"[实验] 预检查发现 {len(errors)} 个错误，实验无法启动", "ERROR")
            if self.dm:
                self.dm.end_run(success=False)
            self.experiment_finished.emit(False)
            return
        
        self._emit_log(f"[实验] 预检查通过，开始执行 {len(self.experiment.steps)} 个步骤")
        
        # ---- 预估总时长 ----
        try:
            est_total = self._estimate_total_duration(self.experiment)
            if est_total > 0:
                h, rem = divmod(int(est_total), 3600)
                m, s = divmod(rem, 60)
                if h > 0:
                    est_str = f"{h}h{m:02d}m{s:02d}s"
                elif m > 0:
                    est_str = f"{m}m{s:02d}s"
                else:
                    est_str = f"{s}s"
                self._emit_log(f"[实验] 预估总时长: {est_str}")
        except Exception:
            pass
        
        all_success = True
        try:
            # 将步骤按并行组分段: 连续的 parallel_group=0 各自独立执行,
            # 连续的相同 parallel_group>0 步骤合并为一个并行段
            execution_segments = self._build_execution_segments(self.experiment.steps)
            
            for segment in execution_segments:
                if self._stop_flag:
                    self._emit_log(f"[实验] 实验已停止", "WARNING")
                    all_success = False
                    break
                
                if len(segment) == 1:
                    # 单步串行执行（兼容原流程）
                    i, step = segment[0]
                    success = self._execute_single_step(i, step)
                    if not success:
                        all_success = False
                        break
                else:
                    # 并行组执行
                    group_id = segment[0][1].parallel_group
                    step_indices = [s[0] for s in segment]
                    self._emit_log(
                        f"[并行组{group_id}] 同时执行步骤 "
                        f"{', '.join(str(idx+1) for idx in step_indices)}"
                    )
                    success = self._execute_parallel_segment(segment)
                    if not success:
                        all_success = False
                        break
                
                time.sleep(0.1)
        except Exception as e:
            self._emit_log(f"[实验] 未预期的异常: {e}", "ERROR")
            import traceback
            self._emit_log(f"[实验] 堆栈: {traceback.format_exc()}", "DEBUG")
            all_success = False
        finally:
            # 安全清理: 每步独立 try 保护，确保后续步骤不被前面的异常阻断
            try:
                if not all_success:
                    self._emergency_stop_all_pumps()
            except Exception as e:
                self._emit_log(f"[安全] 停泵异常: {e}", "ERROR")

            try:
                self._cleanup_chi_bridge()
            except Exception as e:
                self._emit_log(f"[安全] CHI清理异常: {e}", "ERROR")

            # 数据管理：结束运行 — 必须在信号之前，保证日志落盘
            try:
                if self.dm:
                    self.dm.end_run(success=all_success)
            except Exception as e:
                self._emit_log(f"[安全] 数据保存异常: {e}", "ERROR")
            
            status_text = "成功完成" if all_success else "执行失败"
            self._emit_log(f"[实验] {status_text}")
            
            # 信号放在最后：确保泵已停止、数据已保存后 UI 才更新
            self.experiment_finished.emit(all_success)

    # ── 并行执行基础设施 ──────────────────────────────────

    @staticmethod
    def _build_execution_segments(steps: list) -> list:
        """将步骤列表按并行组分段。
        
        - parallel_group == 0 的步骤各自独立成段（串行）
        - 连续的相同 parallel_group > 0 步骤合并为一段（并行）
        
        Returns:
            list of segments, 每段是 [(index, step), ...] 的列表
        """
        segments = []
        current_group = None
        current_segment = []

        for i, step in enumerate(steps):
            pg = getattr(step, 'parallel_group', 0) or 0
            if pg == 0:
                # 串行步骤：先保存之前未完成的并行段
                if current_segment:
                    segments.append(current_segment)
                    current_segment = []
                    current_group = None
                segments.append([(i, step)])
            elif pg == current_group:
                # 继续当前并行组
                current_segment.append((i, step))
            else:
                # 新的并行组或第一个并行步骤
                if current_segment:
                    segments.append(current_segment)
                current_group = pg
                current_segment = [(i, step)]

        if current_segment:
            segments.append(current_segment)

        return segments

    def _execute_single_step(self, i: int, step) -> bool:
        """执行单个步骤（串行模式，兼容原逻辑）"""
        step_type_str = step.step_type.value if hasattr(step.step_type, 'value') else str(step.step_type)

        self.step_started.emit(i, step.step_id)
        self._emit_log(f"[步骤{i}] 开始执行: {step_type_str}")

        if self.dm:
            self.dm.step_started(i, step.step_id, step_type_str,
                                 details=step.notes or "")

        success = False
        step_error_msg = ""
        try:
            success = self._dispatch_step(step, step_index=i)
        except Exception as e:
            step_error_msg = str(e)
            self._emit_log(f"[错误] {step_error_msg}", "ERROR")
            success = False

        if self.dm and i not in self._steps_already_finished:
            if success:
                self.dm.step_finished(i, True)
            else:
                error_detail = step_error_msg or f"{step_type_str} 执行失败"
                self.dm.step_finished(i, False, details=error_detail)
                self.dm.log_error(f"步骤{i} [{step_type_str}] 失败: {error_detail}")

        self.step_finished.emit(i, step.step_id, success)

        if not success:
            self._emit_log(f"[步骤{i}] 执行失败", "ERROR")
        return success

    def _dispatch_step(self, step, step_index: int = -1) -> bool:
        """根据步骤类型分派执行"""
        if step.step_type == ProgramStepType.TRANSFER:
            return self._execute_transfer(step)
        elif step.step_type == ProgramStepType.PREP_SOL:
            return self._execute_prep_sol(step, step_index=step_index)
        elif step.step_type == ProgramStepType.FLUSH:
            return self._execute_flush(step)
        elif step.step_type == ProgramStepType.ECHEM:
            return self._execute_echem(step, step_index=step_index)
        elif step.step_type == ProgramStepType.BLANK:
            return self._execute_blank(step)
        elif step.step_type == ProgramStepType.EVACUATE:
            return self._execute_evacuate(step)
        return False

    def _execute_parallel_segment(self, segment: list) -> bool:
        """并行执行一组步骤。
        
        每个步骤在独立的 threading.Thread 中运行。
        任一步骤失败 → 设置 _stop_flag 停止其余步骤。
        全部完成后汇总结果。
        
        Args:
            segment: [(index, step), ...] — 要并行执行的步骤列表
        """
        import threading

        # 先发出所有步骤的开始信号
        for i, step in segment:
            step_type_str = step.step_type.value if hasattr(step.step_type, 'value') else str(step.step_type)
            self.step_started.emit(i, step.step_id)
            self._emit_log(f"[步骤{i}] 开始执行: {step_type_str} (并行)")
            if self.dm:
                self.dm.step_started(i, step.step_id, step_type_str,
                                     details=step.notes or "")

        results = {}  # index → (success, error_msg)
        lock = threading.Lock()

        def _run_step(idx: int, step_obj):
            success = False
            error_msg = ""
            try:
                success = self._dispatch_step(step_obj, step_index=idx)
            except Exception as e:
                error_msg = str(e)
                self._emit_log(f"[错误] 步骤{idx} 异常: {error_msg}", "ERROR")
            with lock:
                results[idx] = (success, error_msg)

        threads = []
        for i, step in segment:
            t = threading.Thread(
                target=_run_step,
                args=(i, step),
                name=f"ParallelStep-{i}",
                daemon=True,
            )
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 汇总结果并发出完成信号
        all_ok = True
        for i, step in segment:
            success, error_msg = results.get(i, (False, "未执行"))
            step_type_str = step.step_type.value if hasattr(step.step_type, 'value') else str(step.step_type)

            if self.dm and i not in self._steps_already_finished:
                if success:
                    self.dm.step_finished(i, True)
                else:
                    detail = error_msg or f"{step_type_str} 执行失败"
                    self.dm.step_finished(i, False, details=detail)
                    self.dm.log_error(f"步骤{i} [{step_type_str}] 失败: {detail}")

            self.step_finished.emit(i, step.step_id, success)

            if not success:
                self._emit_log(f"[步骤{i}] 执行失败", "ERROR")
                all_ok = False

        return all_ok

    # ── 步骤执行方法 ──────────────────────────────────
    
    def _execute_transfer(self, step: ProgStep) -> bool:
        """执行移液 - 位移模式(编码器闭环) + RPM时间模式回退
        
        百分比逻辑:
        - 混合烧杯(tank1): 从当前→0%, 按 min(1, 泵体积/混合烧杯体积) 线性递减
        - 反应烧杯(tank2): 从当前→100%, 按 已转移/混合烧杯体积 递增, cap 100%
        - 若泵设定体积 > 混合烧杯体积(常见，为保证全部转移), 液体在到达0%/100%后保持
        """
        pump_addr = step.pump_address
        if not pump_addr:
            self._emit_log("  移液: 未指定泵地址")
            return False
        
        if not self._check_pump_connection(pump_addr, "移液"):
            return False
        
        direction = step.pump_direction or "FWD"
        rpm = step.pump_rpm or 100
        volume_ul = step.volume_ul or 0
        
        if volume_ul <= 0:
            self._emit_log("  移液: 体积为0，跳过")
            return True
        
        # 液位动画 (tank1 → tank2)
        # 计算有效比例: 混合烧杯实际液量 vs 泵设定转移量
        mixing_vol = self._tank1_volume_ul  # 混合烧杯中实际溶液
        t1_start = self._tank1_level
        t2_start = self._tank2_level
        
        if mixing_vol > 0 and volume_ul > mixing_vol:
            # 泵体积 > 混合烧杯体积 → 液体在 cap_frac 处就全部转移完毕
            cap_frac = mixing_vol / volume_ul  # <1.0
        else:
            cap_frac = 1.0  # 正常: 泵体积 ≤ 混合烧杯体积
        
        t1_end = 0.0
        # 反应烧杯最终液位 = 原有 + 混合烧杯中全部液量(转移过来)
        # 用分数: t2_start + t1_start 表示全部倒过来
        t2_end = min(1.0, t2_start + t1_start)
        
        result = self._run_single_pump_position(
            pump_addr, direction, rpm, volume_ul,
            label="移液",
            t1_start=t1_start, t1_end=t1_end,
            t2_start=t2_start, t2_end=t2_end,
            cap_frac=cap_frac,
        )
        
        # 更新体积跟踪: 混合烧杯清空, 反应烧杯增加
        if result:
            transferred = min(mixing_vol, volume_ul) if mixing_vol > 0 else volume_ul
            self._tank2_volume_ul += transferred
            self._tank1_volume_ul = max(0, self._tank1_volume_ul - transferred)
        
        return result
    
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
    
    # ── 泵命令验证辅助 ─────────────────────────────────

    # 编码器最小变化阈值 (16384 counts/rev; 100 counts ≈ 0.006 rev)
    _ENCODER_MIN_DELTA = 100
    # 编码器采样间隔(秒) — 越长越准确但延迟也越高
    _ENCODER_CHECK_INTERVAL = 0.4

    def _verify_pump_running(self, pump_addr: int, settle_s: float = 0.5) -> bool:
        """验证泵是否 **物理** 在运行 — 双重校验

        第 1 层: 控制器状态寄存器 (read_run_status, status∈{2,3,4})
        第 2 层: 编码器位置变化 Δ > _ENCODER_MIN_DELTA (多次重试)

        仅当两层均通过时返回 True。
        编码器读取失败时会重试最多 3 次；若始终失败则判定为未确认运行
        (不再盲目降级信任控制器状态，因为控制器可在泵堵转/未连接时仍报"运行")。
        
        Note:
            settle_s 从 0.35s 增至 0.5s，给从空闲状态唤醒的泵更多启动时间。
        """
        time.sleep(settle_s)

        # ——— Layer 1: 控制器状态寄存器 ———
        status = self.rs485.read_run_status(pump_addr)
        if status is None:
            time.sleep(0.2)
            status = self.rs485.read_run_status(pump_addr)
        if status not in (2, 3, 4):
            self._emit_log(
                f"  ⓘ 泵{pump_addr} 控制器状态={status}(非运行)",
                "DEBUG"
            )
            return False

        # ——— Layer 2: 编码器位置变化 (含重试) ———
        MAX_ENC_RETRIES = 3
        enc_fail_count = 0

        for enc_try in range(MAX_ENC_RETRIES):
            if enc_try > 0:
                time.sleep(0.2)  # 重试间隔，让总线稳定

            pos1 = self.rs485.read_encoder_position(pump_addr)
            if pos1 is None:
                enc_fail_count += 1
                self._emit_log(
                    f"  ⚠ 泵{pump_addr} 编码器读取失败 "
                    f"(尝试{enc_try + 1}/{MAX_ENC_RETRIES})",
                    "WARNING"
                )
                continue

            time.sleep(self._ENCODER_CHECK_INTERVAL)

            pos2 = self.rs485.read_encoder_position(pump_addr)
            if pos2 is None:
                enc_fail_count += 1
                self._emit_log(
                    f"  ⚠ 泵{pump_addr} 编码器第二次读取失败 "
                    f"(尝试{enc_try + 1}/{MAX_ENC_RETRIES})",
                    "WARNING"
                )
                continue

            delta = abs(pos2 - pos1)
            if delta >= self._ENCODER_MIN_DELTA:
                self._emit_log(
                    f"  ⓘ 泵{pump_addr} 编码器Δ={delta}"
                    f"(>{self._ENCODER_MIN_DELTA}) ✓ 物理运转确认",
                    "DEBUG"
                )
                return True

            # 编码器可读但无变化 → 延长采样再试
            self._emit_log(
                f"  ⚠ 泵{pump_addr} 控制器报运行(status={status})"
                f"但编码器Δ={delta}≤阈值, 延长采样...",
                "WARNING"
            )
            time.sleep(self._ENCODER_CHECK_INTERVAL * 2)
            pos3 = self.rs485.read_encoder_position(pump_addr)
            if pos3 is not None:
                delta2 = abs(pos3 - pos1)
                if delta2 >= self._ENCODER_MIN_DELTA:
                    self._emit_log(
                        f"  ✓ 泵{pump_addr} 延长采样后编码器Δ={delta2} 确认运转"
                    )
                    return True

            # 编码器确认：泵未运动
            self._emit_log(
                f"  ❌ 泵{pump_addr} 控制器报运行但编码器无变化 → 判定未运动 "
                f"(Δ={delta}, pos1={pos1}, pos2={pos2})",
                "ERROR"
            )
            return False

        # 所有编码器读取尝试均失败 → 不降级，返回 False
        self._emit_log(
            f"  ❌ 泵{pump_addr} 编码器连续{enc_fail_count}次读取失败，"
            f"无法确认物理运转(控制器状态={status}，但不可信) — 判定未启动",
            "ERROR"
        )
        return False

    def _verify_pump_stopped(self, pump_addr: int, settle_s: float = 0.25) -> bool:
        """验证泵是否已停止 — 双重校验

        第 1 层: 控制器状态 == 1 (停止)。若为 3 (减速中)，等待最多 3s。
        第 2 层: 编码器位置稳定 (两次读数差 < 阈值)
        若控制器状态异常但编码器确认物理停止，仍判定为已停止。
        """
        time.sleep(settle_s)

        # Layer 1: 控制器状态
        status = self.rs485.read_run_status(pump_addr)
        if status is None:
            time.sleep(0.2)
            status = self.rs485.read_run_status(pump_addr)
        # 通信失败视为已停止(安全侧)
        if status is None:
            return True
        # 减速中(3) → 额外等待最多 3s 让泵完全停止
        if status == 3:
            for _ in range(6):
                time.sleep(0.5)
                status = self.rs485.read_run_status(pump_addr)
                if status is None or status == 1:
                    break
        if status is None or status == 1:
            pass  # 控制器确认已停止，继续做编码器校验
        else:
            # 控制器仍报非停止状态，但可能是寄存器刷新延迟，
            # 回退到编码器物理稳定性判断
            pos1 = self.rs485.read_encoder_position(pump_addr)
            if pos1 is None:
                return True  # 读不到编码器 → 安全侧
            time.sleep(0.3)
            pos2 = self.rs485.read_encoder_position(pump_addr)
            if pos2 is None:
                return True
            delta = abs(pos2 - pos1)
            if delta < self._ENCODER_MIN_DELTA:
                self._emit_log(
                    f"  ⚠ 泵{pump_addr} 控制器状态={status}(非停止)但编码器已稳定(Δ={delta})，"
                    f"判定为物理停止",
                    "WARNING"
                )
                return True
            # 编码器也确认仍在运动
            return False

        # Layer 2: 编码器位置稳定性验证
        pos1 = self.rs485.read_encoder_position(pump_addr)
        if pos1 is None:
            return True  # 读不到编码器 → 信任控制器
        time.sleep(0.15)
        pos2 = self.rs485.read_encoder_position(pump_addr)
        if pos2 is None:
            return True

        delta = abs(pos2 - pos1)
        if delta < self._ENCODER_MIN_DELTA:
            return True  # 位置稳定 ✓

        self._emit_log(
            f"  ⚠ 泵{pump_addr} 控制器报停止(status=1)但编码器仍在变化 Δ={delta}",
            "WARNING"
        )
        return False

    def _start_pump_verified(self, pump_addr: int, direction: str, rpm: int,
                             label: str = "", max_retries: int = 3) -> bool:
        """启动泵并验证实际物理运转 — 失败时自动重试 + 故障清除 + 重使能

        验证依赖 _verify_pump_running (控制器状态 + 编码器Δ)
        
        Note:
            max_retries 从 2 增至 3，给空闲唤醒后的泵更多重试机会。
        Returns:
            True = 泵已确认物理运转, False = 多次重试仍无法启动
        """
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self._emit_log(
                    f"  🔄 {label} 泵{pump_addr} 启动重试 {attempt}/{max_retries}",
                    "WARNING"
                )
                # 尝试清除故障 + 重新使能电机
                fault = self.rs485.read_pump_fault(pump_addr)
                if fault and fault != 0:
                    self._emit_log(
                        f"  ⚠ 泵{pump_addr} 故障码 0x{fault:02X}，尝试清除 + 重使能",
                        "WARNING"
                    )
                    self.rs485.clear_pump_stall(pump_addr)
                    time.sleep(0.2)
                    # 重使能电机 (disable → enable)
                    self.rs485.enable_motor(pump_addr, False)
                    time.sleep(0.15)
                    self.rs485.enable_motor(pump_addr, True)
                    time.sleep(0.3)
                else:
                    # 无故障码但上次启动失败 → 也尝试重使能
                    self.rs485.enable_motor(pump_addr, False)
                    time.sleep(0.15)
                    self.rs485.enable_motor(pump_addr, True)
                    time.sleep(0.3)
            else:
                # ★ 首次尝试也清除故障锁存 (防止驱动芯片残留故障导致电机不动)
                # pump_manager.start_pump 内部也会做，此处为额外保障
                self.rs485.clear_pump_stall(pump_addr)
                time.sleep(0.05)

            result = self.rs485.start_pump(pump_addr, direction, rpm)
            if not result:
                self._emit_log(f"  ❌ 泵{pump_addr} 启动命令发送失败", "ERROR")
                continue

            # 验证泵是否真的在物理转 (控制器状态 + 编码器Δ)
            if self._verify_pump_running(pump_addr):
                if attempt > 0:
                    self._emit_log(f"  ✓ 泵{pump_addr} 重试启动成功(物理运转已确认)")
                return True

            self._emit_log(
                f"  ⚠ 泵{pump_addr} 命令已发送但物理运转未确认 "
                f"(尝试 {attempt + 1}/{max_retries + 1})",
                "WARNING"
            )
            # 先停止再重试
            self.rs485.stop_pump(pump_addr)
            time.sleep(0.2)

        self._emit_log(
            f"  ❌ {label} 泵{pump_addr} 启动失败 — {max_retries} 次重试后编码器仍无变化",
            "ERROR"
        )
        return False

    def _send_position_verified(self, pump_addr: int, encoder_counts: int,
                                rpm: int, label: str = "",
                                max_retries: int = 3) -> bool:
        """发送位置命令并验证泵物理运动 — 失败时自动重试 + 故障清除 + 重使能

        Note:
            max_retries 从 2 增至 3，给空闲唤醒后的泵更多重试机会。
        Returns:
            True = 泵已确认物理运动, False = 多次重试仍无法启动
        """
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self._emit_log(
                    f"  🔄 {label} 泵{pump_addr} 位置命令重试 {attempt}/{max_retries}",
                    "WARNING"
                )
                fault = self.rs485.read_pump_fault(pump_addr)
                if fault and fault != 0:
                    self._emit_log(
                        f"  ⚠ 泵{pump_addr} 故障码 0x{fault:02X}，尝试清除 + 重使能",
                        "WARNING"
                    )
                    self.rs485.clear_pump_stall(pump_addr)
                    time.sleep(0.2)
                    self.rs485.enable_motor(pump_addr, False)
                    time.sleep(0.15)
                    self.rs485.enable_motor(pump_addr, True)
                    time.sleep(0.3)
                else:
                    self.rs485.enable_motor(pump_addr, False)
                    time.sleep(0.15)
                    self.rs485.enable_motor(pump_addr, True)
                    time.sleep(0.3)
            else:
                # ★ 首次尝试: 清除故障锁存 + 使能电机
                # 驱动芯片可能因上次运行残留故障锁存，导致 MCU 回复"OK"但电机不动
                # pump_manager.move_position_rel 内部也会做，此处为额外保障
                self.rs485.clear_pump_stall(pump_addr)
                time.sleep(0.1)
                self.rs485.enable_motor(pump_addr, True)
                time.sleep(0.1)

            result = self.rs485.run_position_rel(
                pump_addr, encoder_counts, rpm, acceleration=5
            )
            if not result:
                self._emit_log(f"  ❌ 泵{pump_addr} 位置命令发送失败", "ERROR")
                continue

            # 验证泵是否真的在物理运动 (控制器状态 + 编码器Δ)
            if self._verify_pump_running(pump_addr):
                if attempt > 0:
                    self._emit_log(f"  ✓ 泵{pump_addr} 重试位置命令成功(物理运转已确认)")
                return True

            self._emit_log(
                f"  ⚠ 泵{pump_addr} 位置命令已发送但物理运转未确认 "
                f"(尝试 {attempt + 1}/{max_retries + 1})",
                "WARNING"
            )
            self.rs485.stop_pump(pump_addr)
            time.sleep(0.2)

        self._emit_log(
            f"  ❌ {label} 泵{pump_addr} 位置启动失败 — {max_retries} 次重试后编码器仍无变化",
            "ERROR"
        )
        return False

    def _stop_pump_verified(self, pump_addr: int, label: str = "",
                            max_retries: int = 2) -> bool:
        """停止泵并验证已停止 — 失败时自动重试

        Returns:
            True = 泵已确认停止, False = 仍在运行(最终仍会尝试停止)
        """
        for attempt in range(max_retries + 1):
            self.rs485.stop_pump(pump_addr)
            if self._verify_pump_stopped(pump_addr):
                return True
            self._emit_log(
                f"  ⚠ {label} 泵{pump_addr} 停止后仍在运行，"
                f"重试 {attempt + 1}/{max_retries + 1}",
                "WARNING"
            )
            time.sleep(0.2)
        # 最后兜底：强制停止
        self.rs485.stop_pump(pump_addr)
        self._emit_log(f"  ⚠ {label} 泵{pump_addr} 停止验证失败，已发送最终停止命令", "WARNING")
        return False

    # ── 液位动画辅助 ──────────────────────────────────
    
    def _emit_tank_levels(self):
        """发送液位更新信号 (fraction 0-1)"""
        self.liquid_level_update.emit(self._tank1_level, self._tank2_level)
    
    def _interruptible_sleep_with_levels(
        self, total_seconds: float, interval: float = 0.5,
        t1_start: float = None, t1_end: float = None,
        t2_start: float = None, t2_end: float = None,
        cap_frac: float = 1.0,
    ) -> bool:
        """可中断等待 + 液位动画 (支持 cap_frac 非线性封顶)
        
        在等待期间，将 tank1/tank2 液位从 start 插值到 end。
        传 None 表示不改变该烧杯液位。
        
        cap_frac (0,1]:
            实际液体量 / 泵设定体积。例如混合烧杯 80mL, 转移泵设 100mL,
            则 cap_frac=0.8。动画在时间进度到 0.8 时就到达终态，之后保持。
            effective_progress = min(1.0, progress / cap_frac)
        """
        waited = 0.0
        cf = max(1e-6, cap_frac)          # 避免除零
        while waited < total_seconds:
            if self._stop_flag:
                return False
            step_wait = min(interval, total_seconds - waited)
            time.sleep(step_wait)
            waited += step_wait
            
            progress = min(1.0, waited / total_seconds) if total_seconds > 0 else 1.0
            eff = min(1.0, progress / cf)  # 封顶后的有效进度
            if t1_start is not None and t1_end is not None:
                self._tank1_level = t1_start + (t1_end - t1_start) * eff
            if t2_start is not None and t2_end is not None:
                self._tank2_level = t2_start + (t2_end - t2_start) * eff
            self._emit_tank_levels()
        return True
    
    def _run_single_pump_position(
        self, pump_addr: int, direction: str, rpm: int, volume_ul: float,
        label: str = "",
        t1_start: float = None, t1_end: float = None,
        t2_start: float = None, t2_end: float = None,
        cap_frac: float = 1.0,
    ) -> bool:
        """通用单泵位移模式执行 (用于移液/冲洗/排空)
        
        支持位置模式 (编码器闭环) 和 RPM 时间模式回退 + 液位动画。
        **启动后会验证泵实际在运行，失败时自动重试+故障清除。**
        
        cap_frac: 实际液体/泵设定体积, 传给 _interruptible_sleep_with_levels
                  实现非线性封顶动画 (详见该方法文档).
        Returns True on success.
        """
        ENCODER_DIVISIONS_PER_REV = 16384
        DECEL_TIMEOUT_S = 30.0
        
        pos_cal = self._position_calibration.get(pump_addr)
        use_position_mode = pos_cal and pos_cal.get("slope_k", 0) > 0
        
        if use_position_mode:
            slope_k = pos_cal["slope_k"]
            intercept_b = pos_cal.get("intercept_b", 0.0)
            revolutions = (volume_ul - intercept_b) / slope_k
            if revolutions < 0:
                revolutions = 0
            encoder_counts = int(revolutions * ENCODER_DIVISIONS_PER_REV)
            if direction == "REV":
                encoder_counts = -encoder_counts
            estimated_seconds = (abs(revolutions) / (rpm / 60.0)) + 2.0
            
            self._emit_log(
                f"  {label}: 泵{pump_addr} 位移模式, "
                f"{volume_ul:,.2f}μL ({volume_ul/1000:.2f}mL), "
                f"{revolutions:.2f}圈, {rpm}RPM, 预计{estimated_seconds:.1f}s"
            )
            
            # 发送位置命令 + 验证泵实际运转
            if not self._send_position_verified(
                pump_addr, encoder_counts, rpm, label=label
            ):
                self._emit_log(
                    f"  ❌ {label}: 泵{pump_addr} 位置命令验证失败，步骤中止",
                    "ERROR"
                )
                return False
            
            self._emit_log(f"  ✓ 泵{pump_addr} 物理运转已确认(编码器+状态)")
            
            if self.dm:
                self.dm.record_pump_op(
                    pump_addr, label.lower().replace(" ", "_"),
                    direction=direction, rpm=rpm,
                    volume_ul=volume_ul, duration_s=estimated_seconds,
                    mode="position", encoder_counts=encoder_counts,
                )
        else:
            # RPM 时间模式回退
            ul_per_sec = self._pump_calibration.get(pump_addr, 0)
            if ul_per_sec > 0:
                estimated_seconds = volume_ul / ul_per_sec + 2.0
            else:
                estimated_seconds = volume_ul / 1.5 + 2.0
            
            self._emit_log(
                f"  {label}: 泵{pump_addr} RPM时间模式(无位置校准), "
                f"{volume_ul:,.2f}μL ({volume_ul/1000:.2f}mL), "
                f"{rpm}RPM, 预计{estimated_seconds:.1f}s"
            )
            
            # 启动泵 + 验证泵实际运转
            if not self._start_pump_verified(
                pump_addr, direction, rpm, label=label
            ):
                self._emit_log(
                    f"  ❌ {label}: 泵{pump_addr} 启动验证失败，步骤中止",
                    "ERROR"
                )
                return False
            
            self._emit_log(f"  ✓ 泵{pump_addr} 物理运转已确认(编码器+状态)")
            
            if self.dm:
                self.dm.record_pump_op(
                    pump_addr, label.lower().replace(" ", "_"),
                    direction=direction, rpm=rpm,
                    volume_ul=volume_ul, duration_s=estimated_seconds,
                    mode="speed_fallback",
                )
        
        # 泵已确认运行 → 开始等待+液位动画
        if not self._interruptible_sleep_with_levels(
            estimated_seconds, 0.5,
            t1_start=t1_start, t1_end=t1_end,
            t2_start=t2_start, t2_end=t2_end,
            cap_frac=cap_frac,
        ):
            self._stop_pump_verified(pump_addr, label=label)
            return False
        
        # 位置模式: 校验完成
        if use_position_mode:
            if not self.rs485.wait_pump_position_done(
                pump_addr, timeout_s=15, poll_interval_s=0.3,
                decel_timeout_s=DECEL_TIMEOUT_S
            ):
                self._emit_log(f"  ⚠ 泵 {pump_addr} 位置运动超时，强制停止", "WARNING")
                self._stop_pump_verified(pump_addr, label=label)
        else:
            # RPM模式: 停止并验证
            self._stop_pump_verified(pump_addr, label=label)
        
        self._emit_log(f"  ✓ {label} 完成 ({volume_ul/1000:.2f}mL)")
        return True
    
    def _execute_prep_sol(self, step: ProgStep, step_index: int = -1) -> bool:
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
        
        self._emit_log(
            f"  配液: {conc_str}, "
            f"注液顺序{params.injection_order}, 总体积{vol_formatted}"
        )
        
        # 计算各溶液需要的体积 (两遍扫描：先算溶质，再分配溶剂)
        volumes_to_inject = {}  # {溶液名: 体积(uL)}
        remaining_volume = total_volume_ul
        solvent_names = []  # 溶剂列表
        
        # 第一遍：计算所有溶质体积
        for sol_name in params.injection_order:
            if self._stop_flag:
                return False
            
            if not params.selected_solutions.get(sol_name, False):
                continue
            
            is_solvent = params.solvent_flags.get(sol_name, False)
            
            if is_solvent:
                solvent_names.append(sol_name)
                continue
            
            # 计算稀释体积: C1*V1 = C2*V2 => V1 = C2*V2/C1
            target_conc = params.target_concentrations.get(sol_name, 0.0)
            if target_conc <= 0:
                continue
            
            # 获取母液浓度
            channel_info = self._dilution_channels.get(sol_name, {})
            stock_conc = channel_info.get("stock_concentration", target_conc)
            
            if stock_conc <= 0:
                self._emit_log(f"    警告: {sol_name} 母液浓度为0，跳过", "WARNING")
                continue
            
            # 计算需要的体积
            vol_needed = (target_conc * total_volume_ul) / stock_conc
            volumes_to_inject[sol_name] = vol_needed
            remaining_volume -= vol_needed
        
        # 第二遍：分配溶剂体积（剩余体积均分给所有溶剂）
        if remaining_volume < 0:
            self._emit_log(
                f"    ⚠️ 溶质体积之和 ({(total_volume_ul - remaining_volume)/1000:.2f}mL) "
                f"超过总体积 ({total_volume_ul/1000:.2f}mL)，"
                f"已截断为0，请检查浓度参数",
                "WARNING"
            )
            remaining_volume = 0
        
        # 详细的体积分配日志
        vol_lines = []
        for sol_name, vol in volumes_to_inject.items():
            vol_lines.append(f"{sol_name}={vol/1000:.2f}mL")
        sol_total_ml = sum(v for v in volumes_to_inject.values()) / 1000.0
        self._emit_log(
            f"    溶质分配: {', '.join(vol_lines)}，"
            f"合计 {sol_total_ml:.2f}/{total_volume_ul/1000:.2f}mL，"
            f"溶剂可用 {remaining_volume/1000:.2f}mL"
        )
        
        for sol_name in solvent_names:
            if len(solvent_names) == 1:
                volumes_to_inject[sol_name] = remaining_volume
            else:
                volumes_to_inject[sol_name] = remaining_volume / len(solvent_names)
            
            if volumes_to_inject[sol_name] <= 0:
                self._emit_log(
                    f"    ⚠️ 溶剂 {sol_name} 分配体积为 0 "
                    f"(溶质已占满总体积)，该泵不会运行。"
                    f"建议：降低目标浓度或增大总体积",
                    "WARNING"
                )
        
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
                self._emit_log(f"    ❌ {sol_name} 无对应泵配置，跳过", "ERROR")
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
                self._emit_log(
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
        
        # ---- 液位动画准备：按烧杯汇总目标体积 ----
        tank1_total_ul = sum(
            t["vol"] for t in inject_tasks
            if t["pump_addr"] not in self.TANK2_PUMP_ADDRS
        )
        tank2_total_ul = sum(
            t["vol"] for t in inject_tasks
            if t["pump_addr"] in self.TANK2_PUMP_ADDRS
        )
        # 跟踪每个泵已交付体积（实时更新）
        delivered_ul: Dict[int, float] = {t["pump_addr"]: 0.0 for t in inject_tasks}
        # 各泵启动时间（用于估算运行中进度）
        pump_start_time: Dict[int, float] = {}
        
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
                self._emit_log(f"    批次 {order}: {', '.join(names)} (同时注入)")
        
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
            started_in_batch = []  # 本批次已启动的泵地址（用于失败时清理）
            for task in batch:
                role = "(溶剂)" if task["is_solvent"] else ""
                
                if task.get("use_position_mode", True):
                    # 位置模式 (run_position_rel)
                    self._emit_log(
                        f"    注入 {task['sol_name']}{role}: "
                        f"{task['vol']:,.2f}uL, 泵{task['pump_addr']} 位移模式, "
                        f"{task['revolutions']:.2f}圈, 编码器={task['encoder_counts']}, "
                        f"{task['rpm']}RPM, 预计{task['estimated_seconds']:.1f}s"
                    )
                    
                    # ★ 预处理：清除残留故障锁存 + 确保电机使能
                    self.rs485.clear_pump_stall(task["pump_addr"])
                    time.sleep(0.1)
                    self.rs485.enable_motor(task["pump_addr"], True)
                    time.sleep(0.1)
                    
                    result = self.rs485.run_position_rel(
                        task["pump_addr"],
                        task["encoder_counts"],
                        task["rpm"],
                        acceleration=5
                    )
                    if not result:
                        # 首次失败 → 重使能后重试
                        self._emit_log(
                            f"    ⚠ 泵 {task['pump_addr']} ({task['sol_name']}) "
                            f"位置命令首次发送失败，尝试重使能后重试",
                            "WARNING"
                        )
                        fault = self.rs485.read_pump_fault(task["pump_addr"])
                        if fault and fault != 0:
                            self._emit_log(
                                f"    ⚠ 泵{task['pump_addr']} 故障码 0x{fault:02X}，清除中",
                                "WARNING"
                            )
                            self.rs485.clear_pump_stall(task["pump_addr"])
                            time.sleep(0.2)
                        self.rs485.enable_motor(task["pump_addr"], False)
                        time.sleep(0.15)
                        self.rs485.enable_motor(task["pump_addr"], True)
                        time.sleep(0.3)
                        result = self.rs485.run_position_rel(
                            task["pump_addr"],
                            task["encoder_counts"],
                            task["rpm"],
                            acceleration=5
                        )
                        if not result:
                            for prev in started_in_batch:
                                self.rs485.stop_pump(prev)
                            self._emit_log(
                                f"    ❌ 泵 {task['pump_addr']} ({task['sol_name']}) "
                                f"位置命令重试后仍发送失败",
                                "ERROR"
                            )
                            return False
                        self._emit_log(
                            f"    ✓ 泵 {task['pump_addr']} ({task['sol_name']}) "
                            f"重使能后位置命令发送成功"
                        )
                    
                    # 验证泵实际开始运动（控制器状态+编码器Δ）
                    if not self._verify_pump_running(task["pump_addr"]):
                        self._emit_log(
                            f"    ⚠ 泵 {task['pump_addr']} ({task['sol_name']}) "
                            f"位置命令已发送但物理运转未确认，尝试重发",
                            "WARNING"
                        )
                        # 清除可能的故障 + 重使能
                        fault = self.rs485.read_pump_fault(task["pump_addr"])
                        if fault and fault != 0:
                            self.rs485.clear_pump_stall(task["pump_addr"])
                            time.sleep(0.2)
                        self.rs485.enable_motor(task["pump_addr"], False)
                        time.sleep(0.15)
                        self.rs485.enable_motor(task["pump_addr"], True)
                        time.sleep(0.3)
                        # 重试一次
                        self.rs485.run_position_rel(
                            task["pump_addr"],
                            task["encoder_counts"],
                            task["rpm"],
                            acceleration=5
                        )
                        if not self._verify_pump_running(task["pump_addr"]):
                            for prev in started_in_batch:
                                self.rs485.stop_pump(prev)
                            self._emit_log(
                                f"    ❌ 泵 {task['pump_addr']} ({task['sol_name']}) "
                                f"重试后编码器仍无变化，无法启动",
                                "ERROR"
                            )
                            return False
                        self._emit_log(
                            f"    ✓ 泵 {task['pump_addr']} ({task['sol_name']}) "
                            f"重试启动成功(物理运转已确认)"
                        )
                    
                    started_in_batch.append(task["pump_addr"])
                    pump_start_time[task["pump_addr"]] = time.time()
                    # 记录泵操作
                    if self.dm:
                        self.dm.record_pump_op(
                            task["pump_addr"], "prep_sol_inject",
                            direction=task["direction"], rpm=task["rpm"],
                            volume_ul=task["vol"],
                            duration_s=task["estimated_seconds"],
                            mode="position",
                            encoder_counts=task["encoder_counts"],
                        )
                    # RS485 半双工总线间隔：避免多泵连续发送导致总线竞争
                    time.sleep(0.15)
                else:
                    # RPM 时间模式回退
                    self._emit_log(
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
                        # 失败时停止本批次中已启动的泵
                        for prev in started_in_batch:
                            self.rs485.stop_pump(prev)
                        self._emit_log(
                            f"    ❌ 泵 {task['pump_addr']} ({task['sol_name']}) 启动命令失败"
                        )
                        return False
                    
                    # 验证泵实际运行（控制器状态+编码器Δ）
                    if not self._verify_pump_running(task["pump_addr"]):
                        self._emit_log(
                            f"    ⚠ 泵 {task['pump_addr']} ({task['sol_name']}) "
                            f"启动命令已发送但物理运转未确认，尝试重发",
                            "WARNING"
                        )
                        fault = self.rs485.read_pump_fault(task["pump_addr"])
                        if fault and fault != 0:
                            self.rs485.clear_pump_stall(task["pump_addr"])
                            time.sleep(0.2)
                        self.rs485.enable_motor(task["pump_addr"], False)
                        time.sleep(0.15)
                        self.rs485.enable_motor(task["pump_addr"], True)
                        time.sleep(0.3)
                        self.rs485.start_pump(
                            task["pump_addr"], task["direction"], task["rpm"]
                        )
                        if not self._verify_pump_running(task["pump_addr"]):
                            for prev in started_in_batch:
                                self.rs485.stop_pump(prev)
                            self._emit_log(
                                f"    ❌ 泵 {task['pump_addr']} ({task['sol_name']}) "
                                f"重试后编码器仍无变化，无法启动",
                                "ERROR"
                            )
                            return False
                        self._emit_log(
                            f"    ✓ 泵 {task['pump_addr']} ({task['sol_name']}) "
                            f"重试启动成功(物理运转已确认)"
                        )
                    
                    started_in_batch.append(task["pump_addr"])
                    pump_start_time[task["pump_addr"]] = time.time()
                    rpm_tasks.append(task)
                    # 记录泵操作
                    if self.dm:
                        self.dm.record_pump_op(
                            task["pump_addr"], "prep_sol_inject",
                            direction=task["direction"], rpm=task["rpm"],
                            volume_ul=task["vol"],
                            duration_s=task["estimated_seconds"],
                            mode="speed_fallback",
                        )
                
                if task["estimated_seconds"] > max_wait:
                    max_wait = task["estimated_seconds"]
            
            # ---- 记录初始编码器位置（用于堵转重试时计算剩余量）----
            ENCODER_DIVISIONS_PER_REV = 16384
            initial_positions = {}
            for task in batch:
                if task.get("use_position_mode"):
                    pos = self.rs485.read_encoder_position(task["pump_addr"])
                    if pos is not None:
                        initial_positions[task["pump_addr"]] = pos
                    time.sleep(0.15)
            
            # ---- 泵全部启动后立即扣减剩余量（提前反映消耗） ----
            batch_deducted = False
            if self.config:
                for task in batch:
                    sol_name = task["sol_name"]
                    vol_ml = task["vol"] / 1000.0
                    found = False
                    for ch in self.config.dilution_channels:
                        if ch.solution_name == sol_name and ch.total_volume_ml > 0:
                            ch.remaining_volume_ml = max(0.0, ch.remaining_volume_ml - vol_ml)
                            batch_deducted = True
                            found = True
                            break
                    if not found:
                        for ch in self.config.flush_channels:
                            if ch.work_type == "Inlet" and ch.total_volume_ml not in (0, float('inf')):
                                ch.remaining_volume_ml = max(0.0, ch.remaining_volume_ml - vol_ml)
                                batch_deducted = True
                                break
                if batch_deducted:
                    try:
                        self.config.save()
                    except Exception:
                        pass
                    self.volume_updated.emit()
            
            # ---- 等待本批次中最长的泵完成 ----
            DECEL_TIMEOUT_S = 30.0   # 减速状态持续超时(秒)
            STALL_MAX_RETRIES = 2    # 堵转最大重试次数
            HARD_MAX_WAIT_S = 300.0  # 硬性最大等待(秒)，防止无限延长
            
            stall_failures = {}       # {addr: failed_vol_ul} 堵转失败的泵
            stall_retry_counts = {}   # {addr: int} 已重试次数
            decel_start_time = {}     # {addr: float} 首次检测到减速的时间戳
            decel_last_pos = {}       # {addr: int} 减速时上次编码器位置
            
            if max_wait > 0:
                self._emit_log(f"    等待批次 {order_num} 完成... ({max_wait:.1f}s)")
                still_running = set(t["pump_addr"] for t in batch)
                poll_counter = 0
                last_volume_emit = time.time()
                wall_start = time.time()
                
                while (time.time() - wall_start) < (max_wait + 10) and (time.time() - wall_start) < HARD_MAX_WAIT_S:
                    if self._stop_flag:
                        for t in batch:
                            self.rs485.stop_pump(t["pump_addr"])
                        # 中断时已提前扣减，直接返回
                        return False
                    # 所有泵已完成 → 立即退出等待
                    if not still_running:
                        self._emit_log(f"    ✓ 批次 {order_num} 全部泵已完成")
                        break
                    time.sleep(0.5)
                    
                    # 每 ~10s 发送一次 volume_updated 信号刷新 UI 显示
                    now = time.time()
                    if now - last_volume_emit >= 10.0:
                        self.volume_updated.emit()
                        last_volume_emit = now
                    
                    # 每 ~1.5s 轮询一次各泵运行状态
                    poll_counter += 1
                    if poll_counter % 3 == 0 and still_running:
                        newly_done = []
                        for addr in list(still_running):
                            status = self.rs485.read_run_status(addr)
                            time.sleep(0.15)
                            
                            task_info = next((t for t in batch if t["pump_addr"] == addr), None)
                            sol = task_info["sol_name"] if task_info else f"泵{addr}"
                            
                            if status is None or status == 1:
                                # ---- 泵已停止：检查堵转 ----
                                fault = self.rs485.read_pump_fault(addr)
                                time.sleep(0.15)
                                
                                if fault and fault != 0:
                                    # 堵转保护触发
                                    retry_count = stall_retry_counts.get(addr, 0)
                                    self._emit_log(
                                        f"    🚨 泵 {addr} ({sol}) 堵转保护触发! "
                                        f"(故障码=0x{fault:02X})", "ERROR"
                                    )
                                    
                                    if (retry_count < STALL_MAX_RETRIES
                                            and task_info
                                            and task_info.get("use_position_mode")):
                                        # 读取当前编码器位置，计算剩余量
                                        current_pos = self.rs485.read_encoder_position(addr)
                                        time.sleep(0.15)
                                        remaining_counts = None
                                        
                                        if (current_pos is not None
                                                and addr in initial_positions):
                                            delivered = abs(current_pos - initial_positions[addr])
                                            target = abs(task_info["encoder_counts"])
                                            remaining = target - delivered
                                            if remaining > 50:
                                                remaining_counts = remaining
                                                pct = (delivered / target * 100) if target > 0 else 0
                                                self._emit_log(
                                                    f"    📊 已完成 {pct:.0f}%, "
                                                    f"剩余 {remaining / ENCODER_DIVISIONS_PER_REV:.2f}圈"
                                                )
                                        
                                        # 清除堵转 + 重使能电机
                                        self.rs485.clear_pump_stall(addr)
                                        time.sleep(0.2)
                                        self.rs485.enable_motor(addr, False)
                                        time.sleep(0.15)
                                        self.rs485.enable_motor(addr, True)
                                        time.sleep(0.3)
                                        
                                        # 用剩余量重新发送位置命令
                                        if remaining_counts and remaining_counts > 0:
                                            sign = 1 if task_info["encoder_counts"] > 0 else -1
                                            retry_ok = self.rs485.run_position_rel(
                                                addr, sign * remaining_counts,
                                                task_info["rpm"], acceleration=5
                                            )
                                        else:
                                            # 无法计算剩余量，重发原始命令
                                            retry_ok = self.rs485.run_position_rel(
                                                addr, task_info["encoder_counts"],
                                                task_info["rpm"], acceleration=5
                                            )
                                        
                                        # 验证泵是否真正恢复运行
                                        if retry_ok and not self._verify_pump_running(addr):
                                            self._emit_log(
                                                f"    ⚠ 泵 {addr} ({sol}) 堵转清除后位置命令已发送但运行未确认",
                                                "WARNING"
                                            )
                                            retry_ok = False
                                        
                                        if retry_ok:
                                            stall_retry_counts[addr] = retry_count + 1
                                            if current_pos is not None:
                                                initial_positions[addr] = current_pos
                                            self._emit_log(
                                                f"    🔄 泵 {addr} ({sol}) 堵转清除，"
                                                f"重试第 {retry_count + 1} 次"
                                            )
                                            # 延长等待时间
                                            extra = task_info.get("estimated_seconds", 30)
                                            max_wait = max(max_wait, waited + extra)
                                            continue  # 继续监控
                                    
                                    # 重试失败或次数耗尽
                                    self.rs485.clear_pump_stall(addr)
                                    stall_failures[addr] = task_info["vol"] if task_info else 0
                                    self._emit_log(
                                        f"    ❌ 泵 {addr} ({sol}) 堵转无法恢复! "
                                        f"目标注液量 {task_info['vol']:,.0f}μL 未完成",
                                        "ERROR"
                                    )
                                    newly_done.append(addr)
                                    still_running.discard(addr)
                                else:
                                    # 正常停止
                                    newly_done.append(addr)
                                    still_running.discard(addr)
                                    self._emit_log(f"    ✓ 泵 {addr} ({sol}) 已停止")
                                decel_start_time.pop(addr, None)
                            
                            elif status == 3:
                                # ---- 减速中：检测是否卡在减速状态 ----
                                if addr not in decel_start_time:
                                    decel_start_time[addr] = time.time()
                                    # 记录进入减速时的编码器位置
                                    try:
                                        decel_last_pos[addr] = self.rs485.read_encoder_position(addr)
                                    except Exception:
                                        decel_last_pos[addr] = None
                                else:
                                    decel_elapsed = time.time() - decel_start_time[addr]
                                    # 每 5s 检查编码器位置，若不再变化则提前判完成
                                    if decel_elapsed > 5.0 and addr in decel_last_pos:
                                        try:
                                            cur_pos = self.rs485.read_encoder_position(addr)
                                            if (cur_pos is not None and decel_last_pos[addr] is not None
                                                    and abs(cur_pos - decel_last_pos[addr]) < 100):
                                                # 位置不再变化，泵已实际完成
                                                self._emit_log(
                                                    f"    ✓ 泵 {addr} ({sol}) 减速中但位置已稳定 "
                                                    f"({decel_elapsed:.0f}s)，视为完成",
                                                )
                                                self.rs485.stop_pump(addr)
                                                time.sleep(0.15)
                                                newly_done.append(addr)
                                                still_running.discard(addr)
                                                decel_start_time.pop(addr, None)
                                                decel_last_pos.pop(addr, None)
                                                continue
                                            decel_last_pos[addr] = cur_pos
                                        except Exception:
                                            pass
                                    if decel_elapsed > DECEL_TIMEOUT_S:
                                        self._emit_log(
                                            f"    ⚠ 泵 {addr} ({sol}) 持续减速 "
                                            f"{DECEL_TIMEOUT_S:.0f}s，强制停止",
                                            "WARNING"
                                        )
                                        self.rs485.stop_pump(addr)
                                        time.sleep(0.15)
                                        newly_done.append(addr)
                                        still_running.discard(addr)
                                        decel_start_time.pop(addr, None)
                                        decel_last_pos.pop(addr, None)
                            else:
                                # 正常运行(2=加速, 4=全速)
                                decel_start_time.pop(addr, None)
                        
                        if newly_done:
                            # 更新已完成泵的交付量
                            for addr in newly_done:
                                t_info = next((t for t in batch if t["pump_addr"] == addr), None)
                                if t_info:
                                    delivered_ul[addr] = t_info["vol"]
                            self.pump_batch_update.emit(
                                list(still_running), waiting_addrs
                            )
                        
                        # ---- 液位动画：估算当前各泵进度并更新 ----
                        now = time.time()
                        for task in batch:
                            addr = task["pump_addr"]
                            if addr in still_running and addr in pump_start_time:
                                elapsed = now - pump_start_time[addr]
                                est = task["estimated_seconds"]
                                progress = min(1.0, elapsed / est) if est > 0 else 1.0
                                delivered_ul[addr] = task["vol"] * progress
                        
                        t1_del = sum(v for a, v in delivered_ul.items()
                                     if a not in self.TANK2_PUMP_ADDRS)
                        t2_del = sum(v for a, v in delivered_ul.items()
                                     if a in self.TANK2_PUMP_ADDRS)
                        if tank1_total_ul > 0:
                            self._tank1_level = min(1.0, t1_del / tank1_total_ul)
                        if tank2_total_ul > 0:
                            self._tank2_level = min(1.0, t2_del / tank2_total_ul)
                        self._emit_tank_levels()
            
            # 批次等待结束 → 清除本批次所有运行指示（剩余的绿灯归灰）
            self.pump_batch_update.emit([], waiting_addrs)
            
            # 停止RPM时间模式的泵（使用验证停止）
            for t in rpm_tasks:
                self._stop_pump_verified(
                    t["pump_addr"],
                    label=f"prep_sol {t.get('sol_name','')}"
                )
                time.sleep(0.15)
            
            # 校验位置模式泵是否真正完成（编码器闭环验证）
            # 仅校验还在 still_running 中的泵（已在轮询循环中确认完成的跳过）
            position_tasks = [t for t in batch if t.get("use_position_mode")]
            for t in position_tasks:
                addr = t["pump_addr"]
                if addr not in still_running:
                    continue  # 轮询循环中已确认完成
                if addr in stall_failures:
                    continue  # 已标记堵转失败的跳过
                if not self.rs485.wait_pump_position_done(
                    addr, timeout_s=15, poll_interval_s=0.3,
                    decel_timeout_s=DECEL_TIMEOUT_S
                ):
                    self._emit_log(
                        f"    ⚠ 泵 {addr} ({t['sol_name']}) 位置运动超时未完成，强制停止"
                    )
                    self.rs485.stop_pump(addr)
                time.sleep(0.15)
            
            # 报告每个泵的注入结果
            for task in batch:
                addr = task["pump_addr"]
                if addr in stall_failures:
                    self._emit_log(
                        f"    ❌ {task['sol_name']} 注入失败 (堵转保护)，"
                        f"目标 {task['vol']:,.2f}μL 未完全注入",
                        "ERROR"
                    )
                else:
                    # 标记为完全交付
                    delivered_ul[addr] = task["vol"]
                    self._emit_log(
                        f"    ✓ {task['sol_name']} 注入完成 ({task['vol']:,.2f}uL)"
                    )
            
            # ---- 批次完成：报告结果，堵转失败的退回已扣减的体积 ----
            if self.config and stall_failures:
                refund_changed = False
                for task in batch:
                    if task["pump_addr"] in stall_failures:
                        sol_name = task["sol_name"]
                        vol_ml = task["vol"] / 1000.0
                        # 退回之前提前扣减的体积
                        found = False
                        for ch in self.config.dilution_channels:
                            if ch.solution_name == sol_name and ch.total_volume_ml > 0:
                                ch.remaining_volume_ml = min(ch.total_volume_ml, ch.remaining_volume_ml + vol_ml)
                                self._emit_log(
                                    f"    📊 {sol_name} 堵转退回 {vol_ml:.2f}mL，"
                                    f"剩余 {ch.remaining_volume_ml:.1f}/{ch.total_volume_ml:.1f}mL"
                                )
                                refund_changed = True
                                found = True
                                break
                        if not found:
                            for ch in self.config.flush_channels:
                                if ch.work_type == "Inlet" and ch.total_volume_ml not in (0, float('inf')):
                                    ch.remaining_volume_ml = min(ch.total_volume_ml, ch.remaining_volume_ml + vol_ml)
                                    self._emit_log(
                                        f"    📊 {sol_name}(Inlet) 堵转退回 {vol_ml:.2f}mL，"
                                        f"剩余 {ch.remaining_volume_ml:.1f}/{ch.total_volume_ml:.1f}mL"
                                    )
                                    refund_changed = True
                                    break
                if refund_changed:
                    try:
                        self.config.save()
                    except Exception:
                        pass
                    self.volume_updated.emit()
            else:
                # 无堵转：打印最终消耗日志
                if self.config:
                    for task in batch:
                        sol_name = task["sol_name"]
                        vol_ml = task["vol"] / 1000.0
                        for ch in self.config.dilution_channels:
                            if ch.solution_name == sol_name and ch.total_volume_ml > 0:
                                self._emit_log(
                                    f"    📊 {sol_name} 消耗 {vol_ml:.2f}mL，"
                                    f"剩余 {ch.remaining_volume_ml:.1f}/{ch.total_volume_ml:.1f}mL"
                                )
                                break
            
            # 批次间间隔
            time.sleep(0.5)
        
        # 所有批次完成 → 清除全部泵指示灯
        self.pump_batch_update.emit([], [])
        
        # 液位动画：确保达到目标液位 (1.0 = 虚线位置)
        if tank1_total_ul > 0:
            self._tank1_level = 1.0
            self._tank1_volume_ul = tank1_total_ul
        if tank2_total_ul > 0:
            self._tank2_level = 1.0
            self._tank2_volume_ul = tank2_total_ul
        self._emit_tank_levels()
        
        self._emit_log(f"  配液完成")
        
        # 保存配液结果
        if self.dm and step_index >= 0:
            sol_names = [t["sol_name"] for t in inject_tasks]
            sol_vols = ", ".join(f"{t['sol_name']}={t['vol']:.1f}μL" for t in inject_tasks)
            self.dm.save_prep_sol_result(
                step_index=step_index,
                total_volume_ul=total_volume_ul,
                volumes=volumes_to_inject,
                concentrations=params.target_concentrations,
                injection_order=list(params.injection_order),
                solvent_flags=params.solvent_flags,
            )
            self.dm.step_finished(
                step_index, True,
                details=f"配液完成: 总{total_volume_ul:.0f}μL, {sol_vols}",
            )
            self._steps_already_finished.add(step_index)
        
        return True
    
    def _execute_flush(self, step: ProgStep) -> bool:
        """执行冲洗 - 位移模式(编码器闭环) + RPM时间模式回退"""
        pump_addr = step.pump_address
        if not pump_addr:
            self._emit_log("  冲洗: 未指定泵地址")
            return False
        
        if not self._check_pump_connection(pump_addr, "冲洗"):
            return False
        
        direction = step.pump_direction or "FWD"
        rpm = step.flush_rpm or step.pump_rpm or 100
        volume_ul = step.volume_ul or 0
        
        if volume_ul <= 0:
            self._emit_log("  冲洗: 体积为0，跳过")
            return True
        
        # 冲洗不影响液位动画 (冲洗液进入混合烧杯后会被排空)
        return self._run_single_pump_position(
            pump_addr, direction, rpm, volume_ul,
            label="冲洗",
        )
    
    # ----------------------------------------------------------
    # CHI 660F 生命周期管理 (实验级别，不再每步重启)
    # ----------------------------------------------------------

    def _ensure_chi_bridge(self, ec: ECSettings) -> bool:
        """确保 CHI Bridge 已连接（实验级别复用）

        Bridge 实例保存在 self._chi_bridge，整个实验期间只连接一次，
        所有 echem 步骤共享同一连接。在 run() 的 finally 中统一断开。
        """
        from src.echem_sdl.hardware.chi_echem_bridge import CHIBridge, CHIBridgeConfig
        import os

        chi_exe = r"D:\CHI660F\chi660f.exe"
        output_dir = r"D:\CHI660F\data"
        if self.config:
            chi_exe = getattr(self.config, 'chi_exe_path', chi_exe)
            output_dir = getattr(self.config, 'chi_output_dir', output_dir)

        os.makedirs(output_dir, exist_ok=True)

        if not hasattr(self, '_chi_bridge') or self._chi_bridge is None:
            bridge_config = CHIBridgeConfig(
                chi_exe_path=chi_exe,
                output_dir=output_dir,
                use_dummy_cell=getattr(ec, 'use_dummy_cell', True),
            )
            self._chi_bridge = CHIBridge(bridge_config)

        if not self._chi_bridge.is_connected:
            self._emit_log("    正在连接 CHI 660F...")
            if not self._chi_bridge.connect():
                self._emit_log("    ❌ CHI 660F 连接失败", "ERROR")
                return False
            self._emit_log("    ✅ CHI 660F 已连接")

        # 动态同步 dummy cell 模式
        if hasattr(ec, 'use_dummy_cell'):
            self._chi_bridge._config.use_dummy_cell = ec.use_dummy_cell

        # 动态调整超时: 至少 run_time + 120s，确保长时间实验不会被误判超时
        run_time = getattr(ec, 'run_time_s', 0) or 0
        if run_time > 0:
            needed_timeout = run_time + 120
            if self._chi_bridge._controller and hasattr(self._chi_bridge._controller, '_config'):
                if self._chi_bridge._controller._config.timeout < needed_timeout:
                    self._chi_bridge._controller._config.timeout = needed_timeout
                    self._emit_log(f"    调整 CHI 超时: {needed_timeout:.0f}s")

        return True

    def _cleanup_chi_bridge(self):
        """断开 CHI Bridge 连接（实验结束时统一调用）"""
        try:
            if hasattr(self, '_chi_bridge') and self._chi_bridge:
                self._chi_bridge.disconnect()
                self._chi_bridge = None
                self._emit_log("[CHI] CHI 660F 已关闭")
        except Exception as cleanup_err:
            self._emit_log(f"[CHI] 关闭 CHI 660F 时出错: {cleanup_err}", "WARNING")

    def _execute_echem(self, step: ProgStep, step_index: int = -1) -> bool:
        """执行电化学测量 (通过 CHI 660F GUI 控制器)
        
        支持的技术:
        - CV: 循环伏安法
        - LSV: 线性扫描伏安法
        - i-t: 安培-时间曲线
        - ADT: 加速耐久性测试

        注意: CHI Bridge 生命周期由实验级别管理 (_ensure_chi_bridge / _cleanup_chi_bridge)，
        不再每步创建/销毁，避免多步骤实验中反复启动 chi660f.exe。
        """
        if not step.ec_settings:
            self._emit_log("  电化学: 缺少参数配置")
            return False
        
        ec = step.ec_settings
        technique = ec.technique.value if hasattr(ec.technique, 'value') else str(ec.technique)
        
        # 构建参数信息（安全处理 None 值）
        def _fv(val, fmt=".2f", suffix=""):
            """安全格式化可选浮点值"""
            return f"{val:{fmt}}{suffix}" if val is not None else "N/A"
        
        if technique == "CV":
            params_str = (
                f"E0={_fv(ec.e0)}V, Eh={_fv(ec.eh)}V, El={_fv(ec.el)}V, "
                f"扫描速率={ec.scan_rate}V/s, 段数={ec.seg_num}"
            )
        elif technique == "LSV":
            params_str = (
                f"E0={_fv(ec.e0)}V, Ef={_fv(ec.ef)}V, "
                f"扫描速率={ec.scan_rate}V/s"
            )
        elif technique in ["i-t", "IT"]:
            params_str = f"E0={_fv(ec.e0)}V, 运行时间={ec.run_time_s}s"
        elif technique == "ADT":
            cyc = getattr(ec, 'adt_num_cycles', 100)
            cat_mA = getattr(ec, 'adt_cathodic_current_mA', -500)
            cat_t = getattr(ec, 'adt_cathodic_duration_s', 3)
            ano_v = getattr(ec, 'adt_anodic_potential_V', 1.2)
            ano_t = getattr(ec, 'adt_anodic_duration_s', 2)
            params_str = (
                f"{cyc}轮, 阴极={cat_mA}mA/{cat_t}s, "
                f"阳极={ano_v}V/{ano_t}s"
            )
        else:
            params_str = f"采样间隔={ec.sample_interval_ms}ms"
        
        # iR 补偿信息
        ir_enabled = getattr(ec, 'ir_compensation_enabled', False)
        ir_ohm = getattr(ec, 'ir_compensation_ohm', 0.0)
        if ir_enabled and ir_ohm > 0:
            params_str += f", iR补偿={ir_ohm}Ω"

        self._emit_log(f"  电化学: {technique.upper()}, {params_str}")
        
        # ADT 信息
        if getattr(ec, 'adt_enabled', False) or technique == "ADT":
            cyc = getattr(ec, 'adt_num_cycles', 100)
            total_t = cyc * (getattr(ec, 'adt_cathodic_duration_s', 3) + getattr(ec, 'adt_anodic_duration_s', 2))
            self._emit_log(
                f"    ADT 循环测试: {cyc}轮, 预计总时间 {total_t:.0f}s ({total_t/60:.1f}min)"
            )
        
        # 通过 CHIBridge 调用真实 CHI 660F 仪器
        try:
            if not self._ensure_chi_bridge(ec):
                return False
            
            self._emit_log(f"    开始 {technique.upper()} 测量...")
            
            # ---- ADT 多轮循环 ----
            if technique == "ADT":
                def _on_adt_cycle(cycle, total, info):
                    self._emit_log(f"    ⚡ ADT 第 {cycle}/{total} 轮完成")
                result = self._chi_bridge.run_adt(
                    ec,
                    on_cycle=_on_adt_cycle,
                    stop_flag=lambda: self._stop_flag,
                )
            else:
                result = self._chi_bridge.run(ec)
            
            if self._stop_flag:
                self._chi_bridge.stop()
                self._emit_log("    测量被中止")
                return False
            
            if result.success:
                self._emit_log(
                    f"  电化学完成: 采集 {len(result.data_points)} 个数据点, "
                    f"耗时 {result.elapsed_time:.1f}s"
                )
                if result.data_file:
                    self._emit_log(f"    数据文件: {result.data_file}")
                # 保存电化学数据到实验目录
                if self.dm and step_index >= 0:
                    # 构建参数 dict 写入 CSV 注释头
                    ec_params = {
                        "e0": ec.e0, "eh": ec.eh, "el": ec.el, "ef": ec.ef,
                        "scan_rate": ec.scan_rate, "seg_num": ec.seg_num,
                        "run_time_s": ec.run_time_s,
                        "sample_interval_ms": ec.sample_interval_ms,
                        "elapsed_time": f"{result.elapsed_time:.1f}s",
                        "ir_compensation_enabled": ir_enabled,
                        "ir_compensation_ohm": ir_ohm if ir_enabled else 0,
                    }
                    csv_path = self.dm.save_echem_csv(
                        step_index, technique,
                        result.data_points, result.headers,
                        ec_params=ec_params,
                    )
                    if csv_path:
                        self.dm.step_finished(
                            step_index, True,
                            details=f"{technique} 完成, {len(result.data_points)}点",
                            data_file=csv_path,
                            data_points_count=len(result.data_points),
                        )
                        self._steps_already_finished.add(step_index)
                # 发射电化学结果信号，供UI显示图像
                self.echem_result.emit(
                    technique, result.data_points, result.headers
                )
                return True
            else:
                self._emit_log(f"    ❌ 电化学测量失败: {result.error_message}", "ERROR")
                return False
                
        except ImportError:
            self._emit_log("    ⚠ CHI Bridge 模块不可用，使用 Mock 模式", "WARNING")
            return self._execute_echem_mock(ec, technique, step_index)
        except Exception as e:
            self._emit_log(f"    ❌ 电化学异常: {e}", "ERROR")
            return False
    
    def _execute_echem_mock(self, ec: ECSettings, technique: str,
                           step_index: int = -1) -> bool:
        """电化学 Mock 模式 (CHI 不可用时的模拟数据采集)"""
        # 安全获取参数（防止 None）
        _eh = ec.eh if ec.eh is not None else 0.8
        _el = ec.el if ec.el is not None else -0.2
        _ef = ec.ef if ec.ef is not None else 0.5
        _e0 = ec.e0 if ec.e0 is not None else 0.0
        _scan_rate = ec.scan_rate if ec.scan_rate else 0.1
        _seg_num = ec.seg_num if ec.seg_num else 2
        
        # 计算运行时间
        if technique == "CV":
            e_range = abs(_eh - _el)
            run_time = (e_range * _seg_num) / _scan_rate
        elif technique == "LSV":
            e_range = abs(_ef - _e0)
            run_time = e_range / _scan_rate
        elif technique == "ADT":
            cyc = getattr(ec, 'adt_num_cycles', 100)
            cat_t = getattr(ec, 'adt_cathodic_duration_s', 3.0)
            ano_t = getattr(ec, 'adt_anodic_duration_s', 2.0)
            run_time = cyc * (cat_t + ano_t)
        else:
            run_time = ec.run_time_s or 60
        
        actual_run_time = min(run_time, 10)  # Mock 模式最多运行10秒
        self._emit_log(f"    [Mock] 开始模拟 (预计 {run_time:.1f}s, 模拟 {actual_run_time:.1f}s)...")
        
        sample_interval = (ec.sample_interval_ms or 100) / 1000.0
        start_time = time.time()
        data_points = []
        
        while time.time() - start_time < actual_run_time:
            if self._stop_flag:
                self._emit_log("    [Mock] 测量被中止")
                return False
            
            elapsed = time.time() - start_time
            
            if technique == "CV":
                e_range = abs(_eh - _el)
                cycle_time = e_range / _scan_rate
                t_in_cycle = elapsed % cycle_time
                segment = int(elapsed / cycle_time) % 2
                if segment == 0:
                    potential = _el + (t_in_cycle / cycle_time) * e_range
                else:
                    potential = _eh - (t_in_cycle / cycle_time) * e_range
                current = 1e-6 * (potential - 0.3) + 1e-7
            elif technique == "LSV":
                e_range = abs(_ef - _e0)
                progress = elapsed / actual_run_time
                potential = _e0 + progress * (_ef - _e0)
                current = 1e-6 * (potential - 0.3) + 5e-8
            elif technique == "ADT":
                # ADT Mock: 模拟循环数据
                cyc_t = getattr(ec, 'adt_cathodic_duration_s', 3.0) + getattr(ec, 'adt_anodic_duration_s', 2.0)
                t_in_cyc = elapsed % cyc_t
                cat_t = getattr(ec, 'adt_cathodic_duration_s', 3.0)
                if t_in_cyc < cat_t:
                    potential = -1.5  # cathodic
                    current = getattr(ec, 'adt_cathodic_current_mA', -500) * 1e-3
                else:
                    potential = getattr(ec, 'adt_anodic_potential_V', 1.2)
                    current = 5e-3  # anodic current
            elif technique == "OCPT":
                potential = 0.2 + 0.01 * elapsed
                current = 0
            else:
                potential = _e0
                current = 1e-6 * (1 - 2.718 ** (-elapsed / 5))
            
            data_points.append((elapsed, potential, current))
            
            if len(data_points) % 20 == 0:
                progress = (elapsed / actual_run_time) * 100
                self._emit_log(f"    [Mock] 进度: {progress:.0f}% ({len(data_points)} 点)")
            
            time.sleep(sample_interval)
        
        self._emit_log(f"  [Mock] 电化学完成: 采集 {len(data_points)} 个数据点")
        # 保存电化学数据到实验目录
        headers = ["Time/s", "Potential/V", "Current/A"]
        if self.dm and step_index >= 0:
            ec_params = {
                "e0": ec.e0, "eh": ec.eh, "el": ec.el, "ef": ec.ef,
                "scan_rate": ec.scan_rate, "seg_num": ec.seg_num,
                "run_time_s": ec.run_time_s,
                "mock": True,
            }
            csv_path = self.dm.save_echem_csv(
                step_index, technique, data_points, headers,
                ec_params=ec_params,
            )
            if csv_path:
                self.dm.step_finished(
                    step_index, True,
                    details=f"[Mock] {technique} 完成, {len(data_points)}点",
                    data_file=csv_path,
                    data_points_count=len(data_points),
                )
                self._steps_already_finished.add(step_index)
        # 发射结果信号供UI显示
        self.echem_result.emit(technique, data_points, headers)
        return True
    
    def _execute_blank(self, step: ProgStep) -> bool:
        """执行空白步骤"""
        duration = step.duration_s or 5.0
        self._emit_log(f"  空白: 等待 {duration}s")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._stop_flag:
                return False
            time.sleep(0.5)
        
        return True
    
    def _execute_evacuate(self, step: ProgStep) -> bool:
        """执行排空 - 位移模式(编码器闭环) + RPM时间模式回退
        
        百分比逻辑:
        - 反应烧杯(tank2): 从当前→0%, 按 已排出/反应烧杯实际体积 递减, cap 0%
        - 若泵设定体积 > 反应烧杯体积(常见，为保证全部排空), 液体在到达0%后保持
        """
        pump_addr = step.pump_address
        if not pump_addr:
            self._emit_log("  排空: 未指定泵地址")
            return False
        
        if not self._check_pump_connection(pump_addr, "排空"):
            return False
        
        direction = step.pump_direction or "FWD"
        rpm = step.pump_rpm or 100
        volume_ul = step.volume_ul or 0
        
        if volume_ul <= 0:
            self._emit_log("  排空: 体积为0，跳过")
            return True
        
        # 液位动画: 反应烧杯排空
        reaction_vol = self._tank2_volume_ul  # 反应烧杯中实际溶液
        t2_start = self._tank2_level
        t2_end = 0.0
        
        if reaction_vol > 0 and volume_ul > reaction_vol:
            # 泵体积 > 反应烧杯体积 → 液体在 cap_frac 处就全部排完
            cap_frac = reaction_vol / volume_ul  # <1.0
        else:
            cap_frac = 1.0
        
        result = self._run_single_pump_position(
            pump_addr, direction, rpm, volume_ul,
            label="排空",
            t2_start=t2_start, t2_end=t2_end,
            cap_frac=cap_frac,
        )
        
        # 更新体积跟踪: 反应烧杯清空
        if result:
            drained = min(reaction_vol, volume_ul) if reaction_vol > 0 else volume_ul
            self._tank2_volume_ul = max(0, self._tank2_volume_ul - drained)
        
        return result


class ExperimentRunner(QObject):
    """实验运行引擎"""
    
    # 信号
    step_started = Signal(int, str)  # step_index, step_id
    step_finished = Signal(int, str, bool)  # step_index, step_id, success
    log_message = Signal(str, str, str)  # message, level, source
    experiment_finished = Signal(bool)  # success
    echem_result = Signal(str, list, list)  # technique, data_points, headers
    pump_batch_update = Signal(list, list)  # running_pump_addrs, waiting_pump_addrs
    volume_updated = Signal()  # 溶液体积变更信号
    liquid_level_update = Signal(float, float)  # (tank1_fraction, tank2_fraction) 0-1
    paused = Signal()
    resumed = Signal()
    
    def __init__(self, config: Optional[SystemConfig] = None):
        super().__init__()
        self.rs485 = get_rs485_instance()
        self.config = config
        self.is_running = False
        self.is_stopping = False
        self.is_paused = False
        self.experiment: Optional[Experiment] = None
        self.current_step_index = -1
        self._stop_flag = False
        self._pause_flag = False
        self._ocpt_triggered = False  # 旧字段, 保留兼容
        self._adt_running = False
        self._thread: Optional[QThread] = None
        self._worker: Optional[ExperimentWorker] = None
        self._data_manager: Optional[ExperimentDataManager] = None
    
    def set_config(self, config: SystemConfig):
        """设置系统配置"""
        self.config = config
    
    def pre_check_experiment(self, experiment: Experiment) -> list:
        """在 UI 线程中运行预检查（不启动线程），返回错误列表"""
        worker = ExperimentWorker(experiment, self.rs485, self.config)
        return worker.pre_check()
    
    def run_experiment(self, experiment: Experiment):
        """在后台线程运行实验
        
        Returns:
            bool: 是否成功启动
        """
        # 防重入: 运行中/停止中不允许再次启动
        if self.is_busy:
            self.log_message.emit("实验仍在运行或停止中，请稍后再启动", "WARNING", "RUNNER")
            return False
        
        self.experiment = experiment
        self.current_step_index = -1
        self.is_running = True
        self.is_stopping = False
        self._stop_flag = False
        
        # 创建实验数据管理器（每次运行一个独立实例）
        data_dir = self.config.data_dir if self.config else "./data"
        self._data_manager = ExperimentDataManager(base_dir=data_dir)
        
        # 创建线程和worker (传入配置和数据管理器)
        self._thread = QThread()
        self._worker = ExperimentWorker(
            experiment, self.rs485, self.config,
            data_manager=self._data_manager,
        )
        self._worker.moveToThread(self._thread)
        
        # 连接信号
        self._thread.started.connect(self._worker.run)
        self._worker.step_started.connect(self._on_step_started)
        self._worker.step_finished.connect(self._on_step_finished)
        self._worker.log_message.connect(self._on_log_message)
        self._worker.experiment_finished.connect(self._on_experiment_finished)
        self._worker.echem_result.connect(self.echem_result.emit)
        self._worker.pump_batch_update.connect(self.pump_batch_update.emit)
        self._worker.volume_updated.connect(self.volume_updated.emit)
        self._worker.liquid_level_update.connect(self.liquid_level_update.emit)
        self._thread.finished.connect(self._on_thread_finished)
        
        # 启动线程
        self._thread.start()
        return True
    
    def _on_step_started(self, step_index: int, step_id: str):
        self.current_step_index = step_index
        self.step_started.emit(step_index, step_id)
    
    def _on_step_finished(self, step_index: int, step_id: str, success: bool):
        self.step_finished.emit(step_index, step_id, success)
    
    def _on_log_message(self, message: str, level: str, source: str):
        self.log_message.emit(message, level, source)
    
    def _on_experiment_finished(self, success: bool):
        self.is_running = False
        self.is_stopping = False
        self.experiment_finished.emit(success)
        # 安全清理线程
        if self._thread:
            self._thread.quit()

    def _on_thread_finished(self):
        """线程真正结束后的资源清理"""
        self.is_stopping = False
        self.is_running = False
        self._thread = None
        self._worker = None

    @property
    def is_busy(self) -> bool:
        """Runner 是否处于不可启动新实验的状态"""
        thread_running = bool(self._thread and self._thread.isRunning())
        return self.is_running or self.is_stopping or thread_running
    
    @property
    def data_manager(self) -> Optional[ExperimentDataManager]:
        """获取当前实验的数据管理器"""
        return self._data_manager
    
    def stop(self):
        """停止运行"""
        if not self.is_busy:
            return
        self._stop_flag = True
        self.is_running = False
        self.is_stopping = True
        if self._worker:
            self._worker.stop()
        if not self._thread or not self._thread.isRunning():
            self.is_stopping = False
    
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
