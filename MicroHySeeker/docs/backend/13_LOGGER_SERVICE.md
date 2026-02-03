# 13 - LoggerService 模块规范

> **文件路径**: `src/echem_sdl/services/logger_service.py`  
> **优先级**: P0 (核心模块)  
> **依赖**: 无  
> **原C#参考**: 无（Python 特有）

---

## 一、模块职责

LoggerService 是统一日志服务，负责：
1. 提供分级日志记录（DEBUG/INFO/WARNING/ERROR）
2. 输出到文件和控制台
3. 日志文件轮转
4. 结构化日志支持
5. 发出日志事件供 UI 订阅

---

## 二、日志级别

```python
from enum import IntEnum

class LogLevel(IntEnum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
```

---

## 三、类设计

### 3.1 日志配置

```python
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class LogConfig:
    """日志配置"""
    # 日志级别
    level: str = "INFO"
    # 日志目录
    log_dir: str = "logs"
    # 日志文件名格式
    filename_format: str = "app_{date}.log"
    # 最大文件大小 (MB)
    max_size_mb: int = 10
    # 最大文件数
    max_files: int = 10
    # 控制台输出
    console_output: bool = True
    # 日志格式
    format: str = "{time} [{level}] {message}"
    # 包含调用位置
    include_location: bool = False
```

### 3.2 日志条目

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    message: str
    module: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def format(self, fmt: str) -> str:
        """格式化日志"""
        return fmt.format(
            time=self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            level=self.level.name,
            message=self.message,
            module=self.module,
            **self.extra
        )
```

### 3.3 主类定义

```python
from typing import Callable, List
import threading
import logging
from logging.handlers import RotatingFileHandler

class LoggerService:
    """统一日志服务
    
    提供结构化日志记录和事件订阅。
    
    Attributes:
        level: 当前日志级别
        
    Example:
        >>> logger = LoggerService(LogConfig())
        >>> logger.info("程序启动")
        >>> logger.error("发生错误", error=e)
    """
```

### 3.4 构造函数

```python
def __init__(self, config: Optional[LogConfig] = None) -> None:
    """初始化日志服务
    
    Args:
        config: 日志配置
    """
    self._config = config or LogConfig()
    self._level = LogLevel[self._config.level.upper()]
    self._listeners: List[Callable[[LogEntry], None]] = []
    self._lock = threading.Lock()
    
    # 创建日志目录
    self._log_dir = Path(self._config.log_dir)
    self._log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置 Python logging
    self._setup_logging()

def _setup_logging(self) -> None:
    """配置 logging 模块"""
    self._logger = logging.getLogger("echem_sdl")
    self._logger.setLevel(self._level)
    self._logger.handlers.clear()
    
    # 文件处理器（轮转）
    log_file = self._log_dir / self._config.filename_format.format(
        date=datetime.now().strftime("%Y%m%d")
    )
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=self._config.max_size_mb * 1024 * 1024,
        backupCount=self._config.max_files,
        encoding="utf-8"
    )
    file_handler.setLevel(self._level)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))
    self._logger.addHandler(file_handler)
    
    # 控制台处理器
    if self._config.console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._level)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        self._logger.addHandler(console_handler)
```

### 3.5 日志方法

```python
def debug(self, message: str, **kwargs) -> None:
    """调试日志"""
    self._log(LogLevel.DEBUG, message, **kwargs)

def info(self, message: str, **kwargs) -> None:
    """信息日志"""
    self._log(LogLevel.INFO, message, **kwargs)

def warning(self, message: str, **kwargs) -> None:
    """警告日志"""
    self._log(LogLevel.WARNING, message, **kwargs)

def error(self, message: str, **kwargs) -> None:
    """错误日志"""
    self._log(LogLevel.ERROR, message, **kwargs)

def critical(self, message: str, **kwargs) -> None:
    """严重错误日志"""
    self._log(LogLevel.CRITICAL, message, **kwargs)

