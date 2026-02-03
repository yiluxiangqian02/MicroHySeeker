# 17 - Constants 模块规范

> **文件路径**: `src/echem_sdl/utils/constants.py`  
> **优先级**: P0 (基础模块)  
> **依赖**: 无  
> **原C#参考**: 分散在各文件中

---

## 一、模块职责

Constants 是全局常量定义模块，负责：
1. 定义 RS485 协议常量
2. 定义泵参数常量
3. 定义电化学参数常量
4. 定义系统限制常量
5. 提供常量分组和访问

---

## 二、常量定义

### 2.1 RS485 协议常量

```python
"""RS485 协议常量"""

class RS485:
    """RS485 通讯常量"""
    
    # 波特率
    BAUDRATE = 38400
    
    # 数据位
    BYTESIZE = 8
    
    # 停止位
    STOPBITS = 2
    
    # 校验位
    PARITY = "N"  # 无校验
    
    # 超时（秒）
    TIMEOUT = 1.0
    
    # 帧头
    HEADER_QUERY = 0xFA    # 查询帧头
    HEADER_RESPONSE = 0xFB # 响应帧头
    
    # 最小帧长度
    MIN_FRAME_LENGTH = 4
    
    # 最大帧长度
    MAX_FRAME_LENGTH = 256
    
    # 重试次数
    DEFAULT_RETRY_COUNT = 3
    
    # 重试间隔（秒）
    RETRY_INTERVAL = 0.1
```

### 2.2 泵常量

```python
class Pump:
    """泵参数常量"""
    
    # 地址范围
    MIN_ADDRESS = 1
    MAX_ADDRESS = 15
    
    # 速度范围
    MIN_SPEED = 1
    MAX_SPEED = 5
    DEFAULT_SPEED = 3
    
    # 速度对应时间（秒/满程）
    SPEED_TIME_MAP = {
        1: 72.0,
        2: 36.0,
        3: 24.0,
        4: 18.0,
        5: 14.4,
    }
    
    # 注射器参数
    class Syringe:
        """注射器参数"""
        # 默认容量 (uL)
        DEFAULT_VOLUME_UL = 2500.0
        
        # 满程步数
        FULL_STEPS = 24000
        
        # 每步体积
        @classmethod
        def ul_per_step(cls, volume_ul: float = DEFAULT_VOLUME_UL) -> float:
            return volume_ul / cls.FULL_STEPS
    
    # 阀门位置
    class Valve:
        """阀门位置"""
        INPUT = 1   # 进液
        OUTPUT = 2  # 出液
        BYPASS = 3  # 旁路
    
    # 命令码
    class Cmd:
        """泵命令码"""
        INIT = 0x45          # 初始化
        ASPIRATE = 0x4C      # 吸液 (Pickup)
        DISPENSE = 0x44      # 排液 (Dispense)
        SET_VALVE = 0x4F     # 设置阀门
        GET_VALVE = 0x3F     # 查询阀门
        SET_SPEED = 0x53     # 设置速度
        GET_STATUS = 0x51    # 查询状态
        TERMINATE = 0x54     # 终止
        GET_POSITION = 0x3F  # 查询位置
        MOVE_ABS = 0x41      # 绝对移动
```

### 2.3 冲洗常量

```python
class Flush:
    """冲洗参数常量"""
    
    # 默认轮数
    DEFAULT_CYCLES = 3
    MAX_CYCLES = 10
    
    # 默认体积 (uL)
    DEFAULT_VOLUME_UL = 500.0
    
    # 泵分配
    class PumpRole:
        """泵角色"""
        WASH = "wash"        # 清洗液泵
        DRY = "dry"          # 干燥气泵
        EVACUATE = "evacuate"  # 抽空泵
    
    # 各阶段时间 (秒)
    class Timing:
        """时序参数"""
        WASH_TIME = 5.0      # 清洗时间
        DRY_TIME = 3.0       # 干燥时间
        EVACUATE_TIME = 2.0  # 抽空时间
        INTERVAL = 0.5       # 阶段间隔
```

### 2.4 电化学常量

```python
class EChem:
    """电化学参数常量"""
    
    # 支持的技术
    class Technique:
        """电化学技术"""
        CV = "CV"        # 循环伏安
        LSV = "LSV"      # 线性扫描伏安
        IT = "i-t"       # 计时电流
        OCPT = "OCPT"    # 开路电位
        CA = "CA"        # 计时安培
        DPV = "DPV"      # 差分脉冲伏安
        SWV = "SWV"      # 方波伏安
    
    # 电位范围 (V)
    class Potential:
        """电位限制"""
        MIN = -2.0
        MAX = 2.0
        DEFAULT_INIT = 0.0
        DEFAULT_HIGH = 0.8
        DEFAULT_LOW = -0.2
    
    # 扫描速率范围 (V/s)
    class ScanRate:
        """扫描速率限制"""
        MIN = 0.001
        MAX = 10.0
        DEFAULT = 0.1
    
    # 灵敏度范围 (A)
    class Sensitivity:
        """灵敏度选项"""
        OPTIONS = [1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9]
        DEFAULT = 1e-5
    
    # 时间参数
    class Timing:
        """时间参数"""
        MIN_QUIET_TIME = 0.0
        MAX_QUIET_TIME = 1000.0
        DEFAULT_QUIET_TIME = 2.0
        
        MIN_RUN_TIME = 0.1
        MAX_RUN_TIME = 86400.0  # 24 小时
        DEFAULT_RUN_TIME = 60.0
    
    # 扫描段数
    class Segments:
        """扫描段数限制"""
        MIN = 1
        MAX = 100
        DEFAULT = 2
```

