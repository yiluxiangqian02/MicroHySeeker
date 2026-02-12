"""
CHIInstrument - CHI 电化学工作站驱动模块

封装 CHI 电化学仪器的通信，支持多种电化学技术。
支持 Mock 模式用于无仪器开发测试。
"""
from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import Optional, List, Callable, Any
import threading
import time
import math
import random


class ECTechnique(IntEnum):
    """电化学技术代码（与 CHI 仪器兼容）
    
    代码值与 CHI libec.dll 一致：
    - M_CV = 0    循环伏安法
    - M_LSV = 1   线性扫描伏安法  
    - M_CA = 2    计时电流法
    - M_CC = 3    计时库仑法
    - M_CP = 4    计时电位法
    - M_DPV = 5   差分脉冲伏安法
    - M_NPV = 6   正常脉冲伏安法  
    - M_SWV = 7   方波伏安法
    - M_SHACV = 8 二次谐波交流伏安法
    - M_ACIM = 9  交流阻抗
    - M_IMPE = 10 阻抗-电位
    - M_IT = 11   安培-时间曲线 (i-t)
    - M_OCPT = 12 开路电位测量
    """
    CV = 0          # 循环伏安法
    LSV = 1         # 线性扫描伏安法
    CA = 2          # 计时电流法
    CC = 3          # 计时库仑法
    CP = 4          # 计时电位法
    DPV = 5         # 差分脉冲伏安法
    NPV = 6         # 正常脉冲伏安法
    SWV = 7         # 方波伏安法
    SHACV = 8       # 二次谐波交流伏安法
    ACIM = 9        # 交流阻抗
    IMPE = 10       # 阻抗-电位
    IT = 11         # 安培-时间曲线 (i-t)
    OCPT = 12       # 开路电位测量


# 技术名称映射
TECHNIQUE_NAMES = {
    ECTechnique.CV: "循环伏安法 (CV)",
    ECTechnique.LSV: "线性扫描伏安法 (LSV)",
    ECTechnique.CA: "计时电流法 (CA)",
    ECTechnique.CC: "计时库仑法 (CC)",
    ECTechnique.CP: "计时电位法 (CP)",
    ECTechnique.DPV: "差分脉冲伏安法 (DPV)",
    ECTechnique.NPV: "正常脉冲伏安法 (NPV)",
    ECTechnique.SWV: "方波伏安法 (SWV)",
    ECTechnique.SHACV: "二次谐波交流伏安法 (SHACV)",
    ECTechnique.ACIM: "交流阻抗 (ACIM)",
    ECTechnique.IMPE: "阻抗-电位 (IMPE)",
    ECTechnique.IT: "安培-时间曲线 (i-t)",
    ECTechnique.OCPT: "开路电位测量 (OCPT)",
}

# 技术字符串到枚举的映射
TECHNIQUE_FROM_STR = {
    "CV": ECTechnique.CV,
    "LSV": ECTechnique.LSV,
    "CA": ECTechnique.CA,
    "CC": ECTechnique.CC,
    "CP": ECTechnique.CP,
    "DPV": ECTechnique.DPV,
    "NPV": ECTechnique.NPV,
    "SWV": ECTechnique.SWV,
    "SHACV": ECTechnique.SHACV,
    "ACIM": ECTechnique.ACIM,
    "IMPE": ECTechnique.IMPE,
    "i-t": ECTechnique.IT,
    "IT": ECTechnique.IT,
    "OCPT": ECTechnique.OCPT,
}


class CHIState(Enum):
    """CHI 仪器状态"""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class ECParameters:
    """电化学参数配置"""
    technique: ECTechnique = ECTechnique.CV
    
    # 电位参数 (V)
    e_init: float = 0.0      # 初始电位
    e_high: float = 0.5      # 高电位
    e_low: float = -0.5      # 低电位
    e_final: float = 0.0     # 最终电位
    
    # 扫描参数
    scan_rate: float = 0.1   # 扫描速率 (V/s)
    sample_interval: float = 0.001  # 采样间隔 (V)
    
    # 时间参数
    quiet_time: float = 2.0  # 静置时间 (s)
    run_time: float = 60.0   # 运行时间 (s) - 用于 i-t
    
    # 其他
    segments: int = 2        # 段数
    sensitivity: float = -1.0  # 灵敏度 (-1 = 自动)
    
    @classmethod
    def from_ec_config(cls, ec_config) -> "ECParameters":
        """从 ECConfig 创建"""
        technique = TECHNIQUE_FROM_STR.get(ec_config.technique, ECTechnique.CV)
        return cls(
            technique=technique,
            e_init=ec_config.e_init,
            e_high=ec_config.e_high,
            e_low=ec_config.e_low,
            e_final=ec_config.e_final,
            scan_rate=ec_config.scan_rate,
            sample_interval=ec_config.sample_interval,
            quiet_time=ec_config.quiet_time,
            run_time=ec_config.run_time,
            segments=ec_config.segments,
            sensitivity=ec_config.sensitivity,
        )


@dataclass
class ECDataPoint:
    """电化学数据点"""
    time: float      # 时间 (s)
    potential: float # 电位 (V)
    current: float   # 电流 (A)
    
    def to_dict(self):
        return {
            "time": self.time,
            "potential": self.potential,
            "current": self.current,
        }


@dataclass
class ECDataSet:
    """电化学数据集"""
    name: str = ""
    technique: str = "CV"
    timestamp: str = ""
    points: List[ECDataPoint] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    @property
    def times(self) -> List[float]:
        return [p.time for p in self.points]
    
    @property
    def potentials(self) -> List[float]:
        return [p.potential for p in self.points]
    
    @property
    def currents(self) -> List[float]:
        return [p.current for p in self.points]
    
    def add_point(self, point: ECDataPoint):
        self.points.append(point)
    
    def clear(self):
        self.points.clear()


