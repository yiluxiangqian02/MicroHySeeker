# 18 - Errors 模块规范

> **文件路径**: `src/echem_sdl/utils/errors.py`  
> **优先级**: P0 (基础模块)  
> **依赖**: 无  
> **原C#参考**: 分散在各文件中

---

## 一、模块职责

Errors 是异常定义模块，负责：
1. 定义统一的异常层次结构
2. 提供详细的错误信息
3. 支持错误码
4. 提供异常工具函数

---

## 二、异常层次结构

```
ECException (基类)
├── ConfigError (配置错误)
├── HardwareError (硬件错误)
│   ├── RS485Error
│   │   ├── ConnectionError
│   │   ├── TimeoutError
│   │   └── ProtocolError
│   ├── PumpError
│   │   ├── PumpNotFoundError
│   │   ├── PumpBusyError
│   │   └── PumpCommandError
│   ├── CHIError
│   │   ├── CHIDLLError
│   │   ├── CHIConnectionError
│   │   └── CHIExecutionError
│   └── PositionerError
├── EngineError (引擎错误)
│   ├── ProgramError
│   ├── StepExecutionError
│   └── StateError
└── ServiceError (服务错误)
    ├── ExportError
    └── KafkaError
```

---

## 三、异常定义

### 3.1 基类

```python
from typing import Optional, Dict, Any

class ECException(Exception):
    """eChemSDL 异常基类
    
    所有自定义异常的基类，提供统一的错误信息结构。
    
    Attributes:
        message: 错误消息
        code: 错误码
        details: 详细信息字典
        cause: 原始异常
    """
    
    default_code: str = "EC_ERROR"
    default_message: str = "发生错误"
    
    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ) -> None:
        """初始化异常
        
        Args:
            message: 错误消息
            code: 错误码
            details: 详细信息
            cause: 原始异常
        """
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details or {}
        self.cause = cause
        
        super().__init__(self.message)
    
    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.details:
            parts.append(f"详情: {self.details}")
        if self.cause:
            parts.append(f"原因: {self.cause}")
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }
```

### 3.2 配置错误

```python
class ConfigError(ECException):
    """配置错误"""
    default_code = "CONFIG_ERROR"
    default_message = "配置错误"

class ConfigNotFoundError(ConfigError):
    """配置文件未找到"""
    default_code = "CONFIG_NOT_FOUND"
    default_message = "配置文件未找到"

class ConfigInvalidError(ConfigError):
    """配置无效"""
    default_code = "CONFIG_INVALID"
    default_message = "配置格式无效"
```

### 3.3 硬件错误

```python
class HardwareError(ECException):
    """硬件错误基类"""
    default_code = "HARDWARE_ERROR"
    default_message = "硬件错误"

# RS485 错误
class RS485Error(HardwareError):
    """RS485 通讯错误"""
    default_code = "RS485_ERROR"
    default_message = "RS485 通讯错误"

class RS485ConnectionError(RS485Error):
    """RS485 连接错误"""
    default_code = "RS485_CONNECTION_ERROR"
    default_message = "RS485 连接失败"

class RS485TimeoutError(RS485Error):
    """RS485 超时错误"""
    default_code = "RS485_TIMEOUT"
    default_message = "RS485 通讯超时"

class RS485ProtocolError(RS485Error):
    """RS485 协议错误"""
    default_code = "RS485_PROTOCOL_ERROR"
    default_message = "RS485 协议错误"

# 泵错误
class PumpError(HardwareError):
    """泵错误"""
    default_code = "PUMP_ERROR"
    default_message = "泵操作错误"

class PumpNotFoundError(PumpError):
    """泵未找到"""
    default_code = "PUMP_NOT_FOUND"
    default_message = "未找到指定泵"

class PumpBusyError(PumpError):
    """泵忙"""
    default_code = "PUMP_BUSY"
    default_message = "泵正在执行操作"

class PumpCommandError(PumpError):
    """泵命令错误"""
    default_code = "PUMP_COMMAND_ERROR"
    default_message = "泵命令执行失败"

class PumpInitError(PumpError):
    """泵初始化错误"""
    default_code = "PUMP_INIT_ERROR"
    default_message = "泵初始化失败"

# CHI 错误
class CHIError(HardwareError):
    """CHI 仪器错误"""
    default_code = "CHI_ERROR"
    default_message = "CHI 仪器错误"

class CHIDLLError(CHIError):
    """CHI DLL 错误"""
    default_code = "CHI_DLL_ERROR"
    default_message = "CHI DLL 加载或调用失败"

class CHIConnectionError(CHIError):
    """CHI 连接错误"""
    default_code = "CHI_CONNECTION_ERROR"
    default_message = "CHI 仪器连接失败"

class CHIExecutionError(CHIError):
    """CHI 执行错误"""
    default_code = "CHI_EXECUTION_ERROR"
    default_message = "CHI 实验执行错误"

# 定位器错误
class PositionerError(HardwareError):
    """定位器错误"""
    default_code = "POSITIONER_ERROR"
    default_message = "定位器错误"

class PositionerNotHomedError(PositionerError):
    """定位器未回零"""
    default_code = "POSITIONER_NOT_HOMED"
    default_message = "定位器未回零"
```

