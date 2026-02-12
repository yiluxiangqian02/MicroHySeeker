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
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import IntEnum

logger = logging.getLogger(__name__)


# ============================================================
# 常量
# ============================================================

# CHI 660F 默认安装路径
DEFAULT_CHI_EXE = r"D:\CHI660F\chi660f.exe"

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


# 技术 → 宏命令 tech 字符串
TECHNIQUE_NAMES: Dict[Technique, str] = {
    Technique.CV:   "cv",
    Technique.LSV:  "lsv",
    Technique.IT:   "i-t",
    Technique.IMP:  "imp",
    Technique.OCPT: "ocpt",
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
    
    def run_custom_macro(self, macro_text: str) -> ExperimentResult:
        """执行自定义宏命令
        
        Args:
            macro_text: 宏命令文本 (每行一条命令)
            
        Returns:
            ExperimentResult
        """
        return self._execute_macro_text(macro_text)
    
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
            3. 点击 Run Macro(312)
            4. 监测完成
            5. 关闭对话框
        """
        result = ExperimentResult()
        start_time = time.time()
        
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
            
            # 4. 点击 Run Macro
            run_btn = _find_child_by_id(macro_hwnd, MACRO_RUN_BTN_ID)
            if not run_btn:
                result.error_message = "未找到 Run Macro 按钮"
                self._close_macro_dialog(macro_hwnd)
                return result
            
            logger.info("点击 Run Macro...")
            _click_button(run_btn)
            
            # 5. 等待实验完成
            self._is_running = True
            success = self._wait_for_completion(expected_file)
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
                result.error_message = "实验执行超时或失败"
            
            # 7. 关闭 Macro 对话框
            if self._config.auto_close_macro:
                self._close_macro_dialog(macro_hwnd)
        
        except Exception as e:
            result.error_message = f"执行异常: {e}"
            logger.exception("宏执行异常")
        
        result.elapsed_time = time.time() - start_time
        return result
    
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
        
        # 等待对话框出现
        for _ in range(30):  # 最多等15秒
            time.sleep(0.5)
            
            # 检查是否出现了 Connecting 对话框
            conn = self._find_window_by_title("Connecting")
            if conn:
                logger.warning("出现 Connecting to instrument 对话框")
                # 等它自动关或超时
                for _ in range(20):
                    time.sleep(1)
                    if not _is_visible(conn):
                        break
                    # 检查是否有取消按钮
                    cancel = _find_child_by_id(conn, 2)
                    if cancel:
                        logger.info("点击 Cancel 关闭 Connecting 对话框")
                        _click_button(cancel)
                        time.sleep(1)
                        break
            
            # 检查 Macro Command 对话框
            macro_hwnd = self._find_window_by_title("Macro Command")
            if macro_hwnd:
                logger.info(f"Macro Command 对话框已打开 (hwnd=0x{macro_hwnd:08X})")
                _set_foreground(macro_hwnd)
                return macro_hwnd
            
            # 检查错误对话框
            self._dismiss_error_dialogs()
        
        logger.error("Macro Command 对话框打开超时")
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
    
    def _wait_for_completion(self, expected_file: Optional[str]) -> bool:
        """等待实验完成
        
        检测方式:
            1. 如果有预期输出文件，检测文件是否生成
            2. 检测主窗口标题变化 (Data 出现)
            3. 超时退出
        """
        timeout = self._config.timeout
        start = time.time()
        last_size = -1
        stable_count = 0
        
        logger.info(f"等待实验完成 (超时={timeout}s)...")
        
        while time.time() - start < timeout:
            time.sleep(1.0)
            
            # 检查错误对话框
            self._dismiss_error_dialogs()
            
            # 方式1: 检查输出文件
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
            
            # 方式2: 检查窗口标题 (实验完成后标题可能变化)
            if self._main_hwnd:
                title = _get_window_text(self._main_hwnd)
                # 有些技术完成后标题会包含数据文件信息
                if 'Data' in title or '.bin' in title:
                    logger.info(f"检测到标题变化: {title}")
                    time.sleep(2)  # 额外等待数据写入
                    return True
            
            elapsed = time.time() - start
            if int(elapsed) % 10 == 0:
                logger.debug(f"实验进行中... ({int(elapsed)}s)")
        
        logger.warning(f"实验等待超时 ({timeout}s)")
        return False
    
    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------
    
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
    
    def _dismiss_error_dialogs(self):
        """关闭可能出现的错误对话框"""
        for hwnd in _enum_toplevel():
            title = _get_window_text(hwnd)
            cls = _get_class_name(hwnd)
            
            # CH Instruments 错误对话框 (如 CEcDoc::OnGraphicsTestvtk)
            if cls == '#32770' and 'CH Instruments' in title:
                ok_btn = _find_child_by_id(hwnd, 2)  # 确定按钮
                if ok_btn:
                    logger.debug(f"关闭错误对话框: {title}")
                    _click_button(ok_btn)
                    time.sleep(0.3)
            
            # Runtime Error 对话框
            if 'Runtime Error' in title or 'Microsoft Visual C++' in title:
                ok_btn = _find_child_by_id(hwnd, 1)
                if not ok_btn:
                    ok_btn = _find_child_by_id(hwnd, 2)
                if ok_btn:
                    logger.debug(f"关闭运行时错误: {title}")
                    _click_button(ok_btn)
                    time.sleep(0.3)
    
    def _extract_output_file(self, macro_text: str) -> Optional[str]:
        """从宏命令文本中提取预期输出文件路径"""
        import re
        
        # 查找 csvsave: 或 tsave: 命令
        for line in macro_text.split('\n'):
            line = line.strip()
            m = re.match(r'csvsave:\s*(.+)', line, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                if not name.endswith('.csv'):
                    name += '.csv'
                return os.path.join(self._config.output_dir, name)
            
            m = re.match(r'tsave:\s*(.+)', line, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                if not name.endswith('.txt'):
                    name += '.txt'
                return os.path.join(self._config.output_dir, name)
        
        return None
    
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
