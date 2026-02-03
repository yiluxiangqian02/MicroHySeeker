# 11 - LibContext 模块规范

> **文件路径**: `src/echem_sdl/lib_context.py`  
> **优先级**: P0 (核心模块)  
> **依赖**: 所有硬件和服务模块  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\LIB.cs`

---

## 一、模块职责

LibContext 是全局依赖注入容器，负责：
1. 统一管理所有硬件实例
2. 统一管理所有服务实例
3. 提供全局配置访问
4. 管理组件生命周期（初始化/销毁）
5. 提供简化的组件获取接口

**设计模式**: 服务定位器 + 依赖注入

---

## 二、类设计

### 2.1 主类定义

```python
from typing import Optional, TypeVar, Type, Dict, Any
from pathlib import Path
import threading

T = TypeVar("T")

class LibContext:
    """全局上下文容器
    
    管理所有硬件和服务实例，提供统一的依赖注入。
    
    Attributes:
        config: 系统配置
        rs485: RS485 驱动实例
        pump_manager: 泵管理器
        diluter: 配液器
        flusher: 冲洗器
        chi: CHI 电化学仪器
        positioner: 定位器
        logger: 日志服务
        settings: 设置服务
        translator: 翻译服务
        
    Example:
        >>> ctx = LibContext()
        >>> ctx.initialize(config_path="config.json")
        >>> engine = ExperimentEngine(ctx)
        >>> ctx.cleanup()
    """
```

### 2.2 构造函数

```python
_instance: Optional["LibContext"] = None
_lock = threading.Lock()

def __new__(cls) -> "LibContext":
    """单例模式"""
    with cls._lock:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

def __init__(self) -> None:
    """初始化上下文"""
    if self._initialized:
        return
    
    # 配置
    self._config: Optional["SystemConfig"] = None
    
    # 硬件实例
    self._rs485: Optional["RS485Driver"] = None
    self._pump_manager: Optional["PumpManager"] = None
    self._diluter: Optional["Diluter"] = None
    self._flusher: Optional["Flusher"] = None
    self._chi: Optional["CHInstrument"] = None
    self._positioner: Optional["Positioner"] = None
    
    # 服务实例
    self._logger: Optional["LoggerService"] = None
    self._settings: Optional["SettingsService"] = None
    self._translator: Optional["TranslatorService"] = None
    self._data_exporter: Optional["DataExporter"] = None
    self._kafka_client: Optional["KafkaClient"] = None
    
    # 自定义组件注册表
    self._registry: Dict[str, Any] = {}
    
    self._initialized = True
```

### 2.3 初始化方法

```python
def initialize(
    self,
    config_path: Optional[str | Path] = None,
    config: Optional["SystemConfig"] = None,
    mock_mode: bool = False
) -> bool:
    """初始化所有组件
    
    Args:
        config_path: 配置文件路径
        config: 配置对象（优先于 config_path）
        mock_mode: 是否使用模拟硬件
        
    Returns:
        bool: 初始化是否成功
    """
    try:
        # 1. 加载配置
        if config:
            self._config = config
        elif config_path:
            self._config = SystemConfig.load(config_path)
        else:
            self._config = SystemConfig.default()
        
        # 2. 初始化服务
        self._init_services()
        
        # 3. 初始化硬件
        self._init_hardware(mock_mode)
        
        self._logger.info("LibContext 初始化完成")
        return True
        
    except Exception as e:
        if self._logger:
            self._logger.error(f"初始化失败: {e}")
        return False

def _init_services(self) -> None:
    """初始化服务组件"""
    # 日志服务（优先初始化）
    from echem_sdl.services.logger_service import LoggerService
    self._logger = LoggerService(self._config.log_config)
    
    # 设置服务
    from echem_sdl.services.settings_service import SettingsService
    self._settings = SettingsService(self._config)
    
    # 翻译服务
    from echem_sdl.services.translator_service import TranslatorService
    self._translator = TranslatorService(self._config.language)
    
    # 数据导出服务
    from echem_sdl.services.data_exporter import DataExporter
    self._data_exporter = DataExporter()
    
    # Kafka 客户端（可选）
    if self._config.kafka_enabled:
        from echem_sdl.services.kafka_client import KafkaClient
        self._kafka_client = KafkaClient(self._config.kafka_config)

