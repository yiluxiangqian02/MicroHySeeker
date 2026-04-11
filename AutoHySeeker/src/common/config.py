"""Runtime configuration for AutoHySeeker."""

from __future__ import annotations

import json
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

_CONFIGS_DIR = PROJECT_ROOT / "configs"
_PROJECTS_DIR = _CONFIGS_DIR / "projects"
_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")
_AGENT_CONFIG_PATH = _CONFIGS_DIR / "agent_models.toml"
_AGENT_NAME_ALIASES = {
    "chat": "chat",
    "diagnostics": "diagnostics_expert",
    "diagnostics_expert": "diagnostics_expert",
    "exp_designer": "experiment_designer",
    "experiment_designer": "experiment_designer",
    "exp_executor": "experiment_executor",
    "experiment_executor": "experiment_executor",
    "heartbeat_inspector": "heartbeat_inspector",
    "orchestrator": "orchestrator",
}
_AGENT_SECTION_ORDER = (
    "defaults",
    "orchestrator",
    "experiment_designer",
    "experiment_executor",
    "diagnostics_expert",
    "chat",
    "heartbeat_inspector",
)
_DEFAULT_AGENT_SETTINGS: dict[str, Any] = {
    "provider": "openai",
    "model": "anthropic/claude-sonnet-4-6",
    "fallback_model": "anthropic/claude-opus-4-6",
    "base_url": "https://api.mcxhm.cn",
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "temperature": 0.2,
    "max_tokens": None,
    "enabled": True,
}


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _expand_env(value: str) -> str:
    """Expand ``${VAR}`` / ``${VAR:-default}`` env syntax in a string."""

    def _sub(match: re.Match[str]) -> str:
        expr = match.group(1)
        if ":-" in expr:
            var, default = expr.split(":-", 1)
            return os.environ.get(var, default)
        return os.environ.get(expr, match.group(0))

    return _ENV_PATTERN.sub(_sub, value)


def _expand_value(value: Any) -> Any:
    if isinstance(value, str):
        return _expand_env(value)
    if isinstance(value, list):
        return [_expand_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _expand_value(item) for key, item in value.items()}
    return value


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
        cfg["workspace_path"] = str(_resolve_path(_expand_env(workspace_path), PROJECT_ROOT))
    return cfg


def _normalise_agent_name(agent_name: str) -> str:
    return _AGENT_NAME_ALIASES.get(agent_name, agent_name)


