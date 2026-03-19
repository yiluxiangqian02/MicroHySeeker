"""Tests for P1 knowledge foundation (P1-01 / P1-02)."""

from __future__ import annotations


def test_partition_uri_mapping() -> None:
    from src.knowledge.schema import KnowledgePartition, PARTITION_URIS

    assert PARTITION_URIS[KnowledgePartition.EXPERIMENTS] == "viking://resources/experiments/"
    assert PARTITION_URIS[KnowledgePartition.OPERATIONS] == "viking://resources/operations/"


def test_experiment_record_serialization() -> None:
    from src.knowledge.schema import ExperimentRecord, KnowledgePartition

    record = ExperimentRecord(
        run_id="run_001",
        project_id="her_feconi",
        params={"Fe": 0.4, "Co": 0.35, "Ni": 0.25},
        metrics={"overpotential_mV": 182.5},
        round_num=3,
        interpretation="性能改善",
    )

    payload = record.model_dump(mode="json")
    restored = ExperimentRecord.model_validate(payload)

    assert restored.partition == KnowledgePartition.EXPERIMENTS
    assert restored.metrics["overpotential_mV"] == 182.5


def test_project_record_serialization() -> None:
    from src.knowledge.schema import KnowledgePartition, ProjectRecord

    record = ProjectRecord(
        project_id="her_feconi",
        name="HER Fe-Co-Ni 优化",
        goal="最小化过电位",
        target_metric="overpotential_mV",
        direction="minimize",
        elements=["Fe", "Co", "Ni"],
        constraints={"sum_to_one": True},
    )

    payload = record.model_dump(mode="json")
    restored = ProjectRecord.model_validate(payload)

    assert restored.partition == KnowledgePartition.PROJECTS
    assert restored.constraints["sum_to_one"] is True


def test_viking_client_fallback_partition_write_and_search() -> None:
    from src.knowledge.schema import KnowledgePartition
    from src.knowledge.viking_client import OpenVikingClient

    client = OpenVikingClient(workspace_path="./.tmp_viking_workspace")

    write_result = client.write_json(
        partition=KnowledgePartition.EXPERIMENTS,
        payload={"run_id": "r1", "metrics": {"overpotential_mV": 190}},
        resource_name="r1.json",
    )

    assert write_result["written"] is True
    assert write_result["partition"] == "experiments"

    hits = client.search("overpotential", partition=KnowledgePartition.EXPERIMENTS, top_k=3)
    assert len(hits) >= 1
    assert "experiments" in hits[0]["uri"]


def test_viking_client_partition_uri_method() -> None:
    from src.knowledge.viking_client import OpenVikingClient

    client = OpenVikingClient(workspace_path="./.tmp_viking_workspace")
    assert client.get_partition_uri("analysis") == "viking://resources/analysis/"
