"""
应用级日志管理器 - AppLogger

基于 Python logging 模块，提供：
- 按日期文件夹组织 (logs/YYYY-MM-DD/)
- 每次启动生成独立日志文件 (app_HH-MM-SS.log)
- 控制台输出
- 统一的 logger 获取接口
- 日志永久保留，无任何大小限制
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# 日志格式
_LOG_FMT = "[%(asctime)s.%(msecs)03d] [%(levelname)-7s] [%(name)s] %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

# 全局单例
_root_logger: Optional[logging.Logger] = None
_log_dir: Path = Path("./logs")
_log_file: Optional[Path] = None
_initialized: bool = False


def init_app_logging(log_dir: str = "./logs",
                     console_level: int = logging.INFO,
                     file_level: int = logging.DEBUG):
    """初始化应用日志系统（应在 main 入口处调用一次）
    
    日志永久保留，无任何文件大小限制。
    每天一个文件夹，每次启动生成独立日志文件。
    
    目录结构::
    
        logs/
        ├── 2026-02-13/
        │   ├── app_14-30-25.log      # 第一次启动
        │   └── app_16-45-10.log      # 第二次启动
        └── 2026-02-14/
            └── app_09-00-01.log
    
    Args:
        log_dir: 日志根目录
        console_level: 控制台日志级别
        file_level: 文件日志级别
    """
    global _root_logger, _log_dir, _log_file, _initialized
    if _initialized:
        return

    _log_dir = Path(log_dir)
    
    # 按日期创建子文件夹
    now = datetime.now()
    date_dir = _log_dir / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # 每次启动使用时间戳命名，确保唯一
    time_str = now.strftime("%H-%M-%S")
    _log_file = date_dir / f"app_{time_str}.log"

    # 根 logger
    _root_logger = logging.getLogger("MicroHySeeker")
    _root_logger.setLevel(logging.DEBUG)
    _root_logger.handlers.clear()

    # ── 控制台 Handler ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(_LOG_FMT, _DATE_FMT))
    _root_logger.addHandler(console_handler)

    # ── 文件 Handler (无大小限制，追加模式) ──
    file_handler = logging.FileHandler(
        str(_log_file),
        mode="a",
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(_LOG_FMT, _DATE_FMT))
    _root_logger.addHandler(file_handler)

    _initialized = True

    _root_logger.info(f"日志系统已初始化 → {_log_file}（永久保留，无大小限制）")


def get_current_log_file() -> Optional[Path]:
    """获取当前会话的日志文件路径"""
    return _log_file


def get_app_logger(name: str = "") -> logging.Logger:
    """获取子 logger
    
    Args:
        name: 模块名（如 "RUNNER", "RS485", "UI"）
        
    Returns:
        logging.Logger: 子 logger
        
    Example:
        >>> logger = get_app_logger("RUNNER")
        >>> logger.info("步骤0开始")
    """
    if not _initialized:
        init_app_logging()

    if name:
        return logging.getLogger(f"MicroHySeeker.{name}")
    return logging.getLogger("MicroHySeeker")


def shutdown_logging():
    """关闭日志系统（应用退出时调用）"""
    global _initialized
    if _root_logger:
        for handler in _root_logger.handlers[:]:
            handler.close()
            _root_logger.removeHandler(handler)
    _initialized = False
