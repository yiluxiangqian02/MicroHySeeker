"""Tests for Task 7 (experiment control API) and Task 8 (agent status API)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.common.agent_manager import AgentManager

client = TestClient(app)


# ---------------------------------------------------------------------------
# Task 7 — Experiment control API
# ---------------------------------------------------------------------------


class TestExperimentControlAPI:
    """Tests for /experiments/{exp_id}/... endpoints."""

    def test_start_experiment_offline(self):
        """start_experiment returns 200 even when MicroHySeeker is offline."""
        response = client.post(
            "/experiments/test-001/start",
            json={
                "name": "Test Experiment",
                "steps": [{"step_type": "cv", "params": {}}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exp_id"] == "test-001"

    def test_start_experiment_forwarded(self):
        """start_experiment forwards to MicroHySeeker and returns its response."""
        mock_response = {"run_id": "run-42", "status": "running"}
        with patch(
            "src.api.routes.control._call_microhyseeker",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = client.post(
                "/experiments/exp-abc/start",
                json={"name": "CV Sweep", "steps": []},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["exp_id"] == "exp-abc"
        assert data["run_id"] == "run-42"
        assert data["status"] == "running"

    def test_pause_experiment(self):
        with patch(
            "src.api.routes.control._call_microhyseeker",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ):
            response = client.post("/experiments/exp-1/pause")
        assert response.status_code == 200
        assert response.json()["exp_id"] == "exp-1"

    def test_resume_experiment(self):
        with patch(
            "src.api.routes.control._call_microhyseeker",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ):
            response = client.post("/experiments/exp-1/resume")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_stop_experiment(self):
        with patch(
            "src.api.routes.control._call_microhyseeker",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ):
            response = client.post("/experiments/exp-1/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"

    def test_get_experiment_status(self):
        with patch(
            "src.api.routes.control._call_microhyseeker",
            new_callable=AsyncMock,
            return_value={"system_status": "ready", "running": False},
        ):
            response = client.get("/experiments/exp-1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["exp_id"] == "exp-1"
        assert "system_status" in data

    def test_start_experiment_missing_name_is_422(self):
        """Pydantic should reject a request missing the required 'name' field."""
        response = client.post(
            "/experiments/test-001/start",
            json={"steps": []},  # missing 'name'
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Task 8 — Agent status API
# ---------------------------------------------------------------------------


class TestAgentStatusAPI:
    """Tests for /agents/... endpoints."""

    def test_get_all_agents_status(self):
        response = client.get("/agents/status")
        assert response.status_code == 200
        data = response.json()
        assert "data_analyst" in data
        assert "exp_designer" in data
        assert "exp_supervisor" in data
        assert "diagnostics" in data
        assert "knowledge_mgr" in data

    def test_get_all_agents_status_structure(self):
        response = client.get("/agents/status")
        data = response.json()
        for agent_data in data.values():
            assert "status" in agent_data
            assert "tasks" in agent_data

    def test_start_known_agent(self):
        response = client.post("/agents/data_analyst/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["agent_id"] == "data_analyst"
        assert data["agent_status"] == "running"

    def test_stop_known_agent(self):
        response = client.post("/agents/data_analyst/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["agent_status"] == "idle"

    def test_start_unknown_agent_is_404(self):
        response = client.post("/agents/nonexistent_bot/start")
        assert response.status_code == 404

    def test_stop_unknown_agent_is_404(self):
        response = client.post("/agents/ghost/stop")
        assert response.status_code == 404

    def test_get_agent_logs(self):
        # generate a log entry first
        client.post("/agents/exp_designer/start")
        response = client.get("/agents/exp_designer/logs")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "exp_designer"
        assert isinstance(data["logs"], list)

    def test_get_agent_logs_unknown_is_404(self):
        response = client.get("/agents/ghost/logs")
        assert response.status_code == 404

    def test_get_agent_metrics(self):
        response = client.get("/agents/exp_supervisor/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "exp_supervisor"
        metrics = data["metrics"]
        assert "token_usage" in metrics
        assert "response_time" in metrics
        assert "success_count" in metrics
        assert "error_count" in metrics

    def test_get_agent_metrics_unknown_is_404(self):
        response = client.get("/agents/ghost/metrics")
        assert response.status_code == 404

    def test_get_agent_logs_limit(self):
        response = client.get("/agents/data_analyst/logs?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) <= 5


# ---------------------------------------------------------------------------
# Unit tests for AgentManager
# ---------------------------------------------------------------------------


class TestAgentManager:
    def setup_method(self):
        self.mgr = AgentManager()

    def test_initial_status_idle(self):
        for agent_id in ["data_analyst", "exp_designer", "diagnostics"]:
            assert self.mgr.get_status(agent_id)["status"] == "idle"

    def test_start_stop_cycle(self):
        self.mgr.start_agent("data_analyst")
        assert self.mgr.get_status("data_analyst")["status"] == "running"
        self.mgr.stop_agent("data_analyst")
        assert self.mgr.get_status("data_analyst")["status"] == "idle"

    def test_unknown_agent_returns_empty(self):
        assert self.mgr.get_status("does_not_exist") == {}

    def test_logs_trimmed_to_100(self):
        for i in range(120):
            self.mgr.add_log("data_analyst", "INFO", f"msg {i}")
        assert len(self.mgr.logs["data_analyst"]) == 100

    def test_get_logs_limit(self):
        for i in range(30):
            self.mgr.add_log("diagnostics", "DEBUG", f"line {i}")
        logs = self.mgr.get_logs("diagnostics", limit=10)
        assert len(logs) == 10
        assert logs[-1]["message"] == "line 29"

    def test_update_metrics(self):
        self.mgr.update_metrics("exp_supervisor", token_usage=42, success_count=3)
        m = self.mgr.get_metrics("exp_supervisor")
        assert m["token_usage"] == 42
        assert m["success_count"] == 3

    def test_get_all_status_keys(self):
        all_status = self.mgr.get_all_status()
        expected = {"data_analyst", "exp_designer", "exp_supervisor", "diagnostics", "knowledge_mgr"}
        assert set(all_status.keys()) == expected
