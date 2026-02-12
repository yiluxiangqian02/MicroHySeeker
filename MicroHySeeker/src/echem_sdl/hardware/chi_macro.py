"""
CHI 660F 宏命令驱动模块

通过 chi660f.exe 的 /runmacro 命令行接口控制 CHI 660F 电化学工作站。
libec.dll 不支持 660F 系列，因此使用 .mcr 宏文件 + 进程自动化方案。

工作流程:
  1. 根据 ECParameters 动态生成 .mcr 宏文件
  2. 启动 chi660f.exe /runmacro:"<path>.mcr"
  3. 监控 chi660f.exe 进程完成
  4. 解析输出的 CSV 数据文件
  5. 返回 ECDataPoint 列表

参考文档: chi660f.chm -> hid_control_macro.htm (完整宏命令参考)
"""

import os
import re
import csv
import time
import signal
import shutil
import logging
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================
# ECTechnique -> 宏 tech: 字符串映射
# ============================================================

# 正向映射: ECTechnique int value -> macro tech string
TECHNIQUE_MACRO_MAP: Dict[int, str] = {
    0:  "cv",       # 循环伏安法
    1:  "lsv",      # 线性扫描伏安法
    2:  "ca",       # 计时电流法
    3:  "cc",       # 计时库仑法
    4:  "cp",       # 计时电位法
    5:  "dpv",      # 差分脉冲伏安法
    6:  "npv",      # 正常脉冲伏安法
    7:  "swv",      # 方波伏安法
    8:  "shacv",    # 二次谐波交流伏安法
    9:  "imp",      # 交流阻抗
    10: "impe",     # 阻抗-电位
    11: "i-t",      # 安培-时间曲线
    12: "ocpt",     # 开路电位-时间
}

# 660F 额外支持的技术 (以字符串名为键)
EXTRA_TECHNIQUES: Dict[str, str] = {
    "TAFEL":  "tafel",
    "SCV":    "scv",
    "DNPV":   "dnpv",
    "ACV":    "acv",
    "BE":     "be",
    "HMV":    "hmv",
    "SSF":    "ssf",
    "STEP":   "step",
    "IMPT":   "impt",
    "CPCR":   "cpcr",
    "ISTEP":  "istep",
    "PSA":    "psa",
    "ECN":    "ecn",
    "PSC":    "psc",
    "PAC":    "pac",
    "SECM":   "secm",
    "SISECM": "sisecm",
}


@dataclass
class MacroConfig:
    """宏执行配置"""
    chi_exe_path: str = ""          # chi660f.exe 完整路径
    work_dir: str = ""              # 工作目录 (存放 .mcr 和输出)
    output_format: str = "csv"      # 输出格式: "csv" | "text" | "bin"
    timeout: float = 600.0          # 最大等待时间 (秒)
    auto_close: bool = True         # 实验完成后是否自动关闭 chi660f.exe
    file_override: bool = True      # 覆盖已有文件不弹提示
    dummy_cell: bool = False        # 使用 dummy cell (测试用)