# ========================
# Mock 实现
# ========================

class MockCHI:
    """Mock CHI 仪器 - 模拟电化学测量"""
    
    def __init__(self):
        self._params: Optional[ECParameters] = None
        self._running = False
        self._paused = False
        self._data_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._data_points: List[ECDataPoint] = []
    
    def set_parameters(self, params: ECParameters) -> bool:
        self._params = params
        return True
    
    def run(self, data_callback: Callable[[ECDataPoint], None] = None,
            complete_callback: Callable[[], None] = None) -> bool:
        if self._running:
            return False
        
        self._running = True
        self._stop_event.clear()
        self._pause_event.set()  # 初始非暂停
        self._data_points.clear()
        
        self._data_thread = threading.Thread(
            target=self._generate_mock_data,
            args=(data_callback, complete_callback),
            daemon=True
        )
        self._data_thread.start()
        return True
    
    def stop(self) -> bool:
        self._stop_event.set()
        self._running = False
        if self._data_thread and self._data_thread.is_alive():
            self._data_thread.join(timeout=2.0)
        return True
    
    def pause(self) -> bool:
        self._paused = True
        self._pause_event.clear()
        return True
    
    def resume(self) -> bool:
        self._paused = False
        self._pause_event.set()
        return True
    
    def get_data(self) -> List[ECDataPoint]:
        return self._data_points.copy()
    
    def _generate_mock_data(self, callback: Callable = None,
                            complete_callback: Callable = None) -> None:
        """生成模拟数据"""
        if not self._params:
            self._running = False
            return
        
        technique = self._params.technique
        
        if technique == ECTechnique.CV:
            self._generate_cv_data(callback)
        elif technique == ECTechnique.LSV:
            self._generate_lsv_data(callback)
        elif technique in [ECTechnique.IT, ECTechnique.CA]:
            self._generate_it_data(callback)
        elif technique == ECTechnique.OCPT:
            self._generate_ocpt_data(callback)
        else:
            self._generate_cv_data(callback)
        
        self._running = False
        
        if complete_callback:
            complete_callback()
    
    def _generate_cv_data(self, callback: Callable = None):
        """生成 CV 模拟数据"""
        params = self._params
        
        # 静置时间
        time.sleep(min(params.quiet_time, 0.5))
        
        t = 0.0
        dt = 0.05  # 50ms 采样间隔
        
        e_range = params.e_high - params.e_low
        total_time = e_range * params.segments / params.scan_rate
        
        while t < total_time and not self._stop_event.is_set():
            # 等待暂停结束
            self._pause_event.wait()
            
            # 计算当前电位 (锯齿波)
            cycle_time = e_range / params.scan_rate
            segment = int(t / cycle_time) % params.segments
            t_in_segment = t % cycle_time
            
            if segment % 2 == 0:
                # 正向扫描
                e = params.e_low + (t_in_segment / cycle_time) * e_range
            else:
                # 反向扫描
                e = params.e_high - (t_in_segment / cycle_time) * e_range
            
            # 模拟 CV 电流响应 (简化的氧化还原峰)
            e_peak = (params.e_high + params.e_low) / 2
            i_base = 1e-7  # 背景电流
            i_peak = 5e-6  # 峰电流
            peak_width = 0.1  # 峰宽度
            
            # 高斯峰形模拟
            i = i_base + i_peak * math.exp(-((e - e_peak) ** 2) / (2 * peak_width ** 2))
            
            # 添加噪声
            i += random.gauss(0, 1e-8)
            
            point = ECDataPoint(time=t, potential=e, current=i)
            self._data_points.append(point)
            
            if callback:
                callback(point)
            
            t += dt
            time.sleep(dt)
    
    def _generate_lsv_data(self, callback: Callable = None):
        """生成 LSV 模拟数据"""
        params = self._params
        
        time.sleep(min(params.quiet_time, 0.5))
        
        t = 0.0
        dt = 0.05
        
        e_range = abs(params.e_final - params.e_init)
        total_time = e_range / params.scan_rate
        
        direction = 1 if params.e_final > params.e_init else -1
        
        while t < total_time and not self._stop_event.is_set():
            self._pause_event.wait()
            
            e = params.e_init + direction * t * params.scan_rate
            
            # 模拟扩散控制电流
            i = 1e-6 * (1 - math.exp(-t / 5)) + random.gauss(0, 1e-8)
            
            point = ECDataPoint(time=t, potential=e, current=i)
            self._data_points.append(point)
            
            if callback:
                callback(point)
            
            t += dt
            time.sleep(dt)
    
    def _generate_it_data(self, callback: Callable = None):
        """生成 i-t 模拟数据"""
        params = self._params
        
        time.sleep(min(params.quiet_time, 0.5))
        
        t = 0.0
        dt = max(params.sample_interval, 0.05)
        
        # 固定电位
        e = params.e_init
        
        while t < params.run_time and not self._stop_event.is_set():
            self._pause_event.wait()
            
            # Cottrell 方程模拟
            if t > 0:
                i = 1e-5 / math.sqrt(t) + 1e-7 + random.gauss(0, 1e-8)
            else:
                i = 1e-4
            
            point = ECDataPoint(time=t, potential=e, current=i)
            self._data_points.append(point)
            
            if callback:
                callback(point)
            
            t += dt
            time.sleep(dt)
    
    def _generate_ocpt_data(self, callback: Callable = None):
        """生成 OCPT 模拟数据"""
        params = self._params
        
        t = 0.0
        dt = max(params.sample_interval, 0.1)
        
        # 开路电位漂移模拟
        e_start = 0.1
        e_end = 0.05
        
        while t < params.run_time and not self._stop_event.is_set():
            self._pause_event.wait()
            
            # 指数衰减到稳态
            e = e_end + (e_start - e_end) * math.exp(-t / 30)
            e += random.gauss(0, 0.001)  # 添加噪声
            
            i = 0.0  # 开路电位时电流为零
            
            point = ECDataPoint(time=t, potential=e, current=i)
            self._data_points.append(point)
            
            if callback:
                callback(point)
            
            t += dt
            time.sleep(dt)


