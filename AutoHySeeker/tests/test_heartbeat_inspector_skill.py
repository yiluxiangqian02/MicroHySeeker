from __future__ import annotations

import asyncio


class _FakeKnowledgeSkill:
    def __init__(self, results: list[dict] | None = None) -> None:
        self.results = results or []
        self.queries: list[str] = []

    async def search(self, query: str, partitions: list[str] | None = None, top_k: int = 3) -> list[dict]:
        self.queries.append(query)
        return self.results[:top_k]


async def _fake_llm(**_: object) -> str:
    return '{"status":"critical","reason":"compound risk detected","risks":["trend_anomaly"],"need_diagnostics":true}'


def test_disabled_heartbeat_skips() -> None:
    from src.skills.heartbeat_inspector_skill import HeartbeatInspectorSkill

    skill = HeartbeatInspectorSkill(
        knowledge_skill=_FakeKnowledgeSkill(),
        config={"enabled": False, "interval_s": 30, "model": "fake"},
    )
    result = asyncio.run(skill.execute(snapshot={}))

    assert result.data["status"] == "skipped"
    assert result.data["reason"] == "disabled"


def test_interval_gate_prevents_early_run() -> None:
    from src.skills.heartbeat_inspector_skill import HeartbeatInspectorSkill

    skill = HeartbeatInspectorSkill(
        knowledge_skill=_FakeKnowledgeSkill(),
        config={"enabled": True, "interval_s": 30, "model": "fake"},
    )
    result = asyncio.run(skill.execute(snapshot={}, last_run_at=95.0, now=100.0))

    assert result.data["status"] == "skipped"
    assert result.data["reason"] == "interval_not_elapsed"


def test_queries_knowledge_and_warns_on_match() -> None:
    from src.skills.heartbeat_inspector_skill import HeartbeatInspectorSkill

    fake_knowledge = _FakeKnowledgeSkill(results=[{"partition": "operations", "score": 1.0}])
    skill = HeartbeatInspectorSkill(
        knowledge_skill=fake_knowledge,
        config={"enabled": True, "interval_s": 30, "model": "fake"},
    )
    result = asyncio.run(
        skill.execute(
            snapshot={"recent_anomalies": [{"type": "communication_timeout", "severity": "medium"}]},
            force=True,
            allow_llm=False,
        )
    )

    assert fake_knowledge.queries[0] == "communication_timeout"
    assert result.data["status"] == "warning"
    assert result.data["knowledge_hits"][0]["partition"] == "operations"


def test_rule_based_warning_for_progress_delay() -> None:
    from src.skills.heartbeat_inspector_skill import HeartbeatInspectorSkill

    skill = HeartbeatInspectorSkill(
        knowledge_skill=_FakeKnowledgeSkill(),
        config={"enabled": True, "interval_s": 30, "model": "fake"},
    )
    result = asyncio.run(
        skill.execute(
            snapshot={"progress_delay_s": 45},
            force=True,
            allow_llm=False,
        )
    )

    assert result.data["status"] == "warning"
    assert result.data["used_llm"] is False


def test_llm_can_upgrade_decision() -> None:
    from src.skills.heartbeat_inspector_skill import HeartbeatInspectorSkill

    skill = HeartbeatInspectorSkill(
        knowledge_skill=_FakeKnowledgeSkill(),
        llm_callable=_fake_llm,
        config={"enabled": True, "interval_s": 30, "model": "fake"},
    )
    result = asyncio.run(
        skill.execute(
            snapshot={"summary": "trend anomaly without L1 trigger"},
            force=True,
            allow_llm=True,
        )
    )

    assert result.data["status"] == "critical"
    assert result.data["used_llm"] is True
    assert result.success is False
