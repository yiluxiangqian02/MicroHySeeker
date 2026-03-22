"""Experiment executor agent — hardware-facing experiment lifecycle manager.

The executor is the **only** agent that directly operates hardware through the
MicroHySeeker API.  Its responsibilities are:

1. Pre-flight checks (system health, RS485 connection).
2. Parameter validation via dry-run instantiation.
3. Experiment start (template instantiation with overrides).
4. Real-time status monitoring with anomaly detection.
5. Data collection on completion.
6. Emergency stop on critical failures.

The executor does NOT design parameters (Designer's job), analyse data
(Analyst's job), or make strategic decisions (Orchestrator's job).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.common.config import DESIGNER_CONFIG, KNOWLEDGE_CONFIG, MONITOR_CONFIG, ORCHESTRATOR_CONFIG
from src.skills.heartbeat_inspector_skill import HeartbeatInspectorSkill
from src.skills.realtime_monitor_skill import RealtimeMonitorSkill

_logger = logging.getLogger("autohyseeker.exp_executor")
_SHARED_EXECUTOR: "ExperimentExecutorAgent | None" = None

# ── Severity ordering ─────────────────────────────────────────────────────────
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

EXECUTOR_SYSTEM_PROMPT = """\
你是实验执行 Agent（Experiment Executor），负责通过 MicroHySeeker 硬件系统执行电化学实验。

## 工作流程
1. 执行预检查：确认系统健康、串口连接正常
2. 验证参数：通过 dry_run 模式确认参数合法
3. 启动实验：调用模板实例化 API
4. 监控进度：轮询实验状态，检测异常
5. 收集数据：实验完成后获取数据路径

## 安全规则（最高优先级）
- 所有泵转速不得超过 300 RPM
- 检测到 HIGH 异常时必须停止当前步骤并上报
- 检测到 CRITICAL 异常时必须执行紧急停止 (emergency_stop)
- 不确定的操作宁可停止也不冒险继续

