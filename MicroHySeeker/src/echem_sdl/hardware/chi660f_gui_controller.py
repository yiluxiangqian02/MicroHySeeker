"""
CHI 660F GUI 自动化控制器

通过 pywinauto + Win32 API 操控 CHI 660F 电化学工作站的 GUI 界面，
利用 Macro Command 对话框 (WM_COMMAND=32799) 填写宏命令并执行。

支持技术:
    - CV  (循环伏安法)
    - LSV (线性扫描伏安法)
    - i-t (安培-时间曲线)
    - EIS/IMP (交流阻抗谱)
    - OCPT (开路电位-时间)
    - CP  (计时电位法 / Chronopotentiometry)
    - CA  (计时电流法 / Chronoamperometry)

附加功能:
    - iR 补偿 (手动正反馈法): ircompon / ircompoff / mir

架构:
    1. launch() → 启动或连接 chi660f.exe
    2. build_macro() → 根据参数生成宏命令文本
    3. execute_macro() → 打开 Macro 对话框 → 填充 → 运行
    4. wait_for_completion() → 等待实验完成
    5. get_data() → 读取并解析 CSV 数据文件

依赖:
    - pywinauto (pip install pywinauto)
    - pywin32  (pip install pywin32)
"""

import os
import csv
import time
import logging
import subprocess
import ctypes
import ctypes.wintypes as wintypes
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import IntEnum

logger = logging.getLogger(__name__)


# ============================================================
# 常量
# ============================================================

# CHI 660F 默认安装路径
DEFAULT_CHI_EXE = r"D:\AI4S\MicroHySeeker\MicroHySeeker\eChemSDL\chi660f光盘-250103\chi660f光盘-250103\chi660f\chi660f.exe"

# Win32 消息常量
WM_COMMAND = 0x0111
WM_CLOSE = 0x0010
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
BM_CLICK = 0x00F5
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BST_CHECKED = 1
BST_UNCHECKED = 0
EM_SETLIMITTEXT = 0x00C5      # Edit 控件文本长度上限

# CHI 660F 菜单 WM_COMMAND IDs (从 chi660f.exe 菜单资源提取)
CMD_TECHNIQUE = 32789       # Setup → Technique...
CMD_PARAMETERS = 32790      # Setup → Parameters...
CMD_SYSTEM_SETUP = 32791    # Setup → System...
CMD_HARDWARE_TEST = 32792   # Setup → Hardware Test
CMD_RUN_EXPERIMENT = 32793  # Control → Run Experiment
CMD_PAUSE_RESUME = 32794    # Control → Pause / Resume
CMD_STOP_RUN = 32795        # Control → Stop Run
CMD_REVERSE_SCAN = 32796    # Control → Reverse Scan
CMD_RUN_STATUS = 32798      # Control → Run Status...
CMD_REPETITIVE_RUNS = 32797 # Control → Repetitive Runs...
CMD_MACRO_COMMAND = 32799   # Control → Macro Command...
CMD_OPEN_CIRCUIT = 32800    # Control → Open Circuit Potential
CMD_CELL = 32803            # Control → Cell...
CMD_DATA_PLOT = 32807       # Graphics → Present Data Plot
CMD_GRAPH_OPTIONS = 32819   # Graphics → Graph Options...
CMD_DATA_INFO = 32837       # View → Data Information...
CMD_DATA_LISTING = 32838    # View → Data Listing...
CMD_FILE_NEW = 57600        # File → New
CMD_FILE_OPEN = 57601       # File → Open
CMD_FILE_CLOSE = 57602      # File → Close
CMD_FILE_SAVE_AS = 57604    # File → Save As
CMD_FILE_EXIT = 57665       # File → Exit

# Macro Command 对话框控件 IDs
MACRO_EDIT_ID = 308         # 宏命令编辑框
MACRO_RUN_BTN_ID = 312      # Run Macro 按钮
MACRO_OK_BTN_ID = 1         # OK 按钮
MACRO_CANCEL_BTN_ID = 2     # Cancel 按钮
MACRO_READ_BTN_ID = 309     # Read 按钮
MACRO_SAVE_BTN_ID = 310     # Save 按钮
MACRO_TEST_BTN_ID = 1450    # Test 按钮
MACRO_RUN_ON_OK_ID = 1713   # Run on OK 复选框


# ============================================================
# 数据模型
# ============================================================

class Technique(IntEnum):
    """支持的电化学技术"""
    CV = 0      # 循环伏安法
    LSV = 1     # 线性扫描伏安法
    IT = 2      # 安培-时间曲线 (i-t)
    IMP = 3     # 交流阻抗 (EIS)
    OCPT = 4    # 开路电位-时间
    CP = 5      # 计时电位法 (Chronopotentiometry)
    CA = 6      # 计时电流法 (Chronoamperometry)


# 技术 → 宏命令 tech 字符串
TECHNIQUE_NAMES: Dict[Technique, str] = {
    Technique.CV:   "cv",
    Technique.LSV:  "lsv",
    Technique.IT:   "i-t",
    Technique.IMP:  "imp",
    Technique.OCPT: "ocpt",
    Technique.CP:   "cp",
    Technique.CA:   "ca",
}


@dataclass
class CVParams:
    """循环伏安法参数
    
    Attributes:
        e_init: 初始电位 (V), 范围 -10 ~ +10
        e_high: 高电位 (V), 范围 -10 ~ +10
        e_low: 低电位 (V), 范围 -10 ~ +10
        e_final: 终止电位 (V), 范围 -10 ~ +10 (默认=e_init)
        scan_rate: 扫描速率 (V/s), 范围 1e-6 ~ 10000
        segments: 扫描段数 (cl), 范围 1 ~ 10000
        sample_interval: 采样间隔 (V), 范围 0.001 ~ 0.064
        quiet_time: 静默时间 (s), 范围 0 ~ 100000
        sensitivity: 灵敏度 (A/V), 0 表示自动
        polarity: 扫描极性, 'p' = 正向先, 'n' = 负向先
    """
    e_init: float = 0.0
    e_high: float = 0.5
    e_low: float = -0.5
    e_final: float = 0.0
    scan_rate: float = 0.1
    segments: int = 2
    sample_interval: float = 0.001
    quiet_time: float = 2.0
    sensitivity: float = 0.0  # 0 = autosens
    polarity: str = 'p'       # 'p' or 'n'


@dataclass
class LSVParams:
    """线性扫描伏安法参数
    
    Attributes:
        e_init: 初始电位 (V), 范围 -10 ~ +10
        e_final: 终止电位 (V), 范围 -10 ~ +10
        scan_rate: 扫描速率 (V/s), 范围 1e-6 ~ 10000
        sample_interval: 采样间隔 (V), 范围 0.001 ~ 0.064
        quiet_time: 静默时间 (s), 范围 0 ~ 100000
        sensitivity: 灵敏度 (A/V), 0 表示自动
    """
    e_init: float = 0.0
    e_final: float = 0.5
    scan_rate: float = 0.1
    sample_interval: float = 0.001
    quiet_time: float = 2.0
    sensitivity: float = 0.0


@dataclass
class ITParams:
    """安培-时间曲线 (i-t) 参数
    
    Attributes:
        e_init: 初始/恒定电位 (V), 范围 -10 ~ +10
        sample_interval: 采样间隔 (s), 范围 4e-7 ~ 50
        run_time: 运行时间 (s), 范围 0.001 ~ 500000
        quiet_time: 静默时间 (s), 范围 0 ~ 100000
        sensitivity: 灵敏度 (A/V), 0 表示自动
    """
    e_init: float = 0.0
    sample_interval: float = 0.1
    run_time: float = 10.0
    quiet_time: float = 2.0
    sensitivity: float = 0.0


@dataclass
class IMPParams:
    """交流阻抗 (EIS/IMP) 参数
    
    Attributes:
        e_init: 初始电位/DC偏置电位 (V), 范围 -10 ~ +10
        freq_low: 最低频率 (Hz), 范围 1e-5 ~ 100000
        freq_high: 最高频率 (Hz), 范围 1e-4 ~ 3000000
        amplitude: AC振幅 (V), 范围 0.001 ~ 0.7
        quiet_time: 静默时间 (s), 范围 0 ~ 100000
        auto_sensitivity: 是否自动灵敏度
        bias_mode: 偏置模式, 0=vs Eref, 1=vs Eoc, 2=vs Einit, 3=vs Eprevious, 4=specific
    """
    e_init: float = 0.0
    freq_low: float = 1.0
    freq_high: float = 100000.0
    amplitude: float = 0.005
    quiet_time: float = 2.0
    auto_sensitivity: bool = True
    bias_mode: int = 0