def _coerce_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _merge_agent_defaults(raw_defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = dict(_DEFAULT_AGENT_SETTINGS)
    if raw_defaults:
        defaults.update({key: _expand_value(value) for key, value in raw_defaults.items()})
    defaults["provider"] = str(defaults.get("provider", _DEFAULT_AGENT_SETTINGS["provider"]))
    defaults["model"] = str(defaults.get("model", _DEFAULT_AGENT_SETTINGS["model"]))
    defaults["fallback_model"] = str(
        defaults.get("fallback_model", _DEFAULT_AGENT_SETTINGS["fallback_model"]),
    )
    defaults["base_url"] = str(defaults.get("base_url", _DEFAULT_AGENT_SETTINGS["base_url"]))
    defaults["api_key"] = str(defaults.get("api_key", _DEFAULT_AGENT_SETTINGS["api_key"]))
    defaults["temperature"] = _coerce_float(
        defaults.get("temperature", _DEFAULT_AGENT_SETTINGS["temperature"]),
        float(_DEFAULT_AGENT_SETTINGS["temperature"]),
    )
    defaults["max_tokens"] = _coerce_optional_int(defaults.get("max_tokens"))
    defaults["enabled"] = bool(defaults.get("enabled", True))
    return defaults


def _format_toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, "g")
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def _dump_agent_models_toml(config: dict[str, Any]) -> str:
    ordered_sections = list(_AGENT_SECTION_ORDER)
    ordered_sections.extend(
        name for name in sorted(config) if name not in _AGENT_SECTION_ORDER and isinstance(config[name], dict)
    )

    lines = [
        "# AutoHySeeker LLM model configuration",
        "# Last updated: 2026-03-24",
        "",
    ]
    for section_name in ordered_sections:
        section = config.get(section_name)
        if not isinstance(section, dict):
            continue
        lines.append(f"[{section_name}]")
        for key, value in section.items():
            if isinstance(value, (dict, list)):
                continue
            lines.append(f"{key} = {_format_toml_scalar(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


_orchestrator_config: dict[str, Any] | None = None
_monitor_config: dict[str, Any] | None = None
_designer_config: dict[str, Any] | None = None
_knowledge_config: dict[str, Any] | None = None
_project_configs: dict[str, dict[str, Any]] | None = None
_agent_models_config: dict[str, dict[str, Any]] | None = None


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


def get_agent_models_config(*, reload: bool = False) -> dict[str, dict[str, Any]]:
    global _agent_models_config
    if reload or _agent_models_config is None:
        raw = _load_toml(_AGENT_CONFIG_PATH)
        parsed: dict[str, dict[str, Any]] = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                parsed[str(key)] = {
                    str(section_key): _expand_value(section_value)
                    for section_key, section_value in value.items()
                }
        if "defaults" not in parsed:
            parsed["defaults"] = {}
        _agent_models_config = parsed
    return {key: dict(value) for key, value in _agent_models_config.items()}


def get_default_llm_config(*, reload: bool = False) -> dict[str, Any]:
    raw = get_agent_models_config(reload=reload).get("defaults", {})
    return _merge_agent_defaults(raw if isinstance(raw, dict) else None)


def load_agent_config(agent_name: str, *, reload: bool = False) -> dict[str, Any]:
    section_name = _normalise_agent_name(agent_name)
    parsed = get_agent_models_config(reload=reload)
    defaults = get_default_llm_config(reload=reload)
    section = parsed.get(section_name, {})
    if not isinstance(section, dict):
        section = {}

    resolved: dict[str, Any] = {
        "name": str(section.get("name", section_name)),
        "provider": str(section.get("provider", defaults["provider"])),
        "enabled": bool(section.get("enabled", defaults["enabled"])),
        "model": str(section.get("model", defaults["model"])),
        "fallback_model": str(section.get("fallback_model", defaults["fallback_model"])),
        "api_key": str(section.get("api_key", defaults["api_key"])),
        "temperature": _coerce_float(section.get("temperature", defaults["temperature"]), defaults["temperature"]),
        "max_tokens": _coerce_optional_int(section.get("max_tokens", defaults["max_tokens"])),
        "base_url": str(section.get("base_url", defaults["base_url"])),
    }
    for passthrough_key in ("pricing_input", "pricing_output", "context_window"):
        if passthrough_key in section:
            resolved[passthrough_key] = section[passthrough_key]
    return resolved


def update_agent_model_config(agent_name: str, updates: dict[str, Any]) -> dict[str, Any]:
    section_name = _normalise_agent_name(agent_name)
    parsed = _load_toml(_AGENT_CONFIG_PATH)
    section = parsed.get(section_name, {})
    if not isinstance(section, dict):
        section = {}

    for key, value in updates.items():
        if value is None:
            section.pop(key, None)
            continue
        if key in {"temperature"}:
            section[key] = float(value)
        elif key in {"max_tokens"}:
            coerced = _coerce_optional_int(value)
            if coerced is None:
                section.pop(key, None)
            else:
                section[key] = coerced
        elif key in {"enabled"}:
            section[key] = bool(value)
        else:
            section[key] = str(value)

    parsed[section_name] = section
    _AGENT_CONFIG_PATH.write_text(_dump_agent_models_toml(parsed), encoding="utf-8")
    reload_all_configs()
    return load_agent_config(section_name, reload=True)


def reload_all_configs() -> None:
    """Force reload all TOML configs under configs/."""
    global ORCHESTRATOR_CONFIG, MONITOR_CONFIG, DESIGNER_CONFIG, KNOWLEDGE_CONFIG, PROJECT_CONFIGS
    global AGENT_MODELS_CONFIG, OPENAI_BASE_URL, OPENAI_API_KEY, DEFAULT_MODEL, FALLBACK_MODEL
    AGENT_MODELS_CONFIG = get_agent_models_config(reload=True)
    defaults = get_default_llm_config(reload=True)
    OPENAI_BASE_URL = str(defaults["base_url"])
    OPENAI_API_KEY = str(defaults["api_key"])
    DEFAULT_MODEL = str(defaults["model"])
    FALLBACK_MODEL = str(defaults["fallback_model"])
    ORCHESTRATOR_CONFIG = get_orchestrator_config(reload=True)
    MONITOR_CONFIG = get_monitor_config(reload=True)
    DESIGNER_CONFIG = get_designer_config(reload=True)
    KNOWLEDGE_CONFIG = get_knowledge_config(reload=True)
    PROJECT_CONFIGS = load_project_configs(reload=True)


_default_llm_config = get_default_llm_config()
OPENAI_BASE_URL = str(_default_llm_config["base_url"])
OPENAI_API_KEY = str(_default_llm_config["api_key"])
DEFAULT_MODEL = str(_default_llm_config["model"])
FALLBACK_MODEL = str(_default_llm_config["fallback_model"])
OPENAI_CONNECT_TIMEOUT_SECONDS = float(os.getenv("OPENAI_CONNECT_TIMEOUT_SECONDS", "5"))
OPENAI_UNAVAILABLE_COOLDOWN_SECONDS = float(
    os.getenv("OPENAI_UNAVAILABLE_COOLDOWN_SECONDS", "60"),
)
DATA_ROOT = _resolve_path(os.getenv("DATA_ROOT", "../data"), PROJECT_ROOT)
LOG_ROOT = _resolve_path(os.getenv("LOG_ROOT", "../logs"), PROJECT_ROOT)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8200"))
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))

ORCHESTRATOR_CONFIG = get_orchestrator_config()
MONITOR_CONFIG = get_monitor_config()
DESIGNER_CONFIG = get_designer_config()
KNOWLEDGE_CONFIG = get_knowledge_config()
PROJECT_CONFIGS = load_project_configs()
AGENT_MODELS_CONFIG = get_agent_models_config()


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
    "AGENT_MODELS_CONFIG",
    "get_orchestrator_config",
    "get_monitor_config",
    "get_designer_config",
    "get_knowledge_config",
    "load_project_configs",
    "get_project_config",
    "get_agent_models_config",
    "get_default_llm_config",
    "load_agent_config",
    "update_agent_model_config",
    "reload_all_configs",
]
