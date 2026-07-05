"""
CHI 660F 电化学桥接层 —— ECSettings ↔ CHI660FController

将 UI 层的 ECSettings (src.models) 转换为 CHI660FController 的参数，
并提供简单易用的 run_echem() 接口。

用法示例:
    from src.models import ECSettings, ECTechnique
    from src.echem_sdl.hardware.chi_echem_bridge import run_echem, CHIBridge

    # 方式1: 一行调用
    result = run_echem(ECSettings(technique=ECTechnique.CV, e0=0, eh=0.5, el=-0.5, scan_rate=0.1))

    # 方式2: 持久化控制器实例（连续多次实验）
    bridge = CHIBridge()
    bridge.connect()
    r1 = bridge.run(ECSettings(technique=ECTechnique.CV, ...))
    r2 = bridge.run(ECSettings(technique=ECTechnique.LSV, ...))
    bridge.disconnect()
"""

import os
import math
import logging
import re
from typing import Optional, Tuple, Any, Callable
from dataclasses import dataclass

from src.models import ECSettings, ECTechnique

from .chi660f_gui_controller import (
    CHI660FController,
    ExperimentConfig,
    ExperimentResult,
    CVParams,
    LSVParams,
    ITParams,
    IMPParams,
    OCPTParams,
    CPParams,
    CAParams,
    IRCompensation,
    Technique,
)

logger = logging.getLogger(__name__)


# ============================================================
# ECSettings → Controller Params 转换
# ============================================================

def _ec_to_cv(ec: ECSettings) -> CVParams:
    """ECSettings → CVParams"""
    return CVParams(
        e_init=ec.e0 or 0.0,
        e_high=ec.eh or 0.5,
        e_low=ec.el or -0.5,
        e_final=ec.ef if ec.ef is not None else (ec.e0 or 0.0),
        scan_rate=ec.scan_rate or 0.1,
        segments=ec.seg_num or 2,
        sample_interval=0.001,  # CHI CV 的 si 是电压间隔 (V)，使用默认值
        quiet_time=ec.quiet_time_s or 0.0,
        sensitivity=0.0 if ec.autosensitivity else (ec.sensitivity or 0.0),
        polarity='p' if ec.scan_dir == 'FWD' else 'n',
    )


def _ec_to_lsv(ec: ECSettings) -> LSVParams:
    """ECSettings → LSVParams"""
    return LSVParams(
        e_init=ec.e0 or 0.0,
        e_final=ec.ef if ec.ef is not None else (ec.eh or 0.5),
        scan_rate=ec.scan_rate or 0.1,
        sample_interval=0.001,
        quiet_time=ec.quiet_time_s or 0.0,
        sensitivity=0.0 if ec.autosensitivity else (ec.sensitivity or 0.0),
    )


def _ec_to_it(ec: ECSettings) -> ITParams:
    """ECSettings → ITParams"""
    return ITParams(
        e_init=ec.e0 or 0.0,
        sample_interval=(ec.sample_interval_ms or 100) / 1000.0,  # ms → s
        run_time=ec.run_time_s or 60.0,
        quiet_time=ec.quiet_time_s or 0.0,
        sensitivity=0.0 if ec.autosensitivity else (ec.sensitivity or 0.0),
    )


def _ec_to_imp(ec: ECSettings) -> IMPParams:
    """ECSettings → IMPParams"""
    return IMPParams(
        e_init=ec.e0 or 0.0,
        freq_low=ec.freq_low or 1.0,
        freq_high=ec.freq_high or 100000.0,
        amplitude=ec.amplitude or 0.005,
        quiet_time=ec.quiet_time_s or 0.0,
        auto_sensitivity=ec.autosensitivity,
        bias_mode=ec.bias_mode or 0,
    )


def _ec_to_ocpt(ec: ECSettings) -> OCPTParams:
    """ECSettings → OCPTParams (保留兼容)"""
    return OCPTParams(
        sample_interval=(ec.sample_interval_ms or 1000) / 1000.0,  # ms → s
        run_time=ec.run_time_s or 60.0,
        e_high=ec.eh or 10.0,
        e_low=ec.el or -10.0,
    )


