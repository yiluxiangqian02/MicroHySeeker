"""Runtime configuration for AutoHySeeker."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


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
