"""Tests for API routes: /agents, /data, /tasks (and health endpoint).

All LLM calls and graph invocations are mocked.
Uses FastAPI TestClient (sync httpx).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# TestClient is available via httpx (httpx is a declared dependency)
from fastapi.testclient import TestClient


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


# ── app fixture ────────────────────────────────────────────────────────────────

@pytest.fixture
def client() -> TestClient:
    from src.api.main import app
    return TestClient(app, raise_server_exceptions=False)


# ── /health ────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_body(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "autohyseeker" in data["service"].lower()


# ── /tasks ─────────────────────────────────────────────────────────────────────

class TestTasksRoutes:
    def test_create_task_returns_201_or_200(self, client: TestClient) -> None:
        """POST /tasks/create should return a task record."""
        response = client.post("/tasks/create", json={"task_type": "analysis", "payload": {}})
        assert response.status_code in (200, 201)

    def test_create_task_returns_task_id(self, client: TestClient) -> None:
        response = client.post("/tasks/create", json={"task_type": "analysis", "payload": {}})
        data = response.json()
        assert "task_id" in data
        assert data["task_id"].startswith("task_")

    def test_create_task_returns_queued_status(self, client: TestClient) -> None:
        response = client.post("/tasks/create", json={"task_type": "diagnostics"})
        data = response.json()
        assert data["status"] == "queued"

    def test_create_task_stores_task_type(self, client: TestClient) -> None:
        response = client.post("/tasks/create", json={"task_type": "my_type"})
        data = response.json()
        assert data["task_type"] == "my_type"

    def test_create_task_default_type(self, client: TestClient) -> None:
        """Omitting task_type should default to 'general'."""
        response = client.post("/tasks/create", json={})
        data = response.json()
        assert data["task_type"] == "general"

    def test_get_task_status_existing_task(self, client: TestClient) -> None:
        # First create a task
        create_resp = client.post("/tasks/create", json={"task_type": "test"})
        task_id = create_resp.json()["task_id"]
        # Then retrieve its status
        status_resp = client.get(f"/tasks/{task_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["task_id"] == task_id

    def test_get_task_status_unknown_task_returns_404(self, client: TestClient) -> None:
        response = client.get("/tasks/task_nonexistent_abc/status")
        assert response.status_code == 404

    def test_get_task_status_has_created_at(self, client: TestClient) -> None:
        create_resp = client.post("/tasks/create", json={"task_type": "test"})
        task_id = create_resp.json()["task_id"]
        status_resp = client.get(f"/tasks/{task_id}/status")
        assert "created_at" in status_resp.json()


# ── /data ──────────────────────────────────────────────────────────────────────

class TestDataRoutes:
    def test_get_experiments_returns_200(self, client: TestClient) -> None:
        """GET /data/experiments should return 200 even with no data."""
        with patch("src.tools.echem_reader.list_recent_experiments", return_value=[]):
            response = client.get("/data/experiments")
        assert response.status_code == 200

    def test_get_experiments_returns_count_and_items(self, client: TestClient) -> None:
        """Response should have 'count' and 'items' fields."""
        with patch("src.tools.echem_reader.list_recent_experiments", return_value=[]):
            response = client.get("/data/experiments")
        data = response.json()
        assert "count" in data
        assert "items" in data

    def test_get_experiments_with_mock_data(self, client: TestClient) -> None:
        """Mock data should be reflected in response."""
        mock_items = [
            {"run_dir": "/data/2026-03-01/run_001", "name": "run_001", "csv_count": 2}
        ]
        with patch("src.tools.echem_reader.list_recent_experiments", return_value=mock_items):
            response = client.get("/data/experiments")
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "run_001"

    def test_get_experiments_limit_param(self, client: TestClient) -> None:
        """Limit parameter is forwarded to the tool."""
        with patch("src.tools.echem_reader.list_recent_experiments", return_value=[]) as mock_fn:
            client.get("/data/experiments?limit=5")
            mock_fn.assert_called_once_with(5)

    def test_get_latest_no_data_returns_404(self, client: TestClient) -> None:
        """GET /data/latest with no experiments → 404."""
        with patch("src.tools.echem_reader.list_recent_experiments", return_value=[]):
            response = client.get("/data/latest")
        assert response.status_code == 404

    def test_get_latest_with_data_returns_200(self, client: TestClient) -> None:
        """GET /data/latest with mocked data → 200."""
        mock_items = [{"run_dir": "/data/run_001", "name": "run_001"}]
        mock_details: dict[str, Any] = {
            "run_dir": "/data/run_001",
            "metadata": {},
            "files": {"csv": [], "cv": [], "eis": []},
            "counts": {"csv": 0, "cv": 0, "eis": 0},
        }
        with patch("src.tools.echem_reader.list_recent_experiments", return_value=mock_items), \
             patch("src.tools.echem_reader.read_experiment_dir", return_value=mock_details):
            response = client.get("/data/latest")
        assert response.status_code == 200
        data = response.json()
        assert "latest" in data
        assert "details" in data


# ── /agents ────────────────────────────────────────────────────────────────────

class TestAgentsRoutes:
    """Test /agents/invoke endpoint with mocked graph/LLM."""

    def _mock_graph(self, result_payload: dict[str, Any] | None = None) -> MagicMock:
        """Return a mock graph with ainvoke that returns a valid state."""
        payload = result_payload or {"agent": "orchestrator", "content": "analysis", "ok": True}
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "messages": [],
            "current_agent": "orchestrator",
            "task": {},
            "context": {},
            "error": None,
            "result": payload,
        })
        return mock_graph

    def test_invoke_agent_returns_200(self, client: TestClient) -> None:
        """POST /agents/invoke → 200."""
        with patch("src.api.routes.agents.get_supervisor_graph", return_value=self._mock_graph()):
            response = client.post("/agents/invoke", json={
                "task": {"intent": "analyze cv"},
                "context": {},
            })
        assert response.status_code == 200

    def test_invoke_agent_returns_ok_field(self, client: TestClient) -> None:
        with patch("src.api.routes.agents.get_supervisor_graph", return_value=self._mock_graph()):
            response = client.post("/agents/invoke", json={
                "task": {"intent": "analyze"},
                "context": {},
            })
        data = response.json()
        assert "ok" in data

    def test_invoke_agent_returns_result_field(self, client: TestClient) -> None:
        with patch("src.api.routes.agents.get_supervisor_graph", return_value=self._mock_graph()):
            response = client.post("/agents/invoke", json={
                "task": {"intent": "analyze"},
                "context": {},
            })
        data = response.json()
        assert "result" in data

    def test_invoke_agent_with_current_agent_override(self, client: TestClient) -> None:
        """current_agent field should be forwarded to graph state."""
        mock_graph = self._mock_graph()
        with patch("src.api.routes.agents.get_supervisor_graph", return_value=mock_graph):
            client.post("/agents/invoke", json={
                "task": {},
                "context": {},
                "current_agent": "diagnostics",
            })
        call_args = mock_graph.ainvoke.call_args[0][0]
        assert call_args["current_agent"] == "diagnostics"

    def test_invoke_agent_with_messages(self, client: TestClient) -> None:
        """messages list should be forwarded in state."""
        mock_graph = self._mock_graph()
        prior_messages = [{"role": "user", "content": "hello"}]
        with patch("src.api.routes.agents.get_supervisor_graph", return_value=mock_graph):
            client.post("/agents/invoke", json={
                "task": {},
                "messages": prior_messages,
            })
        call_args = mock_graph.ainvoke.call_args[0][0]
        assert len(call_args["messages"]) == 1

    def test_invoke_agent_empty_request_succeeds(self, client: TestClient) -> None:
        """Empty request body should use defaults and return 200."""
        with patch("src.api.routes.agents.get_supervisor_graph", return_value=self._mock_graph()):
            response = client.post("/agents/invoke", json={})
        assert response.status_code == 200

    def test_invoke_agent_graph_exception_returns_500(self, client: TestClient) -> None:
        """When graph raises exception, /agents/invoke should return 500."""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph exploded"))
        with patch("src.api.routes.agents.get_supervisor_graph", return_value=mock_graph):
            response = client.post("/agents/invoke", json={"task": {}})
        assert response.status_code == 500

    def test_invoke_agent_with_data_analyst_task(self, client: TestClient) -> None:
        """Smoke test with realistic data analysis task payload (now routed to orchestrator)."""
        result_payload = {
            "agent": "orchestrator",
            "model": "claude-opus-4.6",
            "content": "CV analysis: peak at -0.35V",
            "ok": True,
        }
        with patch("src.api.routes.agents.get_supervisor_graph",
                   return_value=self._mock_graph(result_payload)):
            response = client.post("/agents/invoke", json={
                "task": {
                    "intent": "analyze cv",
                    "run_id": "run_042",
                    "goal": "interpret electrochemical data",
                },
                "context": {"session_id": "sess_001"},
            })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_invoke_agent_with_diagnostics_task(self, client: TestClient) -> None:
        """Smoke test with diagnostics task payload."""
        result_payload = {"agent": "diagnostics", "content": "No failures detected", "ok": True}
        with patch("src.api.routes.agents.get_supervisor_graph",
                   return_value=self._mock_graph(result_payload)):
            response = client.post("/agents/invoke", json={
                "task": {"intent": "diagnose failure in run_099"},
                "context": {},
            })
        assert response.status_code == 200

    def test_get_agent_models_returns_backend_configs(self, client: TestClient) -> None:
        with patch(
            "src.api.routes.agents.get_agent_models_config",
            return_value={
                "defaults": {"model": "default-model", "fallback_model": "fallback-model", "base_url": "https://api.example.com"},
                "orchestrator": {},
                "chat": {},
            },
        ), patch(
            "src.api.routes.agents.get_default_llm_config",
            return_value={"model": "default-model", "fallback_model": "fallback-model", "base_url": "https://api.example.com"},
        ), patch(
            "src.api.routes.agents.load_agent_config",
            side_effect=lambda agent_name, reload=False: {
                "name": agent_name,
                "enabled": True,
                "model": f"{agent_name}-model",
                "fallback_model": "fallback-model",
                "api_key": "secret",
                "temperature": 0.2,
                "max_tokens": 1000,
                "base_url": "https://api.example.com",
            },
        ):
            response = client.get("/api/agents/models")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["defaults"]["model"] == "default-model"
        assert "orchestrator" in data["agents"]

    def test_update_agent_model_persists_and_reloads(self, client: TestClient) -> None:
        with patch(
            "src.api.routes.agents.update_agent_model_config",
            return_value={"model": "updated-model"},
        ) as update_mock, patch(
            "src.api.routes.agents.reload_all_configs",
        ) as reload_mock, patch(
            "src.api.routes.agents.load_agent_config",
            return_value={
                "name": "chat",
                "enabled": True,
                "model": "updated-model",
                "fallback_model": "fallback-model",
                "api_key": "secret",
                "temperature": 0.3,
                "max_tokens": 2000,
                "base_url": "https://api.example.com",
            },
        ):
            response = client.put(
                "/api/agents/models/chat",
                json={"primary_model": "updated-model", "fallback_model": "fallback-model"},
            )

        assert response.status_code == 200
        update_mock.assert_called_once()
        reload_mock.assert_called_once()
        assert response.json()["agent"]["primary_model"] == "updated-model"


# ── /diagnostics (existing, smoke-tested for regression) ──────────────────────

class TestDiagnosticsRoutesSmoke:
    """Regression smoke tests to ensure diagnostics routes still work."""

    def test_diagnostics_check_health_returns_200(self, client: TestClient) -> None:
        response = client.post("/diagnostics/check-health", json={})
        assert response.status_code == 200

    def test_diagnostics_analyze_failure_returns_200(self, client: TestClient) -> None:
        response = client.post("/diagnostics/analyze-failure", json={})
        assert response.status_code == 200


class TestMonitorRoutes:
    def test_toggle_monitor_returns_200(self, client: TestClient) -> None:
        response = client.post("/api/monitor/toggle", json={"enabled": True})
        assert response.status_code == 200
        assert response.json()["heartbeat_enabled"] is True

    def test_monitor_status_returns_payload(self, client: TestClient) -> None:
        response = client.get("/api/monitor/status")
        assert response.status_code == 200
        data = response.json()
        assert "monitor_status" in data
        assert "heartbeat_enabled" in data

    def test_update_monitor_config(self, client: TestClient) -> None:
        with patch(
            "src.api.routes.monitor.update_agent_model_config",
        ) as update_model_mock, patch(
            "src.api.routes.monitor.load_agent_config",
            return_value={"model": "test-model"},
        ):
            response = client.put(
                "/api/monitor/config",
                json={
                    "heartbeat_enabled": True,
                    "heartbeat_interval_s": 45,
                    "heartbeat_model": "test-model",
                },
            )
        assert response.status_code == 200
        data = response.json()
        update_model_mock.assert_called_once_with("heartbeat_inspector", {"model": "test-model"})
        assert data["config"]["heartbeat_enabled"] is True
        assert data["config"]["heartbeat_interval_s"] == 45
        assert data["config"]["heartbeat_model"] == "test-model"


class TestApprovalRoutes:
    def test_get_pending_approvals_returns_seeded_item(self, client: TestClient) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()
        seeded = run_async(
            orchestrator.request_human_approval(
                decision={"action": "stop", "decision_type": "stop_decision"},
                context={"current_round": 3},
            )
        )

        with patch("src.api.routes.approval.get_shared_orchestrator_agent", return_value=orchestrator):
            response = client.get("/api/approval/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["approval_id"] == seeded["approval_id"]

    def test_respond_approval_resolves_pending_item(self, client: TestClient) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()
        seeded = run_async(
            orchestrator.request_human_approval(
                decision={"action": "adjust_strategy", "decision_type": "strategy_change"},
                context={"current_round": 4},
            )
        )

        with patch("src.api.routes.approval.get_shared_orchestrator_agent", return_value=orchestrator):
            response = client.post(
                "/api/approval/respond",
                json={
                    "approval_id": seeded["approval_id"],
                    "approved": True,
                    "feedback": "proceed",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["approval"]["approved"] is True
        assert data["approval"]["human_feedback"] == "proceed"
        assert data["pending_count"] == 0

    def test_respond_approval_missing_returns_404(self, client: TestClient) -> None:
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent()
        with patch("src.api.routes.approval.get_shared_orchestrator_agent", return_value=orchestrator):
            response = client.post(
                "/api/approval/respond",
                json={
                    "approval_id": "approval_missing",
                    "approved": False,
                    "feedback": "reject",
                },
            )

        assert response.status_code == 404


# ── /context (existing, smoke-tested for regression) ──────────────────────────

class TestContextRoutesSmoke:
    """Regression smoke tests to ensure context routes still work."""

    def test_context_suggest_next_returns_200(self, client: TestClient) -> None:
        response = client.post("/context/suggest-next", json={})
        assert response.status_code == 200