def _init_hardware(self, mock_mode: bool) -> None:
    """初始化硬件组件"""
    # RS485 驱动
    from echem_sdl.hardware.rs485_driver import RS485Driver, MockRS485Driver
    if mock_mode:
        self._rs485 = MockRS485Driver()
    else:
        self._rs485 = RS485Driver(
            port=self._config.rs485_port,
            baudrate=self._config.rs485_baudrate
        )
    self._rs485.connect()
    
    # 泵管理器
    from echem_sdl.hardware.pump_manager import PumpManager
    self._pump_manager = PumpManager(self._rs485, mock_mode=mock_mode)
    self._pump_manager.configure_from_config(self._config.pump_config)
    
    # 配液器
    from echem_sdl.hardware.diluter import Diluter
    self._diluter = Diluter(self._pump_manager, self._config.dilution_config)
    
    # 冲洗器
    from echem_sdl.hardware.flusher import Flusher
    self._flusher = Flusher(self._pump_manager, self._config.flush_config)
    
    # CHI 仪器
    from echem_sdl.hardware.chi import CHInstrument, MockCHInstrument
    if mock_mode:
        self._chi = MockCHInstrument()
    else:
        self._chi = CHInstrument(self._config.chi_config)
    
    # 定位器（可选）
    if self._config.positioner_enabled:
        from echem_sdl.hardware.positioner import Positioner, MockPositioner
        if mock_mode:
            self._positioner = MockPositioner(self._rs485)
        else:
            self._positioner = Positioner(self._rs485)
```

### 2.4 属性访问

```python
@property
def config(self) -> "SystemConfig":
    """系统配置"""
    if self._config is None:
        raise RuntimeError("LibContext 未初始化")
    return self._config

@property
def rs485(self) -> "RS485Driver":
    """RS485 驱动"""
    return self._rs485

@property
def pump_manager(self) -> "PumpManager":
    """泵管理器"""
    return self._pump_manager

@property
def diluter(self) -> "Diluter":
    """配液器"""
    return self._diluter

@property
def flusher(self) -> "Flusher":
    """冲洗器"""
    return self._flusher

@property
def chi(self) -> Optional["CHInstrument"]:
    """CHI 仪器"""
    return self._chi

@property
def positioner(self) -> Optional["Positioner"]:
    """定位器"""
    return self._positioner

@property
def logger(self) -> "LoggerService":
    """日志服务"""
    return self._logger

@property
def settings(self) -> "SettingsService":
    """设置服务"""
    return self._settings

@property
def translator(self) -> "TranslatorService":
    """翻译服务"""
    return self._translator

@property
def data_exporter(self) -> "DataExporter":
    """数据导出服务"""
    return self._data_exporter

@property
def kafka(self) -> Optional["KafkaClient"]:
    """Kafka 客户端"""
    return self._kafka_client
```

### 2.5 组件注册

```python
def register(self, key: str, instance: Any) -> None:
    """注册自定义组件
    
    Args:
        key: 组件键名
        instance: 组件实例
    """
    self._registry[key] = instance

def get(self, key: str, default: Any = None) -> Any:
    """获取自定义组件
    
    Args:
        key: 组件键名
        default: 默认值
        
    Returns:
        组件实例
    """
    return self._registry.get(key, default)

def get_typed(self, key: str, expected_type: Type[T]) -> Optional[T]:
    """获取类型化的组件
    
    Args:
        key: 组件键名
        expected_type: 期望类型
        
    Returns:
        类型匹配的组件
    """
    instance = self._registry.get(key)
    if instance is not None and isinstance(instance, expected_type):
        return instance
    return None
```

### 2.6 生命周期管理

```python
def cleanup(self) -> None:
    """清理所有组件"""
    self._logger.info("开始清理 LibContext...")
    
    # 停止所有硬件
    if self._pump_manager:
        self._pump_manager.stop_all()
    
    if self._chi:
        self._chi.disconnect()
    
    if self._rs485:
        self._rs485.disconnect()
    
    # 停止服务
    if self._kafka_client:
        self._kafka_client.close()
    
    self._logger.info("LibContext 清理完成")

def reset(self) -> None:
    """重置上下文（用于测试）"""
    self.cleanup()
    self._initialized = False
    LibContext._instance = None

@classmethod
def get_instance(cls) -> "LibContext":
    """获取单例实例"""
    return cls()
```

---

## 三、便捷函数

```python
# 模块级便捷函数

def get_context() -> LibContext:
    """获取全局上下文"""
    return LibContext.get_instance()

def init_context(
    config_path: Optional[str] = None,
    mock_mode: bool = False
) -> LibContext:
    """初始化并返回上下文"""
    ctx = get_context()
    ctx.initialize(config_path=config_path, mock_mode=mock_mode)
    return ctx

# 快捷访问
def get_logger() -> "LoggerService":
    """获取日志服务"""
    return get_context().logger

