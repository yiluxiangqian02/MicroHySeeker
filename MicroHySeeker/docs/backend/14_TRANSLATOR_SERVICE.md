# 14 - TranslatorService 模块规范

> **文件路径**: `src/echem_sdl/services/translator_service.py`  
> **优先级**: P1 (增强模块)  
> **依赖**: 无  
> **原C#参考**: 无（Python 特有）

---

## 一、模块职责

TranslatorService 是多语言翻译服务，负责：
1. 管理多语言字符串资源
2. 提供统一的翻译接口
3. 支持运行时语言切换
4. 支持参数化翻译
5. 提供默认回退机制

---

## 二、语言资源结构

### 2.1 目录结构

```
src/echem_sdl/
└── i18n/
    ├── __init__.py
    ├── zh.json      # 中文
    ├── en.json      # 英文
    └── ja.json      # 日文（可选）
```

### 2.2 资源文件格式

```json
{
  "_meta": {
    "language": "zh",
    "name": "简体中文",
    "version": "1.0.0"
  },
  "app": {
    "title": "微流控电化学工作站",
    "version": "版本 {version}"
  },
  "menu": {
    "file": "文件",
    "edit": "编辑",
    "view": "视图",
    "help": "帮助"
  },
  "button": {
    "start": "启动",
    "stop": "停止",
    "pause": "暂停",
    "resume": "恢复",
    "save": "保存",
    "load": "加载",
    "cancel": "取消",
    "ok": "确定"
  },
  "dialog": {
    "confirm_exit": "确定要退出吗？",
    "unsaved_changes": "有未保存的更改，是否保存？"
  },
  "status": {
    "connected": "已连接",
    "disconnected": "未连接",
    "running": "运行中",
    "idle": "空闲",
    "error": "错误"
  },
  "error": {
    "connection_failed": "连接失败: {reason}",
    "timeout": "操作超时",
    "invalid_config": "配置无效: {field}"
  },
  "step_type": {
    "prep_sol": "配液",
    "transfer": "转移",
    "flush": "冲洗",
    "echem": "电化学",
    "blank": "等待",
    "evacuate": "抽空"
  }
}
```

---

## 三、类设计

### 3.1 主类定义

```python
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import json
import threading

class TranslatorService:
    """多语言翻译服务
    
    提供国际化支持，管理多语言字符串资源。
    
    Attributes:
        current_language: 当前语言代码
        available_languages: 可用语言列表
        
    Example:
        >>> tr = TranslatorService("zh")
        >>> text = tr.translate("button.start")  # "启动"
        >>> text = tr.translate("error.connection_failed", reason="超时")
    """
```

### 3.2 构造函数

```python
def __init__(
    self,
    default_language: str = "zh",
    resource_dir: Optional[str | Path] = None
) -> None:
    """初始化翻译服务
    
    Args:
        default_language: 默认语言代码
        resource_dir: 资源文件目录（None 使用内置目录）
    """
    self._lock = threading.RLock()
    self._current_language = default_language
    self._fallback_language = "en"
    
    # 资源目录
    if resource_dir:
        self._resource_dir = Path(resource_dir)
    else:
        self._resource_dir = Path(__file__).parent.parent / "i18n"
    
    # 语言资源缓存
    self._resources: Dict[str, Dict[str, Any]] = {}
    
    # 变更监听器
    self._listeners: List[Callable[[str], None]] = []
    
    # 加载默认语言
    self._load_language(default_language)
    if default_language != self._fallback_language:
        self._load_language(self._fallback_language)
```

### 3.3 翻译方法

```python
def translate(
    self,
    key: str,
    default: Optional[str] = None,
    **kwargs
) -> str:
    """翻译字符串
    
    Args:
        key: 翻译键（点分路径，如 "button.start"）
        default: 未找到时的默认值
        **kwargs: 格式化参数
        
    Returns:
        翻译后的字符串
    """
    # 尝试当前语言
    text = self._get_text(self._current_language, key)
    
    # 回退到默认语言
    if text is None and self._current_language != self._fallback_language:
        text = self._get_text(self._fallback_language, key)
    
    # 使用默认值或键名
    if text is None:
        text = default if default is not None else key
    
    # 格式化参数
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass  # 忽略缺失的参数
    
    return text

def _get_text(self, language: str, key: str) -> Optional[str]:
    """从资源中获取文本"""
    with self._lock:
        if language not in self._resources:
            return None
        
        data = self._resources[language]
        parts = key.split(".")
        
        for part in parts:
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                return None
        
        return data if isinstance(data, str) else None

# 简写别名
def tr(self, key: str, **kwargs) -> str:
    """translate 的简写"""
    return self.translate(key, **kwargs)

def __call__(self, key: str, **kwargs) -> str:
    """支持直接调用"""
    return self.translate(key, **kwargs)
```