def _ec_to_adt_it(ec: ECSettings) -> ITParams:
    """ADT 阳极步 (potentiostatic) → ITParams"""
    return ITParams(
        e_init=ec.adt_anodic_potential_V if hasattr(ec, 'adt_anodic_potential_V') else 1.2,
        sample_interval=0.01,  # 10ms
        run_time=ec.adt_anodic_duration_s if hasattr(ec, 'adt_anodic_duration_s') else 2.0,
        quiet_time=0.0,
        sensitivity=ec.sensitivity or 1e-3,
    )


def _ec_to_cp(ec: ECSettings) -> CPParams:
    """ECSettings → CPParams (计时电位法) — 全部参数映射"""
    cathodic_mA = getattr(ec, 'adt_cathodic_current_mA', -250.0)
    cathodic_A = abs(cathodic_mA) / 1000.0  # mA → A, CP 用绝对值
    anodic_mA = getattr(ec, 'adt_cp_anodic_current_mA', 250.0)
    anodic_A = abs(anodic_mA) / 1000.0
    return CPParams(
        cathodic_current=cathodic_A,
        anodic_current=anodic_A,
        e_high=getattr(ec, 'adt_cp_e_high', 2.0) or 2.0,
        e_low=getattr(ec, 'adt_cp_e_low', -2.0) or -2.0,
        high_e_hold_time=getattr(ec, 'adt_cp_high_e_hold_time', 0.0),
        low_e_hold_time=getattr(ec, 'adt_cp_low_e_hold_time', 0.0),
        cathodic_time=getattr(ec, 'adt_cathodic_duration_s', 3.0),
        anodic_time=max(0.05, getattr(ec, 'adt_cp_anodic_time_s', 3.0)),
        polarity=getattr(ec, 'adt_cp_polarity', 'n'),
        sample_interval=getattr(ec, 'adt_cp_sample_interval', 0.01),
        segments=getattr(ec, 'adt_cp_segments', 2),
        priority=getattr(ec, 'adt_cp_priority', 'time'),
    )


def _ec_to_ca(ec: ECSettings) -> CAParams:
    """ECSettings → CAParams (计时电流法) — 全部参数映射"""
    return CAParams(
        e_init=getattr(ec, 'adt_anodic_potential_V', 1.5),
        e_high=getattr(ec, 'adt_ca_e_high', 1.5) or 1.5,
        e_low=getattr(ec, 'adt_ca_e_low', -0.5) or -0.5,
        polarity=getattr(ec, 'adt_ca_polarity', 'p'),
        steps=getattr(ec, 'adt_ca_steps', 1),
        pulse_width=getattr(ec, 'adt_anodic_duration_s', 2.0),
        sample_interval=getattr(ec, 'adt_ca_sample_interval', 0.01),
        quiet_time=getattr(ec, 'adt_ca_quiet_time', 0.0),
        sensitivity=getattr(ec, 'adt_ca_sensitivity', 0.0) or 0.0,
    )


# ECTechnique → (Technique, 转换函数)
_TECHNIQUE_MAP = {
    ECTechnique.CV:   (Technique.CV, _ec_to_cv),
    ECTechnique.LSV:  (Technique.LSV, _ec_to_lsv),
    ECTechnique.I_T:  (Technique.IT, _ec_to_it),
    ECTechnique.EIS:  (Technique.IMP, _ec_to_imp),
    # ADT 不走单次 run ，而是多轮循环，在 CHIBridge.run_adt() 中处理
    # 保留 OCPT 兼容 key (旧配置加载时 OCPT 已转换为 ADT)
}


def convert_ec_settings(ec: ECSettings) -> Tuple[Technique, Any]:
    """将 ECSettings 转换为 (Technique, Params) 元组

    Args:
        ec: UI 层的 ECSettings

    Returns:
        (Technique, params) 元组

    Raises:
        ValueError: 不支持的技术类型
    """
    entry = _TECHNIQUE_MAP.get(ec.technique)
    if not entry:
        raise ValueError(f"不支持的电化学技术: {ec.technique}")
    technique, converter = entry
    return technique, converter(ec)


# ============================================================
# CHIBridge (持久化控制器)
# ============================================================

@dataclass
class CHIBridgeConfig:
    """桥接层配置

    Attributes:
        chi_exe_path: chi660f.exe 路径
        output_dir: 数据输出目录
        use_dummy_cell: 是否使用 dummy cell (测试模式)
        force_restart: 连接时是否强制重启
        timeout: 单次实验超时 (秒)
    """
    chi_exe_path: str = r"D:\AI4S\MicroHySeeker\MicroHySeeker\eChemSDL\chi660f光盘-250103\chi660f光盘-250103\chi660f\chi660f.exe"
    output_dir: str = r"D:\CHI660F\data"
    use_dummy_cell: bool = False
    force_restart: bool = False
    timeout: float = 600.0


