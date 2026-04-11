"""Logging setup helpers."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from src.common.config import LOG_ROOT

LOGGER_NAME = "autohyseeker"


def configure_logging(level: int | str = logging.INFO) -> logging.Logger:
    """Configure project logger once and return it."""
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # 按日期文件夹 + web 标识
    now = datetime.now()
    date_dir = LOG_ROOT / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    time_str = now.strftime("%H-%M-%S")
    log_file = date_dir / f"web_ahs_{time_str}.log"

    file_handler = logging.FileHandler(
        str(log_file),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a project logger and ensure logging is configured."""
    configure_logging()
    if not name or name == LOGGER_NAME:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")