def exception(self, message: str, exc: Exception = None, **kwargs) -> None:
    """异常日志（包含堆栈）"""
    import traceback
    
    if exc:
        kwargs["exception"] = str(exc)
        kwargs["traceback"] = traceback.format_exc()
    
    self._log(LogLevel.ERROR, message, **kwargs)

def _log(self, level: LogLevel, message: str, **kwargs) -> None:
    """内部日志方法"""
    if level < self._level:
        return
    
    entry = LogEntry(
        timestamp=datetime.now(),
        level=level,
        message=message,
        module=kwargs.pop("module", ""),
        extra=kwargs
    )
    
    # 写入标准日志
    log_message = message
    if kwargs:
        extra_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
        log_message = f"{message} | {extra_str}"
    
    self._logger.log(level, log_message)
    
    # 通知监听器
    self._notify_listeners(entry)
```

### 3.6 事件订阅

```python
def on_log(self, callback: Callable[[LogEntry], None]) -> None:
    """订阅日志事件
    
    Args:
        callback: 回调函数，接收 LogEntry
    """
    with self._lock:
        self._listeners.append(callback)

def off_log(self, callback: Callable[[LogEntry], None]) -> None:
    """取消订阅"""
    with self._lock:
        if callback in self._listeners:
            self._listeners.remove(callback)

def _notify_listeners(self, entry: LogEntry) -> None:
    """通知所有监听器"""
    with self._lock:
        listeners = list(self._listeners)
    
    for listener in listeners:
        try:
            listener(entry)
        except Exception:
            pass  # 忽略监听器错误
```

### 3.7 辅助方法

```python
def set_level(self, level: str | LogLevel) -> None:
    """设置日志级别
    
    Args:
        level: 级别名称或枚举
    """
    if isinstance(level, str):
        level = LogLevel[level.upper()]
    
    self._level = level
    self._logger.setLevel(level)
    for handler in self._logger.handlers:
        handler.setLevel(level)

@property
def level(self) -> LogLevel:
    """当前日志级别"""
    return self._level

def get_log_files(self) -> List[Path]:
    """获取所有日志文件"""
    return list(self._log_dir.glob("*.log"))

def clear_old_logs(self, keep_days: int = 7) -> int:
    """清理旧日志文件
    
    Args:
        keep_days: 保留天数
        
    Returns:
        删除的文件数
    """
    import time
    
    cutoff = time.time() - keep_days * 86400
    deleted = 0
    
    for log_file in self.get_log_files():
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()
            deleted += 1
    
    return deleted
```

### 3.8 上下文管理器

```python
from contextlib import contextmanager

@contextmanager
def timed_operation(self, name: str):
    """计时操作上下文
    
    Example:
        >>> with logger.timed_operation("数据处理"):
        ...     process_data()
    """
    import time
    start = time.perf_counter()
    self.debug(f"开始: {name}")
    
    try:
        yield
        elapsed = time.perf_counter() - start
        self.info(f"完成: {name}", elapsed_ms=round(elapsed * 1000, 2))
    except Exception as e:
        elapsed = time.perf_counter() - start
        self.error(f"失败: {name}", elapsed_ms=round(elapsed * 1000, 2), error=str(e))
        raise