class CHIBridge:
    """CHI 660F 桥接层 —— 管理控制器生命周期

    使用方式:
        bridge = CHIBridge(CHIBridgeConfig(use_dummy_cell=True))
        bridge.connect()
        result = bridge.run(ec_settings)
        bridge.disconnect()
    """

    def __init__(self, config: Optional[CHIBridgeConfig] = None):
        self._config = config or CHIBridgeConfig()
        self._controller: Optional[CHI660FController] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return (self._connected
                and self._controller is not None
                and self._controller.is_connected())

    def connect(self) -> bool:
        """启动并连接 CHI 660F

        Returns:
            是否连接成功
        """
        exp_config = ExperimentConfig(
            chi_exe_path=self._config.chi_exe_path,
            output_dir=self._config.output_dir,
            use_dummy_cell=self._config.use_dummy_cell,
            timeout=self._config.timeout,
        )
        self._controller = CHI660FController(exp_config)

        ok = self._controller.launch(force_restart=self._config.force_restart)
        self._connected = ok
        if ok:
            logger.info("CHIBridge: 连接成功")
        else:
            logger.error("CHIBridge: 连接失败")
        return ok

    def disconnect(self):
        """断开连接"""
        if self._controller:
            self._controller.close()
            self._controller = None
        self._connected = False
        logger.info("CHIBridge: 已断开")

    def run(self, ec_settings: ECSettings, output_name: str = "") -> ExperimentResult:
        """根据 ECSettings 运行电化学实验

        Args:
            ec_settings: UI 层的 ECSettings
            output_name: 输出文件名 (不含后缀, 留空自动生成)

        Returns:
            ExperimentResult
        """
        if not self.is_connected:
            return ExperimentResult(
                success=False,
                error_message="未连接到 CHI 660F，请先调用 connect()"
            )

        try:
            technique, params = convert_ec_settings(ec_settings)
        except ValueError as e:
            return ExperimentResult(success=False, error_message=str(e))

        # 选择对应的 run_xxx 方法
        run_methods = {
            Technique.CV:   self._controller.run_cv,
            Technique.LSV:  self._controller.run_lsv,
            Technique.IT:   self._controller.run_it,
            Technique.IMP:  self._controller.run_imp,
            Technique.OCPT: self._controller.run_ocpt,
            Technique.CP:   self._controller.run_cp,
            Technique.CA:   self._controller.run_ca,
        }

        run_fn = run_methods.get(technique)
        if not run_fn:
            return ExperimentResult(
                success=False,
                error_message=f"未找到技术 {technique} 的执行方法"
            )

        tech_name = ec_settings.technique.value if hasattr(ec_settings.technique, 'value') else str(ec_settings.technique)
        logger.info(f"CHIBridge: 执行 {tech_name} 实验")
        
        # 动态切换 dummy cell 模式
        if hasattr(ec_settings, 'use_dummy_cell'):
            self._controller._config.use_dummy_cell = ec_settings.use_dummy_cell
        
        # iR 补偿: CV / LSV / i-t 支持; EIS 不需要 (测阻抗本身)
        ir_enabled = getattr(ec_settings, 'ir_compensation_enabled', False)
        ir_ohm = getattr(ec_settings, 'ir_compensation_ohm', 0.0)
        if ir_enabled and ir_ohm > 0 and technique in (Technique.CV, Technique.LSV, Technique.IT):
            self._controller.set_ir_compensation(True, ir_ohm)
            logger.info(f"CHIBridge: iR 补偿已启用, R={ir_ohm}Ω")
        else:
            self._controller.set_ir_compensation(False)
        
        result = run_fn(params, output_name)
        
        # 实验完成后关闭 iR 补偿 (恢复默认)
        if ir_enabled and ir_ohm > 0 and technique in (Technique.CV, Technique.LSV, Technique.IT):
            self._controller.set_ir_compensation(False)

        if result.success:
            logger.info(
                f"CHIBridge: 实验成功, {len(result.data_points)} 个数据点, "
                f"耗时 {result.elapsed_time:.1f}s"
            )
        else:
            logger.error(f"CHIBridge: 实验失败 - {result.error_message}")

        return result

    def stop(self):
        """停止当前实验"""
        if self._controller:
            self._controller.stop_experiment()

    # ------ ADT 多轮循环 ------
    def run_adt(self, ec_settings: ECSettings,
                on_cycle: Optional[Callable] = None,
                stop_flag: Optional[Callable] = None,
                output_prefix: str = "adt") -> ExperimentResult:
        """执行 ADT (加速耐久性测试) 多轮循环

        ★ 批量模式: 将 N 轮 CP+CA 合并为一个宏命令一次性执行。
        消除每轮 ~8s 的 Macro 对话框打开/关闭 overhead。
        
        例如: 100 轮 × (CP 3s + CA 2s) 
            旧: ~1800s (每轮 18s, 含 GUI 开关)
            新: ~550s  (纯实验 500s + 少量启动时间)

        每一轮:
          1) CP (galvanostatic) — 阴极恒电流 HER 步骤
          2) CA (potentiostatic step) — 阳极电位阶跃 (模拟反向电流)

        Args:
            ec_settings: 包含 ADT 参数的 ECSettings
            on_cycle: 每轮回调 (cycle_index, total_cycles, cycle_data)
                      批量模式下在宏执行完成后统一回调
            stop_flag: 返回 True 时中止 (批量模式下仅在执行前检查)
            output_prefix: 输出文件前缀

        Returns:
            ExperimentResult 合并结果
        """
        if not self.is_connected:
            return ExperimentResult(success=False, error_message="CHI 未连接")

        if stop_flag and stop_flag():
            return ExperimentResult(success=False, error_message="ADT 被用户中止")

        num = getattr(ec_settings, 'adt_num_cycles', 100)
        cathodic_mA = getattr(ec_settings, 'adt_cathodic_current_mA', -250.0)
        cathodic_set_A = cathodic_mA / 1000.0
        cathodic_abs_A = abs(cathodic_set_A)  # CHI CP macro expects magnitude.

        # 构造 CP 参数
        cp_params = CPParams(
            cathodic_current=cathodic_abs_A,
            anodic_current=cathodic_abs_A,
            e_high=getattr(ec_settings, 'adt_cp_e_high', 2.0),
            e_low=getattr(ec_settings, 'adt_cp_e_low', -2.0),
            cathodic_time=getattr(ec_settings, 'adt_cathodic_duration_s', 3.0),
            anodic_time=max(0.05, getattr(ec_settings, 'adt_cp_anodic_time_s', 3.0)),
            polarity='n',          # 阴极(负方向)先
            sample_interval=getattr(ec_settings, 'adt_cp_sample_interval', 0.01),
            segments=1,            # 单段 (仅阴极方向)
            priority='time',
        )

        # 构造 CA 参数
        anodic_v = getattr(ec_settings, 'adt_anodic_potential_V', 1.5)
        ca_sens_raw = getattr(ec_settings, 'adt_ca_sensitivity', 0.001)
        ca_params = CAParams(
            e_init=anodic_v,
            e_high=getattr(ec_settings, 'adt_ca_e_high', 1.5) or anodic_v + 0.5,
            e_low=getattr(ec_settings, 'adt_ca_e_low', -0.5),
            polarity='p',
            steps=1,
            pulse_width=getattr(ec_settings, 'adt_anodic_duration_s', 2.0),
            sample_interval=getattr(ec_settings, 'adt_ca_sample_interval', 0.01),
            quiet_time=getattr(ec_settings, 'adt_ca_quiet_time', 0.0),
            sensitivity=ca_sens_raw if ca_sens_raw > 0 else 0.0,
        )

        # iR 补偿
        ir_enabled = getattr(ec_settings, 'ir_compensation_enabled', False)
        ir_resistance = getattr(ec_settings, 'ir_compensation_ohm', 0.0)
        if ir_enabled and ir_resistance > 0:
            self._controller.set_ir_compensation(True, ir_resistance)
        else:
            self._controller.set_ir_compensation(False)

        # dummy cell 模式同步
        if hasattr(ec_settings, 'use_dummy_cell'):
            self._controller._config.use_dummy_cell = ec_settings.use_dummy_cell

        start_time = __import__('time').time()
        
        logger.info(
            f"ADT 批量执行: {num} 轮, "
            f"CP ic={cathodic_set_A}A tc={cp_params.cathodic_time}s, "
            f"CA ei={anodic_v}V pw={ca_params.pulse_width}s"
        )

        output_dir = self._controller._config.output_dir
        try:
            for name in os.listdir(output_dir):
                lower = name.lower()
                if (
                    lower.startswith(f"{output_prefix.lower()}_c")
                    and ("_cathodic." in lower or "_anodic." in lower)
                    and lower.endswith((".csv", ".txt"))
                ):
                    os.remove(os.path.join(output_dir, name))
        except Exception as cleanup_err:
            logger.warning(f"ADT old file cleanup failed: {cleanup_err}")

        # ★ 批量执行: 一次性发送所有轮次
        batch_result = self._controller.run_adt_batch(
            cp_params, ca_params, num, output_prefix
        )

        elapsed = __import__('time').time() - start_time

        # 关闭 iR 补偿 (恢复默认)
        if ir_enabled and ir_resistance > 0:
            self._controller.set_ir_compensation(False)

        # 收集所有数据文件
        # 将每个 CP/CA 子文件的本地时间轴拼接成一个连续时间轴，
        # 这样主界面可直接画出 ADT 的交替脉冲波形。
        all_data = []
        all_headers = [
            "time(s)",
            "potential(V)",
            "current(A)",
            "cycle",
            "phase",
            "set_current(A)",
            "set_potential(V)",
        ]
        time_offset = 0.0
        
        # Always collect child files. CHI may time out after writing usable
        # partial ADT data; losing those rows makes failed runs undebuggable.
        if True:
            for cycle in range(num):
                c = cycle + 1
                for suffix in ("cathodic", "anodic"):
                    csv_path = os.path.join(
                        output_dir, f"{output_prefix}_c{c}_{suffix}.csv"
                    )
                    if os.path.isfile(csv_path):
                        headers, data = self._controller._parse_csv(csv_path)
                        if data:
                            if len(data) >= 2 and len(data[0]) >= 1 and len(data[1]) >= 1:
                                step_gap = max(float(data[1][0]) - float(data[0][0]), 1e-6)
                            else:
                                step_gap = 1e-3
                            appended = False
                            for pt in data:
                                if len(pt) < 2:
                                    continue
                                t = float(pt[0]) + time_offset
                                measured = float(pt[1])
                                if suffix == "cathodic":
                                    row = [
                                        t,
                                        measured,
                                        cathodic_set_A,
                                        c,
                                        0,
                                        cathodic_set_A,
                                        math.nan,
                                    ]
                                else:
                                    row = [
                                        t,
                                        anodic_v,
                                        measured,
                                        c,
                                        1,
                                        math.nan,
                                        anodic_v,
                                    ]
                                all_data.append(row)
                                appended = True
                            if appended:
                                time_offset = float(all_data[-1][0]) + step_gap
                            else:
                                logger.warning(f"ADT child file has no numeric rows: {csv_path}")
                    elif batch_result.success:
                        logger.warning(f"ADT child file missing: {csv_path}")
                
                # 回调 (数据收集完每轮后)
                if on_cycle and batch_result.success:
                    on_cycle(c, num, {
                        "cathodic_success": True,
                        "anodic_success": True,
                    })

        logger.info(
            f"ADT 批量完成: success={batch_result.success}, "
            f"{len(all_data)} 数据点, 耗时 {elapsed:.1f}s"
        )

        child_pattern = re.compile(
            rf"^{re.escape(output_prefix)}_c(\d+)_(cathodic|anodic)\.(csv|txt)$",
            re.IGNORECASE,
        )
        child_files = {}
        try:
            for name in os.listdir(output_dir):
                match = child_pattern.match(name)
                if not match:
                    continue
                cycle_no = int(match.group(1))
                if 1 <= cycle_no <= num:
                    child_files.setdefault(cycle_no, set()).add(match.group(2).lower())
        except Exception as scan_err:
            logger.warning(f"ADT child file diagnostic scan failed: {scan_err}")

        complete_cycles = [
            c for c, phases in child_files.items()
            if {"cathodic", "anodic"}.issubset(phases)
        ]
        incomplete_cycles = []
        for c, phases in sorted(child_files.items()):
            missing = []
            if "cathodic" not in phases:
                missing.append("cathodic")
            if "anodic" not in phases:
                missing.append("anodic")
            if missing:
                incomplete_cycles.append((c, missing))

        child_count = sum(len(phases) for phases in child_files.values())
        last_cycle = max(child_files) if child_files else 0
        diag_parts = [
            f"ADT raw files={child_count}",
            f"cycles_with_data={len(child_files)}/{num}",
            f"complete_cycles={len(complete_cycles)}/{num}",
            f"last_cycle={last_cycle}",
            f"raw_dir={output_dir}",
        ]
        if incomplete_cycles:
            shown = ", ".join(
                f"c{c} missing {'/'.join(missing)}"
                for c, missing in incomplete_cycles[:8]
            )
            if len(incomplete_cycles) > 8:
                shown += f", ...(+{len(incomplete_cycles) - 8})"
            diag_parts.append(f"incomplete={shown}")
        recovery_diag = "; ".join(diag_parts)
        if child_files:
            logger.info(f"ADT raw recovery summary: {recovery_diag}")
        elif not batch_result.success:
            logger.warning(f"ADT failed and no child files were found: {recovery_diag}")

        error_message = batch_result.error_message
        if not batch_result.success:
            error_message = (error_message + "; " if error_message else "") + recovery_diag

        return ExperimentResult(
            success=batch_result.success,
            data_points=all_data,
            headers=all_headers,
            elapsed_time=elapsed,
            data_file="",
            error_message=error_message,
        )