def get_settings() -> "SettingsService":
    """获取设置服务"""
    return get_context().settings

def tr(key: str, **kwargs) -> str:
    """翻译函数"""
    return get_context().translator.translate(key, **kwargs)
```

---

## 四、系统配置类

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class SystemConfig:
    """系统配置"""
    # RS485
    rs485_port: str = "COM3"
    rs485_baudrate: int = 38400
    
    # 泵配置
    pump_config: "PumpConfig" = field(default_factory=lambda: PumpConfig())
    
    # 配液配置
    dilution_config: "DilutionConfig" = field(default_factory=lambda: DilutionConfig())
    
    # 冲洗配置
    flush_config: "FlushConfig" = field(default_factory=lambda: FlushConfig())
    
    # CHI 配置
    chi_config: "CHIConfig" = field(default_factory=lambda: CHIConfig())
    
    # 可选功能
    positioner_enabled: bool = False
    kafka_enabled: bool = False
    kafka_config: Optional["KafkaConfig"] = None
    
    # 日志配置
    log_config: "LogConfig" = field(default_factory=lambda: LogConfig())
    
    # 语言
    language: str = "zh"
    
    @classmethod
    def default(cls) -> "SystemConfig":
        """默认配置"""
        return cls()
    
    @classmethod
    def load(cls, path: str | Path) -> "SystemConfig":
        """从文件加载"""
        import json
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
    
    def save(self, path: str | Path) -> None:
        """保存到文件"""
        import json
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
```

---

## 五、测试要求

### 5.1 单元测试

```python
# tests/test_lib_context.py

import pytest
from echem_sdl.lib_context import LibContext, get_context, init_context

class TestLibContext:
    def teardown_method(self):
        """每个测试后重置"""
        LibContext._instance = None
    
    def test_singleton(self):
        """测试单例模式"""
        ctx1 = LibContext()
        ctx2 = LibContext()
        assert ctx1 is ctx2
    
    def test_get_instance(self):
        """测试获取实例"""
        ctx = LibContext.get_instance()
        assert ctx is not None
    
    def test_initialize_mock_mode(self):
        """测试模拟模式初始化"""
        ctx = init_context(mock_mode=True)
        assert ctx.rs485 is not None
        assert ctx.pump_manager is not None
        assert ctx.logger is not None
    
    def test_property_access_before_init(self):
        """测试未初始化时访问属性"""
        ctx = LibContext()
        with pytest.raises(RuntimeError):
            _ = ctx.config
    
    def test_register_custom_component(self):
        """测试注册自定义组件"""
        ctx = init_context(mock_mode=True)
        ctx.register("custom_service", {"test": 123})
        
        result = ctx.get("custom_service")
        assert result["test"] == 123
    
    def test_cleanup(self):
        """测试清理"""
        ctx = init_context(mock_mode=True)
        ctx.cleanup()
        # 清理后应该能正常完成，不抛异常

class TestConvenienceFunctions:
    def teardown_method(self):
        LibContext._instance = None
    
    def test_get_context(self):
        """测试 get_context"""
        ctx = get_context()
        assert isinstance(ctx, LibContext)
    
    def test_init_context(self):
        """测试 init_context"""
        ctx = init_context(mock_mode=True)
        assert ctx.logger is not None
```

---

## 六、使用示例

### 6.1 基本使用

```python
from echem_sdl.lib_context import init_context, get_context

# 初始化（通常在 main 中调用一次）
ctx = init_context(config_path="config.json", mock_mode=False)

# 后续在任何地方获取
ctx = get_context()
ctx.logger.info("开始实验")

# 使用硬件
ctx.pump_manager.get_pump(1).set_speed(3)

# 清理（程序退出时）
ctx.cleanup()
```

### 6.2 测试中使用

```python
import pytest
from echem_sdl.lib_context import LibContext, init_context

@pytest.fixture
def mock_context():
    """提供模拟上下文"""
    ctx = init_context(mock_mode=True)
    yield ctx
    ctx.reset()

def test_experiment(mock_context):
    ctx = mock_context
    assert ctx.pump_manager is not None
```

---

## 七、验收标准

- [ ] 单例模式正确实现
- [ ] 初始化所有硬件组件
- [ ] 初始化所有服务组件
- [ ] 模拟模式正常工作
- [ ] 属性访问正确
- [ ] 自定义组件注册正确
- [ ] cleanup() 正确释放资源
- [ ] reset() 用于测试重置
- [ ] 线程安全
- [ ] 配置加载正确
- [ ] 便捷函数可用
- [ ] 单元测试通过