### 3.4 引擎错误

```python
class EngineError(ECException):
    """引擎错误基类"""
    default_code = "ENGINE_ERROR"
    default_message = "实验引擎错误"

class ProgramError(EngineError):
    """程序错误"""
    default_code = "PROGRAM_ERROR"
    default_message = "实验程序错误"

class ProgramInvalidError(ProgramError):
    """程序无效"""
    default_code = "PROGRAM_INVALID"
    default_message = "实验程序无效"

class ProgramNotLoadedError(ProgramError):
    """程序未加载"""
    default_code = "PROGRAM_NOT_LOADED"
    default_message = "未加载实验程序"

class StepExecutionError(EngineError):
    """步骤执行错误"""
    default_code = "STEP_EXECUTION_ERROR"
    default_message = "步骤执行失败"

class StateError(EngineError):
    """状态错误"""
    default_code = "STATE_ERROR"
    default_message = "引擎状态错误"

class AlreadyRunningError(StateError):
    """已在运行"""
    default_code = "ALREADY_RUNNING"
    default_message = "实验已在运行中"

class NotRunningError(StateError):
    """未运行"""
    default_code = "NOT_RUNNING"
    default_message = "实验未在运行"
```

### 3.5 服务错误

```python
class ServiceError(ECException):
    """服务错误基类"""
    default_code = "SERVICE_ERROR"
    default_message = "服务错误"

class ExportError(ServiceError):
    """导出错误"""
    default_code = "EXPORT_ERROR"
    default_message = "数据导出失败"

class KafkaError(ServiceError):
    """Kafka 错误"""
    default_code = "KAFKA_ERROR"
    default_message = "Kafka 通讯错误"

class TranslationError(ServiceError):
    """翻译错误"""
    default_code = "TRANSLATION_ERROR"
    default_message = "翻译服务错误"
```

---

## 四、工具函数

```python
from typing import Type, Callable
from functools import wraps

def wrap_exception(
    exception_class: Type[ECException],
    message: str = None
) -> Callable:
    """异常包装装饰器
    
    将标准异常转换为自定义异常。
    
    Example:
        >>> @wrap_exception(PumpError, "泵操作失败")
        ... def pump_operation():
        ...     ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ECException:
                raise  # 已经是自定义异常
            except Exception as e:
                raise exception_class(
                    message=message or str(e),
                    cause=e
                ) from e
        return wrapper
    return decorator

def safe_call(
    func: Callable,
    *args,
    default = None,
    log_error: bool = True,
    **kwargs
):
    """安全调用函数
    
    捕获异常并返回默认值。
    
    Example:
        >>> result = safe_call(risky_function, default=0)
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            print(f"调用 {func.__name__} 失败: {e}")
        return default

def raise_if(
    condition: bool,
    exception_class: Type[ECException],
    message: str = None,
    **details
) -> None:
    """条件抛出异常
    
    Example:
        >>> raise_if(value < 0, ValueError, "值不能为负", value=value)
    """
    if condition:
        raise exception_class(message=message, details=details)

def assert_not_none(
    value,
    name: str,
    exception_class: Type[ECException] = ConfigError
) -> None:
    """断言不为 None
    
    Example:
        >>> assert_not_none(config, "config")
    """
    if value is None:
        raise exception_class(
            message=f"{name} 不能为空",
            details={"field": name}
        )
```

---

## 五、错误码表

