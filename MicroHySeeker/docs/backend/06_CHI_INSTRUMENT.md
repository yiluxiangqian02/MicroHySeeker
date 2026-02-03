# 06 - CHIInstrument 模块规范

> **文件路径**: `src/echem_sdl/hardware/chi.py`  
> **优先级**: P2 (硬件驱动)  
> **依赖**: `lib_context.py`  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\CHInstrument.cs`

---

## 一、模块职责

CHIInstrument 是 CHI 电化学工作站的驱动封装，负责：
1. 通过 DLL (libec.dll) 与 CHI 仪器通信
2. 配置电化学实验参数（CV/LSV/i-t/OCPT）
3. 启动/停止电化学测量
4. 采集实时数据（电位/电流曲线）
5. 提供 Mock 模式用于无仪器开发

**核心功能**:
- 循环伏安法 (CV)
- 线性扫描伏安法 (LSV)  
- 安培-时间曲线法 (i-t)
- 开路电位测量 (OCPT)

---

## 二、技术代码常量

### 2.1 电化学技术枚举

```python
from enum import IntEnum

class ECTechnique(IntEnum):
    """电化学技术代码（与 CHI 仪器兼容）"""
    CV = 0          # 循环伏安法
    LSV = 1         # 线性扫描伏安法
    CA = 2          # 计时电流法
    CC = 3          # 计时库仑法
    CP = 4          # 计时电位法
    OCPT = 5        # 开路电位测量
    DPV = 6         # 差分脉冲伏安法
    NPV = 7         # 正常脉冲伏安法
    SWV = 8         # 方波伏安法
    IT = 9          # 安培-时间曲线 (i-t)
    # ... 更多技术代码见 constants.py
```

### 2.2 参数ID常量

```python
# 电位参数
PARAM_EI = "m_ei"      # 初始电位 (V)
PARAM_EH = "m_eh"      # 高电位 (V)
PARAM_EL = "m_el"      # 低电位 (V)
PARAM_EF = "m_ef"      # 最终电位 (V)

# 扫描参数
PARAM_VV = "m_vv"      # 扫描速率 (V/s)
PARAM_SI = "m_si"      # 采样间隔 (V)

# 时间参数
PARAM_QT = "m_qt"      # 静置时间 (s)
PARAM_RT = "m_rt"      # 运行时间 (s)

# 段数/循环
PARAM_NS = "m_ns"      # 段数
PARAM_CL = "m_cl"      # 循环数

# 灵敏度
PARAM_SN = "m_sn"      # 灵敏度
PARAM_AS = "m_as"      # 自动灵敏度
```

---

## 三、类设计

### 3.1 数据类

```python
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

class CHIState(Enum):
    """CHI 仪器状态"""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    RUNNING = "running"
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
    sensitivity: int = -1    # 灵敏度 (-1 = 自动)

@dataclass 
class ECDataPoint:
    """电化学数据点"""
    time: float      # 时间 (s)
    potential: float # 电位 (V)
    current: float   # 电流 (A)
```

### 3.2 主类定义

```python
from typing import Callable, List, Optional
import ctypes
import threading