# ============================================================
# 便捷函数 (一次性调用)
# ============================================================

# 模块级单例，避免每次调用都重新启动 CHI
_global_bridge: Optional[CHIBridge] = None


def run_echem(
    ec_settings: ECSettings,
    chi_exe: str = r"D:\AI4S\MicroHySeeker\MicroHySeeker\eChemSDL\chi660f光盘-250103\chi660f光盘-250103\chi660f\chi660f.exe",
    output_dir: str = r"D:\CHI660F\data",
    dummy: bool = False,
    force_restart: bool = False,
    output_name: str = "",
) -> ExperimentResult:
    """一次性运行电化学实验 (自动管理控制器生命周期)

    首次调用时连接 CHI 660F，后续调用复用连接。

    Args:
        ec_settings: UI 层的 ECSettings
        chi_exe: chi660f.exe 路径
        output_dir: 数据输出目录
        dummy: 是否使用 dummy cell
        force_restart: 是否强制重启 CHI660F
        output_name: 输出文件名 (留空自动生成)

    Returns:
        ExperimentResult
    """
    global _global_bridge

    if _global_bridge is None or not _global_bridge.is_connected:
        bridge_config = CHIBridgeConfig(
            chi_exe_path=chi_exe,
            output_dir=output_dir,
            use_dummy_cell=dummy,
            force_restart=force_restart,
        )
        _global_bridge = CHIBridge(bridge_config)
        if not _global_bridge.connect():
            return ExperimentResult(success=False, error_message="CHI 660F 连接失败")

    return _global_bridge.run(ec_settings, output_name)


