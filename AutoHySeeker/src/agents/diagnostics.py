"""Diagnostics expert agent: fault diagnosis and auto-recovery."""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import re
from typing import Any

from src.agents.base import BaseAgent
from src.skills.knowledge_query_skill import KnowledgeQuerySkill

_logger = logging.getLogger("autohyseeker.diagnostics")

DIAGNOSTICS_SYSTEM_PROMPT = """\
You are the AutoHySeeker diagnostics expert.

Responsibilities:
1. Diagnose hardware, communication, and workflow anomalies.
2. Reuse historical fault and experiment knowledge when available.
3. Attempt safe auto-recovery for known recoverable issues.
4. Escalate to human operators when uncertainty or risk is high.

Always return structured, conservative recommendations.
"""

_KNOWN_FAULTS: dict[str, dict[str, Any]] = {
    "communication_timeout": {
        "category": "communication",
        "auto_fix": "_fix_communication",
        "max_retries": 3,
        "description": "RS485 communication timeout",
    },
    "pump_error": {
        "category": "hardware",
        "auto_fix": "_fix_pump",
        "max_retries": 2,
        "description": "Pump runtime error",
    },
    "pump_failure": {
        "category": "hardware",
        "auto_fix": "_fix_pump",
        "max_retries": 2,
        "description": "Pump failure",
    },
    "serial_failure": {
        "category": "communication",
        "auto_fix": "_fix_communication",
        "max_retries": 3,
        "description": "Serial connection failure",
    },
    "status_poll_failed": {
        "category": "communication",
        "auto_fix": "_fix_communication",
        "max_retries": 2,
        "description": "Status polling failure",
    },
}


