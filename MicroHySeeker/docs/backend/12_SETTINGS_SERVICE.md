# 12 - SettingsService 模块规范

> **文件路径**: `src/echem_sdl/services/settings_service.py`  
> **优先级**: P0 (核心模块)  
> **依赖**: 无  
> **原C#参考**: `D:\AI4S\eChemSDL\eChemSDL\Settings.cs`

---

## 一、模块职责

SettingsService 是配置管理服务，负责：
1. 管理运行时配置参数
2. 提供类型安全的配置访问
3. 配置持久化（保存/加载）
4. 配置变更通知
5. 默认值管理

---

## 二、配置结构

### 2.1 配置分类

| 分类 | 前缀 | 说明 |
|------|------|------|
| 通用 | `general.*` | 语言、主题等 |
| RS485 | `rs485.*` | 串口配置 |
| 泵 | `pump.*` | 泵参数 |
| CHI | `chi.*` | 电化学仪器 |
| 冲洗 | `flush.*` | 冲洗参数 |
| 日志 | `log.*` | 日志配置 |
| 路径 | `path.*` | 文件路径 |

### 2.2 默认配置

```python
DEFAULT_SETTINGS = {
    # 通用
    "general.language": "zh",
    "general.theme": "light",
    "general.auto_save": True,
    "general.auto_save_interval": 60,
    
    # RS485
    "rs485.port": "COM3",
    "rs485.baudrate": 38400,
    "rs485.timeout": 1.0,
    "rs485.retry_count": 3,
    
    # 泵
    "pump.default_speed": 3,
    "pump.max_volume_ul": 2500.0,
    "pump.syringe_type": "Hamilton",
    
    # CHI
    "chi.dll_path": "libec.dll",
    "chi.default_sensitivity": 1e-5,
    
    # 冲洗
    "flush.default_cycles": 3,
    "flush.volume_ul": 500.0,
    
    # 日志
    "log.level": "INFO",
    "log.max_files": 10,
    "log.max_size_mb": 10,
    
    # 路径
    "path.data_dir": "data",
    "path.log_dir": "logs",
    "path.config_file": "config.json",
    "path.program_dir": "programs",
}
```

---

## 三、类设计

### 3.1 主类定义

```python
from typing import Any, Optional, Dict, Callable, List, TypeVar
from pathlib import Path
import json
import threading

T = TypeVar("T")

class SettingsService:
    """配置管理服务
    
    提供类型安全的配置访问和持久化。
    
    Attributes:
        config_path: 配置文件路径
        
    Example:
        >>> settings = SettingsService("config.json")
        >>> port = settings.get_str("rs485.port")
        >>> settings.set("rs485.port", "COM4")
        >>> settings.save()
    """
```

### 3.2 构造函数

```python
def __init__(
    self,
    config_path: Optional[str | Path] = None,
    auto_save: bool = True
) -> None:
    """初始化配置服务
    
    Args:
        config_path: 配置文件路径（None 则使用默认）
        auto_save: 是否自动保存更改
    """
    self._config_path = Path(config_path) if config_path else Path("config.json")
    self._auto_save = auto_save
    self._data: Dict[str, Any] = dict(DEFAULT_SETTINGS)
    self._listeners: Dict[str, List[Callable]] = {}
    self._lock = threading.RLock()
    
    # 尝试加载已有配置
    if self._config_path.exists():
        self.load()
```

### 3.3 获取配置

```python
def get(self, key: str, default: Any = None) -> Any:
    """获取配置值
    
    Args:
        key: 配置键
        default: 默认值
        
    Returns:
        配置值
    """
    with self._lock:
        return self._data.get(key, default)

def get_str(self, key: str, default: str = "") -> str:
    """获取字符串配置"""
    value = self.get(key, default)
    return str(value) if value is not None else default

def get_int(self, key: str, default: int = 0) -> int:
    """获取整数配置"""
    value = self.get(key, default)
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def get_float(self, key: str, default: float = 0.0) -> float:
    """获取浮点数配置"""
    value = self.get(key, default)
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_bool(self, key: str, default: bool = False) -> bool:
    """获取布尔配置"""
    value = self.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)

def get_list(self, key: str, default: List = None) -> List:
    """获取列表配置"""
    value = self.get(key, default or [])
    return value if isinstance(value, list) else (default or [])

def get_dict(self, key: str, default: Dict = None) -> Dict:
    """获取字典配置"""
    value = self.get(key, default or {})
    return value if isinstance(value, dict) else (default or {})

def get_path(self, key: str, default: str = "") -> Path:
    """获取路径配置"""
    return Path(self.get_str(key, default))
```

