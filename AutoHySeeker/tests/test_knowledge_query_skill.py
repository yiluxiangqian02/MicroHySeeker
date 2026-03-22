from __future__ import annotations

import asyncio

from src.knowledge.schema import KnowledgePartition
from src.knowledge.viking_client import OpenVikingClient


def _build_client() -> OpenVikingClient:
    client = OpenVikingClient(workspace_path="./.tmp_viking_query_skill")
    client.write_json(
        partition=KnowledgePartition.EXPERIMENTS,
        resource_name="exp_001.json",
        payload={
            "run_id": "run_001",
            "project_id": "her_feconi",
            "round_num": 1,
            "params": {"Fe": 0.30, "Co": 0.50, "Ni": 0.20},
            "metrics": {"overpotential_mV": 182.5},
        },
    )
    client.write_json(
        partition=KnowledgePartition.EXPERIMENTS,
        resource_name="exp_002.json",
        payload={
            "run_id": "run_002",
            "project_id": "her_feconi",
            "round_num": 2,
            "params": {"Fe": 0.20, "Co": 0.60, "Ni": 0.20},
            "metrics": {"overpotential_mV": 205.0},
        },
    )
    client.write_json(
        partition=KnowledgePartition.OPERATIONS,
        resource_name="fault_001.json",
        payload={
            "event_type": "communication_timeout",
            "severity": "error",
            "message": "RS485 timeout on COM3",
            "action_taken": "disconnect and reconnect",
            "resolved": True,
            "run_id": "run_002",
        },
    )
    client.write_json(
        partition=KnowledgePartition.LITERATURE,
        resource_name="paper_001.json",
        payload={
            "title": "Fe-Co-Ni HER catalyst survey",
            "authors": ["A", "B"],
            "year": 2025,
            "doi": "10.1000/example",
            "abstract": "Co-rich Fe-Co-Ni catalysts often achieve lower HER overpotential.",
            "keywords": ["HER", "Fe-Co-Ni", "Co-rich"],
        },
    )
    return client


def test_search_across_partitions() -> None:
    from src.skills.knowledge_query_skill import KnowledgeQuerySkill

    skill = KnowledgeQuerySkill(client=_build_client())
    results = asyncio.run(skill.search(query="overpotential", partitions=None, top_k=5))

    assert results
    assert any(item["partition"] == "experiments" for item in results)


def test_get_similar_experiments() -> None:
    from src.skills.knowledge_query_skill import KnowledgeQuerySkill

    skill = KnowledgeQuerySkill(client=_build_client())
    results = asyncio.run(
        skill.get_similar_experiments(
            params={"Fe": 0.31, "Co": 0.49, "Ni": 0.20},
            threshold=0.95,
            top_k=3,
        )
    )

    assert results
    assert results[0]["run_id"] == "run_001"


def test_get_fault_history() -> None:
    from src.skills.knowledge_query_skill import KnowledgeQuerySkill

    skill = KnowledgeQuerySkill(client=_build_client())
    results = asyncio.run(skill.get_fault_history("communication_timeout", top_k=3))

    assert len(results) == 1
    assert results[0]["resolved"] is True


def test_get_literature_insights() -> None:
    from src.skills.knowledge_query_skill import KnowledgeQuerySkill

    skill = KnowledgeQuerySkill(client=_build_client())
    results = asyncio.run(skill.get_literature_insights("Co-rich", top_k=3))

    assert len(results) == 1
    assert "Co-rich" in results[0]["summary"]


def test_execute_dispatches_search() -> None:
    from src.skills import KnowledgeQuerySkill

    skill = KnowledgeQuerySkill(client=_build_client())
    result = asyncio.run(skill.execute(action="search", query="timeout", partitions=["operations"], top_k=2))

    assert result.success is True
    assert result.data[0]["partition"] == "operations"
