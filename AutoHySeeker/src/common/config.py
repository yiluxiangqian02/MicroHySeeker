"""Runtime configuration for AutoHySeeker."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import tomllib
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("autohyseeker.config")


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()

_CONFIGS_DIR = PROJECT_ROOT / "configs"
_PROJECTS_DIR = _CONFIGS_DIR / "projects"
_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env(value: str) -> str:
    """Expand ``${VAR}`` / ``${VAR:-default}`` env syntax in a string."""

    def _sub(match: re.Match[str]) -> str:
        expr = match.group(1)
        if ":-" in expr:
            var, default = expr.split(":-", 1)
            return os.environ.get(var, default)
        return os.environ.get(expr, match.group(0))

    return _ENV_PATTERN.sub(_sub, value)


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as fh:
            parsed = tomllib.load(fh)
        return parsed if isinstance(parsed, dict) else {}
    except Exception as exc:  # pragma: no cover - runtime dependent
        logger.warning("failed to read toml config %s: %s", path, exc)
        return {}


def _load_section(filename: str, section: str) -> dict[str, Any]:
    parsed = _load_toml(_CONFIGS_DIR / filename)
    value = parsed.get(section, {})
    return value if isinstance(value, dict) else {}


def _normalise_openviking_config(raw: dict[str, Any]) -> dict[str, Any]:
    cfg: dict[str, Any] = dict(raw)
    workspace_path = cfg.get("workspace_path")
    if isinstance(workspace_path, str) and workspace_path.strip():
        expanded = _expand_env(workspace_path)
        cfg["workspace_path"] = str(_resolve_path(expanded, PROJECT_ROOT))
    return cfg


OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.mcxhm.cn")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "anthropic/claude-sonnet-4-6")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "anthropic/claude-opus-4-6")
OPENAI_CONNECT_TIMEOUT_SECONDS = float(
    os.getenv("OPENAI_CONNECT_TIMEOUT_SECONDS", "5"),
)
OPENAI_UNAVAILABLE_COOLDOWN_SECONDS = float(
    os.getenv("OPENAI_UNAVAILABLE_COOLDOWN_SECONDS", "60"),
)
DATA_ROOT = _resolve_path(os.getenv("DATA_ROOT", "../data"), PROJECT_ROOT)
LOG_ROOT = _resolve_path(os.getenv("LOG_ROOT", "./logs"), PROJECT_ROOT)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8200"))   # 8100 is reserved for MicroHySeeker
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))

# ── Phase 1 typed-ish config accessors (TOML) ────────────────────────────────

_orchestrator_config: dict[str, Any] | None = None
_monitor_config: dict[str, Any] | None = None
_designer_config: dict[str, Any] | None = None
_knowledge_config: dict[str, Any] | None = None
_project_configs: dict[str, dict[str, Any]] | None = None


def get_orchestrator_config(*, reload: bool = False) -> dict[str, Any]:
    global _orchestrator_config
    if reload or _orchestrator_config is None:
        _orchestrator_config = _load_section("orchestrator.toml", "orchestrator")
    return dict(_orchestrator_config)


def get_monitor_config(*, reload: bool = False) -> dict[str, Any]:
    global _monitor_config
    if reload or _monitor_config is None:
        parsed = _load_toml(_CONFIGS_DIR / "monitor.toml")
        _monitor_config = {
            "realtime_monitor": parsed.get("realtime_monitor", {}),
            "heartbeat_inspector": parsed.get("heartbeat_inspector", {}),
        }
    return dict(_monitor_config)


def get_designer_config(*, reload: bool = False) -> dict[str, Any]:
    global _designer_config
    if reload or _designer_config is None:
        _designer_config = _load_section("designer.toml", "designer")
    return dict(_designer_config)


def get_knowledge_config(*, reload: bool = False) -> dict[str, Any]:
    global _knowledge_config
    if reload or _knowledge_config is None:
        raw = _load_section("knowledge.toml", "openviking")
        _knowledge_config = _normalise_openviking_config(raw)
    return dict(_knowledge_config)


def load_project_configs(*, reload: bool = False) -> dict[str, dict[str, Any]]:
    """Load all project configs under configs/projects/*.toml keyed by project id."""
    global _project_configs
    if not reload and _project_configs is not None:
        return dict(_project_configs)

    configs: dict[str, dict[str, Any]] = {}
    if _PROJECTS_DIR.exists():
        for path in sorted(_PROJECTS_DIR.glob("*.toml")):
            parsed = _load_toml(path)
            project_section = parsed.get("project", {})
            project_id = None
            if isinstance(project_section, dict):
                project_id = project_section.get("id")
            key = str(project_id) if project_id else path.stem
            configs[key] = parsed
    _project_configs = configs
    return dict(_project_configs)


def get_project_config(project_id: str, *, reload: bool = False) -> dict[str, Any] | None:
    configs = load_project_configs(reload=reload)
    cfg = configs.get(project_id)
    return dict(cfg) if isinstance(cfg, dict) else None


def reload_all_configs() -> None:
    """Force reload all TOML configs under configs/."""
    global ORCHESTRATOR_CONFIG, MONITOR_CONFIG, DESIGNER_CONFIG, KNOWLEDGE_CONFIG, PROJECT_CONFIGS
    ORCHESTRATOR_CONFIG = get_orchestrator_config(reload=True)
    MONITOR_CONFIG = get_monitor_config(reload=True)
    DESIGNER_CONFIG = get_designer_config(reload=True)
    KNOWLEDGE_CONFIG = get_knowledge_config(reload=True)
    PROJECT_CONFIGS = load_project_configs(reload=True)


# Convenience module-level snapshots (loaded once at import time).
ORCHESTRATOR_CONFIG = get_orchestrator_config()
MONITOR_CONFIG = get_monitor_config()
DESIGNER_CONFIG = get_designer_config()
KNOWLEDGE_CONFIG = get_knowledge_config()
PROJECT_CONFIGS = load_project_configs()


__all__ = [
    "PROJECT_ROOT",
    "DATA_ROOT",
    "LOG_ROOT",
    "API_HOST",
    "API_PORT",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "DEFAULT_MODEL",
    "FALLBACK_MODEL",
    "OPENAI_TIMEOUT_SECONDS",
    "OPENAI_CONNECT_TIMEOUT_SECONDS",
    "OPENAI_UNAVAILABLE_COOLDOWN_SECONDS",
    "ORCHESTRATOR_CONFIG",
    "MONITOR_CONFIG",
    "DESIGNER_CONFIG",
    "KNOWLEDGE_CONFIG",
    "PROJECT_CONFIGS",
    "get_orchestrator_config",
    "get_monitor_config",
    "get_designer_config",
    "get_knowledge_config",
    "load_project_configs",
    "get_project_config",
    "reload_all_configs",
]
