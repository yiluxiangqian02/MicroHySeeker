"""Experiment control stubs. Real hardware integration comes in later phases."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def start_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "stub",
        "action": "start_experiment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Hardware execution is not implemented in this phase.",
        "payload": payload or {},
    }


def stop_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "stub",
        "action": "stop_experiment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Hardware execution is not implemented in this phase.",
        "payload": payload or {},
    }

