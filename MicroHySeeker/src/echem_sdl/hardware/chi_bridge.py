"""CHI 32位 DLL 桥接器

由于 libec.dll 是32位DLL，在64位Python中无法直接加载，
本模块通过启动一个32位 .NET 进程来桥接通信。

通信协议：
- Python 通过 stdin 发送命令行
- 32位进程通过 stdout 返回结果
- 命令格式: COMMAND [args...]
- 响应格式: OK [data...] 或 ERROR [message]

支持的桥接命令:
- PING → PONG
- HAS_TECHNIQUE <id> → OK 0|1
- SET_TECHNIQUE <id> → OK
- SET_PARAMETER <name> <value> → OK
- GET_PARAMETER <name> → OK <value>
- RUN_EXPERIMENT → OK True|False
- IS_RUNNING → OK 0|1
- GET_ERROR → OK <error_string>
- GET_DATA <n> → OK <count> <x1,y1> <x2,y2> ...
- CLOSE_COM → OK COM_CLOSED
- RESET → OK RESET
- INIT_SYSTEM → OK INITIALIZED
- GET_MODEL → OK <model_series>
- STOP → OK STOPPED
- EXIT → BRIDGE_EXIT
"""

import subprocess
import os
import sys
import threading
import time
import logging
from typing import Optional, Tuple, List
from pathlib import Path


logger = logging.getLogger(__name__)


