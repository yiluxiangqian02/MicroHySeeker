"""Config-driven L1 realtime monitoring rule engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.common.config import get_monitor_config
from src.skills.base import BaseSkill, SkillResult

_DEFAULT_RULES = {
    "pump_speed_deviation_pct": 5.0,
    "communication_timeout_s": 3.0,
    "step_timeout_multiplier": 2.0,
    "current_spike_pct": 50.0,
}
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class RealtimeMonitorSkill(BaseSkill):
    """Evaluate a single runtime snapshot against deterministic L1 rules."""

    name = "realtime_monitor"
    description = "Evaluate live experiment snapshots using deterministic L1 rules."
    required_tools: list[str] = []

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._enabled = True
        self._poll_interval_s = 2.0
        self._rules = dict(_DEFAULT_RULES)
        self.reload_config(config)

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Evaluate a monitor snapshot and return structured anomalies."""
        if kwargs.get("reload_config"):
            self.reload_config()

        snapshot = self._build_snapshot(kwargs)
        report = self.evaluate_snapshot(snapshot)
        highest = report["highest_severity"]
        message = f"L1 monitor evaluated snapshot: {report['anomaly_count']} anomalies"
        return SkillResult(
            success=highest not in {"high", "critical"},
            data=report,
            message=message,
            artifacts=[],
        )

    def reload_config(self, config: dict[str, Any] | None = None) -> None:
        """Reload realtime-monitor thresholds from the Phase 1 config."""
        raw = config
        if raw is None:
            raw = get_monitor_config().get("realtime_monitor", {})

        if not isinstance(raw, dict):
            raw = {}

        rules = raw.get("rules", {})
        if not isinstance(rules, dict):
            rules = {}

        merged_rules = dict(_DEFAULT_RULES)
        for key, value in rules.items():
            if isinstance(value, (int, float)):
                merged_rules[key] = float(value)

        self._enabled = bool(raw.get("enabled", True))
        self._poll_interval_s = float(raw.get("poll_interval_s", 2.0))
        self._rules = merged_rules

    def evaluate_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Run all six realtime rules against a monitoring snapshot."""
        anomalies: list[dict[str, Any]] = []
        anomalies.extend(self._check_pump_speed_deviation(snapshot))
        anomalies.extend(self._check_communication_timeout(snapshot))
        anomalies.extend(self._check_step_timeout(snapshot))
        anomalies.extend(self._check_data_file_empty(snapshot))
        anomalies.extend(self._check_pump_no_response(snapshot))
        anomalies.extend(self._check_current_spike(snapshot))

        highest = "low"
        if anomalies:
            highest = max(
                (item["severity"] for item in anomalies),
                key=lambda value: _SEVERITY_RANK.get(value, -1),
            )

        return {
            "source": "L1_realtime_monitor",
            "enabled": self._enabled,
            "poll_interval_s": self._poll_interval_s,
            "rule_thresholds": dict(self._rules),
            "snapshot": snapshot,
            "anomaly_count": len(anomalies),
            "highest_severity": highest,
            "should_stop": highest in {"high", "critical"},
            "should_emergency_stop": highest == "critical",
            "anomalies": anomalies,
        }

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "status": {"type": "object"},
                "snapshot": {"type": "object"},
                "pump_actual_rpm": {"type": "object"},
                "pump_target_rpm": {"type": "object"},
                "communication_age_s": {"type": "number"},
                "current_step_elapsed_s": {"type": "number"},
                "expected_step_duration_s": {"type": "number"},
                "data_file_size_bytes": {"type": "number"},
                "current_values": {"type": "array"},
            },
            "required": [],
        }

    def _build_snapshot(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        status = kwargs.get("status", {})
        snapshot = kwargs.get("snapshot", {})

        combined: dict[str, Any] = {}
        if isinstance(status, dict):
            combined.update(status)
        if isinstance(snapshot, dict):
            combined.update(snapshot)

        passthrough_keys = {
            "run_id",
            "trace_id",
            "pump_actual_rpm",
            "pump_target_rpm",
            "pump_responsive",
            "communication_age_s",
            "current_step_elapsed_s",
            "expected_step_duration_s",
            "data_file_path",
            "data_file_size_bytes",
            "current_values",
            "current_value",
            "previous_current_value",
            "status",
            "state",
        }
        for key in passthrough_keys:
            value = kwargs.get(key)
            if value is not None:
                combined[key] = value

        if "timestamp" not in combined:
            combined["timestamp"] = datetime.now(timezone.utc).isoformat()
        return combined

    def _check_pump_speed_deviation(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        actual = _coerce_number_map(snapshot.get("pump_actual_rpm"))
        target = _coerce_number_map(snapshot.get("pump_target_rpm"))
        threshold = self._rules["pump_speed_deviation_pct"]
        anomalies: list[dict[str, Any]] = []

        for pump_id, actual_rpm in actual.items():
            target_rpm = target.get(pump_id)
            if target_rpm is None or target_rpm == 0:
                continue
            deviation_pct = abs(actual_rpm - target_rpm) / abs(target_rpm) * 100.0
            if deviation_pct > threshold:
                anomalies.append(
                    self._make_anomaly(
                        rule="pump_speed_deviation",
                        anomaly_type="pump_speed_deviation",
                        severity="medium",
                        details=(
                            f"pump {pump_id}: target={target_rpm:.3f} RPM, "
                            f"actual={actual_rpm:.3f} RPM, deviation={deviation_pct:.2f}%"
                        ),
                        snapshot=snapshot,
                        pump_address=pump_id,
                        deviation_pct=round(deviation_pct, 2),
                    )
                )
        return anomalies

    def _check_communication_timeout(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        timeout_s = _first_number(
            snapshot,
            "communication_age_s",
            "last_communication_age_s",
            "communication_timeout_s",
        )
        if timeout_s is None:
            return []

        threshold = self._rules["communication_timeout_s"]
        if timeout_s <= threshold:
            return []

        return [
            self._make_anomaly(
                rule="communication_timeout",
                anomaly_type="communication_timeout",
                severity="high",
                details=f"communication age {timeout_s:.2f}s exceeds {threshold:.2f}s",
                snapshot=snapshot,
                observed_seconds=round(timeout_s, 2),
            )
        ]

    def _check_step_timeout(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        elapsed_s = _first_number(
            snapshot,
            "current_step_elapsed_s",
            "step_elapsed_s",
        )
        expected_s = _first_number(
            snapshot,
            "expected_step_duration_s",
            "step_expected_duration_s",
            "step_duration_expected_s",
        )
        if elapsed_s is None or expected_s is None or expected_s <= 0:
            return []

        multiplier = self._rules["step_timeout_multiplier"]
        threshold_s = expected_s * multiplier
        if elapsed_s <= threshold_s:
            return []

        return [
            self._make_anomaly(
                rule="step_timeout",
                anomaly_type="step_timeout",
                severity="high",
                details=(
                    f"step elapsed {elapsed_s:.2f}s exceeds expected {expected_s:.2f}s "
                    f"x {multiplier:.2f}"
                ),
                snapshot=snapshot,
                observed_seconds=round(elapsed_s, 2),
                expected_seconds=round(expected_s, 2),
            )
        ]

    def _check_data_file_empty(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        size_bytes = _first_number(snapshot, "data_file_size_bytes", "file_size_bytes")
        data_file_path = snapshot.get("data_file_path") or snapshot.get("run_data_path")
        if size_bytes is None or size_bytes > 0 or not data_file_path:
            return []

        return [
            self._make_anomaly(
                rule="data_file_empty",
                anomaly_type="data_file_empty",
                severity="medium",
                details=f"data file is empty: {data_file_path}",
                snapshot=snapshot,
                file_path=str(data_file_path),
            )
        ]

    def _check_pump_no_response(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        pump_responsive = snapshot.get("pump_responsive")
        anomalies: list[dict[str, Any]] = []

        if isinstance(pump_responsive, dict):
            for pump_id, responsive in pump_responsive.items():
                if responsive is False:
                    anomalies.append(
                        self._make_anomaly(
                            rule="pump_no_response",
                            anomaly_type="pump_error",
                            severity="critical",
                            details=f"pump {pump_id} did not respond",
                            snapshot=snapshot,
                            pump_address=pump_id,
                            sub_type="pump_no_response",
                        )
                    )

        pump_status = str(snapshot.get("pump_status", "")).strip().lower()
        if pump_status in {"no_response", "unreachable", "offline"}:
            anomalies.append(
                self._make_anomaly(
                    rule="pump_no_response",
                    anomaly_type="pump_error",
                    severity="critical",
                    details=f"pump status abnormal: {pump_status}",
                    snapshot=snapshot,
                    sub_type="pump_no_response",
                )
            )

        return anomalies

    def _check_current_spike(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        threshold = self._rules["current_spike_pct"]
        current_values = snapshot.get("current_values")

        previous_value: float | None = None
        current_value: float | None = None
        if isinstance(current_values, list) and len(current_values) >= 2:
            previous_value = _to_float(current_values[-2])
            current_value = _to_float(current_values[-1])
        else:
            previous_value = _to_float(snapshot.get("previous_current_value"))
            current_value = _to_float(snapshot.get("current_value"))

        if previous_value is None or current_value is None:
            return []

        baseline = max(abs(previous_value), 1e-9)
        spike_pct = abs(current_value - previous_value) / baseline * 100.0
        if spike_pct <= threshold:
            return []

        return [
            self._make_anomaly(
                rule="current_spike",
                anomaly_type="echem_current_spike",
                severity="medium",
                details=(
                    f"current changed from {previous_value:.6f} to {current_value:.6f} "
                    f"({spike_pct:.2f}%)"
                ),
                snapshot=snapshot,
                spike_pct=round(spike_pct, 2),
            )
        ]

    def _make_anomaly(
        self,
        *,
        rule: str,
        anomaly_type: str,
        severity: str,
        details: str,
        snapshot: dict[str, Any],
        **extra: Any,
    ) -> dict[str, Any]:
        anomaly = {
            "type": anomaly_type,
            "severity": severity,
            "rule": rule,
            "details": details,
            "source": "L1_realtime_monitor",
            "run_id": snapshot.get("run_id", ""),
            "trace_id": snapshot.get("trace_id", ""),
            "timestamp": snapshot.get("timestamp"),
        }
        anomaly.update(extra)
        return anomaly


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _coerce_number_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}

    result: dict[str, float] = {}
    for key, item in value.items():
        parsed = _to_float(item)
        if parsed is not None:
            result[str(key)] = parsed
    return result


def _first_number(snapshot: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        parsed = _to_float(snapshot.get(key))
        if parsed is not None:
            return parsed
    return None
