"""
应用级日志管理器 - AppLogger

基于 Python logging 模块，提供：
- 按日期文件夹组织 (logs/YYYY-MM-DD/)
- 每次启动生成独立日志文件 (app_HH-MM-SS.log)
- 独立的通信日志文件 (comm_HH-MM-SS.log) 记录 RS485 TX/RX 帧数据
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

# 通信日志格式 (更紧凑，突出 TX/RX 数据)
_COMM_LOG_FMT = "[%(asctime)s.%(msecs)03d] %(message)s"

# 全局单例
_root_logger: Optional[logging.Logger] = None
_comm_logger: Optional[logging.Logger] = None
_log_dir: Path = Path("./logs")
_log_file: Optional[Path] = None
_comm_log_file: Optional[Path] = None
_initialized: bool = False


class _ExcludeRunnerFilter(logging.Filter):
    """过滤掉 MicroHySeeker.RUNNER 的日志记录。
    
    RUNNER 日志已通过 ExperimentDataManager 写入 data/ 下的 run_log.log，
    logs/ 下的 app_*.log 不再重复记录，只保留底层驱动/RS485/CHI 等调试日志。
    """
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith("MicroHySeeker.RUNNER")


def init_app_logging(log_dir: str = "./logs",
                     console_level: int = logging.INFO,
                     file_level: int = logging.DEBUG,
                     log_prefix: str = "app"):
    """初始化应用日志系统（应在 main 入口处调用一次）
    
    日志永久保留，无任何文件大小限制。
    每天一个文件夹，每次启动生成独立日志文件。
    同时创建独立的通信日志文件，记录 RS485 TX/RX 帧数据。
    
    目录结构::
    
        logs/
        ├── 2026-02-13/
        │   ├── app_14-30-25.log      # GUI启动的运行日志
        │   ├── web_app_14-30-25.log  # Web(run_server.py)启动的运行日志
        │   ├── comm_14-30-25.log     # 通信日志 (RS485 TX/RX)
        │   └── app_16-45-10.log
        └── 2026-02-14/
            └── app_09-00-01.log
    
    Args:
        log_dir: 日志根目录
        console_level: 控制台日志级别
        file_level: 文件日志级别
        log_prefix: 日志文件名前缀，默认 "app"，web模式传 "web_app"
    """
    global _root_logger, _comm_logger, _log_dir, _log_file, _comm_log_file, _initialized
    if _initialized:
        return

    _log_dir = Path(log_dir)
    
    # 按日期创建子文件夹
    now = datetime.now()
    date_dir = _log_dir / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # 每次启动使用时间戳命名，确保唯一
    time_str = now.strftime("%H-%M-%S")
    _log_file = date_dir / f"{log_prefix}_{time_str}.log"
    comm_prefix = "web_comm" if log_prefix.startswith("web") else "comm"
    _comm_log_file = date_dir / f"{comm_prefix}_{time_str}.log"

    # ── 根 logger (运行日志) ──
    _root_logger = logging.getLogger("MicroHySeeker")
    _root_logger.setLevel(logging.DEBUG)
    _root_logger.handlers.clear()

    # ── 控制台 Handler ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(_LOG_FMT, _DATE_FMT))
    _root_logger.addHandler(console_handler)

    # ── 文件 Handler (无大小限制，追加模式) ──
    # 过滤掉 RUNNER 日志（RUNNER 日志已写入 data/ 下的 run_log.log，
    # logs/ 下的 app_*.log 只保留底层驱动/通信/CHI 等调试日志）
    file_handler = logging.FileHandler(
        str(_log_file),
        mode="a",
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(_LOG_FMT, _DATE_FMT))
    file_handler.addFilter(_ExcludeRunnerFilter())
    _root_logger.addHandler(file_handler)

    # ── 通信日志 logger (独立文件，不传播到根logger) ──
    _comm_logger = logging.getLogger("MicroHySeeker.COMM")
    _comm_logger.setLevel(logging.DEBUG)
    _comm_logger.propagate = False  # 不传播到父logger，避免重复输出
    _comm_logger.handlers.clear()

    comm_file_handler = logging.FileHandler(
        str(_comm_log_file),
        mode="a",
        encoding="utf-8",
    )
    comm_file_handler.setLevel(logging.DEBUG)
    comm_file_handler.setFormatter(logging.Formatter(_COMM_LOG_FMT, _DATE_FMT))
    _comm_logger.addHandler(comm_file_handler)

    _initialized = True

    _root_logger.info(f"日志系统已初始化 → {_log_file}（永久保留，无大小限制）")
    _root_logger.info(f"通信日志已初始化 → {_comm_log_file}")


def get_current_log_file() -> Optional[Path]:
    """获取当前会话的日志文件路径"""
    return _log_file


def get_current_comm_log_file() -> Optional[Path]:
    """获取当前会话的通信日志文件路径"""
    return _comm_log_file


def log_comm(direction: str, addr: int, cmd_name: str, hex_str: str) -> None:
    """记录一条 RS485 通信日志到文件
    
    线程安全，异常不传播（不影响主流程）。
    
    Args:
        direction: "TX" 或 "RX"
        addr: 设备地址 (1-255)
        cmd_name: 命令名称 (如 "SPEED", "ENABLE")
        hex_str: 完整帧的十六进制字符串
    """
    if _comm_logger is None:
        return
    try:
        arrow = "→" if direction == "TX" else "←"
        _comm_logger.debug(
            f"{direction} {arrow} Addr={addr:>2d} {cmd_name:<20s} {hex_str}"
        )
    except Exception:
        pass  # 通信日志写入失败不影响主流程


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
    if _comm_logger:
        for handler in _comm_logger.handlers[:]:
            handler.close()
            _comm_logger.removeHandler(handler)
    _initialized = False
