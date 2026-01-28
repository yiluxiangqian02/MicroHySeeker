"""Thread-safe logging service with optional UI callback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LEVELS: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


class _UICallbackHandler(logging.Handler):
    def __init__(self, callback: Callable[[logging.LogRecord], None]) -> None:
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._callback(record)
        except Exception:
            # UI thread safety is the caller's responsibility.
            pass


class LoggerService:
    def __init__(
        self,
        level: str = "INFO",
        fmt: str | None = None,
        datefmt: str | None = None,
        handlers: list[logging.Handler] | None = None,
        ui_callback: Callable[[logging.LogRecord], None] | None = None,
    ) -> None:
        self._logger = logging.getLogger("echem_sdl")
        self._logger.setLevel(LEVELS.get(level.upper(), logging.INFO))
        self._logger.propagate = False
        self._formatter = logging.Formatter(
            fmt or DEFAULT_LOG_FORMAT, datefmt or DEFAULT_DATE_FORMAT
        )

        if handlers:
            for handler in handlers:
                handler.setFormatter(self._formatter)
                self._logger.addHandler(handler)
        else:
            self.add_console_handler(level)

        if ui_callback is not None:
            self.bind_ui_callback(ui_callback)

    def add_console_handler(self, level: str | None = None) -> None:
        handler = logging.StreamHandler()
        handler.setLevel(LEVELS.get((level or "INFO").upper(), logging.INFO))
        handler.setFormatter(self._formatter)
        self._logger.addHandler(handler)

    def add_file_handler(self, path: Path, level: str | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setLevel(LEVELS.get((level or "INFO").upper(), logging.INFO))
        handler.setFormatter(self._formatter)
        self._logger.addHandler(handler)

    def bind_ui_callback(self, callback: Callable[[logging.LogRecord], None]) -> None:
        handler = _UICallbackHandler(callback)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(self._formatter)
        self._logger.addHandler(handler)

    def log(self, level: str, msg: str, **kwargs) -> None:
        self._logger.log(LEVELS.get(level.upper(), logging.INFO), msg, extra=kwargs)

    def info(self, msg: str, **kwargs) -> None:
        self.log("INFO", msg, **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        self.log("WARNING", msg, **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        self.log("ERROR", msg, **kwargs)

    def debug(self, msg: str, **kwargs) -> None:
        self.log("DEBUG", msg, **kwargs)

    def exception(self, msg: str, exc: BaseException | None = None, **kwargs) -> None:
        if exc is None:
            self._logger.exception(msg, extra=kwargs)
        else:
            self._logger.error(msg, exc_info=exc, extra=kwargs)

    @property
    def logger(self) -> logging.Logger:
        return self._logger