@dataclass
class OCPTParams:
    """开路电位-时间 (OCPT) 参数
    
    Attributes:
        sample_interval: 采样间隔 (s), 范围 1e-6 ~ 50
        run_time: 运行时间 (s), 范围 0.1 ~ 500000
        e_high: 高电位限制 (V), 范围 -10 ~ +10
        e_low: 低电位限制 (V), 范围 -10 ~ +10
    """
    sample_interval: float = 1.0
    run_time: float = 60.0
    e_high: float = 10.0
    e_low: float = -10.0


@dataclass
class CPParams:
    """计时电位法 (Chronopotentiometry, CP) 参数
    
    恒电流模式下记录电位随时间变化。支持阴极/阳极交替循环。
    用于 ADT (加速耐久性测试) 的阴极 HER 步骤。
    
    Attributes:
        cathodic_current: 阴极电流 (A), 范围 0 ~ 0.25
        anodic_current: 阳极电流 (A), 范围 0 ~ 0.25
        e_high: 高电位限 (V), 范围 -10 ~ +10
        e_low: 低电位限 (V), 范围 -10 ~ +10
        high_e_hold_time: 高电位保持时间 (s), 范围 0 ~ 100000
        low_e_hold_time: 低电位保持时间 (s), 范围 0 ~ 100000
        cathodic_time: 阴极时间 (s), 范围 0.005 ~ 100000
        anodic_time: 阳极时间 (s), 范围 0.005 ~ 100000
        polarity: 首步极性, 'p'=阳极先, 'n'=阴极先
        sample_interval: 采样间隔 (s), 范围 0.0025 ~ 32
        segments: 段数, 范围 1 ~ 1000000
        priority: 优先级, 'time' 或 'potential'
    """
    cathodic_current: float = 0.001    # ic (A)
    anodic_current: float = 0.001      # ia (A)
    e_high: float = 2.0                # eh (V)
    e_low: float = -2.0                # el (V)
    high_e_hold_time: float = 0.0      # heht (s)
    low_e_hold_time: float = 0.0       # leht (s)
    cathodic_time: float = 10.0        # tc (s)
    anodic_time: float = 10.0          # ta (s)
    polarity: str = 'n'                # pn: 'p' or 'n', ADT 通常阴极先
    sample_interval: float = 0.1       # si (s)
    segments: int = 2                  # cl: 段数 (1段=单方向)
    priority: str = 'time'             # 'time' or 'potential'


@dataclass
class CAParams:
    """计时电流法 (Chronoamperometry, CA) 参数
    
    恒电位阶跃模式下记录电流随时间变化。支持多步电位阶跃。
    用于 ADT (加速耐久性测试) 的阳极 RC (反向电流) 步骤。
    
    Attributes:
        e_init: 初始电位 (V), 范围 -10 ~ +10
        e_high: 高电位限 (V), 范围 -10 ~ +10
        e_low: 低电位限 (V), 范围 -10 ~ +10
        polarity: 变化方向, 'p'=正向, 'n'=负向
        steps: 阶跃数, 范围 1 ~ 320
        pulse_width: 脉冲宽度 (s), 范围 1e-4 ~ 1000
        sample_interval: 采样间隔 (s), 范围 2e-6 ~ 10
        quiet_time: 静默时间 (s), 范围 0 ~ 100000
        sensitivity: 灵敏度 (A/V), 0 表示自动
    """
    e_init: float = 0.0           # ei (V)
    e_high: float = 1.5           # eh (V)
    e_low: float = -0.5           # el (V)
    polarity: str = 'p'           # pn: 'p' or 'n'
    steps: int = 1                # cl: 阶跃数
    pulse_width: float = 2.0      # pw (s)
    sample_interval: float = 0.01 # si (s)
    quiet_time: float = 2.0       # qt (s)
    sensitivity: float = 0.0      # sens, 0 = autosens


@dataclass
class IRCompensation:
    """iR 补偿配置
    
    CHI 660F 支持手动 iR 补偿 (正反馈法)。
    通过宏命令 ircompon / ircompoff / mir 控制。
    
    Attributes:
        enabled: 是否启用 iR 补偿
        resistance: 手动补偿电阻值 (Ω), 范围 0 ~ 1e9
    """
    enabled: bool = False
    resistance: float = 0.0  # mir (Ω)


@dataclass
class ExperimentConfig:
    """实验配置
    
    Attributes:
        chi_exe_path: chi660f.exe 路径
        output_dir: 数据输出目录
        output_format: 输出格式 ('csv' | 'txt')
        use_dummy_cell: 是否使用内置 dummy cell (测试用)
        file_override: 是否覆盖已有文件
        timeout: 实验最大等待时间 (秒)
        auto_close_macro: 宏执行完后是否自动关闭对话框
        startup_wait: 启动等待时间 (秒)
    """
    chi_exe_path: str = DEFAULT_CHI_EXE
    output_dir: str = ""
    output_format: str = "csv"
    use_dummy_cell: bool = False
    file_override: bool = True
    timeout: float = 600.0
    auto_close_macro: bool = True
    startup_wait: float = 5.0
    ir_compensation: Optional[IRCompensation] = None  # iR 补偿配置


@dataclass
class ExperimentResult:
    """实验结果
    
    Attributes:
        success: 是否成功
        technique: 使用的技术
        data_file: 数据文件路径
        data_points: 数据点列表 [(x, y, ...)]
        headers: 列名列表
        elapsed_time: 实验耗时 (秒)
        error_message: 错误信息 (如有)
    """
    success: bool = False
    technique: str = ""
    data_file: str = ""
    data_points: List[List[float]] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    elapsed_time: float = 0.0
    error_message: str = ""


# ============================================================
# Win32 辅助函数
# ============================================================