### 3.4 设置配置

```python
def set(self, key: str, value: Any) -> None:
    """设置配置值
    
    Args:
        key: 配置键
        value: 配置值
    """
    with self._lock:
        old_value = self._data.get(key)
        self._data[key] = value
        
        # 触发变更通知
        if old_value != value:
            self._notify_listeners(key, value, old_value)
        
        # 自动保存
        if self._auto_save:
            self.save()

def set_many(self, settings: Dict[str, Any]) -> None:
    """批量设置配置
    
    Args:
        settings: 配置字典
    """
    with self._lock:
        for key, value in settings.items():
            old_value = self._data.get(key)
            self._data[key] = value
            if old_value != value:
                self._notify_listeners(key, value, old_value)
        
        if self._auto_save:
            self.save()

def remove(self, key: str) -> None:
    """移除配置项"""
    with self._lock:
        if key in self._data:
            del self._data[key]
            if self._auto_save:
                self.save()
```

### 3.5 持久化

```python
def save(self, path: Optional[str | Path] = None) -> bool:
    """保存配置到文件
    
    Args:
        path: 保存路径（None 则使用默认）
        
    Returns:
        是否成功
    """
    save_path = Path(path) if path else self._config_path
    
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            json_str = json.dumps(self._data, indent=2, ensure_ascii=False)
        save_path.write_text(json_str, encoding="utf-8")
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False

def load(self, path: Optional[str | Path] = None) -> bool:
    """从文件加载配置
    
    Args:
        path: 加载路径（None 则使用默认）
        
    Returns:
        是否成功
    """
    load_path = Path(path) if path else self._config_path
    
    if not load_path.exists():
        return False
    
    try:
        json_str = load_path.read_text(encoding="utf-8")
        loaded_data = json.loads(json_str)
        
        with self._lock:
            # 合并到默认配置（保留默认值）
            self._data = dict(DEFAULT_SETTINGS)
            self._data.update(loaded_data)
        
        return True
    except Exception as e:
        print(f"加载配置失败: {e}")
        return False

def reset(self) -> None:
    """重置为默认配置"""
    with self._lock:
        self._data = dict(DEFAULT_SETTINGS)
        if self._auto_save:
            self.save()
```

### 3.6 变更监听

```python
def on_change(
    self,
    key: str,
    callback: Callable[[Any, Any], None]
) -> None:
    """监听配置变更
    
    Args:
        key: 配置键（支持通配符 "*"）
        callback: 回调函数 (new_value, old_value)
    """
    with self._lock:
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)

def off_change(
    self,
    key: str,
    callback: Optional[Callable] = None
) -> None:
    """取消监听
    
    Args:
        key: 配置键
        callback: 回调函数（None 则移除所有）
    """
    with self._lock:
        if key not in self._listeners:
            return
        
        if callback is None:
            del self._listeners[key]
        else:
            self._listeners[key] = [
                cb for cb in self._listeners[key] if cb != callback
            ]

def _notify_listeners(self, key: str, new_value: Any, old_value: Any) -> None:
    """通知监听器"""
    # 精确匹配
    for callback in self._listeners.get(key, []):
        try:
            callback(new_value, old_value)
        except Exception as e:
            print(f"配置变更回调错误: {e}")
    
    # 通配符匹配
    for pattern, callbacks in self._listeners.items():
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if key.startswith(prefix + "."):
                for callback in callbacks:
                    try:
                        callback(new_value, old_value)
                    except Exception as e:
                        print(f"配置变更回调错误: {e}")
```

### 3.7 分组访问

