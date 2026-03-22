"""Tests for P1 knowledge foundation (P1-01 / P1-02)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


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


def test_viking_client_fallback_partition_write_and_search(monkeypatch) -> None:
    from src.knowledge.schema import KnowledgePartition
    from src.knowledge import viking_client
    from src.knowledge.viking_client import OpenVikingClient

    monkeypatch.setattr(OpenVikingClient, "initialize", lambda self: False)

    client = OpenVikingClient(workspace_path="./.tmp_viking_workspace")
    client._available = False
    client._client = None
    client._init_error = viking_client._OPENVIKING_IMPORT_ERROR

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


def test_viking_client_openviking_write_targets_partition() -> None:
    from src.knowledge.schema import KnowledgePartition
    from src.knowledge.viking_client import OpenVikingClient

    class FakeOpenViking:
        def __init__(self) -> None:
            self.calls: list[dict[str, str]] = []

        def add_resource(self, path: str, target: str) -> dict[str, str]:
            self.calls.append({"path": path, "target": target})
            return {"root_uri": "viking://resources/experiments/probe_run"}

        def wait_processed(self) -> dict[str, str]:
            return {"status": "success"}

    client = OpenVikingClient(workspace_path="./.tmp_viking_workspace")
    fake = FakeOpenViking()
    client._available = True
    client._client = fake

    result = client.write_json(
        partition=KnowledgePartition.EXPERIMENTS,
        payload={"run_id": "probe_run"},
        resource_name="probe_run.json",
    )

    assert fake.calls[0]["target"] == "viking://resources/experiments/"
    assert result["written"] is True
    assert result["mode"] == "openviking"
    assert result["uri"] == "viking://resources/experiments/probe_run"
    assert result["verified_partition"] is True


def test_load_openviking_module_uses_local_source_tree(monkeypatch) -> None:
    from src.knowledge import viking_client

    workspace_tmp = Path(tempfile.mkdtemp(prefix="ov_src_"))
    openviking_src = workspace_tmp / "OpenViking"
    pyagfs_src = workspace_tmp / "pyagfs"
    openviking_src.mkdir(parents=True)
    pyagfs_src.mkdir(parents=True)

    sentinel = object()
    call_count = {"value": 0}

    def fake_import_module(name: str):
        assert name == "openviking"
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise ImportError("not installed")
        return sentinel

    monkeypatch.setenv("AUTOHYSEEKER_OPENVIKING_SRC", str(openviking_src))
    monkeypatch.setenv("AUTOHYSEEKER_PYAGFS_SRC", str(pyagfs_src))
    monkeypatch.setattr(viking_client.importlib, "import_module", fake_import_module)

    original_sys_path = list(sys.path)
    try:
        module, available, error = viking_client._load_openviking_module()
    finally:
        sys.path[:] = original_sys_path
        if pyagfs_src.exists():
            pyagfs_src.rmdir()
        if openviking_src.exists():
            openviking_src.rmdir()
        if workspace_tmp.exists():
            workspace_tmp.rmdir()

    assert module is sentinel
    assert available is True
    assert error is None
    assert call_count["value"] == 2


def test_load_openviking_module_returns_import_error(monkeypatch) -> None:
    from src.knowledge import viking_client

    workspace_tmp = Path(tempfile.mkdtemp(prefix="ov_missing_"))
    missing_src = workspace_tmp / "missing_openviking"
    missing_pyagfs = workspace_tmp / "missing_pyagfs"

    def fake_import_module(name: str):
        assert name == "openviking"
        raise ImportError("engine missing")

    monkeypatch.setenv("AUTOHYSEEKER_OPENVIKING_SRC", str(missing_src))
    monkeypatch.setenv("AUTOHYSEEKER_PYAGFS_SRC", str(missing_pyagfs))
    monkeypatch.setattr(viking_client.importlib, "import_module", fake_import_module)

    module, available, error = viking_client._load_openviking_module()

    assert module is None
    assert available is False
    assert error == "engine missing"
    if workspace_tmp.exists():
        workspace_tmp.rmdir()


def test_viking_client_search_falls_back_to_workspace_files(monkeypatch) -> None:
    from src.knowledge.schema import KnowledgePartition
    from src.knowledge.viking_client import OpenVikingClient

    monkeypatch.setattr(OpenVikingClient, "initialize", lambda self: False)

    workspace_tmp = Path(tempfile.mkdtemp(prefix="ov_workspace_"))
    resource_dir = workspace_tmp / "default" / "resources" / "experiments" / "workspace_probe"
    resource_dir.mkdir(parents=True)
    (resource_dir / "workspace_probe.md").write_text(
        '{"run_id": "workspace_probe", "notes": "workspace fallback keyword"}',
        encoding="utf-8",
    )

    class BrokenOpenViking:
        def find(self, *_args, **_kwargs):
            raise RuntimeError("embedding unavailable")

    try:
        client = OpenVikingClient(workspace_path=str(workspace_tmp))
        client._available = True
        client._client = BrokenOpenViking()

        hits = client.search(
            "workspace fallback keyword",
            partition=KnowledgePartition.EXPERIMENTS,
            top_k=3,
        )
    finally:
        for path in sorted(workspace_tmp.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if workspace_tmp.exists():
            workspace_tmp.rmdir()

    assert len(hits) == 1
    assert hits[0]["uri"] == "viking://resources/experiments/workspace_probe"
    assert hits[0]["metadata"]["mode"] == "workspace_fallback"