def close_echem():
    """关闭全局 CHI 连接"""
    global _global_bridge
    if _global_bridge:
        _global_bridge.disconnect()
        _global_bridge = None


# ============================================================
# 命令行测试入口
# ============================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    print("=" * 60)
    print("CHI 660F Bridge 测试 (Dummy Cell)")
    print("=" * 60)

    # CV 测试
    settings = ECSettings(
        technique=ECTechnique.CV,
        e0=0.0,
        eh=0.5,
        el=-0.5,
        ef=0.0,
        scan_rate=0.1,
        seg_num=2,
        quiet_time_s=2.0,
    )

    print(f"\n技术: {settings.technique.value}")
    print(f"参数: E0={settings.e0}, Eh={settings.eh}, El={settings.el}")
    print(f"       scan_rate={settings.scan_rate}, segments={settings.seg_num}")

    result = run_echem(settings, dummy=True, force_restart=True)

    print(f"\n结果:")
    print(f"  成功: {result.success}")
    print(f"  数据点: {len(result.data_points)}")
    print(f"  列名: {result.headers}")
    print(f"  耗时: {result.elapsed_time:.1f}s")
    print(f"  文件: {result.data_file}")
    if result.error_message:
        print(f"  错误: {result.error_message}")
    if result.data_points:
        print(f"  前3点: {result.data_points[:3]}")
