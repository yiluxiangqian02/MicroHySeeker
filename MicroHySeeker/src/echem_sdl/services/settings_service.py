"""Settings loader/saver with deep merge and basic validation."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .logger import LoggerService


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class SettingsService:
    def __init__(self, base_dir: Path, logger: LoggerService | None = None) -> None:
        self.base_dir = base_dir
        self.defaults_path = base_dir / "src" / "echem_sdl" / "config" / "defaults.json"
        self.user_path = base_dir / "src" / "echem_sdl" / "config" / "settings.json"
        self._lock = threading.RLock()
        self._logger = logger
        self._cache: dict[str, Any] = {}

    def load_defaults(self) -> dict:
        return self._read_json(self.defaults_path, fallback={})

    def load_user_settings(self) -> dict:
        return self._read_json(self.user_path, fallback={})

    def merge_defaults(self, raw_defaults: dict, raw_user: dict) -> dict:
        return _deep_merge(raw_defaults or {}, raw_user or {})

    def validate_settings(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            raise ValueError("settings must be a dict")
        return raw

    def reload(self) -> dict:
        with self._lock:
            defaults = self.load_defaults()
            user = self.load_user_settings()
            merged = self.merge_defaults(defaults, user)
            self._cache = self.validate_settings(merged)
            return dict(self._cache)

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def save_user_settings(self, settings: dict | None = None) -> None:
        data = settings if settings is not None else self._cache
        with self._lock:
            self.user_path.parent.mkdir(parents=True, exist_ok=True)
            with self.user_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2)

    def _read_json(self, path: Path, fallback: dict) -> dict:
        try:
            if not path.exists():
                if self._logger:
                    self._logger.warning(f"settings file not found: {path}")
                return dict(fallback)
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            if self._logger:
                self._logger.error(f"failed to read settings: {path}")
                self._logger.exception("settings read error", exc=exc)
            return dict(fallback)