| 错误码 | 说明 |
|--------|------|
| `EC_ERROR` | 通用错误 |
| `CONFIG_ERROR` | 配置错误 |
| `CONFIG_NOT_FOUND` | 配置文件未找到 |
| `CONFIG_INVALID` | 配置无效 |
| `HARDWARE_ERROR` | 硬件错误 |
| `RS485_ERROR` | RS485 错误 |
| `RS485_CONNECTION_ERROR` | RS485 连接失败 |
| `RS485_TIMEOUT` | RS485 超时 |
| `RS485_PROTOCOL_ERROR` | RS485 协议错误 |
| `PUMP_ERROR` | 泵错误 |
| `PUMP_NOT_FOUND` | 泵未找到 |
| `PUMP_BUSY` | 泵忙 |
| `PUMP_COMMAND_ERROR` | 泵命令失败 |
| `PUMP_INIT_ERROR` | 泵初始化失败 |
| `CHI_ERROR` | CHI 错误 |
| `CHI_DLL_ERROR` | CHI DLL 错误 |
| `CHI_CONNECTION_ERROR` | CHI 连接失败 |
| `CHI_EXECUTION_ERROR` | CHI 执行错误 |
| `POSITIONER_ERROR` | 定位器错误 |
| `POSITIONER_NOT_HOMED` | 定位器未回零 |
| `ENGINE_ERROR` | 引擎错误 |
| `PROGRAM_ERROR` | 程序错误 |
| `PROGRAM_INVALID` | 程序无效 |
| `PROGRAM_NOT_LOADED` | 程序未加载 |
| `STEP_EXECUTION_ERROR` | 步骤执行失败 |
| `STATE_ERROR` | 状态错误 |
| `ALREADY_RUNNING` | 已在运行 |
| `NOT_RUNNING` | 未运行 |
| `SERVICE_ERROR` | 服务错误 |
| `EXPORT_ERROR` | 导出失败 |
| `KAFKA_ERROR` | Kafka 错误 |

---

## 六、测试要求

### 6.1 单元测试

```python
# tests/test_errors.py

import pytest
from echem_sdl.utils.errors import (
    ECException, RS485Error, RS485TimeoutError,
    PumpError, PumpNotFoundError,
    wrap_exception, safe_call, raise_if
)

class TestECException:
    def test_basic_exception(self):
        """测试基本异常"""
        exc = ECException("测试错误")
        assert exc.message == "测试错误"
        assert exc.code == "EC_ERROR"
    
    def test_exception_with_details(self):
        """测试带详情的异常"""
        exc = ECException(
            "操作失败",
            code="TEST_ERROR",
            details={"key": "value"}
        )
        assert exc.details["key"] == "value"
    
    def test_exception_with_cause(self):
        """测试带原因的异常"""
        cause = ValueError("原始错误")
        exc = ECException("包装错误", cause=cause)
        assert exc.cause == cause
    
    def test_to_dict(self):
        """测试转字典"""
        exc = ECException("错误", details={"x": 1})
        d = exc.to_dict()
        assert d["message"] == "错误"
        assert d["details"]["x"] == 1

class TestSpecificExceptions:
    def test_rs485_timeout(self):
        """测试 RS485 超时异常"""
        exc = RS485TimeoutError("超时")
        assert exc.code == "RS485_TIMEOUT"
        assert isinstance(exc, RS485Error)
    
    def test_pump_not_found(self):
        """测试泵未找到异常"""
        exc = PumpNotFoundError(details={"address": 5})
        assert exc.details["address"] == 5

class TestUtilityFunctions:
    def test_wrap_exception(self):
        """测试异常包装"""
        @wrap_exception(PumpError, "操作失败")
        def failing_func():
            raise ValueError("原始错误")
        
        with pytest.raises(PumpError) as exc_info:
            failing_func()
        
        assert exc_info.value.cause is not None
    
    def test_safe_call(self):
        """测试安全调用"""
        def failing_func():
            raise ValueError("错误")
        
        result = safe_call(failing_func, default="默认值", log_error=False)
        assert result == "默认值"
    
    def test_raise_if(self):
        """测试条件抛出"""
        with pytest.raises(PumpError):
            raise_if(True, PumpError, "条件满足")
        
        # 条件不满足时不抛出
        raise_if(False, PumpError, "不会抛出")
```

---

## 七、使用示例

### 7.1 基本使用

```python
from echem_sdl.utils.errors import PumpError, PumpNotFoundError, raise_if

def get_pump(address: int):
    pump = pumps.get(address)
    if pump is None:
        raise PumpNotFoundError(
            message=f"未找到地址 {address} 的泵",
            details={"address": address}
        )
    return pump

# 使用 raise_if
def set_speed(speed: int):
    raise_if(speed < 1 or speed > 5, PumpError, "速度超出范围", speed=speed)
    # ...
```

### 7.2 异常处理

```python
try:
    pump = get_pump(5)
    pump.aspirate(100)
except PumpNotFoundError as e:
    logger.error(f"泵未找到: {e.details}")
except PumpError as e:
    logger.error(f"泵错误: {e}")
except ECException as e:
    logger.error(f"操作失败: {e.to_dict()}")
```

---

## 八、验收标准

- [ ] 异常层次结构完整
- [ ] 所有异常类正确继承
- [ ] 错误码唯一且有意义
- [ ] to_dict() 正确序列化
- [ ] wrap_exception 正确包装
- [ ] safe_call 正确处理异常
- [ ] raise_if 正确条件抛出
- [ ] 单元测试覆盖率 > 90%
- [ ] 文档注释完整
