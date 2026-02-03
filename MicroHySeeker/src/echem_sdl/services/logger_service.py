"""
LoggerService - 统一日志服务（基础版）

提供简单的日志记录功能，满足阶段3的基本需求。
"""
from datetime import datetime
from enum import IntEnum
from typing import Optional


class LogLevel(IntEnum):
    """日志级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LoggerService:
    """日志服务（基础版）
    
    提供基本的日志记录功能：
    - 输出到控制台
    - 分级日志（DEBUG/INFO/WARNING/ERROR）
    - 时间戳
    
    Example:
        >>> logger = LoggerService(level=LogLevel.INFO)
        >>> logger.info("连接成功")
        >>> logger.error("通信失败")
    """
    
    def __init__(self, name: str = "MicroHySeeker", level: LogLevel = LogLevel.INFO):
        """初始化日志服务
        
        Args:
            name: 日志模块名称
            level: 日志级别
        """
        self.name = name
        self.level = level
    
    def _format_message(self, level: str, message: str, module: Optional[str] = None) -> str:
        """格式化日志消息
        
        Args:
            level: 日志级别名称
            message: 日志消息
            module: 模块名称
            
        Returns:
            格式化后的日志字符串
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        if module:
            return f"[{timestamp}] [{level}] [{module}] {message}"
        return f"[{timestamp}] [{level}] {message}"
    
    def debug(self, message: str, module: Optional[str] = None) -> None:
        """记录DEBUG级别日志
        
        Args:
            message: 日志消息
            module: 模块名称
        """
        if self.level <= LogLevel.DEBUG:
            print(self._format_message("DEBUG", message, module))
    
    def info(self, message: str, module: Optional[str] = None) -> None:
        """记录INFO级别日志
        
        Args:
            message: 日志消息
            module: 模块名称
        """
        if self.level <= LogLevel.INFO:
            print(self._format_message("INFO", message, module))
    
    def warning(self, message: str, module: Optional[str] = None) -> None:
        """记录WARNING级别日志
        
        Args:
            message: 日志消息
            module: 模块名称
        """
        if self.level <= LogLevel.WARNING:
            print(self._format_message("WARNING", message, module))
    
    def error(self, message: str, module: Optional[str] = None) -> None:
        """记录ERROR级别日志
        
        Args:
            message: 日志消息
            module: 模块名称
        """
        if self.level <= LogLevel.ERROR:
            print(self._format_message("ERROR", message, module))
    
    def critical(self, message: str, module: Optional[str] = None) -> None:
        """记录CRITICAL级别日志
        
        Args:
            message: 日志消息
            module: 模块名称
        """
        if self.level <= LogLevel.CRITICAL:
            print(self._format_message("CRITICAL", message, module))
    
    def set_level(self, level: LogLevel) -> None:
        """设置日志级别
        
        Args:
            level: 新的日志级别
        """
        self.level = level


# 默认全局实例
_default_logger: Optional[LoggerService] = None


def get_logger(name: str = "MicroHySeeker", level: LogLevel = LogLevel.INFO) -> LoggerService:
    """获取日志实例
    
    Args:
        name: 日志模块名称
        level: 日志级别
        
    Returns:
        LoggerService 实例
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = LoggerService(name, level)
    return _default_logger
