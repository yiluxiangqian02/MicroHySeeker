"""A0 text LLM readiness check.

Reads AutoHySeeker/configs/agent_models.toml [chat] section as the single source
for text LLM settings and validates required fields. Optional --probe sends one
minimal completion request through OpenAI-compatible endpoint.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
AUTOHYSEEKER = HERE.parent
AGENT_MODELS_PATH = AUTOHYSEEKER / "configs" / "agent_models.toml"
_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env(value: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        expr = match.group(1)
        if ":-" in expr:
            var, default = expr.split(":-", 1)
            return os.environ.get(var, default)
        return os.environ.get(expr, "")

    return _ENV_PATTERN.sub(_sub, value)


def _expand_value(value: Any) -> Any:
    if isinstance(value, str):
        return _expand_env(value)
    if isinstance(value, list):
        return [_expand_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _expand_value(v) for k, v in value.items()}
    return value


def load_chat_config() -> dict[str, Any]:
    if not AGENT_MODELS_PATH.exists():
        raise RuntimeError(f"Config not found: {AGENT_MODELS_PATH}")

    with AGENT_MODELS_PATH.open("rb") as fh:
        raw = tomllib.load(fh)

    defaults = raw.get("defaults", {})
    chat = raw.get("chat", {})
    if not isinstance(defaults, dict):
        defaults = {}
    if not isinstance(chat, dict):
        raise RuntimeError("[chat] section missing in agent_models.toml")

    defaults = _expand_value(defaults)
    chat = _expand_value(chat)

    resolved = {
        "provider": str(chat.get("provider", defaults.get("provider", "openai"))),
        "model": str(chat.get("model", defaults.get("model", ""))),
        "base_url": str(chat.get("base_url", defaults.get("base_url", ""))),
        "api_key": str(chat.get("api_key", defaults.get("api_key", ""))),
        "enabled": bool(chat.get("enabled", True)),
    }
    return resolved


def validate_chat_config(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not cfg.get("enabled", True):
        errors.append("[chat].enabled=false")
    if not cfg.get("provider"):
        errors.append("provider is empty")
    if not cfg.get("model"):
        errors.append("model is empty")
    if not cfg.get("base_url"):
        errors.append("base_url is empty")
    if not cfg.get("api_key"):
        errors.append("api_key is empty after env expansion")
    return errors


def probe_chat_completion(cfg: dict[str, Any], prompt: str) -> str:
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("openai package not installed") from exc

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    completion = client.chat.completions.create(
        model=cfg["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        top_p=0.7,
        stream=False,
    )

    if not completion.choices:
        return ""
    content = completion.choices[0].message.content
    return (content or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="A0 text LLM readiness check via [chat] config")
    parser.add_argument("--probe", action="store_true", help="Run one minimal completion request")
    parser.add_argument(
        "--prompt",
        default="Which number is larger, 9.11 or 9.8?",
        help="Prompt used when --probe is enabled",
    )
    args = parser.parse_args()

    try:
        cfg = load_chat_config()
    except Exception as exc:
        print(f"[A0][ERR] failed to read chat config: {exc}")
        sys.exit(2)

    errs = validate_chat_config(cfg)
    if errs:
        print("[A0][ERR] chat config invalid:")
        for err in errs:
            print(f"  - {err}")
        sys.exit(3)

    print("[A0][OK] chat config loaded from configs/agent_models.toml [chat]")
    print(f"  provider={cfg['provider']}")
    print(f"  model={cfg['model']}")
    print(f"  base_url={cfg['base_url']}")
    print(f"  api_key_prefix={(cfg['api_key'][:6] if cfg['api_key'] else 'empty')}")

    if not args.probe:
        return

    try:
        reply = probe_chat_completion(cfg, args.prompt)
        print("[A0][OK] probe completed")
        print(f"  reply={reply[:200]}")
    except Exception as exc:
        print(f"[A0][ERR] probe failed: {exc}")
        sys.exit(4)


if __name__ == "__main__":
    main()
