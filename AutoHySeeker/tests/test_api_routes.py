"""Tests for API routes: /agents/invoke, /data/experiments, /tasks."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


# ── /agents/invoke tests ──────────────────────────────────────────────────────

class TestAgentsInvokeRoute:
    def _client(self) -> Any:
        from fastapi.testclient import TestClient
        from src.api.main import app
        return TestClient(app)

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_returns_ok(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = "mocked LLM response"
        client = self._client()
        resp = client.post("/agents/invoke", json={
            "task": {"intent": "analyse CV data"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["result"] is not None

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_routes_to_data_analyst(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = "analysis"
        client = self._client()
        resp = client.post("/agents/invoke", json={
            "task": {"intent": "analyse CV signal"},
        })
        data = resp.json()
        state = data.get("state", {})
        assert state.get("current_agent") == "data_analyst"

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_routes_to_diagnostics(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = "diagnosed"
        client = self._client()
        resp = client.post("/agents/invoke", json={
            "task": {"intent": "diagnose pump error"},
        })
        data = resp.json()
        state = data.get("state", {})
        assert state.get("current_agent") == "diagnostics"

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_with_explicit_agent(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = "knowledge response"
        client = self._client()
        resp = client.post("/agents/invoke", json={
            "task": {"query": "any"},
            "current_agent": "knowledge_mgr",
        })
        data = resp.json()
        state = data.get("state", {})
        assert state.get("current_agent") == "knowledge_mgr"

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_with_context_and_messages(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = "contextual reply"
        client = self._client()
        resp = client.post("/agents/invoke", json={
            "task": {"intent": "run next step"},
            "context": {"experiment_id": "run_042"},
            "messages": [{"role": "user", "content": "previous msg"}],
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_empty_task(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = "default"
        client = self._client()
        resp = client.post("/agents/invoke", json={"task": {}})
        assert resp.status_code == 200

    @patch("src.common.llm_client.chat_completion", new_callable=AsyncMock)
    def test_invoke_llm_error_returns_500(self, mock_llm: AsyncMock) -> None:
        mock_llm.side_effect = RuntimeError("LLM service down")
        client = self._client()
        resp = client.post("/agents/invoke", json={
            "task": {"intent": "analyse data"},
        })
        # The route wraps errors in HTTPException(500)
        assert resp.status_code == 500


# ── /data/experiments tests ───────────────────────────────────────────────────

class TestDataExperimentsRoute:
    def _client(self) -> Any:
        from fastapi.testclient import TestClient
        from src.api.main import app
        return TestClient(app)

    @patch("src.api.routes.data.list_recent_experiments")
    def test_get_experiments_default(self, mock_list: Any) -> None:
        mock_list.return_value = [
            {"run_dir": "/data/run1", "day": "2025-01-01", "name": "run1",
             "has_echem_dir": True, "csv_count": 3},
        ]
        client = self._client()
        resp = client.get("/data/experiments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "run1"

    @patch("src.api.routes.data.list_recent_experiments")
    def test_get_experiments_with_limit(self, mock_list: Any) -> None:
        mock_list.return_value = []
        client = self._client()
        resp = client.get("/data/experiments?limit=5")
        assert resp.status_code == 200
        mock_list.assert_called_once_with(5)

    @patch("src.api.routes.data.list_recent_experiments")
    def test_get_experiments_empty(self, mock_list: Any) -> None:
        mock_list.return_value = []
        client = self._client()
        resp = client.get("/data/experiments")
        data = resp.json()
        assert data["count"] == 0
        assert data["items"] == []

    @patch("src.api.routes.data.list_recent_experiments")
    @patch("src.api.routes.data.read_experiment_dir")
    def test_get_latest_experiment(self, mock_read: Any, mock_list: Any) -> None:
        mock_list.return_value = [
            {"run_dir": "/data/run1", "day": "2025-01-01", "name": "run1",
             "has_echem_dir": True, "csv_count": 2},
        ]
        mock_read.return_value = {
            "run_dir": "/data/run1",
            "metadata": {},
            "files": {"csv": [], "cv": [], "eis": []},
            "counts": {"csv": 0, "cv": 0, "eis": 0},
        }
        client = self._client()
        resp = client.get("/data/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert "latest" in data
        assert "details" in data

    @patch("src.api.routes.data.list_recent_experiments")
    def test_get_latest_no_experiments_404(self, mock_list: Any) -> None:
        mock_list.return_value = []
        client = self._client()
        resp = client.get("/data/latest")
        assert resp.status_code == 404


# ── /tasks routes tests ──────────────────────────────────────────────────────

class TestTasksRoutes:
    def _client(self) -> Any:
        from fastapi.testclient import TestClient
        from src.api.main import app
        return TestClient(app)

    def test_create_task(self) -> None:
        client = self._client()
        resp = client.post("/tasks/create", json={
            "task_type": "cv_analysis",
            "payload": {"run_dir": "/data/run_042"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["task_type"] == "cv_analysis"
        assert data["task_id"].startswith("task_")
        assert "created_at" in data

    def test_create_task_default_type(self) -> None:
        client = self._client()
        resp = client.post("/tasks/create", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_type"] == "general"

    def test_get_task_status(self) -> None:
        client = self._client()
        # Create a task first
        create_resp = client.post("/tasks/create", json={
            "task_type": "test",
            "payload": {"key": "value"},
        })
        task_id = create_resp.json()["task_id"]

        # Retrieve status
        status_resp = client.get(f"/tasks/{task_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["task_id"] == task_id
        assert data["status"] == "queued"

    def test_get_nonexistent_task_404(self) -> None:
        client = self._client()
        resp = client.get("/tasks/nonexistent_id/status")
        assert resp.status_code == 404

    def test_create_multiple_tasks(self) -> None:
        client = self._client()
        ids = set()
        for i in range(3):
            resp = client.post("/tasks/create", json={
                "task_type": f"type_{i}",
                "payload": {"index": i},
            })
            assert resp.status_code == 200
            ids.add(resp.json()["task_id"])
        # All IDs should be unique
        assert len(ids) == 3


# ── /health endpoint test ─────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "autohyseeker-api"
