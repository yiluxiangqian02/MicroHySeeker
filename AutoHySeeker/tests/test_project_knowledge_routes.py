from __future__ import annotations

import json
from pathlib import Path
import shutil
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from src.api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def local_tmp_path() -> Path:
    base = Path(__file__).resolve().parent / ".tmp_project_route_tests"
    path = base / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _write_project_file(projects_dir, project_id: str, name: str) -> None:
    content = f"""
[project]
id = "{project_id}"
name = "{name}"
goal = "optimize {name}"

[optimization]
max_rounds = 12
target_metric = "overpotential_mV"
direction = "minimize"
template_id = "tpl_her_standard"
total_volume_ul = 1000.0

[search_space.Fe]
min = 0.1
max = 0.7

[search_space.Co]
min = 0.1
max = 0.7

[constraints]
sum_equals = 1.0
min_component = 0.05
""".strip()
    (projects_dir / f"{project_id}.toml").write_text(content, encoding="utf-8")


def _configure_temp_project_store(monkeypatch: pytest.MonkeyPatch, tmp_path):
    import src.api.routes.projects as projects_route
    import src.common.config as config_mod

    config_dir = tmp_path / "configs"
    projects_dir = config_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config_mod, "_CONFIGS_DIR", config_dir)
    monkeypatch.setattr(config_mod, "_PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(config_mod, "_project_configs", None)
    monkeypatch.setattr(config_mod, "PROJECT_CONFIGS", {})

    monkeypatch.setattr(projects_route, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(projects_route, "_current_project_id", None)
    return projects_dir


class TestProjectsRoutes:
    def test_list_projects_returns_items(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        local_tmp_path: Path,
    ) -> None:
        import src.common.config as config_mod

        projects_dir = _configure_temp_project_store(monkeypatch, local_tmp_path)
        _write_project_file(projects_dir, "her_feconi", "HER Fe-Co-Ni")
        config_mod.load_project_configs(reload=True)

        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["current_project_id"] == "her_feconi"
        assert data["items"][0]["project_id"] == "her_feconi"

    def test_create_project_writes_toml_and_sets_current(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        local_tmp_path: Path,
    ) -> None:
        projects_dir = _configure_temp_project_store(monkeypatch, local_tmp_path)

        response = client.post(
            "/api/projects",
            json={
                "project_id": "her_binary",
                "name": "HER Binary",
                "goal": "optimize Fe-Co",
                "elements": ["Fe", "Co"],
                "search_space": {
                    "Fe": {"min": 0.2, "max": 0.8},
                    "Co": {"min": 0.2, "max": 0.8},
                },
                "constraints": {"max_rpm": 250},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "created"
        assert data["current_project_id"] == "her_binary"
        created_file = projects_dir / "her_binary.toml"
        assert created_file.exists()
        assert "max_rpm = 250" in created_file.read_text(encoding="utf-8")

    def test_select_project_switches_current_project(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        local_tmp_path: Path,
    ) -> None:
        import src.common.config as config_mod

        projects_dir = _configure_temp_project_store(monkeypatch, local_tmp_path)
        _write_project_file(projects_dir, "project_a", "Project A")
        _write_project_file(projects_dir, "project_b", "Project B")
        config_mod.load_project_configs(reload=True)

        select_response = client.post("/api/projects/project_b/select")
        current_response = client.get("/api/projects/current")

        assert select_response.status_code == 200
        assert select_response.json()["current_project_id"] == "project_b"
        assert current_response.status_code == 200
        assert current_response.json()["current_project_id"] == "project_b"


class TestKnowledgeRoutes:
    def test_search_route_returns_skill_results(self, client: TestClient) -> None:
        mock_items = [{"partition": "literature", "title": "Paper A"}]
        with patch(
            "src.api.routes.knowledge.KnowledgeQuerySkill.search",
            new=AsyncMock(return_value=mock_items),
        ):
            response = client.get("/api/knowledge/search", params={"query": "Fe-Co-Ni", "partitions": "literature"})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["partition"] == "literature"

    def test_similar_experiments_route_parses_params_and_filters_project(self, client: TestClient) -> None:
        mock_items = [
            {"run_id": "run_001", "project_id": "her_feconi", "similarity": 0.98},
            {"run_id": "run_002", "project_id": "other_project", "similarity": 0.95},
        ]
        with patch(
            "src.api.routes.knowledge.KnowledgeQuerySkill.get_similar_experiments",
            new=AsyncMock(return_value=mock_items),
        ):
            response = client.get(
                "/api/knowledge/experiments",
                params={
                    "params": json.dumps({"Fe": 0.3, "Co": 0.5, "Ni": 0.2}),
                    "project_id": "her_feconi",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["run_id"] == "run_001"
        assert data["params"]["Fe"] == 0.3

    def test_similar_experiments_route_rejects_invalid_json(self, client: TestClient) -> None:
        response = client.get("/api/knowledge/experiments", params={"params": "{bad-json"})

        assert response.status_code == 400
        assert "valid JSON" in response.json()["detail"]

    def test_fault_history_route_returns_items(self, client: TestClient) -> None:
        mock_items = [{"event_type": "communication_timeout", "resolved": True}]
        with patch(
            "src.api.routes.knowledge.KnowledgeQuerySkill.get_fault_history",
            new=AsyncMock(return_value=mock_items),
        ):
            response = client.get("/api/knowledge/faults", params={"fault_type": "communication_timeout"})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["resolved"] is True
