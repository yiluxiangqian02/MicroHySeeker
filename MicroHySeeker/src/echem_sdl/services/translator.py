"""Translation loader for JSON-based locale files."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable

from .logger import LoggerService


class TranslatorService:
    def __init__(
        self,
        translations_dir: Path,
        default_locale: str = "zh",
        logger: LoggerService | None = None,
    ) -> None:
        self._dir = translations_dir
        self._default = default_locale
        self._locale = default_locale
        self._translations: dict[str, str] = {}
        self._callbacks: list[Callable[[str], None]] = []
        self._lock = threading.RLock()
        self._logger = logger
        self.load_translations(default_locale)

    def load_translations(self, locale: str | None = None) -> None:
        with self._lock:
            target = locale or self._locale
            path = self._dir / f"{target}.json"
            try:
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    data = {}
            except Exception as exc:
                if self._logger:
                    self._logger.warning(f"failed to load locale {target}")
                    self._logger.exception("translation load error", exc=exc)
                data = {}

            if not data and target != self._default:
                fallback = self._dir / f"{self._default}.json"
                try:
                    data = json.loads(fallback.read_text(encoding="utf-8"))
                except Exception:
                    data = {}

            self._translations = dict(data)
            self._locale = target

    def gettext(self, key: str) -> str:
        with self._lock:
            return self._translations.get(key, key)

    def set_locale(self, locale: str) -> None:
        self.load_translations(locale)
        for callback in list(self._callbacks):
            try:
                callback(self._locale)
            except Exception:
                pass

    def available_locales(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted([p.stem for p in self._dir.glob("*.json")])

    def bind_reload_callback(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)