class CHI660FMacroDriver:
    """CHI 660F 宏命令驱动
    
    通过生成 .mcr 宏文件并调用 chi660f.exe /runmacro 来控制工作站。
    
    Usage:
        driver = CHI660FMacroDriver(config)
        driver.connect()  # 验证 exe 存在
        
        params = ECParameters(technique=ECTechnique.CV, e_init=0, e_high=0.5, ...)
        driver.set_parameters(params)
        
        success = driver.run_experiment()  # 阻塞等待完成
        data = driver.get_data()           # 获取数据
        
        driver.disconnect()
    """
    
    def __init__(self, config: Optional[MacroConfig] = None, log_service=None):
        self._config = config or MacroConfig()
        self._log_service = log_service
        
        # 状态
        self._connected = False
        self._running = False
        self._process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        
        # 参数
        self._params = None  # ECParameters
        self._technique_str: str = "cv"
        
        # 输出
        self._output_dir: str = ""
        self._output_file: str = ""
        self._data_points: list = []  # List[ECDataPoint]
        
        # 回调
        self._complete_callback: Optional[Callable] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        
        # 确保工作目录存在
        if not self._config.work_dir:
            self._config.work_dir = os.path.join(
                tempfile.gettempdir(), "chi660f_macro"
            )
        os.makedirs(self._config.work_dir, exist_ok=True)
        
        self._log(f"CHI660FMacroDriver 初始化, work_dir={self._config.work_dir}")
    
    # ----------------------------------------------------------
    # 公共接口
    # ----------------------------------------------------------
    
    def connect(self) -> bool:
        """验证 chi660f.exe 是否存在且可访问
        
        不同于 libec.dll 方式，宏模式不需要维持串口连接。
        chi660f.exe 启动时会自动连接工作站。
        """
        exe_path = self._resolve_exe_path()
        if not exe_path:
            self._log("chi660f.exe 未找到", level="error")
            return False
        
        self._config.chi_exe_path = exe_path
        self._connected = True
        self._log(f"已定位 chi660f.exe: {exe_path}")
        return True
    
    def disconnect(self) -> None:
        """清理资源"""
        if self._running:
            self.stop_experiment()
        self._connected = False
        self._log("CHI660F 宏驱动已断开")
    
    def set_parameters(self, params) -> bool:
        """设置实验参数
        
        Args:
            params: ECParameters 实例
            
        Returns:
            是否设置成功
        """
        self._params = params
        
        # 将 ECTechnique 映射到宏命令字符串
        tech_id = int(params.technique)
        self._technique_str = TECHNIQUE_MACRO_MAP.get(tech_id, "cv")
        
        self._log(f"参数已设置: tech={self._technique_str}, "
                   f"Ei={params.e_init}V, Eh={params.e_high}V, "
                   f"El={params.e_low}V, v={params.scan_rate}V/s")
        return True
    
    def run_experiment(self, blocking: bool = True) -> bool:
        """执行实验
        
        Args:
            blocking: 是否阻塞等待完成 (True=同步, False=异步)
            
        Returns:
            是否成功启动
        """
        if not self._connected:
            self._log("未连接，无法执行实验", level="error")
            return False
        
        if self._running:
            self._log("已有实验在运行中", level="warning")
            return False
        
        if not self._params:
            self._log("未设置实验参数", level="error")
            return False
        
        # 1. 生成宏文件
        mcr_path = self._generate_macro_file()
        if not mcr_path:
            return False
        
        self._log(f"宏文件已生成: {mcr_path}")
        
        # 2. 启动 chi660f.exe
        self._running = True
        self._stop_event.clear()
        self._data_points.clear()
        
        if blocking:
            return self._run_blocking(mcr_path)
        else:
            thread = threading.Thread(
                target=self._run_blocking,
                args=(mcr_path,),
                daemon=True
            )
            thread.start()
            return True
    
    def stop_experiment(self) -> bool:
        """停止正在进行的实验"""
        self._stop_event.set()
        
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._log("chi660f.exe 进程已终止")
        
        self._running = False
        return True
    
    def get_data(self) -> list:
        """获取实验数据
        
        Returns:
            ECDataPoint 列表
        """
        if not self._data_points and self._output_file:
            self._parse_output_file()
        return self._data_points.copy()
    
    def get_raw_data_path(self) -> str:
        """获取原始数据文件路径"""
        return self._output_file
    
    @property 
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def on_complete(self, callback: Callable):
        """注册完成回调"""
        self._complete_callback = callback
    
    def on_error(self, callback: Callable[[Exception], None]):
        """注册错误回调"""
        self._error_callback = callback
    
    # ----------------------------------------------------------
    # 宏文件生成
    # ----------------------------------------------------------
    
    def _generate_macro_file(self) -> Optional[str]:
        """根据当前参数生成 .mcr 宏文件
        
        Returns:
            宏文件路径，失败返回 None
        """
        if not self._params:
            return None
        
        params = self._params
        lines: List[str] = []
        
        # 文件头注释
        lines.append("; ====================================")
        lines.append("; CHI 660F Auto-Generated Macro")
        lines.append(f"; Technique: {self._technique_str}")
        lines.append(f"; Generated by MicroHySeeker")
        lines.append("; ====================================")
        lines.append("")
        
        # 输出目录设置
        self._output_dir = os.path.join(self._config.work_dir, "data")
        os.makedirs(self._output_dir, exist_ok=True)
        
        lines.append(f"folder: {self._output_dir}")
        
        if self._config.file_override:
            lines.append("fileoverride")
        
        # Dummy cell (测试用)
        if self._config.dummy_cell:
            lines.append("dummyon")
        
        # 选择技术
        lines.append(f"tech: {self._technique_str}")
        lines.append("")
        
        # 根据技术类型生成参数命令
        tech = self._technique_str
        
        if tech == "cv":
            lines.extend(self._gen_cv_params(params))
        elif tech in ("lsv", "lssv"):
            lines.extend(self._gen_lsv_params(params))
        elif tech == "ca":
            lines.extend(self._gen_ca_params(params))
        elif tech == "cc":
            lines.extend(self._gen_cc_params(params))
        elif tech == "i-t":
            lines.extend(self._gen_it_params(params))
        elif tech in ("dpv", "dpp", "dpsv"):
            lines.extend(self._gen_dpv_params(params))
        elif tech in ("npv", "npp", "npsv"):
            lines.extend(self._gen_npv_params(params))
        elif tech in ("swv", "swsv"):
            lines.extend(self._gen_swv_params(params))
        elif tech in ("acv", "acp", "acsv"):
            lines.extend(self._gen_acv_params(params))
        elif tech in ("shacv", "shacp", "shacsv"):
            lines.extend(self._gen_shacv_params(params))
        elif tech == "imp":
            lines.extend(self._gen_imp_params(params))
        elif tech == "impe":
            lines.extend(self._gen_impe_params(params))
        elif tech == "impt":
            lines.extend(self._gen_impt_params(params))
        elif tech == "ocpt":
            lines.extend(self._gen_ocpt_params(params))
        elif tech == "cp":
            lines.extend(self._gen_cp_params(params))
        elif tech == "tafel":
            lines.extend(self._gen_tafel_params(params))
        else:
            # 通用参数 fallback
            lines.extend(self._gen_generic_params(params))
        
        lines.append("")
        
        # 执行实验
        lines.append("; --- 执行实验 ---")
        lines.append("run")
        lines.append("")
        
        # 保存数据
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_name = f"{tech}_{timestamp}"
        
        if self._config.output_format == "csv":
            lines.append(f"csvsave: {output_name}")
            self._output_file = os.path.join(
                self._output_dir, f"{output_name}.csv"
            )
        elif self._config.output_format == "text":
            lines.append(f"tsave: {output_name}")
            self._output_file = os.path.join(
                self._output_dir, f"{output_name}.txt"
            )
        else:
            lines.append(f"save: {output_name}")
            self._output_file = os.path.join(
                self._output_dir, f"{output_name}.bin"
            )
        
        # Dummy cell 关闭
        if self._config.dummy_cell:
            lines.append("dummyoff")
        
        # 自动关闭程序
        if self._config.auto_close:
            lines.append("")
            lines.append("forcequit:yesiamsure")
        
        lines.append("")
        lines.append("end")
        
        # 写入文件
        mcr_path = os.path.join(
            self._config.work_dir,
            f"auto_{tech}_{timestamp}.mcr"
        )
        
        try:
            with open(mcr_path, 'w', encoding='ascii', errors='replace') as f:
                f.write('\n'.join(lines))
            return mcr_path
        except Exception as e:
            self._log(f"写入宏文件失败: {e}", level="error")
            return None
    
    # ----------------------------------------------------------
    # 各技术参数生成器
    # ----------------------------------------------------------
    
    def _gen_cv_params(self, p) -> List[str]:
        """循环伏安法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
            f"ef = {p.e_final}",
            f"v = {p.scan_rate}",
            f"cl = {p.segments}",
            f"si = {p.sample_interval}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_lsv_params(self, p) -> List[str]:
        """线性扫描伏安法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"v = {p.scan_rate}",
            f"si = {p.sample_interval}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_ca_params(self, p) -> List[str]:
        """计时电流法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
            f"pn = p",
            f"cl = {p.segments}",
            f"pw = {getattr(p, 'pulse_width', 0.1)}",
            f"si = {p.sample_interval}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_cc_params(self, p) -> List[str]:
        """计时库仑法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"cl = {p.segments}",
            f"pw = {getattr(p, 'pulse_width', 0.1)}",
            f"si = {p.sample_interval}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_it_params(self, p) -> List[str]:
        """安培-时间曲线参数"""
        lines = [
            f"ei = {p.e_init}",
            f"si = {p.sample_interval}",
            f"st = {p.run_time}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_dpv_params(self, p) -> List[str]:
        """差分脉冲伏安法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"incre = {getattr(p, 'increment_e', 0.004)}",
            f"amp = {getattr(p, 'amplitude', 0.05)}",
            f"pw = {getattr(p, 'pulse_width', 0.05)}",
            f"sw = {p.sample_interval}",
            f"prod = {getattr(p, 'pulse_period', 0.5)}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_npv_params(self, p) -> List[str]:
        """正常脉冲伏安法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"incre = {getattr(p, 'increment_e', 0.004)}",
            f"pw = {getattr(p, 'pulse_width', 0.05)}",
            f"sw = {p.sample_interval}",
            f"prod = {getattr(p, 'pulse_period', 0.5)}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_swv_params(self, p) -> List[str]:
        """方波伏安法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"incre = {getattr(p, 'increment_e', 0.004)}",
            f"amp = {getattr(p, 'amplitude', 0.025)}",
            f"freq = {getattr(p, 'frequency', 15)}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_acv_params(self, p) -> List[str]:
        """交流伏安法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"incre = {getattr(p, 'increment_e', 0.004)}",
            f"amp = {getattr(p, 'amplitude', 0.025)}",
            f"freq = {getattr(p, 'frequency', 10)}",
            f"prod = {getattr(p, 'sample_period', 1)}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_shacv_params(self, p) -> List[str]:
        """二次谐波交流伏安法参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"incre = {getattr(p, 'increment_e', 0.004)}",
            f"amp = {getattr(p, 'amplitude', 0.025)}",
            f"freq = {getattr(p, 'frequency', 10)}",
            f"prod = {getattr(p, 'sample_period', 1)}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_imp_params(self, p) -> List[str]:
        """交流阻抗参数"""
        lines = [
            f"ei = {p.e_init}",
            f"fl = {getattr(p, 'freq_low', 1)}",
            f"fh = {getattr(p, 'freq_high', 100000)}",
            f"amp = {getattr(p, 'amplitude', 0.005)}",
            f"qt = {p.quiet_time}",
            "impautosens",
        ]
        return lines
    
    def _gen_impe_params(self, p) -> List[str]:
        """阻抗-电位参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"incre = {getattr(p, 'increment_e', 0.01)}",
            f"amp = {getattr(p, 'amplitude', 0.005)}",
            f"freq = {getattr(p, 'frequency', 1000)}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_impt_params(self, p) -> List[str]:
        """阻抗-时间参数"""
        lines = [
            f"ei = {p.e_init}",
            f"amp = {getattr(p, 'amplitude', 0.005)}",
            f"freq = {getattr(p, 'frequency', 1000)}",
            f"si = {p.sample_interval}",
            f"st = {p.run_time}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_ocpt_params(self, p) -> List[str]:
        """开路电位-时间参数"""
        lines = [
            f"si = {p.sample_interval}",
            f"st = {p.run_time}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
        ]
        return lines
    
    def _gen_cp_params(self, p) -> List[str]:
        """计时电位法参数"""
        lines = [
            f"ic = {getattr(p, 'cathodic_current', 0.001)}",
            f"ia = {getattr(p, 'anodic_current', 0.001)}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
            f"tc = {getattr(p, 'cathodic_time', 10)}",
            f"ta = {getattr(p, 'anodic_time', 10)}",
            f"pn = p",
            f"si = {p.sample_interval}",
            f"cl = {p.segments}",
        ]
        return lines
    
    def _gen_tafel_params(self, p) -> List[str]:
        """Tafel图参数"""
        lines = [
            f"ei = {p.e_init}",
            f"ef = {p.e_final}",
            f"v = {p.scan_rate}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_generic_params(self, p) -> List[str]:
        """通用参数 (fallback)"""
        lines = [
            f"ei = {p.e_init}",
            f"eh = {p.e_high}",
            f"el = {p.e_low}",
            f"ef = {p.e_final}",
            f"v = {p.scan_rate}",
            f"qt = {p.quiet_time}",
        ]
        lines.extend(self._gen_sensitivity(p))
        return lines
    
    def _gen_sensitivity(self, p) -> List[str]:
        """生成灵敏度命令"""
        if hasattr(p, 'sensitivity') and p.sensitivity > 0:
            return [f"sens = {p.sensitivity}"]
        else:
            return ["autosens"]
    
    # ----------------------------------------------------------
    # 进程管理
    # ----------------------------------------------------------
    
    def _run_blocking(self, mcr_path: str) -> bool:
        """阻塞式执行宏并等待完成
        
        Args:
            mcr_path: .mcr 宏文件路径
            
        Returns:
            是否成功完成
        """
        exe_path = self._config.chi_exe_path
        cmd = f'"{exe_path}" /runmacro:"{mcr_path}"'
        
        self._log(f"启动 chi660f.exe: {cmd}")
        
        try:
            # 使用 CREATE_NO_WINDOW 标志在 Windows 上隐藏窗口
            # 注意: chi660f.exe 是 GUI 程序，不会有 stdout 输出
            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                # 不隐藏窗口，因为 chi660f.exe 需要 GUI 来运行
                # 用户可以看到进度
                creationflags = 0
            
            self._process = subprocess.Popen(
                cmd,
                shell=True,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            
            self._log(f"chi660f.exe PID={self._process.pid}, 等待完成...")
            
            # 等待进程完成或超时
            start_time = time.time()
            while not self._stop_event.is_set():
                retcode = self._process.poll()
                if retcode is not None:
                    self._log(f"chi660f.exe 已退出, code={retcode}")
                    break
                
                elapsed = time.time() - start_time
                if elapsed > self._config.timeout:
                    self._log(f"实验超时 ({self._config.timeout}s), 终止进程",
                              level="warning")
                    self._process.terminate()
                    self._running = False
                    return False
                
                time.sleep(0.5)
            
            self._running = False
            
            # 检查输出文件是否生成
            if self._output_file and os.path.exists(self._output_file):
                self._log(f"数据文件已生成: {self._output_file}")
                self._parse_output_file()
                
                if self._complete_callback:
                    try:
                        self._complete_callback()
                    except Exception as e:
                        self._log(f"完成回调异常: {e}", level="error")
                
                return True
            else:
                # 检查可能的文件名变体
                found = self._find_output_file()
                if found:
                    self._output_file = found
                    self._log(f"找到数据文件: {found}")
                    self._parse_output_file()
                    
                    if self._complete_callback:
                        try:
                            self._complete_callback()
                        except Exception:
                            pass
                    return True
                
                self._log("未找到输出数据文件", level="warning")
                return False
                
        except FileNotFoundError:
            self._log(f"chi660f.exe 未找到: {exe_path}", level="error")
            self._running = False
            return False
        except Exception as e:
            self._log(f"执行宏失败: {e}", level="error")
            self._running = False
            if self._error_callback:
                self._error_callback(e)
            return False
    
    def _find_output_file(self) -> Optional[str]:
        """搜索输出目录中最新的数据文件"""
        if not self._output_dir or not os.path.isdir(self._output_dir):
            return None
        
        # 查找 csv/txt 文件
        exts = {'.csv', '.txt', '.bin'}
        candidates = []
        for f in os.listdir(self._output_dir):
            _, ext = os.path.splitext(f)
            if ext.lower() in exts:
                fp = os.path.join(self._output_dir, f)
                candidates.append((os.path.getmtime(fp), fp))
        
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return None
    
    # ----------------------------------------------------------
    # 数据解析
    # ----------------------------------------------------------
    
    def _parse_output_file(self) -> bool:
        """解析输出文件到 ECDataPoint 列表
        
        CHI 660F CSV/Text 格式:
        - 文件头包含实验参数信息 (以文本行开头)
        - 数据区域: 逗号分隔的数值列
        - CV/LSV: Potential/V, Current/A
        - i-t: Time/s, Current/A  
        - OCPT: Time/s, Potential/V
        - IMP: Freq/Hz, Zre/ohm, Zim/ohm
        """
        if not self._output_file or not os.path.exists(self._output_file):
            return False
        
        self._data_points.clear()
        
        ext = os.path.splitext(self._output_file)[1].lower()
        
        try:
            if ext == '.csv':
                return self._parse_csv_file(self._output_file)
            elif ext == '.txt':
                return self._parse_text_file(self._output_file)
            else:
                self._log(f"不支持的文件格式: {ext}", level="warning")
                return False
        except Exception as e:
            self._log(f"解析数据文件失败: {e}", level="error")
            return False
    
    def _parse_csv_file(self, filepath: str) -> bool:
        """解析 CHI CSV 数据文件
        
        CHI CSV 文件格式:
        - 前若干行为文本头 (技术名、参数等)
        - 数据行: 逗号分隔的浮点数
        - 可能有多段数据 (CV segments)
        """
        from . import chi  # 延迟导入避免循环
        
        data_started = False
        col_headers = []
        row_index = 0
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # 尝试检测数据行 (全部是数字和逗号)
                parts = line.split(',')
                
                if not data_started:
                    # 检查是否是列标题行或数据行
                    try:
                        vals = [float(x.strip()) for x in parts if x.strip()]
                        if len(vals) >= 2:
                            data_started = True
                            # 处理这一行数据
                            self._add_data_point(vals, row_index)
                            row_index += 1
                    except ValueError:
                        # 可能是标题行
                        if any(kw in line.lower() for kw in 
                               ['potential', 'current', 'time', 'freq', 
                                'impedance', 'zre', 'zim']):
                            col_headers = [h.strip().lower() for h in parts]
                        continue
                else:
                    try:
                        vals = [float(x.strip()) for x in parts if x.strip()]
                        if len(vals) >= 2:
                            self._add_data_point(vals, row_index)
                            row_index += 1
                    except ValueError:
                        # 可能是段分隔符
                        continue
        
        self._log(f"解析完成: {len(self._data_points)} 个数据点")
        return len(self._data_points) > 0
    
    def _parse_text_file(self, filepath: str) -> bool:
        """解析 CHI 文本数据文件
        
        CHI 文本格式 (tsave):
        - 标题/参数行
        - 空行
        - 数据列 (制表符或空格分隔)
        """
        data_started = False
        row_index = 0
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    if row_index > 0:
                        # 数据段结束（可能有多段）
                        pass
                    continue
                
                # 尝试解析为数值（使用多种分隔符）
                parts = re.split(r'[,\t\s]+', line)
                
                if not data_started:
                    try:
                        vals = [float(x) for x in parts if x]
                        if len(vals) >= 2:
                            data_started = True
                            self._add_data_point(vals, row_index)
                            row_index += 1
                    except ValueError:
                        continue
                else:
                    try:
                        vals = [float(x) for x in parts if x]
                        if len(vals) >= 2:
                            self._add_data_point(vals, row_index)
                            row_index += 1
                    except ValueError:
                        continue
        
        self._log(f"解析完成: {len(self._data_points)} 个数据点")
        return len(self._data_points) > 0
    
    def _add_data_point(self, vals: List[float], index: int):
        """添加数据点
        
        根据技术类型解释列含义:
        - CV/LSV: [Potential(V), Current(A)]
        - i-t/CA: [Time(s), Current(A)]
        - OCPT:   [Time(s), Potential(V)]
        - IMP:    [Freq(Hz), Zre(ohm), Zim(ohm)]
        """
        from . import chi as chi_module
        
        tech = self._technique_str
        
        if tech in ("cv", "lsv", "lssv", "scv", "scp", "scsv",
                     "dpv", "dpp", "dpsv", "npv", "npp", "npsv",
                     "swv", "swsv", "acv", "acp", "acsv",
                     "shacv", "shacp", "shacsv", "tafel"):
            # 电位 vs 电流
            point = chi_module.ECDataPoint(
                time=float(index) * 0.01,  # 近似时间戳
                potential=vals[0],
                current=vals[1] if len(vals) > 1 else 0.0,
            )
        elif tech in ("i-t", "ca", "cc", "be"):
            # 时间 vs 电流
            point = chi_module.ECDataPoint(
                time=vals[0],
                potential=0.0,
                current=vals[1] if len(vals) > 1 else 0.0,
            )
        elif tech == "ocpt":
            # 时间 vs 电位
            point = chi_module.ECDataPoint(
                time=vals[0],
                potential=vals[1] if len(vals) > 1 else 0.0,
                current=0.0,
            )
        elif tech in ("imp", "impe", "impt"):
            # 阻抗数据: Freq, Zre, Zim
            point = chi_module.ECDataPoint(
                time=vals[0],  # 存频率
                potential=vals[1] if len(vals) > 1 else 0.0,  # Zre
                current=vals[2] if len(vals) > 2 else 0.0,    # Zim
            )
        elif tech in ("cp", "cpcr"):
            # 时间 vs 电位
            point = chi_module.ECDataPoint(
                time=vals[0],
                potential=vals[1] if len(vals) > 1 else 0.0,
                current=0.0,
            )
        else:
            # 默认: 第一列 = x, 第二列 = y
            point = chi_module.ECDataPoint(
                time=vals[0],
                potential=vals[0],
                current=vals[1] if len(vals) > 1 else 0.0,
            )
        
        self._data_points.append(point)
    
    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------
    
    def _resolve_exe_path(self) -> Optional[str]:
        """查找 chi660f.exe 路径
        
        搜索顺序:
        1. config 指定的路径
        2. 项目内 eChemSDL 目录
        3. 常见安装位置
        4. PATH 环境变量
        """
        # 1. 已指定路径
        if self._config.chi_exe_path and os.path.isfile(self._config.chi_exe_path):
            return self._config.chi_exe_path
        
        # 2. 项目内查找
        candidates = [
            # 光盘目录 (从 hardware/ -> src/ -> echem_sdl/ -> MicroHySeeker/ -> MicroHySeeker/)
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
                "eChemSDL", "chi660f光盘-250103", "chi660f光盘-250103",
                "chi660f", "chi660f.exe"
            ),
            # hardware/ -> src/ -> echem_sdl/ -> MicroHySeeker/
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))))),
                "eChemSDL", "chi660f光盘-250103", "chi660f光盘-250103",
                "chi660f", "chi660f.exe"
            ),
            # 上级目录
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))))),
                "chi660f", "chi660f.exe"
            ),
        ]
        
        # 3. 常见安装位置
        for drive in ['C', 'D', 'E']:
            candidates.extend([
                f"{drive}:\\CHI\\chi660f\\chi660f.exe",
                f"{drive}:\\Program Files\\CHI\\chi660f\\chi660f.exe",
                f"{drive}:\\Program Files (x86)\\CHI\\chi660f\\chi660f.exe",
                f"{drive}:\\CHI660F\\chi660f.exe",
            ])
        
        for path in candidates:
            if os.path.isfile(path):
                return path
        
        # 4. PATH 查找
        found = shutil.which("chi660f.exe") or shutil.which("chi660f")
        return found
    
    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        prefix = "[CHI660F-Macro]"
        if self._log_service:
            log_func = getattr(self._log_service, level, self._log_service.info)
            log_func(f"{prefix} {message}")
        else:
            log_func = getattr(logger, level, logger.info)
            log_func(f"{prefix} {message}")