### 3.4 语言管理

```python
@property
def current_language(self) -> str:
    """当前语言代码"""
    return self._current_language

@property
def available_languages(self) -> List[str]:
    """可用语言列表"""
    languages = []
    for file in self._resource_dir.glob("*.json"):
        lang_code = file.stem
        if lang_code not in languages:
            languages.append(lang_code)
    return languages

def get_language_name(self, code: str) -> str:
    """获取语言显示名称"""
    if code in self._resources:
        return self._resources[code].get("_meta", {}).get("name", code)
    return code

def set_language(self, language: str) -> bool:
    """切换语言
    
    Args:
        language: 语言代码
        
    Returns:
        是否成功
    """
    if language == self._current_language:
        return True
    
    if not self._load_language(language):
        return False
    
    old_language = self._current_language
    self._current_language = language
    
    # 通知监听器
    self._notify_listeners(language)
    
    return True

def _load_language(self, language: str) -> bool:
    """加载语言资源"""
    with self._lock:
        if language in self._resources:
            return True
        
        file_path = self._resource_dir / f"{language}.json"
        if not file_path.exists():
            return False
        
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            self._resources[language] = data
            return True
        except Exception as e:
            print(f"加载语言资源失败: {e}")
            return False
```

### 3.5 变更监听

```python
def on_language_change(self, callback: Callable[[str], None]) -> None:
    """监听语言变更
    
    Args:
        callback: 回调函数，接收新语言代码
    """
    with self._lock:
        self._listeners.append(callback)

def off_language_change(self, callback: Callable[[str], None]) -> None:
    """取消监听"""
    with self._lock:
        if callback in self._listeners:
            self._listeners.remove(callback)

def _notify_listeners(self, new_language: str) -> None:
    """通知监听器"""
    with self._lock:
        listeners = list(self._listeners)
    
    for listener in listeners:
        try:
            listener(new_language)
        except Exception:
            pass
```

### 3.6 批量翻译

```python
def translate_many(self, keys: List[str], **kwargs) -> Dict[str, str]:
    """批量翻译
    
    Args:
        keys: 键列表
        **kwargs: 共享的格式化参数
        
    Returns:
        {key: translated_text}
    """
    return {key: self.translate(key, **kwargs) for key in keys}

def get_group(self, prefix: str) -> Dict[str, str]:
    """获取一组翻译
    
    Args:
        prefix: 前缀（如 "button"）
        
    Returns:
        该组下的所有翻译
    """
    with self._lock:
        data = self._resources.get(self._current_language, {})
        
        parts = prefix.split(".")
        for part in parts:
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                return {}
        
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, str)}
        
        return {}
```

### 3.7 枚举翻译

```python
def translate_enum(self, enum_value, prefix: str = "") -> str:
    """翻译枚举值
    
    Args:
        enum_value: 枚举值
        prefix: 键前缀
        
    Returns:
        翻译文本
    """
    if hasattr(enum_value, "value"):
        value = enum_value.value
    else:
        value = str(enum_value)
    
    key = f"{prefix}.{value}" if prefix else value
    return self.translate(key, default=value)
```

---

## 四、便捷函数

```python
# 模块级便捷函数
_translator: Optional[TranslatorService] = None

def init_translator(language: str = "zh") -> TranslatorService:
    """初始化全局翻译器"""
    global _translator
    _translator = TranslatorService(language)
    return _translator

def get_translator() -> TranslatorService:
    """获取全局翻译器"""
    global _translator
    if _translator is None:
        _translator = TranslatorService()
    return _translator

def tr(key: str, **kwargs) -> str:
    """全局翻译函数"""
    return get_translator().translate(key, **kwargs)
```

---

## 五、测试要求

