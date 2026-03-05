"""AutoHySeeker configuration module.

Loads and exposes typed configuration from TOML files under ``configs/``:

- ``settings.toml``       → :class:`Settings`
- ``llm_config.toml``     → :class:`LLMConfig`
- ``microhyseeker.toml``  → :class:`MicroHySeekerConfig`

Usage::

    from src.configs import get_settings, get_llm_config, get_microhyseeker_config

    s = get_settings()
    print(s.general.project_name)   # "AutoHySeeker"
    print(s.api.port)               # 8100

    llm = get_llm_config()
    print(llm.default.model)        # "anthropic/claude-sonnet-4-6"

    mhs = get_microhyseeker_config()
    print(mhs.engine.mode)          # "file"
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# configs/ lives two levels above src/configs.py: src/ → AutoHySeeker/
_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


def _load_toml(filename: str) -> dict:
    """Load a TOML file from the configs directory; return empty dict if missing."""
    path = _CONFIGS_DIR / filename
    if not path.exists():
        return {}
    with path.open("rb") as fp:
        return tomllib.load(fp)


# ── settings.toml ─────────────────────────────────────────────────────────────

@dataclass
class GeneralSettings:
    project_name: str = "AutoHySeeker"
    version: str = "0.1.0"
    log_level: str = "INFO"


@dataclass
class ApiSettings:
    host: str = "0.0.0.0"
    port: int = 8100
    prefix: str = "/api/v1"


@dataclass
class Settings:
    """Typed representation of ``settings.toml``."""

    general: GeneralSettings = field(default_factory=GeneralSettings)
    api: ApiSettings = field(default_factory=ApiSettings)

    @classmethod
    def load(cls) -> "Settings":
        data = _load_toml("settings.toml")
        return cls(
            general=GeneralSettings(**data.get("general", {})),
            api=ApiSettings(**data.get("api", {})),
        )


# ── llm_config.toml ───────────────────────────────────────────────────────────

@dataclass
class LLMModelConfig:
    provider: str = "openai"
    model: str = "anthropic/claude-sonnet-4-6"
    temperature: float = 0.1
    max_tokens: int = 4096
    base_url: str = "https://api.mcxhm.cn"
    api_key_env: str = "OPENAI_API_KEY"


@dataclass
class LLMFallbackConfig:
    model: str = "anthropic/claude-opus-4-6"


@dataclass
class LLMConfig:
    """Typed representation of ``llm_config.toml``."""

    default: LLMModelConfig = field(default_factory=LLMModelConfig)
    fallback: LLMFallbackConfig = field(default_factory=LLMFallbackConfig)

    @classmethod
    def load(cls) -> "LLMConfig":
        data = _load_toml("llm_config.toml")
        return cls(
            default=LLMModelConfig(**data.get("default", {})),
            fallback=LLMFallbackConfig(**data.get("fallback", {})),
        )


# ── microhyseeker.toml ────────────────────────────────────────────────────────

@dataclass
class PathsConfig:
    data_dir: str = ""
    config_dir: str = ""
    logs_dir: str = ""


@dataclass
class EngineConfig:
    mode: str = "file"


@dataclass
class MicroHySeekerConfig:
    """Typed representation of ``microhyseeker.toml``."""

    paths: PathsConfig = field(default_factory=PathsConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)

    @classmethod
    def load(cls) -> "MicroHySeekerConfig":
        data = _load_toml("microhyseeker.toml")
        return cls(
            paths=PathsConfig(**data.get("paths", {})),
            engine=EngineConfig(**data.get("engine", {})),
        )


# ── Lazy singleton accessors ──────────────────────────────────────────────────

_settings: Optional[Settings] = None
_llm_config: Optional[LLMConfig] = None
_mhs_config: Optional[MicroHySeekerConfig] = None


def get_settings() -> Settings:
    """Return the cached :class:`Settings` singleton (loads once on first call)."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings


def get_llm_config() -> LLMConfig:
    """Return the cached :class:`LLMConfig` singleton (loads once on first call)."""
    global _llm_config
    if _llm_config is None:
        _llm_config = LLMConfig.load()
    return _llm_config


def get_microhyseeker_config() -> MicroHySeekerConfig:
    """Return the cached :class:`MicroHySeekerConfig` singleton."""
    global _mhs_config
    if _mhs_config is None:
        _mhs_config = MicroHySeekerConfig.load()
    return _mhs_config


__all__ = [
    "Settings",
    "GeneralSettings",
    "ApiSettings",
    "LLMConfig",
    "LLMModelConfig",
    "LLMFallbackConfig",
    "MicroHySeekerConfig",
    "PathsConfig",
    "EngineConfig",
    "get_settings",
    "get_llm_config",
    "get_microhyseeker_config",
]