```

---

## 四、子日志器

```python
class SubLogger:
    """子日志器（带模块前缀）"""
    
    def __init__(self, parent: LoggerService, module: str):
        self._parent = parent
        self._module = module
    
    def debug(self, message: str, **kwargs) -> None:
        self._parent.debug(message, module=self._module, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self._parent.info(message, module=self._module, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self._parent.warning(message, module=self._module, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        self._parent.error(message, module=self._module, **kwargs)

# LoggerService 方法
def get_logger(self, module: str) -> SubLogger:
    """获取模块子日志器
    
    Args:
        module: 模块名称
        
    Returns:
        SubLogger 实例
    """
    return SubLogger(self, module)
```

---

## 五、测试要求

### 5.1 单元测试

```python
# tests/test_logger_service.py

import pytest
import tempfile
from pathlib import Path
from echem_sdl.services.logger_service import LoggerService, LogConfig, LogLevel

class TestLoggerService:
    @pytest.fixture
    def temp_log_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)
    
    @pytest.fixture
    def logger(self, temp_log_dir):
        config = LogConfig(
            log_dir=str(temp_log_dir),
            level="DEBUG",
            console_output=False
        )
        return LoggerService(config)
    
    def test_log_levels(self, logger):
        """测试日志级别"""
        logs = []
        logger.on_log(lambda e: logs.append(e))
        
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        
        assert len(logs) == 4
        assert logs[0].level == LogLevel.DEBUG
        assert logs[3].level == LogLevel.ERROR
    
    def test_level_filtering(self, logger):
        """测试级别过滤"""
        logs = []
        logger.on_log(lambda e: logs.append(e))
        
        logger.set_level("WARNING")
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        
        assert len(logs) == 1
        assert logs[0].level == LogLevel.WARNING
    
    def test_extra_data(self, logger):
        """测试额外数据"""
        logs = []
        logger.on_log(lambda e: logs.append(e))
        
        logger.info("message", key1="value1", key2=123)
        
        assert logs[0].extra["key1"] == "value1"
        assert logs[0].extra["key2"] == 123
    
    def test_file_output(self, logger, temp_log_dir):
        """测试文件输出"""
        logger.info("test message")
        
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) >= 1
        
        content = log_files[0].read_text(encoding="utf-8")
        assert "test message" in content

class TestSubLogger:
    def test_sub_logger(self, logger):
        """测试子日志器"""
        logs = []
        logger.on_log(lambda e: logs.append(e))
        
        sub = logger.get_logger("MyModule")
        sub.info("message from module")
        
        assert logs[0].module == "MyModule"

class TestTimedOperation:
    def test_timed_success(self, logger):
        """测试计时成功"""
        logs = []
        logger.on_log(lambda e: logs.append(e))
        
        with logger.timed_operation("test"):
            pass
        
        assert len(logs) == 2
        assert "开始" in logs[0].message
        assert "完成" in logs[1].message
    
    def test_timed_failure(self, logger):
        """测试计时失败"""
        logs = []
        logger.on_log(lambda e: logs.append(e))
        
        with pytest.raises(ValueError):
            with logger.timed_operation("test"):
                raise ValueError("error")
        
        assert "失败" in logs[1].message
```

---

## 六、使用示例

### 6.1 基本使用

```python
from echem_sdl.services.logger_service import LoggerService, LogConfig

# 创建日志服务
logger = LoggerService(LogConfig(
    level="INFO",
    log_dir="logs",
    console_output=True
))

# 记录日志
logger.info("程序启动")
logger.warning("配置缺失", key="api_key")
logger.error("连接失败", host="192.168.1.1", port=8080)

# 计时操作
with logger.timed_operation("数据处理"):
    process_data()

# 模块日志
pump_logger = logger.get_logger("Pump")
pump_logger.info("泵启动")
```

### 6.2 UI 订阅

```python
def on_log_entry(entry):
    """日志条目回调"""
    text = f"[{entry.level.name}] {entry.message}"
    log_viewer.append_log(text, level=entry.level)

logger.on_log(on_log_entry)
```

---

## 七、验收标准

- [ ] 所有日志级别正确工作
- [ ] 级别过滤正确
- [ ] 文件输出正确
- [ ] 文件轮转正确
- [ ] 控制台输出正确
- [ ] 事件订阅正确
- [ ] 额外数据支持
- [ ] 子日志器正确
- [ ] 计时上下文正确
- [ ] 清理旧日志正确
- [ ] 线程安全
- [ ] 单元测试通过