# ========================
# 主类
# ========================

class CHIInstrument:
    """CHI 电化学仪器驱动
    
    封装 CHI 工作站的通信，支持多种电化学技术。
    
    Attributes:
        state: 当前状态
        is_connected: 是否已连接
        is_running: 是否正在测量
        data_points: 采集的数据点
        
    Example:
        >>> chi = CHIInstrument(mock_mode=True)
        >>> chi.connect()
        >>> params = ECParameters(technique=ECTechnique.CV)
        >>> chi.set_parameters(params)
        >>> chi.run()
        >>> data = chi.get_data()
    """
    
    def __init__(
        self,
        dll_path: Optional[str] = None,
        logger: Optional[Any] = None,
        mock_mode: bool = True,
        instrument_model: str = "",
        chi_exe_path: str = "",
    ) -> None:
        """初始化 CHI 仪器
        
        Args:
            dll_path: libec.dll 路径，默认在系统PATH中查找
            logger: 日志服务
            mock_mode: 是否使用模拟模式
            instrument_model: 仪器型号 ("660f" 将使用宏命令驱动)
            chi_exe_path: chi660f.exe 路径 (仅 660F 宏模式)
        """
        self._dll_path = dll_path
        self._logger = logger
        self._mock_mode = mock_mode
        self._instrument_model = instrument_model.lower().strip()
        self._chi_exe_path = chi_exe_path
        
        self._state = CHIState.DISCONNECTED
        self._params: Optional[ECParameters] = None
        self._data_points: List[ECDataPoint] = []
        
        # 回调
        self._data_callback: Optional[Callable[[ECDataPoint], None]] = None
        self._complete_callback: Optional[Callable[[], None]] = None
        self._error_callback: Optional[Callable[[Exception], None]] = None
        
        # Mock 或真实 DLL
        self._mock: Optional[MockCHI] = None
        self._dll = None
        
        # 32位桥接器（当 Python 为 64位时使用）
        self._bridge = None
        self._use_bridge = False
        
        # CHI 660F 宏命令驱动
        self._macro_driver = None
        self._use_macro = False
        
        # 线程
        self._lock = threading.RLock()
        
        if self._logger:
            mode_str = "Mock" if mock_mode else "Hardware"
            if self._instrument_model == "660f":
                mode_str = "660F-Macro"
            self._logger.info(f"CHIInstrument 初始化 ({mode_str}模式)")
    
    @property
    def state(self) -> CHIState:
        """获取当前状态"""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._state != CHIState.DISCONNECTED
    
    @property
    def is_running(self) -> bool:
        """是否正在测量"""
        return self._state == CHIState.RUNNING
    
    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._state == CHIState.PAUSED
    
    def connect(self) -> bool:
        """连接 CHI 仪器
        
        参考 C# CHIInitialize:
        1. 加载 libec.dll（32位：直接ctypes，64位：32位桥接进程）
        2. 查询支持的技术
        3. 设置默认灵敏度和参数
        4. 运行假实验测试连接 (可选)
        
        Returns:
            bool: 连接是否成功
        """
        with self._lock:
            if self._state != CHIState.DISCONNECTED:
                return True
            
            if self._mock_mode:
                self._mock = MockCHI()
                self._state = CHIState.IDLE
                self._log("Mock CHI 已连接")
                return True
            
            # 真实硬件连接
            try:
                # CHI 660F: 使用宏命令驱动 (libec.dll 不支持 660F)
                if self._instrument_model == "660f":
                    return self._connect_via_macro()
                
                import sys
                is_64bit = sys.maxsize > 2**32
                
                if is_64bit:
                    # 64位Python：使用32位桥接进程
                    return self._connect_via_bridge()
                else:
                    # 32位Python：直接加载DLL
                    return self._connect_via_ctypes()
                
            except FileNotFoundError as e:
                self._log(f"DLL/桥接程序未找到: {e}，将使用模拟模式", level="error")
                # 降级到 mock 模式
                self._mock_mode = True
                self._mock = MockCHI()
                self._state = CHIState.IDLE
                return True
                
            except Exception as e:
                self._log(f"CHI 连接失败: {e}", level="error")
                self._state = CHIState.ERROR
                return False
    
    def _connect_via_macro(self) -> bool:
        """通过宏命令驱动连接 CHI 660F
        
        660F 系列不被 libec.dll 支持，使用 chi660f.exe 的
        宏命令 (/runmacro) 接口来控制。
        """
        from .chi_macro import CHI660FMacroDriver, MacroConfig
        
        config = MacroConfig(
            chi_exe_path=self._chi_exe_path,
        )
        self._macro_driver = CHI660FMacroDriver(config, self._logger)
        
        if not self._macro_driver.connect():
            raise FileNotFoundError("chi660f.exe 未找到")
        
        self._use_macro = True
        self._state = CHIState.IDLE
        self._log("CHI 660F 已连接 (宏命令模式)")
        return True
    
    def _connect_via_bridge(self) -> bool:
        """通过32位桥接进程连接（64位Python专用）"""
        from .chi_bridge import CHIBridge32
        
        self._bridge = CHIBridge32()
        if not self._bridge.start():
            raise RuntimeError("无法启动32位桥接进程")
        
        self._use_bridge = True
        
        # 初始化系统设置
        self._bridge.init_system()
        
        # 设置默认参数
        self._bridge.set_parameter("m_iSens", 1e-6)
        self._bridge.set_parameter("m_ei", 0.0)
        self._bridge.set_parameter("m_eh", 0.0)
        self._bridge.set_parameter("m_el", 0.0)
        self._bridge.set_parameter("m_ef", 0.0)
        self._bridge.set_parameter("m_inpcl", 1.0)
        
        # 查询支持的技术
        self._supported_techniques = []
        for tid in self._bridge.get_supported_techniques():
            try:
                self._supported_techniques.append(ECTechnique(tid))
            except ValueError:
                pass
        self._log(f"[桥接模式] 支持 {len(self._supported_techniques)} 种电化学技术")
        
        self._state = CHIState.IDLE
        self._log("CHI 仪器已连接 (32位桥接模式)")
        return True
    
    def _connect_via_ctypes(self) -> bool:
        """通过ctypes直接连接（32位Python专用）"""
        import ctypes
        dll_path = self._dll_path or "libec.dll"
        self._dll = ctypes.CDLL(dll_path)
        self._setup_dll_functions()
        
        # 设置默认灵敏度 (与 C# 一致: 1e-6 V/A)
        self._dll.CHI_setParameter(b"m_iSens", 1e-6)
        # 初始化电位参数为 0
        self._dll.CHI_setParameter(b"m_ei", 0.0)
        self._dll.CHI_setParameter(b"m_eh", 0.0)
        self._dll.CHI_setParameter(b"m_el", 0.0)
        self._dll.CHI_setParameter(b"m_ef", 0.0)
        self._dll.CHI_setParameter(b"m_inpcl", 1.0)
        
        # 查询支持的技术
        self._supported_techniques = self.get_supported_techniques()
        self._log(f"支持 {len(self._supported_techniques)} 种电化学技术")
        
        self._state = CHIState.IDLE
        self._log("CHI 仪器已连接 (DLL 加载成功)")
        return True
    
    def disconnect(self) -> None:
        """断开连接"""
        with self._lock:
            if self.is_running:
                self.stop()
            
            # 关闭宏驱动
            if self._macro_driver:
                try:
                    self._macro_driver.disconnect()
                except Exception:
                    pass
                self._macro_driver = None
                self._use_macro = False
            
            # 关闭桥接进程
            if self._bridge:
                try:
                    self._bridge.close_com()
                except Exception:
                    pass
                try:
                    self._bridge.stop()
                except Exception:
                    pass
                self._bridge = None
                self._use_bridge = False
            
            self._mock = None
            self._dll = None
            self._state = CHIState.DISCONNECTED
            self._log("CHI 已断开连接")
    
    def set_parameters(self, params: ECParameters) -> bool:
        """设置电化学参数
        
        Args:
            params: 电化学参数配置
            
        Returns:
            bool: 设置是否成功
        """
        with self._lock:
            if self._state not in [CHIState.IDLE, CHIState.PAUSED]:
                return False
            
            self._params = params
            
            if self._mock_mode and self._mock:
                return self._mock.set_parameters(params)
            
            if self._use_macro and self._macro_driver:
                return self._macro_driver.set_parameters(params)
            
            if self._use_bridge and self._bridge:
                return self._set_bridge_parameters(params)
            
            if self._dll:
                return self._set_dll_parameters(params)
            
            return True
    
    def run(self) -> bool:
        """开始测量
        
        Returns:
            bool: 是否成功启动
            
        Note:
            此方法非阻塞，测量在后台进行
        """
        with self._lock:
            if self._state != CHIState.IDLE:
                return False
            
            self._data_points.clear()
            self._state = CHIState.RUNNING
            
            if self._mock_mode and self._mock:
                def on_data(point: ECDataPoint):
                    self._data_points.append(point)
                    if self._data_callback:
                        self._data_callback(point)
                
                def on_complete():
                    self._state = CHIState.IDLE
                    if self._complete_callback:
                        self._complete_callback()
                
                return self._mock.run(on_data, on_complete)
            
            if self._use_macro and self._macro_driver:
                return self._run_macro()
            
            if self._use_bridge and self._bridge:
                return self._run_bridge()
            
            if self._dll:
                return self._run_dll()
            
            return False
    
    def stop(self) -> bool:
        """停止测量
        
        Returns:
            bool: 是否成功停止
        """
        with self._lock:
            if self._state not in [CHIState.RUNNING, CHIState.PAUSED]:
                return True
            
            if self._mock_mode and self._mock:
                result = self._mock.stop()
            elif self._use_macro and self._macro_driver:
                result = self._macro_driver.stop_experiment()
            elif self._use_bridge and self._bridge:
                result = self._stop_bridge()
            elif self._dll:
                result = self._stop_dll()
            else:
                result = True
            
            self._state = CHIState.IDLE
            return result
    
    def pause(self) -> bool:
        """暂停测量"""
        with self._lock:
            if self._state != CHIState.RUNNING:
                return False
            
            if self._mock_mode and self._mock:
                self._mock.pause()
            
            self._state = CHIState.PAUSED
            return True
    
    def resume(self) -> bool:
        """恢复测量"""
        with self._lock:
            if self._state != CHIState.PAUSED:
                return False
            
            if self._mock_mode and self._mock:
                self._mock.resume()
            
            self._state = CHIState.RUNNING
            return True
    
    def get_data(self) -> List[ECDataPoint]:
        """获取采集的数据
        
        Returns:
            数据点列表
        """
        with self._lock:
            if self._mock_mode and self._mock:
                return self._mock.get_data()
            if self._use_macro and self._macro_driver:
                return self._macro_driver.get_data()
            return self._data_points.copy()
    
    def get_data_set(self) -> ECDataSet:
        """获取数据集对象"""
        from datetime import datetime
        
        technique_name = "CV"
        if self._params:
            technique_name = self._params.technique.name
        
        data_set = ECDataSet(
            name=f"EC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            technique=technique_name,
            timestamp=datetime.now().isoformat(),
            points=self.get_data(),
            metadata={
                "params": {
                    "e_init": self._params.e_init if self._params else 0,
                    "e_high": self._params.e_high if self._params else 0.5,
                    "e_low": self._params.e_low if self._params else -0.5,
                    "scan_rate": self._params.scan_rate if self._params else 0.1,
                }
            }
        )
        return data_set
    
    def on_data(self, callback: Callable[[ECDataPoint], None]) -> None:
        """注册实时数据回调"""
        self._data_callback = callback
    
    def on_complete(self, callback: Callable[[], None]) -> None:
        """注册测量完成回调"""
        self._complete_callback = callback
    
    def on_error(self, callback: Callable[[Exception], None]) -> None:
        """注册错误回调"""
        self._error_callback = callback
    
    def get_estimated_duration(self, params: Optional[ECParameters] = None) -> float:
        """计算预估测量时间
        
        Args:
            params: 电化学参数（None 使用当前参数）
            
        Returns:
            预估秒数
        """
        params = params or self._params
        if not params:
            return 60.0
        
        if params.technique == ECTechnique.CV:
            # CV: 扫描范围 / 扫描速率 * 段数
            voltage_range = params.e_high - params.e_low
            time_per_segment = voltage_range / params.scan_rate
            return params.quiet_time + time_per_segment * params.segments
        
        elif params.technique == ECTechnique.LSV:
            # LSV: 扫描范围 / 扫描速率
            voltage_range = abs(params.e_final - params.e_init)
            return params.quiet_time + voltage_range / params.scan_rate
        
        elif params.technique in [ECTechnique.IT, ECTechnique.CA]:
            # i-t: 直接使用运行时间
            return params.quiet_time + params.run_time
        
        elif params.technique == ECTechnique.OCPT:
            # OCPT: 使用运行时间
            return params.run_time
        
        else:
            return params.quiet_time + 60.0  # 默认 1 分钟
    
    # ========================
    # 私有方法
    # ========================
    
    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self._logger:
            log_func = getattr(self._logger, level, self._logger.info)
            log_func(f"[CHI] {message}")
    
    def _setup_dll_functions(self):
        """设置 DLL 函数原型
        
        参考 C# CHInstrument.cs 的 DllImport 声明:
        - CHI_hasTechnique(int x) -> byte
        - CHI_setTechnique(int x) -> void
        - CHI_setParameter(byte[] id, float newValue) -> void  
        - CHI_runExperiment() -> bool
        - CHI_experimentIsRunning() -> byte
        - CHI_showErrorStatus() -> void
        - CHI_getExperimentData(float[] x, float[] y, int n) -> void
        - CHI_getErrorStatus(byte[] buffer, int length) -> void
        - CHI_getParameter(byte[] id) -> float
        """
        import ctypes
        
        # CHI_hasTechnique(int x) -> byte  
        # 检查仪器是否支持指定技术
        self._dll.CHI_hasTechnique.argtypes = [ctypes.c_int]
        self._dll.CHI_hasTechnique.restype = ctypes.c_ubyte
        
        # CHI_setTechnique(int x) -> void
        # 设置当前电化学技术
        self._dll.CHI_setTechnique.argtypes = [ctypes.c_int]
        self._dll.CHI_setTechnique.restype = None
        
        # CHI_setParameter(byte[] id, float newValue) -> void
        # 设置参数 (id 为 ASCII 编码的参数名)
        self._dll.CHI_setParameter.argtypes = [ctypes.c_char_p, ctypes.c_float]
        self._dll.CHI_setParameter.restype = None
        
        # CHI_getParameter(byte[] id) -> float
        # 读取参数
        self._dll.CHI_getParameter.argtypes = [ctypes.c_char_p]
        self._dll.CHI_getParameter.restype = ctypes.c_float
        
        # CHI_runExperiment() -> bool
        # 启动实验，返回 True 表示成功
        self._dll.CHI_runExperiment.argtypes = []
        self._dll.CHI_runExperiment.restype = ctypes.c_bool
        
        # CHI_experimentIsRunning() -> byte
        # 查询实验是否正在运行 (1=运行中, 0=已停止)
        self._dll.CHI_experimentIsRunning.argtypes = []
        self._dll.CHI_experimentIsRunning.restype = ctypes.c_ubyte
        
        # CHI_showErrorStatus() -> void
        self._dll.CHI_showErrorStatus.argtypes = []
        self._dll.CHI_showErrorStatus.restype = None
        
        # CHI_getExperimentData(float[] x, float[] y, int n) -> void
        # 获取实验数据到预分配的数组中
        self._dll.CHI_getExperimentData.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int
        ]
        self._dll.CHI_getExperimentData.restype = None
        
        # CHI_getErrorStatus(byte[] buffer, int length) -> void
        self._dll.CHI_getErrorStatus.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self._dll.CHI_getErrorStatus.restype = None
    
    def _set_dll_parameters(self, params: ECParameters) -> bool:
        """将参数写入 DLL
        
        参数名映射 (来自 C# CHInstrument.cs SetExperiment):
        - m_ei      : 初始电位 E0
        - m_eh      : 高电位 EH
        - m_el      : 低电位 EL  
        - m_ef      : 终止电位 EF
        - m_vv      : 扫描速率
        - m_qt      : 静置时间
        - m_st      : 运行时间 (i-t)
        - m_inpcl   : 段数/圈数
        - m_pn      : 扫描方向 (1=正向, 0=反向)
        - m_inpsi   : 采样间隔
        - m_bAutoSens : 自动灵敏度 (1=自动)
        - m_iSens   : 灵敏度 (V/A)
        
        注意: 6E类仪器不支持LSV，需用CV单段替代
        """
        try:
            technique = params.technique
            
            # LSV 在 660e 上不支持，使用 CV 单段替代
            use_technique = technique
            if technique == ECTechnique.LSV:
                use_technique = ECTechnique.CV
                self._log("LSV 使用 CV 单段替代 (兼容 660e)")
            
            # 设置通用参数
            self._dll.CHI_setParameter(b"m_ei", params.e_init)
            self._dll.CHI_setParameter(b"m_iSens", params.sensitivity if params.sensitivity > 0 else 1e-6)
            
            if technique == ECTechnique.CV:
                self._dll.CHI_setParameter(b"m_eh", params.e_high)
                self._dll.CHI_setParameter(b"m_el", params.e_low)
                self._dll.CHI_setParameter(b"m_ef", params.e_final)
                self._dll.CHI_setParameter(b"m_vv", params.scan_rate)
                self._dll.CHI_setParameter(b"m_qt", params.quiet_time)
                self._dll.CHI_setParameter(b"m_inpcl", float(params.segments))
                self._dll.CHI_setParameter(b"m_pn", 1.0)  # 正向扫描
                self._dll.CHI_setParameter(b"m_inpsi", params.sample_interval)
                auto_sens = 1.0 if params.sensitivity < 0 else 0.0
                self._dll.CHI_setParameter(b"m_bAutoSens", auto_sens)
                self._dll.CHI_setTechnique(int(ECTechnique.CV))
                
            elif technique == ECTechnique.LSV:
                # 使用 CV 单段替代 LSV (兼容 660e)
                if params.e_final > params.e_init:
                    self._dll.CHI_setParameter(b"m_eh", params.e_final)
                    self._dll.CHI_setParameter(b"m_pn", 1.0)
                else:
                    self._dll.CHI_setParameter(b"m_el", params.e_final)
                    self._dll.CHI_setParameter(b"m_pn", 0.0)
                self._dll.CHI_setParameter(b"m_vv", params.scan_rate)
                self._dll.CHI_setParameter(b"m_qt", params.quiet_time)
                self._dll.CHI_setParameter(b"m_inpcl", 1.0)  # 只扫一段
                self._dll.CHI_setParameter(b"m_inpsi", params.sample_interval)
                auto_sens = 1.0 if params.sensitivity < 0 else 0.0
                self._dll.CHI_setParameter(b"m_bAutoSens", auto_sens)
                self._dll.CHI_setTechnique(int(ECTechnique.CV))
                
            elif technique in (ECTechnique.IT, ECTechnique.CA):
                self._dll.CHI_setParameter(b"m_qt", params.quiet_time)
                self._dll.CHI_setParameter(b"m_st", params.run_time)
                self._dll.CHI_setParameter(b"m_inpsi", params.sample_interval)
                self._dll.CHI_setTechnique(int(ECTechnique.IT))
                
            elif technique == ECTechnique.OCPT:
                self._dll.CHI_setParameter(b"m_st", params.run_time)
                self._dll.CHI_setParameter(b"m_inpsi", params.sample_interval)
                self._dll.CHI_setTechnique(int(ECTechnique.OCPT))
                
            else:
                # 其他技术使用通用设置
                self._dll.CHI_setParameter(b"m_eh", params.e_high)
                self._dll.CHI_setParameter(b"m_el", params.e_low)
                self._dll.CHI_setParameter(b"m_ef", params.e_final)
                self._dll.CHI_setParameter(b"m_vv", params.scan_rate)
                self._dll.CHI_setParameter(b"m_qt", params.quiet_time)
                self._dll.CHI_setTechnique(int(technique))
            
            return True
        except Exception as e:
            self._log(f"设置参数失败: {e}", level="error")
            return False
    
    def _run_dll(self) -> bool:
        """通过 DLL 运行测量
        
        参考 C# ReadData_DoWork: 
        1. 调用 CHI_runExperiment() 启动
        2. 在后台线程中轮询 CHI_experimentIsRunning()
        3. 调用 CHI_getExperimentData() 读取增量数据
        """
        import ctypes
        
        try:
            # 预分配数据缓冲区 (与 C# 项目一致, n=65536)
            n = 65536
            x_buf = (ctypes.c_float * n)()
            y_buf = (ctypes.c_float * n)()
            
            # 启动实验
            success = self._dll.CHI_runExperiment()
            if not success:
                # 检查错误
                err_buf = ctypes.create_string_buffer(200)
                self._dll.CHI_getErrorStatus(err_buf, 200)
                err_msg = err_buf.value.decode("utf-8", errors="ignore").strip('\x00')
                if "Link failed" in err_msg:
                    self._log("仪器连接失败 (Link failed)", level="error")
                    self._state = CHIState.ERROR
                else:
                    self._log(f"启动实验失败: {err_msg}", level="error")
                return False
            
            # 后台数据采集线程
            self._stop_event = threading.Event()
            
            def _poll_data():
                last_point = 0
                while not self._stop_event.is_set():
                    # 检查实验是否仍在运行
                    running = self._dll.CHI_experimentIsRunning()
                    
                    # 读取数据
                    self._dll.CHI_getExperimentData(x_buf, y_buf, n)
                    
                    # 提取新增数据点
                    i = last_point
                    while i < n and y_buf[i] != 0.0:
                        point = ECDataPoint(
                            time=float(x_buf[i]),
                            potential=float(x_buf[i]),
                            current=float(y_buf[i])
                        )
                        self._data_points.append(point)
                        if self._data_callback:
                            try:
                                self._data_callback(point)
                            except Exception:
                                pass
                        i += 1
                    last_point = i
                    
                    if running != 1:
                        break
                    
                    time.sleep(0.05)  # 50ms 采样间隔 (与 C# 一致)
                
                # 测量结束
                self._state = CHIState.IDLE
                if self._complete_callback:
                    try:
                        self._complete_callback()
                    except Exception:
                        pass
            
            self._data_thread = threading.Thread(target=_poll_data, daemon=True)
            self._data_thread.start()
            return True
            
        except Exception as e:
            self._log(f"运行失败: {e}", level="error")
            return False
    
    def _stop_dll(self) -> bool:
        """通过 DLL 停止测量"""
        try:
            if hasattr(self, '_stop_event'):
                self._stop_event.set()
            if hasattr(self, '_data_thread') and self._data_thread and self._data_thread.is_alive():
                self._data_thread.join(timeout=2.0)
            return True
        except Exception as e:
            self._log(f"停止失败: {e}", level="error")
            return False
    
    def check_connection(self) -> bool:
        """检测仪器连接状态
        
        参考 C# CHIInitialize：
        运行一个假实验，如果返回失败且错误信息包含 "Link failed"，
        则判定未连接。
        
        注意：此操作会尝试打开串口。
        测试完成后会调用 closeCom 关闭串口（解决了 C# 代码中的串口泄漏问题）。
        
        Returns:
            bool: 是否已连接
        """
        if self._mock_mode:
            return True
        
        if self._use_bridge and self._bridge:
            return self._bridge.check_connection()
        
        if not self._dll:
            return False
        
        try:
            import ctypes
            # 设置一个简单的 CV 技术
            self._dll.CHI_setTechnique(int(ECTechnique.CV))
            self._dll.CHI_setParameter(b"m_ei", 0.0)
            self._dll.CHI_setParameter(b"m_eh", 0.0)
            self._dll.CHI_setParameter(b"m_el", 0.0)
            self._dll.CHI_setParameter(b"m_inpcl", 1.0)
            
            result = self._dll.CHI_runExperiment()
            if not result:
                err_buf = ctypes.create_string_buffer(200)
                self._dll.CHI_getErrorStatus(err_buf, 200)
                err_msg = err_buf.value.decode("utf-8", errors="ignore").strip('\x00')
                if "Link failed" in err_msg:
                    self._log("连接检测: 仪器未连接 (Link failed)")
                    return False
            return True
        except Exception as e:
            self._log(f"连接检测异常: {e}", level="error")
            return False
        finally:
            # 关闭串口防止冲突（新发现的 closeCom 函数）
            self._close_com()
    
    def close_com(self) -> None:
        """关闭 libec.dll 占用的串口
        
        解决了 C# 代码中"找不到关闭串口的方法"的问题。
        libec.dll 导出了 Libec::closeCom() 函数可用于此目的。
        应在连接测试后调用，防止串口冲突影响泵的 RS485 通信。
        """
        self._close_com()
    
    def _close_com(self):
        """内部关闭串口"""
        if self._use_bridge and self._bridge:
            try:
                self._bridge.close_com()
            except Exception:
                pass
        elif self._dll:
            try:
                # 调用 Libec::closeCom() (C++ mangled name)
                close_func = getattr(self._dll, '?closeCom@Libec@@YAXXZ', None)
                if close_func:
                    close_func()
            except Exception:
                pass
    
    def get_supported_techniques(self) -> list:
        """查询仪器支持的电化学技术
        
        Returns:
            list: 支持的 ECTechnique 列表
        """
        if self._mock_mode:
            return list(ECTechnique)
        
        if self._use_bridge and self._bridge:
            supported = []
            for tid in self._bridge.get_supported_techniques():
                try:
                    supported.append(ECTechnique(tid))
                except ValueError:
                    pass
            return supported
        
        if not self._dll:
            return []
        
        supported = []
        for i in range(45):  # CHI 仪器最多 44 种技术
            try:
                if self._dll.CHI_hasTechnique(i) == 1:
                    try:
                        supported.append(ECTechnique(i))
                    except ValueError:
                        pass  # 未知技术编号
            except Exception:
                break
        return supported
    
    # ========================
    # 桥接模式 私有方法
    # ========================
    
    def _set_bridge_parameters(self, params: ECParameters) -> bool:
        """通过桥接设置参数"""
        try:
            technique = params.technique
            use_technique = technique
            
            # LSV 在 660e 上不支持，使用 CV 单段替代
            if technique == ECTechnique.LSV:
                use_technique = ECTechnique.CV
                self._log("LSV 使用 CV 单段替代 (兼容 660e)")
            
            # 通用参数
            self._bridge.set_parameter("m_ei", params.e_init)
            self._bridge.set_parameter("m_iSens", 
                params.sensitivity if params.sensitivity > 0 else 1e-6)
            
            if technique == ECTechnique.CV:
                self._bridge.set_parameter("m_eh", params.e_high)
                self._bridge.set_parameter("m_el", params.e_low)
                self._bridge.set_parameter("m_ef", params.e_final)
                self._bridge.set_parameter("m_vv", params.scan_rate)
                self._bridge.set_parameter("m_qt", params.quiet_time)
                self._bridge.set_parameter("m_inpcl", float(params.segments))
                self._bridge.set_parameter("m_pn", 1.0)
                self._bridge.set_parameter("m_inpsi", params.sample_interval)
                auto_sens = 1.0 if params.sensitivity < 0 else 0.0
                self._bridge.set_parameter("m_bAutoSens", auto_sens)
                self._bridge.set_technique(int(ECTechnique.CV))
                
            elif technique == ECTechnique.LSV:
                if params.e_final > params.e_init:
                    self._bridge.set_parameter("m_eh", params.e_final)
                    self._bridge.set_parameter("m_pn", 1.0)
                else:
                    self._bridge.set_parameter("m_el", params.e_final)
                    self._bridge.set_parameter("m_pn", 0.0)
                self._bridge.set_parameter("m_vv", params.scan_rate)
                self._bridge.set_parameter("m_qt", params.quiet_time)
                self._bridge.set_parameter("m_inpcl", 1.0)
                self._bridge.set_parameter("m_inpsi", params.sample_interval)
                auto_sens = 1.0 if params.sensitivity < 0 else 0.0
                self._bridge.set_parameter("m_bAutoSens", auto_sens)
                self._bridge.set_technique(int(ECTechnique.CV))
                
            elif technique in (ECTechnique.IT, ECTechnique.CA):
                self._bridge.set_parameter("m_qt", params.quiet_time)
                self._bridge.set_parameter("m_st", params.run_time)
                self._bridge.set_parameter("m_inpsi", params.sample_interval)
                self._bridge.set_technique(int(ECTechnique.IT))
                
            elif technique == ECTechnique.OCPT:
                self._bridge.set_parameter("m_st", params.run_time)
                self._bridge.set_parameter("m_inpsi", params.sample_interval)
                self._bridge.set_technique(int(ECTechnique.OCPT))
                
            else:
                self._bridge.set_parameter("m_eh", params.e_high)
                self._bridge.set_parameter("m_el", params.e_low)
                self._bridge.set_parameter("m_ef", params.e_final)
                self._bridge.set_parameter("m_vv", params.scan_rate)
                self._bridge.set_parameter("m_qt", params.quiet_time)
                self._bridge.set_technique(int(technique))
            
            return True
        except Exception as e:
            self._log(f"桥接设置参数失败: {e}", level="error")
            return False
    
    def _run_bridge(self) -> bool:
        """通过桥接运行测量"""
        try:
            success = self._bridge.run_experiment()
            if not success:
                error = self._bridge.get_error_status()
                if "Link failed" in error:
                    self._log("仪器连接失败 (Link failed)", level="error")
                    self._state = CHIState.ERROR
                else:
                    self._log(f"启动实验失败: {error}", level="error")
                return False
            
            # 后台数据采集线程
            self._stop_event = threading.Event()
            
            def _poll_bridge_data():
                while not self._stop_event.is_set():
                    running = self._bridge.experiment_is_running()
                    
                    # 读取数据
                    data = self._bridge.get_experiment_data(65536)
                    
                    # 提取新数据点
                    new_start = len(self._data_points)
                    for i in range(new_start, len(data)):
                        x, y = data[i]
                        point = ECDataPoint(
                            time=float(x),
                            potential=float(x),
                            current=float(y)
                        )
                        self._data_points.append(point)
                        if self._data_callback:
                            try:
                                self._data_callback(point)
                            except Exception:
                                pass
                    
                    if not running:
                        break
                    
                    time.sleep(0.1)
                
                self._state = CHIState.IDLE
                if self._complete_callback:
                    try:
                        self._complete_callback()
                    except Exception:
                        pass
            
            self._data_thread = threading.Thread(
                target=_poll_bridge_data, daemon=True
            )
            self._data_thread.start()
            return True
            
        except Exception as e:
            self._log(f"桥接运行失败: {e}", level="error")
            return False
    
    def _stop_bridge(self) -> bool:
        """通过桥接停止测量"""
        try:
            if hasattr(self, '_stop_event'):
                self._stop_event.set()
            self._bridge.stop_experiment()
            if hasattr(self, '_data_thread') and self._data_thread and self._data_thread.is_alive():
                self._data_thread.join(timeout=2.0)
            return True
        except Exception as e:
            self._log(f"桥接停止失败: {e}", level="error")
            return False
    
    # ========================
    # 宏命令模式 (660F)
    # ========================
    
    def _run_macro(self) -> bool:
        """通过宏命令运行实验 (CHI 660F)
        
        非阻塞: 在后台线程中运行 chi660f.exe，完成后触发回调。
        """
        if not self._macro_driver:
            return False
        
        # 注册回调
        def _on_macro_complete():
            self._state = CHIState.IDLE
            self._data_points = self._macro_driver.get_data()
            self._log(f"宏实验完成, 获得 {len(self._data_points)} 个数据点")
            if self._complete_callback:
                try:
                    self._complete_callback()
                except Exception:
                    pass
        
        def _on_macro_error(e: Exception):
            self._state = CHIState.ERROR
            self._log(f"宏实验失败: {e}", level="error")
            if self._error_callback:
                try:
                    self._error_callback(e)
                except Exception:
                    pass
        
        self._macro_driver.on_complete(_on_macro_complete)
        self._macro_driver.on_error(_on_macro_error)
        
        # 非阻塞启动
        return self._macro_driver.run_experiment(blocking=False)