class CHIInstrument:
    """CHI 电化学仪器驱动
    
    封装 CHI 工作站的 DLL 调用，支持多种电化学技术。
    
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
```

### 3.3 构造函数

```python
def __init__(
    self,
    dll_path: Optional[str] = None,
    logger: Optional["LoggerService"] = None,
    mock_mode: bool = False
) -> None:
    """初始化 CHI 仪器
    
    Args:
        dll_path: libec.dll 路径，默认在系统PATH中查找
        logger: 日志服务
        mock_mode: 是否使用模拟模式
    """
```

### 3.4 公开方法

#### connect() / disconnect()
```python
def connect(self) -> bool:
    """连接 CHI 仪器
    
    Returns:
        bool: 连接是否成功
    """

def disconnect(self) -> None:
    """断开连接"""
```

#### set_parameters()
```python
def set_parameters(self, params: ECParameters) -> bool:
    """设置电化学参数
    
    Args:
        params: 电化学参数配置
        
    Returns:
        bool: 设置是否成功
    """
```

#### run() / stop()
```python
def run(self) -> bool:
    """开始测量
    
    Returns:
        bool: 是否成功启动
        
    Note:
        此方法非阻塞，测量在后台进行
    """

def stop(self) -> bool:
    """停止测量
    
    Returns:
        bool: 是否成功停止
    """
```

#### get_data()
```python
def get_data(self) -> List[ECDataPoint]:
    """获取采集的数据
    
    Returns:
        数据点列表
    """
```

#### set_data_callback()
```python
def set_data_callback(
    self,
    callback: Callable[[ECDataPoint], None]
) -> None:
    """设置数据回调（实时数据推送）
    
    Args:
        callback: 数据点回调函数
    """
```

#### get_estimated_duration()
```python
def get_estimated_duration(self, params: ECParameters) -> float:
    """计算预估测量时间
    
    Args:
        params: 电化学参数
        
    Returns:
        预估秒数
    """
```

---

## 四、DLL 接口封装

### 4.1 DLL 加载

```python
class CHIDll:
    """CHI DLL 封装"""
    
    def __init__(self, dll_path: str = "libec.dll"):
        self._dll = ctypes.CDLL(dll_path)
        self._setup_functions()
    
    def _setup_functions(self):
        """设置函数原型"""
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
        
        # chi_getdata(int id, double* e, double* i, int* n)
        self._dll.chi_getdata.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_int)
        ]
        self._dll.chi_getdata.restype = ctypes.c_int
```

### 4.2 参数设置

```python
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
        self._logger.error(f"设置参数失败: {e}")
        return False
```

### 4.3 数据采集

```python
def _poll_data(self) -> None:
    """轮询数据（后台线程）"""
    e_buffer = (ctypes.c_double * 10000)()
    i_buffer = (ctypes.c_double * 10000)()
    n = ctypes.c_int(0)
    
    while self.state == CHIState.RUNNING:
        result = self._dll.chi_getdata(
            0,
            e_buffer,
            i_buffer,
            ctypes.byref(n)
        )
        
        if result == 0 and n.value > len(self._data_points):
            # 有新数据
            for i in range(len(self._data_points), n.value):
                point = ECDataPoint(
                    time=i * self._sample_interval,
                    potential=e_buffer[i],
                    current=i_buffer[i]
                )
                self._data_points.append(point)
                
                if self._data_callback:
                    self._data_callback(point)
        
        time.sleep(0.05)  # 50ms 轮询间隔
```

---

## 五、Mock 模式

### 5.1 Mock 实现

```python
class MockCHI:
    """Mock CHI 仪器"""
    
    def __init__(self):
        self._params: Optional[ECParameters] = None
        self._running = False
        self._data_thread: Optional[threading.Thread] = None
    
    def set_parameters(self, params: ECParameters) -> bool:
        self._params = params
        return True
    
    def run(self, data_callback: Callable) -> bool:
        self._running = True
        self._data_thread = threading.Thread(
            target=self._generate_mock_data,
            args=(data_callback,)
        )
        self._data_thread.start()
        return True
    
    def stop(self) -> bool:
        self._running = False
        if self._data_thread:
            self._data_thread.join()
        return True
    
    def _generate_mock_data(self, callback: Callable) -> None:
        """生成模拟数据"""
        import math
        
        t = 0.0
        dt = 0.1
        
        while self._running and t < self._params.run_time:
            # 生成模拟 CV 曲线
            e = self._params.e_init + 0.5 * math.sin(t * 0.5)
            i = 1e-6 * math.sin(t * 0.5) + 1e-7 * (random.random() - 0.5)
            
            point = ECDataPoint(time=t, potential=e, current=i)
            callback(point)
            
            t += dt
            time.sleep(dt)
```

---

## 六、时间估算

### 6.1 不同技术的时间计算

```python
def get_estimated_duration(self, params: ECParameters) -> float:
    """计算预估测量时间"""
    
    if params.technique == ECTechnique.CV:
        # CV: 扫描范围 / 扫描速率 * 段数
        voltage_range = params.e_high - params.e_low
        time_per_segment = voltage_range / params.scan_rate
        return params.quiet_time + time_per_segment * params.segments
    
    elif params.technique == ECTechnique.LSV:
        # LSV: 扫描范围 / 扫描速率
        voltage_range = abs(params.e_final - params.e_init)
        return params.quiet_time + voltage_range / params.scan_rate
    
    elif params.technique == ECTechnique.IT:
        # i-t: 直接使用运行时间
        return params.quiet_time + params.run_time
    
    elif params.technique == ECTechnique.OCPT:
        # OCPT: 使用运行时间
        return params.run_time
    
    else:
        return params.quiet_time + 60.0  # 默认 1 分钟
```

---

## 七、事件回调

### 7.1 回调类型

```python
from typing import TypeAlias

OnDataPoint: TypeAlias = Callable[[ECDataPoint], None]
OnMeasurementComplete: TypeAlias = Callable[[List[ECDataPoint]], None]
OnError: TypeAlias = Callable[[Exception], None]
```

### 7.2 注册回调

```python
def on_data(self, callback: OnDataPoint) -> None:
    """注册实时数据回调"""
    self._data_callback = callback

def on_complete(self, callback: OnMeasurementComplete) -> None:
    """注册测量完成回调"""
    self._complete_callback = callback

def on_error(self, callback: OnError) -> None:
    """注册错误回调"""
    self._error_callback = callback
```

---

## 八、测试要求

### 8.1 单元测试

```python
# tests/test_chi.py

import pytest
import time
from echem_sdl.hardware.chi import (
    CHIInstrument, ECParameters, ECTechnique,
    CHIState, ECDataPoint
)

class TestCHIInstrument:
    @pytest.fixture
    def chi(self):
        return CHIInstrument(mock_mode=True)
    
    def test_connect(self, chi):
        """测试连接"""
        assert chi.connect() == True
        assert chi.state == CHIState.IDLE
        chi.disconnect()
        assert chi.state == CHIState.DISCONNECTED
    
    def test_set_parameters(self, chi):
        """测试参数设置"""
        chi.connect()
        params = ECParameters(
            technique=ECTechnique.CV,
            e_init=0.0,
            e_high=0.5,
            e_low=-0.5,
            scan_rate=0.1
        )
        result = chi.set_parameters(params)
        assert result == True
    
    def test_run_cv(self, chi):
        """测试 CV 测量"""
        chi.connect()
        params = ECParameters(
            technique=ECTechnique.CV,
            scan_rate=0.1,
            segments=2
        )
        chi.set_parameters(params)
        
        data = []
        chi.on_data(lambda p: data.append(p))
        
        chi.run()
        time.sleep(1)  # 等待一些数据
        chi.stop()
        
        assert len(data) > 0
        assert all(isinstance(p, ECDataPoint) for p in data)
    
    def test_estimated_duration(self, chi):
        """测试时间估算"""
        params = ECParameters(
            technique=ECTechnique.CV,
            e_high=0.5,
            e_low=-0.5,
            scan_rate=0.1,
            segments=2,
            quiet_time=2.0
        )
        duration = chi.get_estimated_duration(params)
        # 电压范围 1V，速率 0.1 V/s，2段 = 20s + 2s 静置 = 22s
        assert duration == pytest.approx(22.0, rel=0.1)

class TestECParameters:
    def test_default_values(self):
        """测试默认值"""
        params = ECParameters()
        assert params.technique == ECTechnique.CV
        assert params.scan_rate == 0.1
    
    def test_custom_values(self):
        """测试自定义值"""
        params = ECParameters(
            technique=ECTechnique.LSV,
            e_init=0.0,
            e_final=1.0,
            scan_rate=0.05
        )
        assert params.technique == ECTechnique.LSV
        assert params.e_final == 1.0
```

---

## 九、使用示例

### 9.1 CV 测量

```python
from echem_sdl.hardware.chi import CHIInstrument, ECParameters, ECTechnique

chi = CHIInstrument(mock_mode=True)
chi.connect()

# 配置 CV 参数
params = ECParameters(
    technique=ECTechnique.CV,
    e_init=0.0,
    e_high=0.8,
    e_low=-0.3,
    e_final=0.0,
    scan_rate=0.05,  # 50 mV/s
    segments=4,
    quiet_time=5.0
)

chi.set_parameters(params)

# 设置数据回调
data_points = []
def on_data(point):
    data_points.append(point)
    print(f"E={point.potential:.3f}V, I={point.current*1e6:.3f}μA")

chi.on_data(on_data)

# 运行测量
print(f"预计时间: {chi.get_estimated_duration(params):.1f}秒")
chi.run()

# 等待完成
while chi.is_running:
    time.sleep(0.5)

print(f"采集 {len(data_points)} 个数据点")
chi.disconnect()
```

### 9.2 i-t 测量

```python
# 配置 i-t 参数
params = ECParameters(
    technique=ECTechnique.IT,
    e_init=0.3,  # 恒电位
    run_time=300.0,  # 5分钟
    sample_interval=0.1
)

chi.set_parameters(params)
chi.run()
```

---

## 十、验收标准

- [ ] 类与接口按规范实现
- [ ] 支持 CV/LSV/i-t/OCPT 技术
- [ ] DLL 调用封装正确（真实模式）
- [ ] Mock 模式生成合理数据
- [ ] 实时数据回调正常
- [ ] 时间估算准确
- [ ] 状态机转换正确
- [ ] 线程安全
- [ ] 单元测试覆盖率 > 80%
- [ ] 类型注解完整
- [ ] docstring 规范