# ============================================================
# 便捷函数
# ============================================================

def create_macro_driver(
    chi_exe_path: str = "",
    work_dir: str = "",
    dummy_cell: bool = False,
    log_service=None,
) -> CHI660FMacroDriver:
    """创建并初始化宏驱动的便捷函数
    
    Args:
        chi_exe_path: chi660f.exe 路径 (空字符串=自动查找)
        work_dir: 工作目录 (空=临时目录)
        dummy_cell: 使用 dummy cell 测试
        log_service: 日志服务
        
    Returns:
        已初始化的 CHI660FMacroDriver 实例
    """
    config = MacroConfig(
        chi_exe_path=chi_exe_path,
        work_dir=work_dir,
        dummy_cell=dummy_cell,
    )
    driver = CHI660FMacroDriver(config, log_service)
    return driver


def generate_macro_string(
    technique: str = "cv",
    params: Dict[str, Any] = None,
    output_name: str = "experiment",
    output_format: str = "csv",
    dummy_cell: bool = False,
    auto_close: bool = True,
    folder: str = "",
) -> str:
    """直接生成宏字符串 (不通过驱动)
    
    这是一个简便函数，可以在不创建驱动实例的情况下生成 .mcr 内容。
    
    Args:
        technique: 技术字符串 (cv, lsv, i-t, imp, ocpt 等)
        params: 参数字典 {命令: 值}，如 {"ei": 0, "eh": 0.5, "v": 0.1}
        output_name: 输出文件名 (无扩展名)
        output_format: 输出格式 (csv/text/bin)
        dummy_cell: 使用虚拟电池
        auto_close: 完成后自动关闭
        folder: 输出目录
        
    Returns:
        宏文件内容字符串
        
    Example:
        >>> mcr = generate_macro_string(
        ...     technique="cv",
        ...     params={"ei": 0, "eh": 0.5, "el": -0.5, "ef": 0, 
        ...             "v": 0.1, "cl": 2, "si": 0.001, "qt": 2},
        ...     output_name="test_cv",
        ... )
        >>> print(mcr)
    """
    lines = [
        "; CHI 660F Macro",
        f"; Technique: {technique}",
        "",
    ]
    
    if folder:
        lines.append(f"folder: {folder}")
    lines.append("fileoverride")
    
    if dummy_cell:
        lines.append("dummyon")
    
    lines.append(f"tech: {technique}")
    
    if params:
        for cmd, val in params.items():
            lines.append(f"{cmd} = {val}")
    
    lines.append("")
    lines.append("run")
    
    save_cmd = {"csv": "csvsave", "text": "tsave", "bin": "save"}
    lines.append(f"{save_cmd.get(output_format, 'csvsave')}: {output_name}")
    
    if dummy_cell:
        lines.append("dummyoff")
    
    if auto_close:
        lines.append("")
        lines.append("forcequit:yesiamsure")
    
    lines.append("")
    lines.append("end")
    
    return '\n'.join(lines)