_user32 = ctypes.windll.user32
_WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def _get_window_text(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def _get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _is_visible(hwnd: int) -> bool:
    return bool(_user32.IsWindowVisible(hwnd))


def _enum_toplevel() -> List[int]:
    windows = []
    @_WNDENUMPROC
    def cb(hwnd, _):
        if _is_visible(hwnd):
            windows.append(hwnd)
        return True
    _user32.EnumWindows(cb, 0)
    return windows


def _enum_children(parent: int) -> List[int]:
    children = []
    @_WNDENUMPROC
    def cb(hwnd, _):
        children.append(hwnd)
        return True
    _user32.EnumChildWindows(parent, cb, 0)
    return children


def _find_child_by_id(parent: int, ctrl_id: int) -> Optional[int]:
    hwnd = _user32.GetDlgItem(parent, ctrl_id)
    return hwnd if hwnd else None


def _set_edit_text(hwnd: int, text: str):
    """设置 Edit 控件文字"""
    # 扩大文本长度上限 (默认 32KB, ADT 批量宏可能 > 64KB)
    need_limit = len(text) + 1024
    if need_limit > 30000:
        _user32.SendMessageW(hwnd, EM_SETLIMITTEXT, need_limit, 0)
    _user32.SendMessageW(hwnd, WM_SETTEXT, 0, text)


def _get_edit_text(hwnd: int) -> str:
    """获取 Edit 控件文字"""
    length = _user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    _user32.SendMessageW(hwnd, WM_GETTEXT, length + 1, buf)
    return buf.value


def _click_button(hwnd: int):
    """点击按钮"""
    _user32.SendMessageW(hwnd, BM_CLICK, 0, 0)


def _post_command(hwnd: int, cmd_id: int):
    """发送 WM_COMMAND"""
    _user32.PostMessageW(hwnd, WM_COMMAND, cmd_id, 0)


def _set_foreground(hwnd: int):
    """前置窗口"""
    _user32.SetForegroundWindow(hwnd)


# ============================================================
# 宏命令生成
# ============================================================

class MacroBuilder:
    """宏命令文本生成器
    
    根据技术类型和参数生成 CHI 660F 宏命令文本。
    """
    
    @staticmethod
    def build(technique: Technique, params, config: ExperimentConfig,
              output_name: str = "") -> str:
        """生成完整的宏命令文本
        
        Args:
            technique: 实验技术
            params: 对应技术的参数 dataclass
            config: 实验配置
            output_name: 输出文件名 (不含后缀)
            
        Returns:
            宏命令文本
        """
        lines = []
        
        # 输出目录
        if config.output_dir:
            lines.append(f"folder: {config.output_dir}")
        
        # 文件覆盖
        if config.file_override:
            lines.append("fileoverride")
        
        # Dummy cell
        if config.use_dummy_cell:
            lines.append("dummyon")
        
        # 选择技术
        tech_str = TECHNIQUE_NAMES[technique]
        lines.append(f"tech: {tech_str}")
        
        # 技术参数
        if technique == Technique.CV:
            lines.extend(MacroBuilder._cv_params(params))
        elif technique == Technique.LSV:
            lines.extend(MacroBuilder._lsv_params(params))
        elif technique == Technique.IT:
            lines.extend(MacroBuilder._it_params(params))
        elif technique == Technique.IMP:
            lines.extend(MacroBuilder._imp_params(params))
        elif technique == Technique.OCPT:
            lines.extend(MacroBuilder._ocpt_params(params))
        elif technique == Technique.CP:
            lines.extend(MacroBuilder._cp_params(params))
        elif technique == Technique.CA:
            lines.extend(MacroBuilder._ca_params(params))
        
        # iR 补偿 (在 run 之前设置)
        lines.extend(MacroBuilder._ir_comp_commands(config))
        
        # 执行实验
        lines.append("run")
        
        # 保存数据
        if not output_name:
            output_name = f"{tech_str}_{time.strftime('%Y%m%d_%H%M%S')}"
        
        if config.output_format == "csv":
            lines.append(f"csvsave: {output_name}")
        else:
            lines.append(f"tsave: {output_name}")
        
        # 关闭 dummy cell
        if config.use_dummy_cell:
            lines.append("dummyoff")
        
        return "\n".join(lines)
    
    @staticmethod
    def build_adt_batch(cp_params: 'CPParams', ca_params: 'CAParams',
                        config: 'ExperimentConfig', num_cycles: int,
                        output_prefix: str = "adt") -> str:
        """生成 ADT 批量宏命令 —— 将 N 轮 CP+CA 合并到一个宏文本中
        
        CHI 660F 宏语言支持在一个文本中顺序写多个 tech→params→run→save 块。
        每条 run 完成后才执行下一条，这样只需打开一次 Macro 对话框，
        消除每轮 ~8s 的 GUI 开关 overhead。
        
        100 轮 × (CP 3s + CA 2s) = ~500s 纯实验时间 vs 旧方式 ~1800s。
        
        Args:
            cp_params: CP 参数
            ca_params: CA 参数
            config: 实验配置
            num_cycles: 循环轮数
            output_prefix: 输出文件前缀
            
        Returns:
            完整的宏命令文本
        """
        lines = []
        
        # 输出目录 (只设一次)
        if config.output_dir:
            lines.append(f"folder: {config.output_dir}")
        if config.file_override:
            lines.append("fileoverride")
        
        # Dummy cell
        if config.use_dummy_cell:
            lines.append("dummyon")
        
        # iR 补偿 (全局设置一次)
        lines.extend(MacroBuilder._ir_comp_commands(config))
        
        # N 轮循环: 每轮 CP → save → CA → save
        for cycle in range(num_cycles):
            c = cycle + 1
            # --- CP 块 ---
            lines.append("tech: cp")
            lines.extend(MacroBuilder._cp_params(cp_params))
            lines.append("run")
            if config.output_format == "csv":
                lines.append(f"csvsave: {output_prefix}_c{c}_cathodic")
            else:
                lines.append(f"tsave: {output_prefix}_c{c}_cathodic")
            
            # --- CA 块 ---
            lines.append("tech: ca")
            lines.extend(MacroBuilder._ca_params(ca_params))
            lines.append("run")
            if config.output_format == "csv":
                lines.append(f"csvsave: {output_prefix}_c{c}_anodic")
            else:
                lines.append(f"tsave: {output_prefix}_c{c}_anodic")
        
        # 关闭 dummy cell
        if config.use_dummy_cell:
            lines.append("dummyoff")
        
        # 关闭 iR 补偿 (恢复)
        ir = config.ir_compensation
        if ir and ir.enabled:
            lines.append("ircompoff")
        
        return "\n".join(lines)
    
    @staticmethod
    def _cv_params(p: CVParams) -> List[str]:
        lines = [
            f"ei = {p.e_init}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
            f"ef = {p.e_final}",
            f"pn = {p.polarity}",
            f"v = {p.scan_rate}",
            f"cl = {p.segments}",
            f"si = {p.sample_interval}",
            f"qt = {p.quiet_time}",
        ]
        if p.sensitivity > 0:
            lines.append(f"sens = {p.sensitivity}")
        else:
            lines.append("autosens")
        return lines
    
    @staticmethod
    def _lsv_params(p: LSVParams) -> List[str]:
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"v = {p.scan_rate}",
            f"si = {p.sample_interval}",
            f"qt = {p.quiet_time}",
        ]
        if p.sensitivity > 0:
            lines.append(f"sens = {p.sensitivity}")
        else:
            lines.append("autosens")
        return lines
    
    @staticmethod
    def _it_params(p: ITParams) -> List[str]:
        lines = [
            f"ei = {p.e_init}",
            f"si = {p.sample_interval}",
            f"st = {p.run_time}",
            f"qt = {p.quiet_time}",
        ]
        if p.sensitivity > 0:
            lines.append(f"sens = {p.sensitivity}")
        else:
            lines.append("autosens")
        return lines
    
    @staticmethod
    def _imp_params(p: IMPParams) -> List[str]:
        lines = [
            f"ei = {p.e_init}",
            f"fl = {p.freq_low}",
            f"fh = {p.freq_high}",
            f"amp = {p.amplitude}",
            f"qt = {p.quiet_time}",
        ]
        if p.auto_sensitivity:
            lines.append("impautosens")
        if p.bias_mode > 0:
            lines.append(f"ibias = {p.bias_mode}")
        return lines
    
    @staticmethod
    def _ocpt_params(p: OCPTParams) -> List[str]:
        return [
            f"si = {p.sample_interval}",
            f"st = {p.run_time}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
        ]
    
    @staticmethod
    def _cp_params(p: CPParams) -> List[str]:
        """计时电位法 (CP) 宏参数
        
        CHI 660F CP 命令参考:
            ic: 阴极电流 (A), 0 ~ 0.25
            ia: 阳极电流 (A), 0 ~ 0.25
            eh: 高电位限 (V)
            el: 低电位限 (V)
            heht: 高电位保持时间 (s)
            leht: 低电位保持时间 (s)
            tc: 阴极时间 (s), 0.005 ~ 100000
            ta: 阳极时间 (s), 0.005 ~ 100000
            pn: 首步极性 ('p' 或 'n')
            si: 采样间隔 (s), 0.0025 ~ 32
            cl: 段数, 1 ~ 1000000
            priot / prioe: 时间优先 / 电位优先
        """
        lines = [
            f"ic = {p.cathodic_current}",
            f"ia = {p.anodic_current}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
            f"tc = {p.cathodic_time}",
            f"ta = {p.anodic_time}",
            f"pn = {p.polarity}",
            f"si = {p.sample_interval}",
            f"cl = {p.segments}",
        ]
        # 高低电位保持时间 (非零才写)
        if p.high_e_hold_time > 0:
            lines.append(f"heht = {p.high_e_hold_time}")
        if p.low_e_hold_time > 0:
            lines.append(f"leht = {p.low_e_hold_time}")
        # 优先级
        if p.priority == 'potential':
            lines.append("prioe")
        else:
            lines.append("priot")
        return lines
    
    @staticmethod
    def _ca_params(p: CAParams) -> List[str]:
        """计时电流法 (CA) 宏参数
        
        CHI 660F CA 命令参考:
            ei: 初始电位 (V), -10 ~ +10
            eh: 高电位限 (V)
            el: 低电位限 (V)
            pn: 变化方向 ('p' 或 'n')
            cl: 阶跃数, 1 ~ 320
            pw: 脉冲宽度 (s), 1e-4 ~ 1000
            si: 采样间隔 (s), 2e-6 ~ 10
            qt: 静默时间 (s), 0 ~ 100000
            sens: 灵敏度 (A/V)
        """
        lines = [
            f"ei = {p.e_init}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
            f"pn = {p.polarity}",
            f"cl = {p.steps}",
            f"pw = {p.pulse_width}",
            f"si = {p.sample_interval}",
            f"qt = {p.quiet_time}",
        ]
        if p.sensitivity > 0:
            lines.append(f"sens = {p.sensitivity}")
        else:
            lines.append("autosens")
        return lines
    
    @staticmethod
    def _ir_comp_commands(config: ExperimentConfig) -> List[str]:
        """生成 iR 补偿宏命令
        
        CHI 660F 支持手动 iR 补偿 (正反馈法):
            ircompon  — 开启手动 iR 补偿
            ircompoff — 关闭 iR 补偿
            mir = X   — 设置手动补偿电阻 (Ω)
        """
        ir = config.ir_compensation
        if ir is None or not ir.enabled:
            return []
        lines = ["ircompon"]
        if ir.resistance > 0:
            lines.append(f"mir = {ir.resistance}")
        return lines


