"""Settings service for application configuration."""

from PySide6.QtCore import QObject, Signal
import json
import os
from typing import Any, Dict, Optional


class SettingsService(QObject):
    """管理应用设置的服务。"""
    
    settings_changed = Signal(str, object)  # key, value
    
    def __init__(self, config_path: str = "config.json"):
        super().__init__()
        self.config_path = config_path
        self.settings: Dict[str, Any] = {}
        self._load_settings()
    
    def _load_settings(self) -> None:
        """从配置文件加载设置。"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception as e:
                print(f"Failed to load settings: {e}")
                self._init_defaults()
        else:
            self._init_defaults()
    
    def _init_defaults(self) -> None:
        """初始化默认设置。"""
        self.settings = {
            "language": "zh_CN",
            "rs485_port": "COM1",
            "rs485_baudrate": 9600,
            "stop_on_error": False,
            "data_path": "./data",
            "ocpt_enabled": False,
            "channels": [],
            "flush_settings": []
        }
        self._save_settings()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取设置值。"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置值并通知。"""
        self.settings[key] = value
        self.settings_changed.emit(key, value)
        self._save_settings()
    
    def _save_settings(self) -> None:
        """保存设置到文件。"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有设置。"""
        return self.settings.copy()