### 2.5 配液常量

```python
class Dilution:
    """配液参数常量"""
    
    # 最大通道数
    MAX_CHANNELS = 8
    
    # 体积范围 (uL)
    class Volume:
        """体积限制"""
        MIN = 1.0
        MAX = 2500.0
        DEFAULT_TOTAL = 100.0
    
    # 浓度范围 (相对)
    class Concentration:
        """浓度限制"""
        MIN = 0.0
        MAX = 1.0
```

### 2.6 系统常量

```python
class System:
    """系统常量"""
    
    # 版本
    VERSION = "1.0.0"
    APP_NAME = "MicroHySeeker"
    
    # 文件路径
    class Paths:
        """路径常量"""
        DEFAULT_CONFIG = "config.json"
        DEFAULT_LOG_DIR = "logs"
        DEFAULT_DATA_DIR = "data"
        DEFAULT_PROGRAM_DIR = "programs"
    
    # 定时器
    class Timer:
        """定时器常量"""
        UI_REFRESH_MS = 100
        ENGINE_TICK_MS = 1000
        STATUS_POLL_MS = 500
    
    # 日志
    class Log:
        """日志常量"""
        MAX_FILE_SIZE_MB = 10
        MAX_FILE_COUNT = 10
        DEFAULT_LEVEL = "INFO"
```

### 2.7 CHI 仪器常量

```python
class CHI:
    """CHI 仪器常量"""
    
    # DLL 名称
    DLL_NAME = "libec.dll"
    
    # 设备索引
    DEFAULT_DEVICE_INDEX = 0
    
    # 状态码
    class Status:
        """状态码"""
        IDLE = 0
        RUNNING = 1
        PAUSED = 2
        ERROR = -1
    
    # 返回码
    class ReturnCode:
        """返回码"""
        SUCCESS = 0
        ERROR = -1
        NOT_CONNECTED = -2
        INVALID_PARAM = -3
```

---

## 三、使用示例

```python
from echem_sdl.utils.constants import RS485, Pump, EChem, System

# 使用常量
port_config = {
    "baudrate": RS485.BAUDRATE,
    "bytesize": RS485.BYTESIZE,
    "stopbits": RS485.STOPBITS,
}

# 验证参数
if speed < Pump.MIN_SPEED or speed > Pump.MAX_SPEED:
    raise ValueError(f"速度必须在 {Pump.MIN_SPEED}-{Pump.MAX_SPEED} 之间")

# 获取速度时间
time_per_stroke = Pump.SPEED_TIME_MAP[speed]

# 检查电位范围
if potential < EChem.Potential.MIN or potential > EChem.Potential.MAX:
    raise ValueError("电位超出范围")
```

---

## 四、测试要求

### 4.1 单元测试

```python
# tests/test_constants.py

import pytest
from echem_sdl.utils.constants import RS485, Pump, EChem

class TestRS485Constants:
    def test_baudrate(self):
        assert RS485.BAUDRATE == 38400
    
    def test_headers(self):
        assert RS485.HEADER_QUERY == 0xFA
        assert RS485.HEADER_RESPONSE == 0xFB

class TestPumpConstants:
    def test_speed_range(self):
        assert Pump.MIN_SPEED == 1
        assert Pump.MAX_SPEED == 5
    
    def test_speed_time_map(self):
        assert len(Pump.SPEED_TIME_MAP) == 5
        for speed in range(1, 6):
            assert speed in Pump.SPEED_TIME_MAP
    
    def test_syringe_calculation(self):
        ul_per_step = Pump.Syringe.ul_per_step()
        assert ul_per_step == pytest.approx(2500.0 / 24000)

class TestEChemConstants:
    def test_techniques(self):
        assert EChem.Technique.CV == "CV"
        assert EChem.Technique.LSV == "LSV"
    
    def test_potential_range(self):
        assert EChem.Potential.MIN < EChem.Potential.MAX
    
    def test_sensitivity_options(self):
        assert len(EChem.Sensitivity.OPTIONS) > 0
        assert EChem.Sensitivity.DEFAULT in EChem.Sensitivity.OPTIONS
```

---

## 五、验收标准

- [ ] 所有常量正确定义
- [ ] 常量分类清晰
- [ ] 嵌套类结构合理
- [ ] 常量值与硬件规格匹配
- [ ] 提供参数验证辅助
- [ ] 文档注释完整
- [ ] 单元测试通过