class CHIBridge32:
    """通过 32 位子进程桥接 libec.dll 调用
    
    自动管理子进程生命周期，提供同步 API。
    
    Usage:
        bridge = CHIBridge32(bridge_exe_path="path/to/test_chi_connection.exe")
        bridge.start()
        
        has = bridge.has_technique(0)  # CV
        bridge.set_technique(0)
        bridge.set_parameter("m_ei", 0.0)
        success = bridge.run_experiment()
        
        bridge.close_com()
        bridge.stop()
    """
    
    def __init__(
        self,
        bridge_exe_path: Optional[str] = None,
        dll_dir: Optional[str] = None,
        qt_dll_dir: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """初始化桥接器
        
        Args:
            bridge_exe_path: 32位桥接可执行文件路径
            dll_dir: libec.dll 所在目录
            qt_dll_dir: Qt4 DLL 所在目录（QtCore4.dll 等）
            timeout: 命令超时时间（秒）
        """
        self._bridge_exe = bridge_exe_path
        self._dll_dir = dll_dir
        self._qt_dll_dir = qt_dll_dir
        self._timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._started = False
        
        # 自动查找路径
        if not self._bridge_exe:
            self._bridge_exe = self._find_bridge_exe()
        if not self._dll_dir:
            self._dll_dir = self._find_dll_dir()
        if not self._qt_dll_dir:
            self._qt_dll_dir = self._find_qt_dll_dir()
    
    def _find_bridge_exe(self) -> str:
        """自动查找桥接可执行文件"""
        # 查找顺序：当前目录 → bin目录 → 上级目录
        search_paths = [
            Path(__file__).parent / "chi_bridge.exe",
            Path(__file__).parent.parent.parent.parent / "chi_bridge.exe",
            Path(__file__).parent.parent.parent.parent / "test_chi_connection.exe",
            Path(__file__).parent.parent.parent.parent / "bin" / "chi_bridge.exe",
        ]
        for p in search_paths:
            if p.exists():
                return str(p)
        
        # 查找同目录下的 libec.dll 附近
        dll_candidates = [
            Path(__file__).parent.parent.parent.parent / "libec.dll",
        ]
        for dll_path in dll_candidates:
            if dll_path.exists():
                exe_path = dll_path.parent / "test_chi_connection.exe"
                if exe_path.exists():
                    return str(exe_path)
        
        raise FileNotFoundError(
            "找不到 CHI 32位桥接程序 (test_chi_connection.exe 或 chi_bridge.exe)"
        )
    
    def _find_dll_dir(self) -> str:
        """自动查找 libec.dll 目录"""
        candidates = [
            Path(__file__).parent.parent.parent.parent / "libec.dll",
            Path(__file__).parent.parent.parent.parent.parent / "eChemSDL" / "eChemSDL" / "bin" / "Debug" / "libec.dll",
        ]
        for p in candidates:
            if p.exists():
                return str(p.parent)
        return str(Path(self._bridge_exe).parent) if self._bridge_exe else "."
    
    def _find_qt_dll_dir(self) -> str:
        """自动查找 Qt4 DLL 目录"""
        candidates = [
            Path(__file__).parent.parent.parent.parent.parent / "eChemSDL" / "eChemSDL" / "bin" / "Debug",
        ]
        for p in candidates:
            qt_core = p / "QtCore4.dll"
            if qt_core.exists():
                return str(p)
        # 默认同 dll_dir
        return self._dll_dir or "."
    
    @property
    def is_running(self) -> bool:
        """桥接进程是否运行中"""
        return self._started and self._process is not None and self._process.poll() is None
    
    def start(self) -> bool:
        """启动32位桥接进程
        
        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if self.is_running:
                return True
            
            try:
                # 设置环境变量，确保能找到 Qt4 DLLs
                env = os.environ.copy()
                path_dirs = []
                if self._dll_dir:
                    path_dirs.append(self._dll_dir)
                if self._qt_dll_dir and self._qt_dll_dir != self._dll_dir:
                    path_dirs.append(self._qt_dll_dir)
                if path_dirs:
                    env["PATH"] = ";".join(path_dirs) + ";" + env.get("PATH", "")
                
                # 工作目录设为 DLL 所在目录
                cwd = self._dll_dir or os.path.dirname(self._bridge_exe)
                
                logger.info(f"启动 CHI 桥接: {self._bridge_exe} bridge")
                logger.info(f"工作目录: {cwd}")
                
                self._process = subprocess.Popen(
                    [self._bridge_exe, "bridge"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                
                # 等待 BRIDGE_READY（跳过Qt警告等非协议输出）
                max_attempts = 10
                for _ in range(max_attempts):
                    ready_line = self._read_line(timeout=15.0)
                    if ready_line and "BRIDGE_READY" in ready_line:
                        self._started = True
                        logger.info("CHI 桥接已就绪")
                        return True
                    elif ready_line:
                        logger.debug(f"桥接启动时跳过: {ready_line}")
                    else:
                        break
                
                logger.error(f"桥接启动失败: 未收到 BRIDGE_READY")
                self._kill_process()
                return False
                    
            except FileNotFoundError:
                logger.error(f"找不到桥接程序: {self._bridge_exe}")
                return False
            except Exception as e:
                logger.error(f"桥接启动异常: {e}")
                self._kill_process()
                return False
    
    def stop(self):
        """停止桥接进程"""
        with self._lock:
            if self._process and self._process.poll() is None:
                try:
                    self._send_command("EXIT")
                    self._process.wait(timeout=5.0)
                except Exception:
                    self._kill_process()
            self._started = False
            self._process = None
    
    def _kill_process(self):
        """强制终止进程"""
        if self._process:
            try:
                self._process.kill()
                self._process.wait(timeout=3.0)
            except Exception:
                pass
            self._process = None
    
    def _send_command(self, command: str) -> str:
        """发送命令并读取响应
        
        Args:
            command: 命令字符串
            
        Returns:
            响应字符串
            
        Raises:
            RuntimeError: 桥接未启动或通信失败
        """
        if not self.is_running:
            raise RuntimeError("CHI 桥接未启动")
        
        try:
            cmd_bytes = (command + "\n").encode("utf-8")
            self._process.stdin.write(cmd_bytes)
            self._process.stdin.flush()
            
            response = self._read_line(timeout=self._timeout)
            if response is None:
                raise RuntimeError(f"桥接响应超时 (命令: {command})")
            return response
            
        except (BrokenPipeError, OSError) as e:
            self._started = False
            raise RuntimeError(f"桥接通信断开: {e}")
    
    def _read_line(self, timeout: float = None) -> Optional[str]:
        """从子进程读取一行（带超时）"""
        timeout = timeout or self._timeout
        
        import select
        if sys.platform == "win32":
            # Windows: 使用线程读取（无 select）
            result = [None]
            
            def _read():
                try:
                    line = self._process.stdout.readline()
                    if line:
                        result[0] = line.decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
            
            reader = threading.Thread(target=_read, daemon=True)
            reader.start()
            reader.join(timeout=timeout)
            return result[0]
        else:
            # Unix: 使用 select
            ready, _, _ = select.select([self._process.stdout], [], [], timeout)
            if ready:
                line = self._process.stdout.readline()
                return line.decode("utf-8", errors="replace").strip()
            return None
    
    def _parse_response(self, response: str) -> Tuple[bool, str]:
        """解析响应
        
        Returns:
            (success, data) — success=True 如果以 OK 开头
        """
        if response.startswith("OK"):
            data = response[2:].strip() if len(response) > 2 else ""
            return True, data
        elif response.startswith("ERROR"):
            return False, response[5:].strip()
        elif response.startswith("PONG"):
            return True, "PONG"
        else:
            return False, response
    
    # ========================
    # 高层 API
    # ========================
    
    def ping(self) -> bool:
        """测试桥接是否响应"""
        try:
            response = self._send_command("PING")
            return "PONG" in response
        except Exception:
            return False
    
    def has_technique(self, technique_id: int) -> bool:
        """检查是否支持指定技术"""
        response = self._send_command(f"HAS_TECHNIQUE {technique_id}")
        ok, data = self._parse_response(response)
        return ok and data.strip() == "1"
    
    def set_technique(self, technique_id: int):
        """设置电化学技术"""
        response = self._send_command(f"SET_TECHNIQUE {technique_id}")
        ok, data = self._parse_response(response)
        if not ok:
            raise RuntimeError(f"SET_TECHNIQUE 失败: {data}")
    
    def set_parameter(self, name: str, value: float):
        """设置参数"""
        response = self._send_command(f"SET_PARAMETER {name} {value}")
        ok, data = self._parse_response(response)
        if not ok:
            raise RuntimeError(f"SET_PARAMETER 失败: {data}")
    
    def get_parameter(self, name: str) -> float:
        """读取参数"""
        response = self._send_command(f"GET_PARAMETER {name}")
        ok, data = self._parse_response(response)
        if ok:
            return float(data)
        raise RuntimeError(f"GET_PARAMETER 失败: {data}")
    
    def run_experiment(self) -> bool:
        """启动实验"""
        response = self._send_command("RUN_EXPERIMENT")
        ok, data = self._parse_response(response)
        if ok:
            return data.strip() == "True"
        return False
    
    def experiment_is_running(self) -> bool:
        """查询实验是否运行中"""
        response = self._send_command("IS_RUNNING")
        ok, data = self._parse_response(response)
        return ok and data.strip() == "1"
    
    def get_error_status(self) -> str:
        """获取错误状态"""
        response = self._send_command("GET_ERROR")
        ok, data = self._parse_response(response)
        return data if ok else f"ERROR: {data}"
    
    def get_experiment_data(self, n: int = 65536) -> List[Tuple[float, float]]:
        """获取实验数据
        
        Returns:
            list of (x, y) tuples
        """
        response = self._send_command(f"GET_DATA {n}")
        ok, data = self._parse_response(response)
        if not ok:
            return []
        
        parts = data.split()
        if not parts:
            return []
        
        count = int(parts[0])
        points = []
        for i in range(1, min(len(parts), count + 1)):
            xy = parts[i].split(",")
            if len(xy) == 2:
                points.append((float(xy[0]), float(xy[1])))
        return points
    
    def close_com(self):
        """关闭串口（重要！防止端口冲突）"""
        response = self._send_command("CLOSE_COM")
        ok, data = self._parse_response(response)
        if not ok:
            logger.warning(f"CLOSE_COM 失败: {data}")
    
    def reset(self):
        """重置 libec"""
        response = self._send_command("RESET")
        ok, data = self._parse_response(response)
        if not ok:
            logger.warning(f"RESET 失败: {data}")
    
    def init_system(self):
        """初始化系统设置"""
        response = self._send_command("INIT_SYSTEM")
        ok, data = self._parse_response(response)
        if not ok:
            logger.warning(f"INIT_SYSTEM 失败: {data}")
    
    def stop_experiment(self):
        """停止实验"""
        response = self._send_command("STOP")
        ok, data = self._parse_response(response)
        if not ok:
            logger.warning(f"STOP 失败: {data}")
    
    def get_supported_techniques(self) -> List[int]:
        """枚举所有支持的技术
        
        Returns:
            list of supported technique IDs
        """
        supported = []
        for i in range(45):
            try:
                if self.has_technique(i):
                    supported.append(i)
            except Exception:
                break
        return supported
    
    def check_connection(self) -> bool:
        """检测仪器连接状态
        
        通过运行假实验并检查 "Link failed" 错误来判断。
        注意：此操作会尝试打开串口。
        
        Returns:
            bool: 是否已连接
        """
        try:
            # 设置最小 CV 参数
            self.set_technique(0)  # CV
            self.set_parameter("m_ei", 0.0)
            self.set_parameter("m_eh", 0.0)
            self.set_parameter("m_el", 0.0)
            self.set_parameter("m_inpcl", 1.0)
            
            result = self.run_experiment()
            if not result:
                error = self.get_error_status()
                if "Link failed" in error:
                    return False
            return True
        except Exception as e:
            logger.error(f"连接检测异常: {e}")
            return False
        finally:
            # 关闭串口防止冲突
            try:
                self.close_com()
            except Exception:
                pass
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close_com()
        except Exception:
            pass
        self.stop()
    
    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass


def is_64bit_python() -> bool:
    """检测当前 Python 是否为 64 位"""
    return sys.maxsize > 2**32


def needs_bridge() -> bool:
    """是否需要使用32位桥接
    
    当 Python 为 64 位时需要桥接来调用 32 位 libec.dll
    """
    return is_64bit_python()
