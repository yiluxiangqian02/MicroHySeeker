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
        mock_mode: bool = True
    ) -> None:
        """初始化 CHI 仪器
        
        Args:
            dll_path: libec.dll 路径，默认在系统PATH中查找
            logger: 日志服务
            mock_mode: 是否使用模拟模式
        """
        self._dll_path = dll_path
        self._logger = logger
        self._mock_mode = mock_mode
        
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
        
        # 线程
        self._lock = threading.RLock()
        
        if self._logger:
            mode_str = "Mock" if mock_mode else "Hardware"
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
                import ctypes
                dll_path = self._dll_path or "libec.dll"
                self._dll = ctypes.CDLL(dll_path)
                self._setup_dll_functions()
                self._state = CHIState.IDLE
                self._log("CHI 仪器已连接")
                return True
            except Exception as e:
                self._log(f"CHI 连接失败: {e}", level="error")
                self._state = CHIState.ERROR
                return False
    
    def disconnect(self) -> None:
        """断开连接"""
        with self._lock:
            if self.is_running:
                self.stop()
            
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
        """设置 DLL 函数原型"""
        import ctypes
        
        # chi_setpara(int id, char* name, double value)
        self._dll.chi_setpara.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_double
        ]
        self._dll.chi_setpara.restype = ctypes.c_int
        
        # chi_run(int id)
        self._dll.chi_run.argtypes = [ctypes.c_int]
        self._dll.chi_run.restype = ctypes.c_int
        
        # chi_stop(int id)
        self._dll.chi_stop.argtypes = [ctypes.c_int]
        self._dll.chi_stop.restype = ctypes.c_int
    
    def _set_dll_parameters(self, params: ECParameters) -> bool:
        """将参数写入 DLL"""
        try:
            # 设置技术类型
            self._dll.chi_setpara(0, b"m_tech", float(params.technique))
            
            # 设置电位参数
            self._dll.chi_setpara(0, b"m_ei", params.e_init)
            self._dll.chi_setpara(0, b"m_eh", params.e_high)
            self._dll.chi_setpara(0, b"m_el", params.e_low)
            self._dll.chi_setpara(0, b"m_ef", params.e_final)
            
            # 设置扫描参数
            self._dll.chi_setpara(0, b"m_vv", params.scan_rate)
            self._dll.chi_setpara(0, b"m_si", params.sample_interval)
            
            # 设置时间参数
            self._dll.chi_setpara(0, b"m_qt", params.quiet_time)
            self._dll.chi_setpara(0, b"m_rt", params.run_time)
            
            return True
        except Exception as e:
            self._log(f"设置参数失败: {e}", level="error")
            return False
    
    def _run_dll(self) -> bool:
        """通过 DLL 运行测量"""
        try:
            result = self._dll.chi_run(0)
            return result == 0
        except Exception as e:
            self._log(f"运行失败: {e}", level="error")
            return False
    
    def _stop_dll(self) -> bool:
        """通过 DLL 停止测量"""
        try:
            result = self._dll.chi_stop(0)
            return result == 0
        except Exception as e:
            self._log(f"停止失败: {e}", level="error")
            return False
