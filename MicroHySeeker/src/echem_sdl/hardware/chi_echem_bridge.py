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

import logging
from typing import Optional, Tuple, Any
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
    """ECSettings → OCPTParams"""
    return OCPTParams(
        sample_interval=(ec.sample_interval_ms or 1000) / 1000.0,  # ms → s
        run_time=ec.run_time_s or 60.0,
        e_high=ec.eh or 10.0,
        e_low=ec.el or -10.0,
    )


# ECTechnique → (Technique, 转换函数)
_TECHNIQUE_MAP = {
    ECTechnique.CV:   (Technique.CV, _ec_to_cv),
    ECTechnique.LSV:  (Technique.LSV, _ec_to_lsv),
    ECTechnique.I_T:  (Technique.IT, _ec_to_it),
    ECTechnique.EIS:  (Technique.IMP, _ec_to_imp),
    ECTechnique.OCPT: (Technique.OCPT, _ec_to_ocpt),
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
    chi_exe_path: str = r"D:\CHI660F\chi660f.exe"
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
        
        result = run_fn(params, output_name)

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


# ============================================================
# 便捷函数 (一次性调用)
# ============================================================

# 模块级单例，避免每次调用都重新启动 CHI
_global_bridge: Optional[CHIBridge] = None


def run_echem(
    ec_settings: ECSettings,
    chi_exe: str = r"D:\CHI660F\chi660f.exe",
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
