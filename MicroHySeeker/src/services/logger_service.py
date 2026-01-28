"""Logger service for application logging."""

from PySide6.QtCore import QObject, Signal
from datetime import datetime
from typing import List
import os


class LoggerService(QObject):
    """管理应用日志的服务。"""
    
    message_logged = Signal(str, str)  # level, message
    
    def __init__(self, log_path: str = "logs"):
        super().__init__()
        self.log_path = log_path
        self.log_messages: List[str] = []
        
        # 创建日志目录
        os.makedirs(log_path, exist_ok=True)
    
    def _format_message(self, level: str, message: str) -> str:
        """格式化日志消息。"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level}] {message}"
    
    def info(self, message: str) -> None:
        """记录信息级日志。"""
        formatted = self._format_message("INFO", message)
        self.log_messages.append(formatted)
        self.message_logged.emit("INFO", message)
        print(formatted)
    
    def warning(self, message: str) -> None:
        """记录警告级日志。"""
        formatted = self._format_message("WARNING", message)
        self.log_messages.append(formatted)
        self.message_logged.emit("WARNING", message)
        print(formatted)
    
    def error(self, message: str) -> None:
        """记录错误级日志。"""
        formatted = self._format_message("ERROR", message)
        self.log_messages.append(formatted)
        self.message_logged.emit("ERROR", message)
        print(formatted)
    
    def debug(self, message: str) -> None:
        """记录调试级日志。"""
        formatted = self._format_message("DEBUG", message)
        self.log_messages.append(formatted)
        self.message_logged.emit("DEBUG", message)
        print(formatted)
    
    def get_messages(self, level: str = None) -> List[str]:
        """获取日志消息。"""
        if level is None:
            return self.log_messages.copy()
        return [msg for msg in self.log_messages if f"[{level}]" in msg]
    
    def clear(self) -> None:
        """清空日志消息。"""
        self.log_messages.clear()
    
    def save_to_file(self, filename: str = None) -> None:
        """保存日志到文件。"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"app_{timestamp}.log"
        
        filepath = os.path.join(self.log_path, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.log_messages))
        except Exception as e:
            self.error(f"Failed to save log file: {e}")