### 5.1 单元测试

```python
# tests/test_translator_service.py

import pytest
import tempfile
import json
from pathlib import Path
from echem_sdl.services.translator_service import TranslatorService

class TestTranslatorService:
    @pytest.fixture
    def temp_i18n_dir(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            
            # 创建中文资源
            zh_data = {
                "_meta": {"language": "zh", "name": "中文"},
                "button": {"start": "启动", "stop": "停止"},
                "message": {"hello": "你好 {name}"}
            }
            (path / "zh.json").write_text(json.dumps(zh_data), encoding="utf-8")
            
            # 创建英文资源
            en_data = {
                "_meta": {"language": "en", "name": "English"},
                "button": {"start": "Start", "stop": "Stop"},
                "message": {"hello": "Hello {name}"}
            }
            (path / "en.json").write_text(json.dumps(en_data), encoding="utf-8")
            
            yield path
    
    @pytest.fixture
    def translator(self, temp_i18n_dir):
        return TranslatorService("zh", temp_i18n_dir)
    
    def test_basic_translate(self, translator):
        """测试基本翻译"""
        assert translator.translate("button.start") == "启动"
        assert translator.translate("button.stop") == "停止"
    
    def test_missing_key(self, translator):
        """测试缺失键"""
        # 返回键名
        assert translator.translate("nonexistent.key") == "nonexistent.key"
        # 使用默认值
        assert translator.translate("nonexistent.key", default="默认") == "默认"
    
    def test_parameterized(self, translator):
        """测试参数化翻译"""
        result = translator.translate("message.hello", name="张三")
        assert result == "你好 张三"
    
    def test_language_switch(self, translator):
        """测试语言切换"""
        assert translator.translate("button.start") == "启动"
        
        translator.set_language("en")
        assert translator.translate("button.start") == "Start"
    
    def test_available_languages(self, translator):
        """测试可用语言"""
        languages = translator.available_languages
        assert "zh" in languages
        assert "en" in languages
    
    def test_language_change_listener(self, translator):
        """测试语言变更监听"""
        changes = []
        translator.on_language_change(lambda lang: changes.append(lang))
        
        translator.set_language("en")
        
        assert len(changes) == 1
        assert changes[0] == "en"

class TestShortcuts:
    def test_tr_shortcut(self, translator):
        """测试 tr 简写"""
        assert translator.tr("button.start") == "启动"
    
    def test_call_shortcut(self, translator):
        """测试直接调用"""
        assert translator("button.start") == "启动"
    
    def test_translate_many(self, translator):
        """测试批量翻译"""
        result = translator.translate_many(["button.start", "button.stop"])
        assert result["button.start"] == "启动"
        assert result["button.stop"] == "停止"
    
    def test_get_group(self, translator):
        """测试获取分组"""
        buttons = translator.get_group("button")
        assert "start" in buttons
        assert "stop" in buttons
```

---

## 六、使用示例

### 6.1 基本使用

```python
from echem_sdl.services.translator_service import TranslatorService, tr

# 创建翻译服务
translator = TranslatorService("zh")

# 基本翻译
text = translator.translate("button.start")  # "启动"

# 参数化翻译
error = translator.translate("error.connection_failed", reason="超时")

# 使用全局函数
from echem_sdl.services.translator_service import tr
text = tr("button.stop")
```

### 6.2 UI 集成

```python
class MainWindow(QMainWindow):
    def __init__(self, translator):
        self._tr = translator
        self._setup_ui()
        
        # 监听语言变更
        translator.on_language_change(self._retranslate_ui)
    
    def _setup_ui(self):
        self.start_btn.setText(self._tr("button.start"))
        self.stop_btn.setText(self._tr("button.stop"))
    
    def _retranslate_ui(self, new_lang):
        """语言切换时重新翻译"""
        self.start_btn.setText(self._tr("button.start"))
        self.stop_btn.setText(self._tr("button.stop"))
```

---

## 七、验收标准

- [ ] 基本翻译正确
- [ ] 参数化翻译正确
- [ ] 缺失键回退正确
- [ ] 语言切换正确
- [ ] 变更监听正确
- [ ] 批量翻译正确
- [ ] 分组获取正确
- [ ] 枚举翻译正确
- [ ] 线程安全
- [ ] 单元测试通过
