"""Configurable L2 heartbeat inspection with knowledge lookup and LLM fallback."""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable

from src.common.config import get_monitor_config
from src.common.llm_client import chat_completion
from src.skills.base import BaseSkill, SkillResult
from src.skills.knowledge_query_skill import KnowledgeQuerySkill

LlmCallable = Callable[..., Awaitable[str]]


class HeartbeatInspectorSkill(BaseSkill):
    """Periodic L2 inspection that combines snapshots, knowledge, and LLM review."""

    name = "heartbeat_inspector"
    description = "Perform configurable L2 heartbeat inspections with knowledge lookup."
    required_tools: list[str] = []

    def __init__(
        self,
        knowledge_skill: KnowledgeQuerySkill | None = None,
        llm_callable: LlmCallable | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._knowledge_skill = knowledge_skill or KnowledgeQuerySkill()
        self._llm_callable = llm_callable or chat_completion
        self._enabled = False
        self._interval_s = 30.0
        self._model = "qwen3-max"
        self.reload_config(config)

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Run a heartbeat inspection if enabled and the interval has elapsed."""
        if kwargs.get("reload_config"):
            self.reload_config()

        snapshot = kwargs.get("snapshot", {})
        if not isinstance(snapshot, dict):
            snapshot = {}

        now = float(kwargs.get("now", time.monotonic()))
        last_run_at = kwargs.get("last_run_at")

        report = await self.inspect(
            snapshot=snapshot,
            last_run_at=float(last_run_at) if isinstance(last_run_at, (int, float)) else None,
            now=now,
            force=bool(kwargs.get("force", False)),
            allow_llm=bool(kwargs.get("allow_llm", True)),
        )
        success = report.get("status") != "critical"
        return SkillResult(
            success=success,
            data=report,
            message=f"Heartbeat inspection status: {report.get('status', 'unknown')}",
            artifacts=[],
        )

    def reload_config(self, config: dict[str, Any] | None = None) -> None:
        raw = config
        if raw is None:
            raw = get_monitor_config().get("heartbeat_inspector", {})

        if not isinstance(raw, dict):
            raw = {}

        self._enabled = bool(raw.get("enabled", False))
        self._interval_s = float(raw.get("interval_s", 30))
        self._model = str(raw.get("model", "qwen3-max"))

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def should_run(
        self,
        *,
        last_run_at: float | None,
        now: float | None = None,
        force: bool = False,
    ) -> bool:
        if not self._enabled:
            return False
        if force:
            return True
        if last_run_at is None:
            return True
        current = now if now is not None else time.monotonic()
        return current - last_run_at >= self._interval_s

    async def inspect(
        self,
        *,
        snapshot: dict[str, Any],
        last_run_at: float | None = None,
        now: float | None = None,
        force: bool = False,
        allow_llm: bool = True,
    ) -> dict[str, Any]:
        current = now if now is not None else time.monotonic()
        if not self._enabled:
            return self._build_skip_report("disabled", current, last_run_at)
        if not self.should_run(last_run_at=last_run_at, now=current, force=force):
            return self._build_skip_report("interval_not_elapsed", current, last_run_at)

        knowledge_query = self._build_knowledge_query(snapshot)
        knowledge_hits = await self._query_knowledge(knowledge_query)
        rule_assessment = self._rule_based_assessment(snapshot, knowledge_hits)
        decision = rule_assessment

        if allow_llm:
            llm_decision = await self._llm_assessment(snapshot, knowledge_hits, rule_assessment)
            if llm_decision is not None:
                decision = llm_decision

        decision.update(
            {
                "source": "L2_heartbeat_inspector",
                "knowledge_query": knowledge_query,
                "knowledge_hits": knowledge_hits,
                "executed_at": current,
                "next_due_in_s": self._interval_s,
                "enabled": self._enabled,
                "interval_s": self._interval_s,
                "model": self._model,
            }
        )
        return decision

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "snapshot": {"type": "object"},
                "last_run_at": {"type": "number"},
                "force": {"type": "boolean"},
                "allow_llm": {"type": "boolean"},
            },
            "required": ["snapshot"],
        }

    def _build_skip_report(
        self,
        reason: str,
        now: float,
        last_run_at: float | None,
    ) -> dict[str, Any]:
        return {
            "status": "skipped",
            "reason": reason,
            "enabled": self._enabled,
            "interval_s": self._interval_s,
            "executed_at": now,
            "last_run_at": last_run_at,
            "source": "L2_heartbeat_inspector",
        }

    async def _query_knowledge(self, query: str) -> list[dict[str, Any]]:
        if not query:
            return []
        try:
            return await self._knowledge_skill.search(
                query=query,
                partitions=["operations", "experiments"],
                top_k=3,
            )
        except Exception:
            return []

    def _build_knowledge_query(self, snapshot: dict[str, Any]) -> str:
        keywords: list[str] = []
        if snapshot.get("recent_anomalies"):
            anomalies = snapshot["recent_anomalies"]
            if isinstance(anomalies, list):
                keywords.extend(str(item.get("type", "")) for item in anomalies if isinstance(item, dict))

        state = snapshot.get("state")
        if state:
            keywords.append(str(state))

        summary = snapshot.get("summary") or snapshot.get("recent_logs")
        if isinstance(summary, str) and summary.strip():
            keywords.append(summary.strip())

        return " ".join(part for part in keywords if part).strip()

    def _rule_based_assessment(
        self,
        snapshot: dict[str, Any],
        knowledge_hits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        recent_anomalies = snapshot.get("recent_anomalies", [])
        if not isinstance(recent_anomalies, list):
            recent_anomalies = []

        severe_types = {
            str(item.get("severity", "")).lower(): str(item.get("type", ""))
            for item in recent_anomalies
            if isinstance(item, dict)
        }

        if "critical" in severe_types:
            return {
                "status": "critical",
                "reason": f"recent anomaly is critical: {severe_types['critical']}",
                "risks": [severe_types["critical"]],
                "need_diagnostics": True,
                "used_llm": False,
            }
        if "high" in severe_types:
            return {
                "status": "warning",
                "reason": f"recent anomaly is high severity: {severe_types['high']}",
                "risks": [severe_types["high"]],
                "need_diagnostics": True,
                "used_llm": False,
            }

        progress_delay_s = _to_float(snapshot.get("progress_delay_s"))
        if progress_delay_s is not None and progress_delay_s > self._interval_s:
            return {
                "status": "warning",
                "reason": f"experiment progress delayed by {progress_delay_s:.1f}s",
                "risks": ["progress_delay"],
                "need_diagnostics": False,
                "used_llm": False,
            }

        if knowledge_hits:
            return {
                "status": "warning",
                "reason": "knowledge base contains related operational history",
                "risks": ["historical_pattern_match"],
                "need_diagnostics": False,
                "used_llm": False,
            }

        return {
            "status": "normal",
            "reason": "no heartbeat risk detected",
            "risks": [],
            "need_diagnostics": False,
            "used_llm": False,
        }

    async def _llm_assessment(
        self,
        snapshot: dict[str, Any],
        knowledge_hits: list[dict[str, Any]],
        fallback: dict[str, Any],
    ) -> dict[str, Any] | None:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the AutoHySeeker heartbeat inspector. "
                    "Return strict JSON with keys: status, reason, risks, need_diagnostics. "
                    "status must be one of normal, warning, critical."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "snapshot": snapshot,
                        "knowledge_hits": knowledge_hits,
                        "fallback_assessment": fallback,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        try:
            content = await self._llm_callable(
                messages=messages,
                model=self._model,
                temperature=0.0,
            )
        except Exception:
            return None

        parsed = _parse_json_object(content)
        if not isinstance(parsed, dict):
            return None

        status = str(parsed.get("status", "")).lower()
        if status not in {"normal", "warning", "critical"}:
            return None

        risks = parsed.get("risks", [])
        if not isinstance(risks, list):
            risks = [str(risks)]

        return {
            "status": status,
            "reason": str(parsed.get("reason", fallback.get("reason", ""))),
            "risks": [str(item) for item in risks],
            "need_diagnostics": bool(parsed.get("need_diagnostics", status == "critical")),
            "used_llm": True,
        }


def _parse_json_object(content: str) -> dict[str, Any] | None:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(content[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