# ============================================================
# CHI 660F GUI 控制器
# ============================================================

class CHI660FController:
    """CHI 660F 电化学工作站 GUI 自动化控制器
    
    核心工作流:
        controller = CHI660FController(config)
        controller.launch()                        # 启动/连接
        result = controller.run_cv(CVParams(...))   # 运行实验
        controller.close()                         # 关闭
    
    通过 Macro Command 对话框实现全自动化:
        1. 启动 chi660f.exe (如未运行)
        2. WM_COMMAND 32799 打开 Macro Command 对话框
        3. 向 Edit(id=308) 填写宏命令
        4. 点击 Run Macro(id=312) 执行
        5. 监测实验完成状态
        6. 读取 CSV 数据
    """
    
    def __init__(self, config: Optional[ExperimentConfig] = None):
        self._config = config or ExperimentConfig()
        self._main_hwnd: Optional[int] = None
        self._process: Optional[subprocess.Popen] = None
        self._is_running = False
        self._last_dialog_error = ""
        
        # 确保输出目录
        if not self._config.output_dir:
            self._config.output_dir = os.path.join(
                os.path.dirname(self._config.chi_exe_path), "data"
            )
        os.makedirs(self._config.output_dir, exist_ok=True)
        
        logger.info(f"CHI660F Controller 初始化, output_dir={self._config.output_dir}")
    
    # ----------------------------------------------------------
    # 启动 & 连接
    # ----------------------------------------------------------
    
    def launch(self, force_restart: bool = False) -> bool:
        """启动 chi660f.exe 或连接到已运行的实例
        
        Args:
            force_restart: 是否强制重启 (杀掉旧进程再启动)
            
        Returns:
            是否成功连接
            
        Raises:
            FileNotFoundError: chi660f.exe 不存在
        """
        exe_path = self._config.chi_exe_path
        if not os.path.isfile(exe_path):
            raise FileNotFoundError(f"chi660f.exe 未找到: {exe_path}")
        
        if force_restart:
            self._kill_chi()
        
        # 先检查是否已运行
        self._main_hwnd = self._find_chi_window()
        if self._main_hwnd:
            # 检查应用是否处于健康状态
            if self._is_app_healthy():
                logger.info(f"已连接到运行中的 CHI660F (hwnd=0x{self._main_hwnd:08X})")
                self._dismiss_error_dialogs()
                return True
            else:
                logger.warning("CHI660F 处于异常状态，重启中...")
                self._kill_chi()
                time.sleep(2)
        
        # 启动新进程
        logger.info(f"启动 chi660f.exe: {exe_path}")
        self._process = subprocess.Popen([exe_path])
        
        # 等待窗口出现 (最多15秒)
        for _ in range(30):
            time.sleep(0.5)
            self._main_hwnd = self._find_chi_window()
            if self._main_hwnd:
                break
        
        if not self._main_hwnd:
            logger.error("chi660f.exe 启动超时")
            return False
        
        # 等额外2秒让窗口完全加载
        time.sleep(2.0)
        
        # ★ 处理启动时的 "Connecting to instrument" 对话框
        # CHI660F 启动后会自动尝试连接仪器，可能弹出此对话框
        self._handle_connecting_dialog(timeout=30.0)
        
        # 关闭可能出现的错误对话框
        self._dismiss_error_dialogs()
        
        logger.info(f"CHI660F 已启动 (hwnd=0x{self._main_hwnd:08X})")
        return True
    
    def close(self):
        """关闭 CHI 660F"""
        if self._main_hwnd:
            _post_command(self._main_hwnd, CMD_FILE_EXIT)
            time.sleep(1)
            
            # 如果还存在，强制关闭
            if self._find_chi_window():
                _user32.PostMessageW(self._main_hwnd, WM_CLOSE, 0, 0)
                time.sleep(1)
        
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None
        
        self._main_hwnd = None
        logger.info("CHI660F 已关闭")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        if not self._main_hwnd:
            return False
        return bool(_is_visible(self._main_hwnd))
    
    # ----------------------------------------------------------
    # 便捷实验方法
    # ----------------------------------------------------------
    
    def run_cv(self, params: CVParams, output_name: str = "") -> ExperimentResult:
        """执行循环伏安法 (CV) 实验"""
        return self._run_experiment(Technique.CV, params, output_name)
    
    def run_lsv(self, params: LSVParams, output_name: str = "") -> ExperimentResult:
        """执行线性扫描伏安法 (LSV) 实验"""
        return self._run_experiment(Technique.LSV, params, output_name)
    
    def run_it(self, params: ITParams, output_name: str = "") -> ExperimentResult:
        """执行安培-时间曲线 (i-t) 实验"""
        return self._run_experiment(Technique.IT, params, output_name)
    
    def run_imp(self, params: IMPParams, output_name: str = "") -> ExperimentResult:
        """执行交流阻抗 (EIS/IMP) 实验"""
        return self._run_experiment(Technique.IMP, params, output_name)
    
    def run_ocpt(self, params: OCPTParams, output_name: str = "") -> ExperimentResult:
        """执行开路电位-时间 (OCPT) 实验"""
        return self._run_experiment(Technique.OCPT, params, output_name)
    
    def run_cp(self, params: CPParams, output_name: str = "") -> ExperimentResult:
        """执行计时电位法 (Chronopotentiometry, CP) 实验
        
        恒电流模式下记录电位随时间变化。
        用于 ADT 的阴极 HER 步骤或电池充放电测试。
        """
        return self._run_experiment(Technique.CP, params, output_name)
    
    def run_ca(self, params: CAParams, output_name: str = "") -> ExperimentResult:
        """执行计时电流法 (Chronoamperometry, CA) 实验
        
        恒电位阶跃模式下记录电流随时间变化。
        用于 ADT 的阳极反向电流步骤或扩散系数测定。
        """
        return self._run_experiment(Technique.CA, params, output_name)
    
    def set_ir_compensation(self, enabled: bool, resistance: float = 0.0):
        """设置实验的 iR 补偿参数
        
        Args:
            enabled: 是否启用手动 iR 补偿
            resistance: 补偿电阻 (Ω), 通过 EIS 预先测量
        """
        self._config.ir_compensation = IRCompensation(
            enabled=enabled, resistance=resistance
        )
        logger.info(f"iR 补偿设置: enabled={enabled}, R={resistance}Ω")
    
    def run_custom_macro(self, macro_text: str) -> ExperimentResult:
        """执行自定义宏命令
        
        Args:
            macro_text: 宏命令文本 (每行一条命令)
            
        Returns:
            ExperimentResult
        """
        return self._execute_macro_text(macro_text)
    
    def run_adt_batch(self, cp_params: CPParams, ca_params: CAParams,
                      num_cycles: int, output_prefix: str = "adt",
                      timeout_override: float = 0) -> ExperimentResult:
        """批量执行 ADT 循环 —— 一次性发送 N 轮 CP+CA 到单个宏命令
        
        将所有循环合并到一个宏文本中执行，消除每轮的 GUI overhead。
        
        Args:
            cp_params: CP 参数
            ca_params: CA 参数  
            num_cycles: 循环轮数
            output_prefix: 输出文件前缀
            timeout_override: 超时覆盖 (秒), 0=自动计算
            
        Returns:
            ExperimentResult
        """
        if not self.is_connected():
            return ExperimentResult(
                success=False,
                error_message="未连接到 CHI660F，请先调用 launch()"
            )
        
        # 生成批量宏文本
        macro_text = MacroBuilder.build_adt_batch(
            cp_params, ca_params, self._config, num_cycles, output_prefix
        )
        
        macro_size = len(macro_text)
        logger.info(
            f"生成 ADT 批量宏命令: {num_cycles} 轮 CP+CA, "
            f"宏文本 {macro_size} 字符"
        )
        
        if timeout_override > 0:
            logger.info("忽略 ADT timeout_override；实验执行不使用总时长超时")
        logger.info("ADT 批量执行不使用总时长超时，等待明确完成/失败信号")
        
        result = self._execute_macro_text(macro_text)
        result.technique = f"ADT_batch_{num_cycles}cycles"
        
        return result
    
    # ----------------------------------------------------------
    # 核心执行流程
    # ----------------------------------------------------------
    
    def _run_experiment(self, technique: Technique, params,
                        output_name: str = "") -> ExperimentResult:
        """执行实验的核心方法"""
        if not self.is_connected():
            return ExperimentResult(
                success=False,
                error_message="未连接到 CHI660F，请先调用 launch()"
            )
        
        # 生成宏命令
        macro_text = MacroBuilder.build(
            technique, params, self._config, output_name
        )
        
        logger.info(f"生成宏命令 ({TECHNIQUE_NAMES[technique]}):\n{macro_text}")
        
        # 执行宏
        result = self._execute_macro_text(macro_text)
        result.technique = TECHNIQUE_NAMES[technique]
        
        return result
    
    def _execute_macro_text(self, macro_text: str) -> ExperimentResult:
        """通过 Macro Command 对话框执行宏命令
        
        工作流:
            1. WM_COMMAND 32799 → 打开对话框
            2. 查找 Edit(308) → 填入宏文本
            3. 触发宏执行 (多策略: Run Macro / WM_COMMAND / OK+RunOnOK)
            4. 监测完成
            5. 关闭对话框 (如果还在)
        """
        result = ExperimentResult()
        start_time = time.time()
        macro_dialog_closed = False  # 跟踪对话框是否已被 OK 关闭
        
        try:
            # 确保无残留对话框
            self._dismiss_error_dialogs()
            
            # 1. 打开 Macro Command 对话框
            macro_hwnd = self._open_macro_dialog()
            if not macro_hwnd:
                result.error_message = "无法打开 Macro Command 对话框"
                return result
            
            # 2. 填写宏命令
            edit_hwnd = _find_child_by_id(macro_hwnd, MACRO_EDIT_ID)
            if not edit_hwnd:
                result.error_message = "未找到宏命令编辑框"
                self._close_macro_dialog(macro_hwnd)
                return result
            
            # 将换行符转为 \r\n (Windows Edit 控件)
            text = macro_text.replace('\n', '\r\n')
            _set_edit_text(edit_hwnd, text)
            time.sleep(0.3)
            
            # 验证文本已填入
            filled = _get_edit_text(edit_hwnd)
            if len(filled) < 10:
                result.error_message = "宏命令文本填写失败"
                self._close_macro_dialog(macro_hwnd)
                return result
            
            logger.info(f"宏命令已填写 ({len(filled)} 字符)")
            
            # 3. 推算预期输出文件
            expected_file = self._extract_output_file(macro_text)
            
            # 4. 触发宏执行 (多重策略，自动选择可靠的方式)
            triggered = self._trigger_macro_run(macro_hwnd)
            if not triggered:
                result.error_message = "无法触发宏执行 (所有策略均失败)"
                self._close_macro_dialog(macro_hwnd)
                return result
            
            # 检查对话框是否已被 OK 按钮关闭
            time.sleep(0.3)
            if not _is_visible(macro_hwnd):
                macro_dialog_closed = True
                logger.info("Macro 对话框已被 OK 关闭, 宏正在后台执行")
            
            # 5. 等待实验完成
            self._is_running = True
            wait_hwnd = None if macro_dialog_closed else macro_hwnd
            success = self._wait_for_completion(expected_file, macro_hwnd=wait_hwnd)
            self._is_running = False
            
            if success:
                result.success = True
                result.data_file = expected_file or ""
                
                # 6. 读取数据
                if expected_file and os.path.isfile(expected_file):
                    headers, data = self._parse_csv(expected_file)
                    result.headers = headers
                    result.data_points = data
                    logger.info(f"数据读取完成: {len(data)} 点, 列={headers}")
            else:
                diag = self._collect_chi_gui_diagnostics()
                result.error_message = "实验执行失败或未完成"
                if diag:
                    result.error_message += f"; {diag}"
            
            # 7. 关闭 Macro 对话框 (仅在对话框仍然打开时)
            if not macro_dialog_closed and self._config.auto_close_macro:
                self._close_macro_dialog(macro_hwnd)
        
        except Exception as e:
            result.error_message = f"执行异常: {e}"
            logger.exception("宏执行异常")
        
        result.elapsed_time = time.time() - start_time
        return result
    
    def _trigger_macro_run(self, macro_hwnd: int) -> bool:
        """触发宏执行 —— 多重策略确保可靠
        
        CHI660F 是老式 MFC 应用，部分按钮不响应 BM_CLICK。
        按优先级依次尝试:
            策略1: BM_CLICK 点击 Run Macro 按钮
            策略2: WM_COMMAND 模拟按钮点击通知
            策略3: 勾选 "Run on OK" → 点击 OK (此策略会关闭对话框)
        
        Returns:
            是否成功触发宏执行
        """
        run_btn = _find_child_by_id(macro_hwnd, MACRO_RUN_BTN_ID)
        
        # --- 策略 1: BM_CLICK ---
        if run_btn:
            # 先聚焦按钮，再点击
            _user32.SetFocus(run_btn)
            time.sleep(0.1)
            logger.info("触发宏 — 策略1: BM_CLICK Run Macro")
            _click_button(run_btn)
            time.sleep(2.0)
            
            # 检查 Run 按钮是否被禁用 (= 宏正在执行)
            if run_btn and not _user32.IsWindowEnabled(run_btn):
                logger.info("✅ 宏开始执行 (策略1: BM_CLICK)")
                return True
        
        # --- 策略 2: WM_COMMAND (BN_CLICKED 通知) ---
        if run_btn:
            logger.info("触发宏 — 策略2: WM_COMMAND BN_CLICKED")
            # BN_CLICKED = 0, wParam = MAKEWPARAM(ctrl_id, BN_CLICKED)
            _user32.SendMessageW(macro_hwnd, WM_COMMAND,
                                 MACRO_RUN_BTN_ID, run_btn)
            time.sleep(2.0)
            
            if not _user32.IsWindowEnabled(run_btn):
                logger.info("✅ 宏开始执行 (策略2: WM_COMMAND)")
                return True
        
        # --- 策略 3: 确保 "Run on OK" 勾选 → 点击 OK ---
        # OK 按钮会关闭对话框并执行宏 (调用者需检查对话框是否已关闭)
        logger.info("触发宏 — 策略3: OK 按钮 + Run on OK")
        run_on_ok_ckb = _find_child_by_id(macro_hwnd, MACRO_RUN_ON_OK_ID)
        if run_on_ok_ckb:
            check_state = _user32.SendMessageW(run_on_ok_ckb, BM_GETCHECK, 0, 0)
            if check_state != BST_CHECKED:
                # 勾选 "Run on OK"
                _click_button(run_on_ok_ckb)
                time.sleep(0.3)
                logger.info("已勾选 'Run on OK'")
        
        ok_btn = _find_child_by_id(macro_hwnd, MACRO_OK_BTN_ID)
        if ok_btn:
            logger.info("点击 OK (Run on OK 模式)...")
            _click_button(ok_btn)
            time.sleep(1.0)
            # OK 关闭对话框并触发宏 — 对话框不再可见即为成功
            if not _is_visible(macro_hwnd):
                logger.info("✅ 宏开始执行 (策略3: OK + Run on OK)")
                return True
            # 对话框仍在 → 尝试 WM_COMMAND 方式点击 OK
            logger.info("BM_CLICK OK 无效, 尝试 WM_COMMAND OK...")
            _user32.SendMessageW(macro_hwnd, WM_COMMAND,
                                 MACRO_OK_BTN_ID, ok_btn)
            time.sleep(1.0)
            if not _is_visible(macro_hwnd):
                logger.info("✅ 宏开始执行 (策略3b: WM_COMMAND OK)")
                return True
        
        logger.error("❌ 所有宏触发策略均失败")
        return False
    
    # ----------------------------------------------------------
    # Macro 对话框操作
    # ----------------------------------------------------------
    
    def _open_macro_dialog(self) -> Optional[int]:
        """打开 Macro Command 对话框
        
        Returns:
            对话框 HWND, 失败返回 None
        """
        # 先检查是否已经打开
        existing = self._find_window_by_title("Macro Command")
        if existing:
            _set_foreground(existing)
            return existing
        
        # 发送命令
        _post_command(self._main_hwnd, CMD_MACRO_COMMAND)
        
        # 等待对话框出现 (总超时 120 秒)
        start = time.time()
        timeout = 120.0
        connecting_seen = False
        connecting_dismiss_attempted = False
        
        while time.time() - start < timeout:
            time.sleep(0.5)
            elapsed = time.time() - start
            
            # ★★ 最高优先级: 检查 Macro Command 对话框 ★★
            # 即使 Connecting 对话框还在，Macro Command 可能已经打开了
            macro_hwnd = self._find_window_by_title("Macro Command")
            if macro_hwnd:
                logger.info(
                    f"Macro Command 对话框已打开 "
                    f"(hwnd=0x{macro_hwnd:08X}, 等待 {elapsed:.1f}s)")
                _set_foreground(macro_hwnd)
                return macro_hwnd
            
            # 处理 Connecting 对话框 (非阻塞方式)
            conn = self._find_window_by_title("Connecting")
            if conn:
                if not connecting_seen:
                    logger.info("出现 Connecting to instrument 对话框，等待连接...")
                    connecting_seen = True
                
                # 每 10 秒报告一次
                if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                    logger.info(f"Connecting 对话框仍在... ({elapsed:.0f}s)")
                
                # 超过 30 秒 → 尝试主动关闭 Connecting
                if elapsed > 30 and not connecting_dismiss_attempted:
                    connecting_dismiss_attempted = True
                    logger.warning("Connecting 超时 30s, 尝试主动关闭...")
                    self._handle_connecting_dialog(timeout=5.0)
                
                continue
            
            # 检查错误对话框 (如 Link failed)
            self._dismiss_error_dialogs()
        
        logger.error(f"Macro Command 对话框打开超时 ({timeout}s)")
        return None
    
    def _close_macro_dialog(self, hwnd: int):
        """关闭 Macro Command 对话框"""
        cancel_btn = _find_child_by_id(hwnd, MACRO_CANCEL_BTN_ID)
        if cancel_btn:
            _click_button(cancel_btn)
        else:
            _user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        time.sleep(0.5)
    
    # ----------------------------------------------------------
    # 等待实验完成
    # ----------------------------------------------------------
    
    def _wait_for_completion(self, expected_file: Optional[str],
                             macro_hwnd: Optional[int] = None) -> bool:
        """等待实验完成
        
        检测方式 (按优先级):
            1. 检查 Macro 对话框的 Run 按钮是否重新启用 (最可靠)
            2. 如果有预期输出文件，检测文件是否生成且大小稳定
            3. 检测主窗口标题 *变化* (与初始标题不同且包含 Data)
            4. 不使用总时长超时；没有明确完成/失败信号时持续等待
        """
        start = time.time()
        last_size = -1
        stable_count = 0
        run_btn_was_disabled = False  # 标记是否观测到 Run 按钮被禁用
        is_adt_batch = self._is_adt_batch_expected_file(expected_file)
        progress_snapshot = self._adt_progress_snapshot(expected_file) if is_adt_batch else None
        
        # 记录初始标题，用于检测 *变化* 而非静态匹配
        # 修复: 旧代码直接检查 'Data' in title，当 CHI660F 窗口保留了
        # 上一次实验数据的标题时会立即误判为完成
        initial_title = _get_window_text(self._main_hwnd) if self._main_hwnd else ""
        
        # 如果预期文件已存在 (上一次残留)，先删除以避免误判
        if expected_file and os.path.isfile(expected_file):
            try:
                os.remove(expected_file)
                logger.info(f"已删除旧的输出文件: {expected_file}")
            except OSError as e:
                logger.warning(f"删除旧输出文件失败: {e}")
        
        if is_adt_batch:
            logger.info(
                f"等待 ADT 批量实验完成 "
                f"(无总时长超时, 初始标题='{initial_title[:60]}')..."
            )
        else:
            logger.info(f"等待实验完成 (无总时长超时, 初始标题='{initial_title[:60]}')...")
        
        while True:
            time.sleep(1.0)
            elapsed = time.time() - start
            
            # 检查外部停止请求 (stop_experiment() 会设置 _is_running = False)
            if not self._is_running:
                logger.info(f"实验已被外部停止，退出等待 ({elapsed:.1f}s)")
                return False
            
            # 检查错误对话框 (包括 Link failed 检测)
            if self._dismiss_error_dialogs(capture_link_failed=True):
                logger.error("实验执行时检测到 Link failed - 仪器未连接")
                return False
            
            # 处理宏执行期间弹出的 Connecting 对话框 (非阻塞)
            # ★ 不再进入60秒子循环！仅记录日志，继续检查其他完成信号
            conn = self._find_window_by_title("Connecting")
            if conn:
                if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                    logger.info(f"宏执行期间 Connecting 对话框仍在... ({elapsed:.0f}s)")
                # 超过 30 秒尝试主动关闭
                if elapsed > 30:
                    self._handle_connecting_dialog(timeout=3.0)
            
            # 方式1: 检查 Macro 对话框 Run Macro 按钮是否重新启用
            # 宏运行期间 Run 按钮会被禁用；宏完成后按钮重新启用
            if macro_hwnd:
                run_btn = _find_child_by_id(macro_hwnd, MACRO_RUN_BTN_ID)
                if run_btn:
                    btn_enabled = bool(_user32.IsWindowEnabled(run_btn))
                    if not btn_enabled:
                        run_btn_was_disabled = True
                        logger.debug(f"Run 按钮已禁用 — 宏正在执行 ({elapsed:.0f}s)")
                    elif run_btn_was_disabled and btn_enabled:
                        # 按钮从禁用→启用 = 宏执行完毕
                        logger.info(f"Macro Run 按钮已重新启用 — 宏执行完成 ({elapsed:.1f}s)")
                        time.sleep(1.0)  # 额外等待文件写入完成
                        return True
            
            # 方式2: 检查输出文件
            if expected_file:
                if os.path.isfile(expected_file):
                    size = os.path.getsize(expected_file)
                    if size > 0:
                        if size == last_size:
                            stable_count += 1
                            if stable_count >= 3:
                                # 文件大小稳定3秒，表示写入完成
                                logger.info(f"输出文件已生成: {expected_file} ({size} bytes)")
                                return True
                        else:
                            stable_count = 0
                        last_size = size

            # ADT 批量宏会逐轮写出 child csv。只要文件还在新增或变大，
            # 就说明 CHI 仍在工作，不应因为固定总时长而误杀。
            if is_adt_batch:
                current_snapshot = self._adt_progress_snapshot(expected_file)
                if current_snapshot != progress_snapshot:
                    progress_snapshot = current_snapshot
                    count, total_size, last_cycle = current_snapshot
                    logger.info(
                        f"ADT raw 文件仍在更新: files={count}, "
                        f"bytes={total_size}, last_cycle={last_cycle}, elapsed={elapsed:.0f}s"
                    )
            
            # 方式3: 检查窗口标题 *变化*
            # 修复: 必须与初始标题不同才算完成，避免旧数据标题误判
            if self._main_hwnd:
                title = _get_window_text(self._main_hwnd)
                if title != initial_title and ('Data' in title or '.bin' in title):
                    logger.info(f"检测到标题变化: '{initial_title[:40]}' → '{title[:40]}'")
                    time.sleep(2)  # 额外等待数据写入
                    return True
            
            if int(elapsed) % 10 == 0 and elapsed > 0:
                logger.debug(f"实验进行中... ({int(elapsed)}s)")

    def _is_adt_batch_expected_file(self, expected_file: Optional[str]) -> bool:
        if not expected_file:
            return False
        name = os.path.basename(expected_file)
        return bool(re.search(r"_c\d+_(cathodic|anodic)\.(csv|txt)$", name, re.IGNORECASE))

    def _adt_progress_snapshot(self, expected_file: Optional[str]) -> Tuple[int, int, int]:
        """Return (matching_file_count, total_size, last_cycle) for ADT child files."""
        if not expected_file:
            return (0, 0, 0)
        directory = os.path.dirname(expected_file) or "."
        expected_name = os.path.basename(expected_file)
        match = re.match(r"(.+)_c\d+_(?:cathodic|anodic)\.(csv|txt)$", expected_name, re.IGNORECASE)
        if not match or not os.path.isdir(directory):
            return (0, 0, 0)
        prefix = match.group(1)
        pattern = re.compile(
            rf"^{re.escape(prefix)}_c(\d+)_(cathodic|anodic)\.(csv|txt)$",
            re.IGNORECASE,
        )
        count = 0
        total_size = 0
        last_cycle = 0
        try:
            for name in os.listdir(directory):
                child = pattern.match(name)
                if not child:
                    continue
                path = os.path.join(directory, name)
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                count += 1
                total_size += stat.st_size
                last_cycle = max(last_cycle, int(child.group(1)))
        except OSError:
            return (0, 0, 0)
        return (count, total_size, last_cycle)
    
    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------
    
    def _handle_connecting_dialog(self, timeout: float = 30.0) -> bool:
        """处理 "Connecting to instrument" 对话框
        
        CHI660F 在启动或执行宏命令时会弹出此对话框进行仪器通信。
        先等待自动关闭，超时后尝试主动关闭。
        
        Args:
            timeout: 等待自动关闭的最大时间 (秒)
            
        Returns:
            True = 对话框已关闭或不存在, False = 无法关闭
        """
        conn = self._find_window_by_title("Connecting")
        if not conn:
            return True
        
        logger.info(f"处理 Connecting 对话框 (超时={timeout:.0f}s)...")
        start = time.time()
        
        # 第一阶段: 等待自动关闭
        while time.time() - start < timeout:
            time.sleep(0.5)
            # 每次重新搜索,因为窗口可能被销毁后重建
            conn = self._find_window_by_title("Connecting")
            if not conn:
                logger.info(f"Connecting 对话框已自动关闭 ({time.time()-start:.1f}s)")
                return True
        
        # 第二阶段: 超时,尝试主动关闭
        conn = self._find_window_by_title("Connecting")
        if not conn:
            return True
        
        logger.warning(f"Connecting 对话框超时 ({timeout:.0f}s), 尝试主动关闭...")
        
        # 尝试1: Cancel 按钮 (id=2)
        cancel_btn = _find_child_by_id(conn, 2)
        if cancel_btn:
            _click_button(cancel_btn)
            time.sleep(1.0)
            if not self._find_window_by_title("Connecting"):
                logger.info("Connecting 已通过 Cancel 关闭")
                return True
        
        # 尝试2: WM_CLOSE
        _user32.PostMessageW(conn, WM_CLOSE, 0, 0)
        time.sleep(1.0)
        if not self._find_window_by_title("Connecting"):
            logger.info("Connecting 已通过 WM_CLOSE 关闭")
            return True
        
        # 尝试3: 查找对话框中所有按钮并逐个点击
        for child in _enum_children(conn):
            cls = _get_class_name(child)
            if cls.lower() == 'button':
                _click_button(child)
                time.sleep(0.5)
                if not self._find_window_by_title("Connecting"):
                    logger.info("Connecting 已通过子按钮关闭")
                    return True
        
        logger.error("无法关闭 Connecting 对话框")
        return False
    
    def _find_chi_window(self) -> Optional[int]:
        """查找 CHI660F 主窗口"""
        for hwnd in _enum_toplevel():
            title = _get_window_text(hwnd)
            if 'CHI660F' in title:
                return hwnd
        return None
    
    def _is_app_healthy(self) -> bool:
        """检查应用是否处于健康/干净状态
        
        如果有残留的 Customize、Run Status 等对话框，说明状态异常。
        """
        bad_dialogs = ['Customize', 'Run Status', 'Runtime Error']
        for hwnd in _enum_toplevel():
            title = _get_window_text(hwnd)
            cls = _get_class_name(hwnd)
            if cls == '#32770':
                for bad in bad_dialogs:
                    if bad in title:
                        logger.warning(f"检测到异常对话框: '{title}'")
                        return False
        return True
    
    def _kill_chi(self):
        """强制结束 chi660f.exe 进程"""
        # 先关闭所有对话框
        for _ in range(5):
            for hwnd in _enum_toplevel():
                cls = _get_class_name(hwnd)
                if cls == '#32770':
                    cancel = _find_child_by_id(hwnd, 2)
                    ok = _find_child_by_id(hwnd, 1)
                    if cancel:
                        _click_button(cancel)
                    elif ok:
                        _click_button(ok)
                    time.sleep(0.2)
        
        # 关闭主窗口
        main = self._find_chi_window()
        if main:
            _user32.PostMessageW(main, WM_CLOSE, 0, 0)
            time.sleep(2)
        
        # 强制结束
        if self._find_chi_window():
            subprocess.run(['taskkill', '/F', '/IM', 'chi660f.exe'],
                           capture_output=True, timeout=5)
            time.sleep(1)
        
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None
        
        self._main_hwnd = None
    
    def _find_window_by_title(self, title_substr: str) -> Optional[int]:
        """查找标题包含指定文字的可见窗口"""
        for hwnd in _enum_toplevel():
            title = _get_window_text(hwnd)
            if title_substr in title:
                return hwnd
        return None
    
    def _dismiss_error_dialogs(self, capture_link_failed: bool = False) -> bool:
        """关闭可能出现的错误对话框
        
        Args:
            capture_link_failed: 如果为 True，检测到 Link failed 时返回 True
            
        Returns:
            bool: 是否检测到 Link failed 错误
        """
        link_failed = False
        for hwnd in _enum_toplevel():
            title = _get_window_text(hwnd)
            cls = _get_class_name(hwnd)
            
            # CH Instruments 错误对话框 (如 CEcDoc::OnGraphicsTestvtk)
            if cls == '#32770' and 'CH Instruments' in title:
                # 读取对话框内的静态文本，检测 Link failed
                dialog_text = self._read_dialog_static_text(hwnd)
                if dialog_text:
                    self._last_dialog_error = f"{title}: {dialog_text[:500]}"
                    self._capture_failure_screenshot("dialog")
                if 'Link failed' in dialog_text or 'Link failed' in title:
                    logger.error(f"检测到 Link failed 错误: {dialog_text[:200]}")
                    link_failed = True
                else:
                    logger.debug(f"关闭错误对话框: {title}")
                
                ok_btn = _find_child_by_id(hwnd, 2)  # 确定按钮
                if ok_btn:
                    _click_button(ok_btn)
                    time.sleep(0.3)
            
            # Runtime Error 对话框
            if 'Runtime Error' in title or 'Microsoft Visual C++' in title:
                dialog_text = self._read_dialog_static_text(hwnd)
                self._last_dialog_error = f"{title}: {dialog_text[:500]}"
                self._capture_failure_screenshot("runtime")
                ok_btn = _find_child_by_id(hwnd, 1)
                if not ok_btn:
                    ok_btn = _find_child_by_id(hwnd, 2)
                if ok_btn:
                    logger.debug(f"关闭运行时错误: {title}")
                    _click_button(ok_btn)
                    time.sleep(0.3)
            
            # Warning 对话框 (如 "Amp booster is required for current greater than 0.25 A")
            # CHI660F 在设置大电流 CP 时弹出此警告，点击"确定"即可继续
            if title == 'Warning' and cls == '#32770':
                logger.info(f"检测到 Warning 对话框，自动确认")
                ok_btn = _find_child_by_id(hwnd, 1)  # 确定按钮
                if not ok_btn:
                    ok_btn = _find_child_by_id(hwnd, 2)
                if ok_btn:
                    _click_button(ok_btn)
                    time.sleep(0.3)
        
        return link_failed
    
    def _read_dialog_static_text(self, hwnd: int) -> str:
        """读取对话框中静态文本控件的内容"""
        texts = []
        for child in _enum_children(hwnd):
            cls = _get_class_name(child)
            if cls in ('Static', 'STATIC', '#32770'):
                text = _get_window_text(child)
                if text and len(text) > 1:
                    texts.append(text)
        return ' '.join(texts)

    def _collect_chi_gui_diagnostics(self) -> str:
        """Collect visible CHI GUI state for failure logs."""
        parts = []
        if self._main_hwnd:
            title = _get_window_text(self._main_hwnd)
            if title:
                parts.append(f"CHI main title='{title[:160]}'")
        if self._last_dialog_error:
            parts.append(f"last_dialog='{self._last_dialog_error[:240]}'")

        dialogs = []
        for hwnd in _enum_toplevel():
            title = _get_window_text(hwnd)
            cls = _get_class_name(hwnd)
            if cls == '#32770' or 'CHI' in title or 'Connecting' in title:
                text = self._read_dialog_static_text(hwnd)
                item = title
                if text:
                    item = f"{title}: {text}"
                if item:
                    dialogs.append(item[:240])
        if dialogs:
            parts.append("visible_dialogs=[" + " | ".join(dialogs[:5]) + "]")
        screenshot = self._capture_failure_screenshot("failure")
        if screenshot:
            parts.append(f"failure_screenshot='{screenshot}'")
        return "; ".join(parts)

    def _capture_failure_screenshot(self, reason: str = "failure") -> str:
        """Save a best-effort screenshot when CHI fails without a dialog."""
        try:
            from PIL import ImageGrab

            output_dir = Path(self._config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_reason = "".join(ch for ch in reason if ch.isalnum() or ch in ("-", "_"))
            path = output_dir / f"chi_failure_{safe_reason}_{ts}.png"
            img = ImageGrab.grab()
            img.save(path)
            logger.info(f"CHI failure screenshot saved: {path}")
            return str(path)
        except Exception as exc:
            logger.warning(f"CHI failure screenshot failed: {exc}")
            return ""
    
    def _extract_output_file(self, macro_text: str) -> Optional[str]:
        """从宏命令文本中提取预期输出文件路径
        
        对于批量宏 (多个 csvsave/tsave)，返回 **最后一个** 保存文件路径，
        因为只有最后一个文件写入完成才表示整个宏执行结束。
        """
        import re
        
        last_file = None
        for line in macro_text.split('\n'):
            line = line.strip()
            m = re.match(r'csvsave:\s*(.+)', line, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                if not name.endswith('.csv'):
                    name += '.csv'
                last_file = os.path.join(self._config.output_dir, name)
                continue
            
            m = re.match(r'tsave:\s*(.+)', line, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                if not name.endswith('.txt'):
                    name += '.txt'
                last_file = os.path.join(self._config.output_dir, name)
        
        return last_file
    
    def _parse_csv(self, filepath: str) -> Tuple[List[str], List[List[float]]]:
        """解析 CHI 660F CSV 输出文件
        
        CHI CSV 格式:
            1. 头信息 (日期、技术名、参数等)
            2. 空行
            3. 列名行 (如 "Potential/V, Current/A")
            4. 空行 (可能有)
            5. 数据行 (数值, 数值, ...)
        """
        headers = []
        data = []
        metadata = {}
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                in_data = False
                prev_line = ""
                
                for line in f:
                    line = line.strip()
                    
                    if not in_data:
                        # 检测列名行 (包含 "/" 和 ","，如 "Potential/V, Current/A")
                        if '/' in line and ',' in line:
                            parts = [h.strip() for h in line.split(',')]
                            if any('/' in p for p in parts):
                                headers = parts
                                in_data = True
                                continue
                        
                        # 提取元数据
                        if '=' in line:
                            k, _, v = line.partition('=')
                            metadata[k.strip()] = v.strip()
                        continue
                    
                    if not line:
                        continue
                    
                    # 解析数据行
                    parts = line.split(',')
                    try:
                        row = [float(x.strip()) for x in parts if x.strip()]
                        if row:
                            data.append(row)
                    except ValueError:
                        # 可能遇到 Segment 分隔行等
                        continue
        
        except Exception as e:
            logger.error(f"CSV 解析失败: {e}")
        
        logger.info(f"CSV 解析完成: {len(data)} 数据点, 列={headers}, "
                     f"元数据={len(metadata)}项")
        return headers, data
    
    # ----------------------------------------------------------
    # 额外工具方法
    # ----------------------------------------------------------
    
    def get_window_title(self) -> str:
        """获取当前主窗口标题"""
        if self._main_hwnd:
            return _get_window_text(self._main_hwnd)
        return ""
    
    def send_command(self, cmd_id: int):
        """发送任意 WM_COMMAND 到主窗口
        
        Args:
            cmd_id: WM_COMMAND ID (参见文件顶部常量定义)
        """
        if self._main_hwnd:
            _post_command(self._main_hwnd, cmd_id)
    
    def stop_experiment(self):
        """停止正在进行的实验"""
        if self._main_hwnd:
            _post_command(self._main_hwnd, CMD_STOP_RUN)
            self._is_running = False
            logger.info("已发送停止命令")
    
    def get_open_circuit_potential(self):
        """获取开路电位"""
        if self._main_hwnd:
            _post_command(self._main_hwnd, CMD_OPEN_CIRCUIT)


# ============================================================
# 便捷函数
# ============================================================

def quick_cv(e_init=0, e_high=0.5, e_low=-0.5, scan_rate=0.1,
             segments=2, dummy=True, output_dir="", **kwargs) -> ExperimentResult:
    """快速运行 CV 实验
    
    Args:
        e_init: 初始电位 (V)
        e_high: 高电位 (V)
        e_low: 低电位 (V)
        scan_rate: 扫描速率 (V/s)
        segments: 扫描段数
        dummy: 是否使用 dummy cell
        output_dir: 输出目录
        
    Returns:
        ExperimentResult
    """
    config = ExperimentConfig(use_dummy_cell=dummy)
    if output_dir:
        config.output_dir = output_dir
    
    ctrl = CHI660FController(config)
    if not ctrl.launch():
        return ExperimentResult(success=False, error_message="启动失败")
    
    params = CVParams(
        e_init=e_init, e_high=e_high, e_low=e_low,
        scan_rate=scan_rate, segments=segments, **kwargs
    )
    return ctrl.run_cv(params)


def quick_it(e_init=0, run_time=10, sample_interval=0.1,
             dummy=True, output_dir="", **kwargs) -> ExperimentResult:
    """快速运行 i-t 实验"""
    config = ExperimentConfig(use_dummy_cell=dummy)
    if output_dir:
        config.output_dir = output_dir
    
    ctrl = CHI660FController(config)
    if not ctrl.launch():
        return ExperimentResult(success=False, error_message="启动失败")
    
    params = ITParams(
        e_init=e_init, run_time=run_time,
        sample_interval=sample_interval, **kwargs
    )
    return ctrl.run_it(params)


def quick_imp(e_init=0, freq_low=1, freq_high=100000, amplitude=0.005,
              dummy=True, output_dir="", **kwargs) -> ExperimentResult:
    """快速运行 EIS/IMP 实验"""
    config = ExperimentConfig(use_dummy_cell=dummy)
    if output_dir:
        config.output_dir = output_dir
    
    ctrl = CHI660FController(config)
    if not ctrl.launch():
        return ExperimentResult(success=False, error_message="启动失败")
    
    params = IMPParams(
        e_init=e_init, freq_low=freq_low,
        freq_high=freq_high, amplitude=amplitude, **kwargs
    )
    return ctrl.run_imp(params)


# ============================================================
# 入口 (测试)
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    print("=" * 60)
    print("CHI 660F GUI 控制器 - 完整测试 (Dummy Cell CV)")
    print("=" * 60)
    
    config = ExperimentConfig(
        use_dummy_cell=True,
        output_dir=r"D:\CHI660F\data",
        timeout=120,
    )
    
    ctrl = CHI660FController(config)
    
    if ctrl.launch(force_restart=True):
        print(f"已连接: {ctrl.get_window_title()}")
        
        params = CVParams(
            e_init=0.0, e_high=0.5, e_low=-0.5,
            scan_rate=0.1, segments=2,
        )
        
        print("\n运行 Dummy Cell CV...")
        result = ctrl.run_cv(params)
        
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
    else:
        print("启动失败!")
    
    print("\n完成")