## 异常分类
- LOW: 记录日志，继续执行
- MEDIUM: 记录日志，上报 Orchestrator，等待指示
- HIGH: 停止当前步骤，上报 Orchestrator
- CRITICAL: 执行 emergency_stop，立即上报
"""


class ExperimentExecutorAgent(BaseAgent):
    """Experiment executor — manages the full experiment lifecycle via API."""

    def __init__(self) -> None:
        super().__init__(
            name="experiment_executor",
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
        )
        self._monitoring = False
        self._current_run_id: str | None = None
        self._realtime_monitor_skill = RealtimeMonitorSkill()
        self._heartbeat_inspector_skill = HeartbeatInspectorSkill()
        self._last_l1_report: dict[str, Any] | None = None
        self._last_l2_report: dict[str, Any] | None = None
        self._heartbeat_last_run_at: float | None = None
        self._last_observed_step: int | None = None
        self._last_step_change_at: float | None = None
        self._recent_currents: list[float] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    async def execute_experiment(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a complete experiment: pre-check → validate → start → monitor → collect.

        Args:
            task: Dict with keys ``template_id``, ``step_overrides`` (optional),
                ``exp_name`` (optional), ``pre_check`` (bool, default True),
                ``monitor_interval_s`` (float, default 5).

        Returns:
            Result dict with ``status``, ``run_id``, ``duration_s``, etc.
        """
        start_ts = time.monotonic()
        self._current_run_id = None
        self._heartbeat_last_run_at = None
        self._last_l1_report = None
        self._last_l2_report = None
        self._last_observed_step = None
        self._last_step_change_at = None
        self._recent_currents = []
        if "heartbeat_enabled" in task:
            self._heartbeat_inspector_skill.set_enabled(bool(task["heartbeat_enabled"]))

        # ── 1. Pre-flight checks ──────────────────────────────────────────────
        if task.get("pre_check", True):
            health = await self._pre_check()
            if not health["ok"]:
                _logger.warning("Pre-check failed: %s", health["error"])
                return {
                    "status": "pre_check_failed",
                    "error": health["error"],
                    "duration_s": time.monotonic() - start_ts,
                }

        # ── 2. Validate parameters (dry-run) ─────────────────────────────────
        template_id = task.get("template_id", "")
        step_overrides = task.get("step_overrides", {})
        if not template_id:
            return {
                "status": "validation_failed",
                "error": "template_id is required",
                "duration_s": time.monotonic() - start_ts,
            }

        validation = await self._validate_params(template_id, step_overrides)
        if not validation["valid"]:
            _logger.warning("Validation failed: %s", validation["errors"])
            return {
                "status": "validation_failed",
                "errors": validation["errors"],
                "duration_s": time.monotonic() - start_ts,
            }

        # ── 3. Start experiment ───────────────────────────────────────────────
        try:
            start_result = await self._start_experiment(
                template_id=template_id,
                step_overrides=step_overrides,
                exp_name=task.get("exp_name"),
            )
            self._current_run_id = start_result.get("run_id")
            _logger.info(
                "Experiment started: run_id=%s", self._current_run_id
            )
        except Exception as exc:
            _logger.error("Experiment start failed: %s", exc)
            return {
                "status": "start_failed",
                "error": str(exc),
                "duration_s": time.monotonic() - start_ts,
            }

        environment_snapshot = await self._record_environment_snapshot(
            template_id=template_id,
            params_source=str(task.get("params_source", "executor_task")),
        )

        # ── 4. Monitor until complete ─────────────────────────────────────────
        interval = task.get("monitor_interval_s", 5.0)
        monitor_result = await self._monitor_until_complete(interval_s=interval, task=task)
        monitor_result["duration_s"] = time.monotonic() - start_ts
        monitor_result["environment_snapshot"] = environment_snapshot
        monitor_result["monitor_status"] = self.get_monitor_status()

        # ── 5. Collect data on success ────────────────────────────────────────
        if monitor_result["status"] == "completed" and self._current_run_id:
            data = await self._collect_data(self._current_run_id)
            monitor_result["data_path"] = data.get("data_path", "")

        return monitor_result

    async def emergency_stop(self) -> dict[str, Any]:
        """Execute immediate emergency stop via API."""
        self._monitoring = False
        try:
            from src.tools import experiment_ctrl as ctrl
            result = ctrl.emergency_stop()
            _logger.warning("Emergency stop executed: %s", result)
            return {"ok": True, "result": result}
        except Exception as exc:
            _logger.error("Emergency stop FAILED: %s", exc)
            return {"ok": False, "error": str(exc)}

    def stop_monitoring(self) -> None:
        """Cancel the monitoring loop (called externally by Orchestrator)."""
        self._monitoring = False
        _logger.info("Monitoring stop requested")

    def set_heartbeat_enabled(self, enabled: bool) -> None:
        """Enable/disable the L2 heartbeat inspector at runtime."""
        self._heartbeat_inspector_skill.set_enabled(enabled)

    def get_monitor_status(self) -> dict[str, Any]:
        """Return the current state of the embedded L1/L2 monitors."""
        return {
            "monitoring": self._monitoring,
            "run_id": self._current_run_id,
            "l1": self._last_l1_report or {},
            "l2": self._last_l2_report or {},
            "heartbeat_last_run_at": self._heartbeat_last_run_at,
        }

    def update_monitor_config(
        self,
        *,
        heartbeat: dict[str, Any] | None = None,
        realtime: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update embedded monitor configs and return current monitor status."""
        if heartbeat is not None:
            self._heartbeat_inspector_skill.reload_config(heartbeat)
        if realtime is not None:
            self._realtime_monitor_skill.reload_config(realtime)
        return self.get_monitor_status()

    @property
    def is_monitoring(self) -> bool:
        """True while a monitoring loop is running."""
        return self._monitoring

    @property
    def current_run_id(self) -> str | None:
        return self._current_run_id

    # ── Private: Pre-check ────────────────────────────────────────────────────

    async def _pre_check(self) -> dict[str, Any]:
        """Check system health and RS485 connection."""
        try:
            from src.tools import experiment_ctrl as ctrl
        except ImportError:
            return {"ok": False, "error": "experiment_ctrl module not available"}

        try:
            health = ctrl.health_check()
            if health.get("status") != "ok":
                return {"ok": False, "error": f"Health check: {health}"}
        except Exception as exc:
            return {"ok": False, "error": f"Health check failed: {exc}"}

        try:
            conn = ctrl.get_connection_info()
            if not conn.get("connected"):
                return {"ok": False, "error": "RS485 not connected"}
        except Exception as exc:
            return {"ok": False, "error": f"Connection check failed: {exc}"}

        return {"ok": True}

    async def _record_environment_snapshot(
        self,
        *,
        template_id: str,
        params_source: str,
    ) -> dict[str, Any]:
        """Capture a reproducibility snapshot for the current execution."""
        device_status: dict[str, Any] = {}
        try:
            from src.tools import experiment_ctrl as ctrl

            try:
                device_status["health"] = ctrl.health_check()
            except Exception as exc:
                device_status["health_error"] = str(exc)
            try:
                device_status["connection"] = ctrl.get_connection_info()
            except Exception as exc:
                device_status["connection_error"] = str(exc)
            try:
                device_status["pump_status"] = ctrl.get_pump_status()
            except Exception as exc:
                device_status["pump_status_error"] = str(exc)
        except ImportError:
            device_status["module"] = "experiment_ctrl unavailable"

        config_payload = {
            "orchestrator": ORCHESTRATOR_CONFIG,
            "monitor": MONITOR_CONFIG,
            "designer": DESIGNER_CONFIG,
            "knowledge": KNOWLEDGE_CONFIG,
        }
        config_hash = hashlib.sha256(
            json.dumps(config_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_status": device_status,
            "software_version": "0.1.0",
            "config_hash": config_hash,
            "params_source": params_source,
            "template_id": template_id,
        }

    # ── Private: Validation ───────────────────────────────────────────────────

    async def _validate_params(
        self,
        template_id: str,
        step_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate experiment parameters via dry-run instantiation."""
        try:
            from src.tools import experiment_ctrl as ctrl
        except ImportError:
            return {"valid": False, "errors": ["experiment_ctrl not available"]}

        try:
            result = ctrl.instantiate_template(
                template_id=template_id,
                overrides={"step_overrides": step_overrides},
                dry_run=True,
            )
            if result.get("status") == "error":
                return {
                    "valid": False,
                    "errors": result.get("errors", [result.get("message", "unknown")]),
                }
            experiment = result.get("experiment")
            if isinstance(experiment, dict):
                solution_errors = self._validate_solution_configuration(ctrl, experiment)
                if solution_errors:
                    return {"valid": False, "errors": solution_errors}
            return {"valid": True}
        except Exception as exc:
            return {"valid": False, "errors": [str(exc)]}

    # ── Private: Start ────────────────────────────────────────────────────────

    def _validate_solution_configuration(
        self,
        ctrl: Any,
        experiment: dict[str, Any],
    ) -> list[str]:
        """Ensure prep-sol solution names exist in MicroHySeeker capabilities."""
        if not hasattr(ctrl, "get_capabilities"):
            return []

        try:
            capabilities = ctrl.get_capabilities()
        except Exception as exc:
            return [f"Failed to query MicroHySeeker capabilities: {exc}"]

        if not isinstance(capabilities, dict):
            return []

        available = [
            item.get("name", "").strip()
            for item in capabilities.get("dilution_solutions", [])
            if isinstance(item, dict) and item.get("name")
        ]
        if not available:
            return []

        required = self._extract_required_solution_names(experiment)
        missing = [name for name in required if name not in available]
        if not missing:
            return []

        return [
            "Template requires dilution solutions not present in MicroHySeeker "
            f"config: {missing}. Available solutions: {available}"
        ]

    def _extract_required_solution_names(self, experiment: dict[str, Any]) -> list[str]:
        """Extract selected prep-sol solution names from an instantiated experiment."""
        names: list[str] = []
        for step in experiment.get("steps", []):
            if not isinstance(step, dict) or step.get("step_type") != "prep_sol":
                continue
            params = step.get("prep_sol_params") or {}
            selected = params.get("selected_solutions") or {}
            if isinstance(selected, dict) and selected:
                names.extend(
                    str(name)
                    for name, enabled in selected.items()
                    if enabled
                )
                continue
            injection_order = params.get("injection_order") or []
            if isinstance(injection_order, list):
                names.extend(str(name) for name in injection_order)

        deduped: list[str] = []
        for name in names:
            if name not in deduped:
                deduped.append(name)
        return deduped

    async def _start_experiment(
        self,
        template_id: str,
        step_overrides: dict[str, Any],
        exp_name: str | None = None,
    ) -> dict[str, Any]:
        """Instantiate template and start experiment."""
        from src.tools import experiment_ctrl as ctrl

        overrides: dict[str, Any] = {"step_overrides": step_overrides}
        if exp_name:
            overrides["exp_name"] = exp_name

        result = ctrl.instantiate_template(
            template_id=template_id,
            overrides=overrides,
            dry_run=False,
        )

        if result.get("status") == "error":
            raise RuntimeError(f"Template instantiation failed: {result.get('message')}")

        return result

    # ── Private: Monitor ──────────────────────────────────────────────────────

    async def _monitor_until_complete(
        self,
        interval_s: float = 5.0,
        task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Poll experiment status until completion, failure, or external stop.

        Returns a result dict with ``status``, ``run_id``, ``anomalies``, etc.
        """
        self._monitoring = True
        task = task or {}
        anomalies: list[dict[str, Any]] = []
        seen_log_ids: set[str] = set()

        try:
            from src.tools import experiment_ctrl as ctrl
        except ImportError:
            self._monitoring = False
            return {
                "status": "error",
                "run_id": self._current_run_id,
                "error": "experiment_ctrl not available",
            }

        poll_count = 0
        while self._monitoring:
            poll_count += 1

            # ── Get experiment status ─────────────────────────────────────
            try:
                status = ctrl.get_experiment_status()
            except Exception as exc:
                _logger.error("Status poll failed: %s", exc)
                anomalies.append({
                    "type": "status_poll_failed",
                    "severity": "medium",
                    "details": str(exc),
                    "poll": poll_count,
                })
                await asyncio.sleep(interval_s)
                continue

            monitor_snapshot = self._build_monitor_snapshot(status, task, interval_s, poll_count, anomalies)
            l1_result = await self._realtime_monitor_skill.execute(snapshot=monitor_snapshot)
            self._last_l1_report = l1_result.data if isinstance(l1_result.data, dict) else {}
            anomalies = self._merge_anomalies(
                anomalies,
                self._last_l1_report.get("anomalies", []),
            )

            l2_result = await self._heartbeat_inspector_skill.execute(
                snapshot=monitor_snapshot,
                last_run_at=self._heartbeat_last_run_at,
                now=time.monotonic(),
                force=bool(task.get("force_heartbeat", False)),
                allow_llm=bool(task.get("heartbeat_allow_llm", True)),
            )
            if isinstance(l2_result.data, dict) and l2_result.data.get("status") != "skipped":
                self._last_l2_report = l2_result.data
                self._heartbeat_last_run_at = float(l2_result.data.get("executed_at", time.monotonic()))
                heartbeat_anomaly = self._heartbeat_report_to_anomaly(l2_result.data)
                if heartbeat_anomaly is not None:
                    anomalies = self._merge_anomalies(anomalies, [heartbeat_anomaly])

            state = status.get("state", "unknown")

            # ── Completed (idle after running) ────────────────────────────
            if state == "idle" and poll_count > 1:
                _logger.info("Experiment completed (polls=%d)", poll_count)
                return {
                    "status": "completed",
                    "run_id": self._current_run_id,
                    "steps_completed": status.get("current_step", 0),
                    "steps_total": status.get("total_steps", 0),
                    "anomalies": anomalies,
                    "poll_count": poll_count,
                }

            # ── Error state ───────────────────────────────────────────────
            if state == "error" or status.get("has_error"):
                error_msg = status.get("error_message", "unknown error")
                _logger.error("Experiment error: %s", error_msg)
                classified = self._classify_error(error_msg, status)
                return {
                    "status": "failed",
                    "run_id": self._current_run_id,
                    "error": error_msg,
                    "anomaly": classified,
                    "steps_completed": status.get("current_step", 0),
                    "steps_total": status.get("total_steps", 0),
                    "anomalies": anomalies,
                    "poll_count": poll_count,
                }

            # ── Check warning logs for anomalies ─────────────────────────
            try:
                log_entries = ctrl.get_logs(n=20, level="warning")
                new_anomalies = self._detect_anomalies(
                    log_entries,
                    status,
                    seen_log_ids,
                )
                if new_anomalies:
                    anomalies.extend(new_anomalies)
                    max_sev = max(
                        (_SEVERITY_RANK.get(a["severity"], 0) for a in new_anomalies),
                        default=0,
                    )
                    if max_sev >= _SEVERITY_RANK["critical"]:
                        _logger.critical(
                            "CRITICAL anomaly detected — executing emergency stop"
                        )
                        await self.emergency_stop()
                        return {
                            "status": "emergency_stopped",
                            "run_id": self._current_run_id,
                            "anomaly": new_anomalies[-1],
                            "anomalies": anomalies,
                            "poll_count": poll_count,
                        }
                    if max_sev >= _SEVERITY_RANK["high"]:
                        _logger.warning("HIGH anomaly — stopping experiment")
                        self._monitoring = False
                        return {
                            "status": "failed",
                            "run_id": self._current_run_id,
                            "anomaly": new_anomalies[-1],
                            "anomalies": anomalies,
                            "poll_count": poll_count,
                        }
            except Exception as exc:
                _logger.debug("Log query failed (non-critical): %s", exc)

            critical_anomaly = self._highest_severity_anomaly(anomalies, "critical")
            if critical_anomaly and critical_anomaly.get("source") == "L1_realtime_monitor":
                _logger.critical("L1 CRITICAL anomaly detected — executing emergency stop")
                await self.emergency_stop()
                return {
                    "status": "emergency_stopped",
                    "run_id": self._current_run_id,
                    "anomaly": critical_anomaly,
                    "anomalies": anomalies,
                    "poll_count": poll_count,
                }

            high_anomaly = self._highest_severity_anomaly(anomalies, "high")
            if high_anomaly or critical_anomaly:
                chosen = critical_anomaly or high_anomaly
                _logger.warning("Monitor anomaly requires stop: %s", chosen)
                self._monitoring = False
                return {
                    "status": "failed",
                    "run_id": self._current_run_id,
                    "anomaly": chosen,
                    "anomalies": anomalies,
                    "poll_count": poll_count,
                }

            await asyncio.sleep(interval_s)

        # External stop requested
        return {
            "status": "stopped",
            "run_id": self._current_run_id,
            "anomalies": anomalies,
            "poll_count": poll_count,
        }

    # ── Private: Data Collection ──────────────────────────────────────────────

    async def _collect_data(self, run_id: str) -> dict[str, Any]:
        """Retrieve data path for completed experiment."""
        try:
            from src.tools import experiment_ctrl as ctrl
            detail = ctrl.get_run_detail(run_id)
            return {
                "data_path": detail.get("run_dir", ""),
                "files": detail.get("files", []),
            }
        except Exception as exc:
            _logger.warning("Data collection failed: %s", exc)
            return {"data_path": "", "error": str(exc)}

    # ── Private: Anomaly Detection ────────────────────────────────────────────

    def _detect_anomalies(
        self,
        log_entries: list[Any],
        status: dict[str, Any],
        seen_ids: set[str],
    ) -> list[dict[str, Any]]:
        """Detect anomalies from log entries and current status.

        Uses ``seen_ids`` set to avoid reporting the same log entry twice.
        """
        anomalies: list[dict[str, Any]] = []

        for entry in log_entries:
            # Entries can be strings or dicts
            if isinstance(entry, dict):
                text = entry.get("message", "")
                entry_id = entry.get("timestamp", "") + text[:50]
            else:
                text = str(entry)
                entry_id = text[:80]

            if entry_id in seen_ids:
                continue
            seen_ids.add(entry_id)

            text_lower = text.lower()

            if "emergency" in text_lower or "紧急" in text_lower:
                anomalies.append({
                    "type": "emergency_signal",
                    "severity": "critical",
                    "details": text,
                })
            elif "pump" in text_lower and "error" in text_lower:
                anomalies.append({
                    "type": "pump_error",
                    "severity": "high",
                    "details": text,
                })
            elif "timeout" in text_lower or "超时" in text_lower:
                anomalies.append({
                    "type": "communication_timeout",
                    "severity": "medium",
                    "details": text,
                })
            elif "warning" in text_lower or "警告" in text_lower:
                anomalies.append({
                    "type": "general_warning",
                    "severity": "low",
                    "details": text,
                })

        return anomalies

    def _build_monitor_snapshot(
        self,
        status: dict[str, Any],
        task: dict[str, Any],
        interval_s: float,
        poll_count: int,
        anomalies: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = time.monotonic()
        current_step = status.get("current_step")
        if current_step != self._last_observed_step:
            self._last_observed_step = current_step if isinstance(current_step, int) else None
            self._last_step_change_at = now

        step_elapsed_s = 0.0
        if self._last_step_change_at is not None:
            step_elapsed_s = now - self._last_step_change_at

        current_value = self._extract_current_value(status)
        if current_value is not None:
            self._recent_currents.append(current_value)
            self._recent_currents = self._recent_currents[-2:]

        snapshot: dict[str, Any] = dict(status)
        snapshot.update(
            {
                "run_id": self._current_run_id or status.get("run_id", ""),
                "poll_count": poll_count,
                "recent_anomalies": anomalies[-5:],
                "current_step_elapsed_s": step_elapsed_s,
                "expected_step_duration_s": float(task.get("expected_step_duration_s", max(interval_s * 2.0, 1.0))),
                "current_values": list(self._recent_currents),
            }
        )

        pump_target_rpm = task.get("pump_target_rpm")
        if isinstance(pump_target_rpm, dict):
            snapshot["pump_target_rpm"] = pump_target_rpm

        try:
            from src.tools import experiment_ctrl as ctrl

            connection = ctrl.get_connection_info()
            if not connection.get("connected", True):
                snapshot["communication_age_s"] = MONITOR_CONFIG.get("realtime_monitor", {}).get("rules", {}).get(
                    "communication_timeout_s",
                    3.0,
                ) + 1.0

            pump_status = ctrl.get_pump_status()
            if isinstance(pump_status, dict):
                pump_actual_rpm: dict[str, float] = {}
                pump_responsive: dict[str, bool] = {}
                pumps = pump_status.get("pumps", pump_status)
                if isinstance(pumps, dict):
                    iterable = pumps.items()
                elif isinstance(pumps, list):
                    iterable = (
                        (str(item.get("address", index + 1)), item)
                        for index, item in enumerate(pumps)
                        if isinstance(item, dict)
                    )
                else:
                    iterable = []

                for pump_id, item in iterable:
                    if not isinstance(item, dict):
                        continue
                    rpm = item.get("rpm") or item.get("current_rpm")
                    if isinstance(rpm, (int, float)):
                        pump_actual_rpm[str(pump_id)] = float(rpm)
                    responsive = item.get("responsive")
                    if isinstance(responsive, bool):
                        pump_responsive[str(pump_id)] = responsive

                if pump_actual_rpm:
                    snapshot["pump_actual_rpm"] = pump_actual_rpm
                if pump_responsive:
                    snapshot["pump_responsive"] = pump_responsive
        except Exception:
            pass

        return snapshot

    def _extract_current_value(self, status: dict[str, Any]) -> float | None:
        for key in ("current_value", "current", "latest_current"):
            value = status.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def _merge_anomalies(
        self,
        existing: list[dict[str, Any]],
        new_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged = list(existing)
        seen = {
            (
                item.get("type"),
                item.get("severity"),
                item.get("details"),
                item.get("source"),
            )
            for item in merged
        }
        for item in new_items:
            key = (
                item.get("type"),
                item.get("severity"),
                item.get("details"),
                item.get("source"),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged

    def _heartbeat_report_to_anomaly(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any] | None:
        status = str(report.get("status", "")).lower()
        if status not in {"warning", "critical"}:
            return None

        severity = "critical" if status == "critical" else "high"
        return {
            "type": "heartbeat_inspection",
            "severity": severity,
            "details": report.get("reason", ""),
            "source": "L2_heartbeat_inspector",
            "run_id": self._current_run_id,
            "risks": report.get("risks", []),
        }

    def _highest_severity_anomaly(
        self,
        anomalies: list[dict[str, Any]],
        severity: str,
    ) -> dict[str, Any] | None:
        for item in reversed(anomalies):
            if item.get("severity") == severity:
                return item
        return None

    def _classify_error(
        self,
        error_msg: str,
        status: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify an error state into a structured anomaly."""
        msg_lower = error_msg.lower()

        if "pump" in msg_lower or "泵" in msg_lower:
            return {"type": "pump_failure", "severity": "high", "details": error_msg}
        if "timeout" in msg_lower or "超时" in msg_lower:
            return {"type": "timeout", "severity": "medium", "details": error_msg}
        if "chi" in msg_lower or "echem" in msg_lower or "电化学" in msg_lower:
            return {"type": "echem_failure", "severity": "high", "details": error_msg}
        if "serial" in msg_lower or "串口" in msg_lower or "rs485" in msg_lower:
            return {"type": "serial_failure", "severity": "high", "details": error_msg}

        return {"type": "unknown", "severity": "medium", "details": error_msg}


def get_shared_executor_agent() -> ExperimentExecutorAgent:
    """Return a shared executor instance for API/runtime coordination."""
    global _SHARED_EXECUTOR
    if _SHARED_EXECUTOR is None:
        _SHARED_EXECUTOR = ExperimentExecutorAgent()
    return _SHARED_EXECUTOR