```python
def get_group(self, prefix: str) -> Dict[str, Any]:
    """获取配置分组
    
    Args:
        prefix: 前缀（如 "rs485"）
        
    Returns:
        该前缀下的所有配置
    """
    prefix_with_dot = prefix + "."
    with self._lock:
        return {
            k[len(prefix_with_dot):]: v
            for k, v in self._data.items()
            if k.startswith(prefix_with_dot)
        }

def set_group(self, prefix: str, values: Dict[str, Any]) -> None:
    """设置配置分组
    
    Args:
        prefix: 前缀
        values: 配置字典
    """
    settings = {
        f"{prefix}.{k}": v for k, v in values.items()
    }
    self.set_many(settings)

def keys(self) -> List[str]:
    """获取所有配置键"""
    with self._lock:
        return list(self._data.keys())

def has(self, key: str) -> bool:
    """检查配置是否存在"""
    with self._lock:
        return key in self._data
```

---

## 四、测试要求

### 4.1 单元测试

```python
# tests/test_settings_service.py

import pytest
import tempfile
from pathlib import Path
from echem_sdl.services.settings_service import SettingsService

class TestSettingsService:
    @pytest.fixture
    def temp_config_path(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        yield path
        if path.exists():
            path.unlink()
    
    @pytest.fixture
    def settings(self, temp_config_path):
        return SettingsService(temp_config_path, auto_save=False)
    
    def test_get_default(self, settings):
        """测试获取默认值"""
        port = settings.get_str("rs485.port")
        assert port == "COM3"
    
    def test_get_with_default(self, settings):
        """测试不存在的键返回默认值"""
        value = settings.get_str("nonexistent", "default")
        assert value == "default"
    
    def test_set_and_get(self, settings):
        """测试设置和获取"""
        settings.set("rs485.port", "COM5")
        assert settings.get_str("rs485.port") == "COM5"
    
    def test_get_int(self, settings):
        """测试获取整数"""
        settings.set("test.int", 42)
        assert settings.get_int("test.int") == 42
    
    def test_get_float(self, settings):
        """测试获取浮点数"""
        settings.set("test.float", 3.14)
        assert settings.get_float("test.float") == pytest.approx(3.14)
    
    def test_get_bool(self, settings):
        """测试获取布尔值"""
        settings.set("test.bool", True)
        assert settings.get_bool("test.bool") == True
        
        settings.set("test.bool_str", "true")
        assert settings.get_bool("test.bool_str") == True

class TestPersistence:
    def test_save_and_load(self, temp_config_path):
        """测试保存和加载"""
        settings1 = SettingsService(temp_config_path)
        settings1.set("test.key", "test_value")
        settings1.save()
        
        settings2 = SettingsService(temp_config_path)
        assert settings2.get_str("test.key") == "test_value"
    
    def test_reset(self, settings):
        """测试重置"""
        settings.set("rs485.port", "COM10")
        settings.reset()
        assert settings.get_str("rs485.port") == "COM3"

class TestChangeListeners:
    def test_on_change(self, settings):
        """测试变更监听"""
        changes = []
        settings.on_change("rs485.port", lambda n, o: changes.append((n, o)))
        
        settings.set("rs485.port", "COM6")
        
        assert len(changes) == 1
        assert changes[0] == ("COM6", "COM3")
    
    def test_wildcard_listener(self, settings):
        """测试通配符监听"""
        changes = []
        settings.on_change("rs485.*", lambda n, o: changes.append((n, o)))
        
        settings.set("rs485.port", "COM7")
        settings.set("rs485.baudrate", 9600)
        
        assert len(changes) == 2

class TestGroupAccess:
    def test_get_group(self, settings):
        """测试获取分组"""
        group = settings.get_group("rs485")
        assert "port" in group
        assert "baudrate" in group
    
    def test_set_group(self, settings):
        """测试设置分组"""
        settings.set_group("rs485", {"port": "COM8", "baudrate": 115200})
        assert settings.get_str("rs485.port") == "COM8"
        assert settings.get_int("rs485.baudrate") == 115200
```

---

## 五、验收标准

- [ ] 默认配置完整
- [ ] 类型安全的 getter 正确
- [ ] set/set_many 正确
- [ ] 持久化保存/加载正确
- [ ] reset() 恢复默认
- [ ] 变更监听正确触发
- [ ] 通配符监听正确
- [ ] 分组访问正确
- [ ] 线程安全
- [ ] 自动保存可配置
- [ ] 单元测试覆盖率 > 90%