class DiagnosticsExpertAgent(BaseAgent):
    """Diagnostics expert: diagnose anomalies and attempt safe recovery."""

    def __init__(self, knowledge_skill: KnowledgeQuerySkill | None = None) -> None:
        super().__init__(name="diagnostics", system_prompt=DIAGNOSTICS_SYSTEM_PROMPT)
        self._knowledge_skill = knowledge_skill or KnowledgeQuerySkill()

    async def diagnose_and_fix(self, task: dict[str, Any]) -> dict[str, Any]:
        """Full diagnose -> fix -> verify pipeline."""
        anomaly = task.get("anomaly", {})
        context = dict(task.get("context", {}))
        anomaly_type = anomaly.get("type", "unknown")

        _logger.info(
            "DiagnosticsExpertAgent: diagnosing anomaly type=%s severity=%s",
            anomaly_type,
            anomaly.get("severity", "unknown"),
        )

        knowledge_context = await self._collect_knowledge_context(anomaly, context)
        diagnosis = await self._diagnose(
            anomaly,
            {
                **context,
                "knowledge_context": knowledge_context,
            },
        )

        fault_info = _KNOWN_FAULTS.get(anomaly_type)
        if fault_info is None:
            return await self._handle_unknown_fault(
                anomaly,
                diagnosis,
                {
                    **context,
                    "knowledge_context": knowledge_context,
                },
            )

        fix_method = getattr(self, fault_info["auto_fix"], None)
        if fix_method is None:
            return self._build_unresolved(
                diagnosis=diagnosis,
                action_taken="Fix method is not implemented",
                steps=[],
                anomaly=anomaly,
                knowledge_context=knowledge_context,
            )

        max_retries = int(fault_info["max_retries"])
        all_steps: list[dict[str, str]] = []

        for attempt in range(1, max_retries + 1):
            fix_result = await fix_method(anomaly, context)
            all_steps.extend(fix_result.get("steps", []))
            if await self._verify_fix(anomaly):
                return {
                    "status": "resolved",
                    "diagnosis": diagnosis,
                    "knowledge_context": knowledge_context,
                    "action_taken": fix_result.get("description", ""),
                    "recovery_steps": all_steps,
                    "can_continue": True,
                    "recommendation": diagnosis.get("recommendation", ""),
                    "attempts": attempt,
                }
            if attempt < max_retries:
                await asyncio.sleep(0.05)

        return self._build_unresolved(
            diagnosis=diagnosis,
            action_taken=f"Auto-recovery failed after {max_retries} attempts",
            steps=all_steps,
            anomaly=anomaly,
            knowledge_context=knowledge_context,
        )

    async def _collect_knowledge_context(
        self,
        anomaly: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Collect relevant fault and experiment history from the knowledge base."""
        anomaly_type = str(anomaly.get("type", "unknown"))
        query = str(anomaly.get("details") or context.get("query") or anomaly_type)

        try:
            fault_history = await self._knowledge_skill.get_fault_history(anomaly_type, top_k=3)
        except Exception as exc:
            _logger.warning("Diagnostics fault history lookup failed: %s", exc)
            fault_history = []

        try:
            related_records = await self._knowledge_skill.search(
                query=query,
                partitions=["operations", "experiments"],
                top_k=5,
            )
        except Exception as exc:
            _logger.warning("Diagnostics knowledge search failed: %s", exc)
            related_records = []

        summary = self._build_knowledge_summary(fault_history, related_records)
        return {
            "fault_history": fault_history,
            "related_records": related_records,
            "summary": summary,
        }

    def _build_knowledge_summary(
        self,
        fault_history: list[dict[str, Any]],
        related_records: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = []
        if fault_history:
            parts.append(f"{len(fault_history)} similar fault records")
        if related_records:
            parts.append(f"{len(related_records)} related knowledge records")
        return ", ".join(parts) if parts else "no relevant knowledge records"

    async def _diagnose(
        self,
        anomaly: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Diagnose root cause using known patterns first, then LLM fallback."""
        anomaly_type = anomaly.get("type", "unknown")
        fault_info = _KNOWN_FAULTS.get(anomaly_type)
        knowledge_context = context.get("knowledge_context", {})
        knowledge_summary = str(knowledge_context.get("summary", ""))

        if fault_info:
            recommendation = f"Inspect components related to {anomaly_type}."
            if knowledge_summary and knowledge_summary != "no relevant knowledge records":
                recommendation += f" Historical context: {knowledge_summary}."
            return {
                "root_cause": fault_info["description"],
                "confidence": 0.8,
                "category": fault_info["category"],
                "recommendation": recommendation,
                "knowledge_hits": len(knowledge_context.get("fault_history", [])),
            }

        try:
            result = await self.invoke(
                task={"type": "diagnose_anomaly", "anomaly": anomaly},
                context=context,
            )
            content = result.get("content", "")
            parsed = self._parse_diagnosis(content, anomaly)
            parsed["knowledge_hits"] = len(knowledge_context.get("fault_history", []))
            return parsed
        except Exception as exc:
            _logger.warning("LLM diagnosis failed: %s", exc)
            recommendation = "Manual inspection recommended."
            if knowledge_summary and knowledge_summary != "no relevant knowledge records":
                recommendation = f"{recommendation} Historical context: {knowledge_summary}."
            return {
                "root_cause": f"Unknown fault: {anomaly.get('details', anomaly_type)}",
                "confidence": 0.3,
                "category": "unknown",
                "recommendation": recommendation,
                "knowledge_hits": len(knowledge_context.get("fault_history", [])),
            }

    def _parse_diagnosis(
        self,
        content: str,
        anomaly: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse LLM diagnosis response."""
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                diagnosis = parsed.get("diagnosis", parsed)
                return {
                    "root_cause": diagnosis.get("root_cause", "LLM diagnosis"),
                    "confidence": float(diagnosis.get("confidence", 0.5)),
                    "category": diagnosis.get("category", "unknown"),
                    "recommendation": diagnosis.get(
                        "recommendation",
                        parsed.get("recommendation", ""),
                    ),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        return {
            "root_cause": content[:200] if content else f"Unable to diagnose {anomaly.get('type', 'unknown')}",
            "confidence": 0.3,
            "category": "unknown",
            "recommendation": "Manual inspection recommended.",
        }

    async def _fix_communication(
        self,
        anomaly: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Fix communication timeout: disconnect -> wait -> reconnect."""
        steps: list[dict[str, str]] = []
        try:
            ctrl = importlib.import_module("src.tools.experiment_ctrl")
        except ImportError:
            return {
                "steps": [{"step": "import_ctrl", "result": "failed - module unavailable"}],
                "description": "Control module unavailable",
            }

        try:
            conn = ctrl.get_connection_info()
            port = conn.get("port", "")
            baud = conn.get("baudrate", 9600)
            steps.append({"step": "get_connection_info", "result": f"port={port}"})
        except Exception as exc:
            port = ""
            baud = 9600
            steps.append({"step": "get_connection_info", "result": f"failed - {exc}"})

        try:
            ctrl.disconnect_port()
            steps.append({"step": "disconnect", "result": "ok"})
        except Exception as exc:
            steps.append({"step": "disconnect", "result": f"failed - {exc}"})

        await asyncio.sleep(0.05)
        steps.append({"step": "wait", "result": "ok"})

        if port:
            try:
                ctrl.connect_port(port, baud)
                steps.append({"step": "reconnect", "result": "ok"})
            except Exception as exc:
                steps.append({"step": "reconnect", "result": f"failed - {exc}"})
        else:
            steps.append({"step": "reconnect", "result": "skipped - no port info"})

        return {"steps": steps, "description": "Re-established serial connection"}

    async def _fix_pump(
        self,
        anomaly: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Fix pump error: stop pump -> health check."""
        steps: list[dict[str, str]] = []
        address = anomaly.get("pump_address", 1)
        try:
            ctrl = importlib.import_module("src.tools.experiment_ctrl")
        except ImportError:
            return {
                "steps": [{"step": "import_ctrl", "result": "failed - module unavailable"}],
                "description": "Control module unavailable",
            }

        try:
            ctrl.pump_stop(address)
            steps.append({"step": f"stop_pump_{address}", "result": "ok"})
        except Exception as exc:
            steps.append({"step": f"stop_pump_{address}", "result": f"failed - {exc}"})

        await asyncio.sleep(0.05)
        steps.append({"step": "wait", "result": "ok"})

        try:
            health = ctrl.health_check()
            steps.append({"step": "health_check", "result": health.get("status", "unknown")})
        except Exception as exc:
            steps.append({"step": "health_check", "result": f"failed - {exc}"})

        return {"steps": steps, "description": f"Stopped and checked pump {address}"}

    async def _verify_fix(self, anomaly: dict[str, Any]) -> bool:
        """Verify that the system has recovered after a fix attempt."""
        try:
            ctrl = importlib.import_module("src.tools.experiment_ctrl")
        except ImportError:
            return False

        try:
            health = ctrl.health_check()
            if health.get("status") != "ok":
                return False
        except Exception:
            return False

        try:
            conn = ctrl.get_connection_info()
            if not conn.get("connected"):
                return False
        except Exception:
            return False

        return True

    async def _handle_unknown_fault(
        self,
        anomaly: dict[str, Any],
        diagnosis: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle faults not in the known registry."""
        knowledge_context = context.get("knowledge_context", {})
        try:
            result = await self.invoke(
                task={
                    "type": "suggest_manual_fix",
                    "anomaly": anomaly,
                    "diagnosis": diagnosis,
                },
                context=context,
            )
            recommendation = result.get("content", "Manual inspection recommended.")
        except Exception:
            recommendation = "Manual inspection recommended."

        if knowledge_context.get("summary") and knowledge_context["summary"] != "no relevant knowledge records":
            recommendation = f"{recommendation} Historical context: {knowledge_context['summary']}."

        return {
            "status": "unresolved",
            "diagnosis": diagnosis,
            "knowledge_context": knowledge_context,
            "action_taken": "Unknown fault type; no safe auto-recovery available",
            "recovery_steps": [],
            "can_continue": False,
            "need_human": True,
            "recommendation": recommendation[:500],
        }

    def _build_unresolved(
        self,
        diagnosis: dict[str, Any],
        action_taken: str,
        steps: list[dict[str, str]],
        anomaly: dict[str, Any],
        knowledge_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a standard unresolved result."""
        return {
            "status": "unresolved",
            "diagnosis": diagnosis,
            "knowledge_context": knowledge_context or {},
            "action_taken": action_taken,
            "recovery_steps": steps,
            "can_continue": False,
            "need_human": True,
            "recommendation": diagnosis.get("recommendation", "Manual inspection recommended."),
        }
