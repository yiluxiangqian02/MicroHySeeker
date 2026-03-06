"""Experiment control stubs. Real hardware integration comes in later phases."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger("autohyseeker.experiment_ctrl")

_STUB_MSG = (
    "[STUB] Hardware execution is not implemented. "
    "Replace experiment_ctrl.py with a real hardware driver before running on equipment."
)


def start_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _logger.warning("start_experiment: Hardware interface not implemented")
    return {
        "status": "stub",
        "action": "start_experiment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Hardware execution is not implemented in this phase.",
        "payload": payload or {},
    }


def stop_experiment(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _logger.warning("stop_experiment: Hardware interface not implemented")
    return {
        "status": "stub",
        "action": "stop_experiment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Hardware execution is not implemented in this phase.",
        "payload": payload or {},
    }

