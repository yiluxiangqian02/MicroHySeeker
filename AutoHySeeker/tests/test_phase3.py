"""Phase 3 tests — DiagnosticsExpert LangGraph subgraph + diagnostics API routes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_run_dir(tmp_path: Path, success: bool = False) -> Path:
    """Create a minimal experiment run directory for testing."""
    summary = {
        "success": success,
        "steps": [{"step_index": 0, "step_type": "cv", "success": False}],
        "error_count": 1 if not success else 0,
    }
    (tmp_path / "run_summary.json").write_text(json.dumps(summary))

    log_lines = [
        "2024-01-01 10:00:00 INFO [cv] Starting CV measurement\n",
        "2024-01-01 10:00:05 ERROR [pump] Pump pressure anomaly detected\n",
        "2024-01-01 10:00:10 ERROR [echem] No signal from potentiostat\n",
    ]
    (tmp_path / "run_log.log").write_text("".join(log_lines))
    return tmp_path


# ── DiagnosticsGraph unit tests ───────────────────────────────────────────────

class TestBuildDiagnosticsGraph:
    def test_build_returns_graph(self) -> None:
        from src.graph.diagnostics_graph import build_diagnostics_graph

        graph = build_diagnostics_graph()
        assert graph is not None

    def test_get_diagnostics_graph_cached(self) -> None:
        from src.graph.diagnostics_graph import get_diagnostics_graph

        g1 = get_diagnostics_graph()
        g2 = get_diagnostics_graph()
        assert g1 is g2  # same cached instance

    def test_exported_from_graph_package(self) -> None:
        from src.graph import build_diagnostics_graph, get_diagnostics_graph

        assert callable(build_diagnostics_graph)
        assert callable(get_diagnostics_graph)

    def test_diagnostics_state_type(self) -> None:
        from src.graph.diagnostics_graph import DiagnosticsState

        # DiagnosticsState should be a TypedDict-based class
        assert hasattr(DiagnosticsState, "__annotations__") or hasattr(
            DiagnosticsState, "__required_keys__"
        )


class TestDiagnosticsGraphInvoke:
    def test_check_health_default_action(self, tmp_path: Path) -> None:
        from src.graph.diagnostics_graph import build_diagnostics_graph

        graph = build_diagnostics_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "diagnostics",
            "task": {"action": "check_health", "data_dir": str(tmp_path)},
            "context": {},
            "error": None,
            "result": None,
            "diagnostics_results": [],
        }
        result = run_async(graph.ainvoke(state))
        assert "result" in result
        report = result["result"]
        assert report is not None
        assert "action" in report
        assert report["action"] == "check_health"

    def test_analyze_failure_action(self, tmp_path: Path) -> None:
        from src.graph.diagnostics_graph import build_diagnostics_graph

        _make_run_dir(tmp_path, success=False)
        graph = build_diagnostics_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "diagnostics",
            "task": {"action": "analyze_failure", "run_dir": str(tmp_path)},
            "context": {},
            "error": None,
            "result": None,
            "diagnostics_results": [],
        }
        result = run_async(graph.ainvoke(state))
        report = result.get("result") or {}
        assert report.get("action") == "analyze_failure"
        assert "total_findings" in report

    def test_unknown_action_routes_to_check_health(self, tmp_path: Path) -> None:
        from src.graph.diagnostics_graph import build_diagnostics_graph

        graph = build_diagnostics_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "diagnostics",
            "task": {"action": "unknown_action", "data_dir": str(tmp_path)},
            "context": {},
            "error": None,
            "result": None,
            "diagnostics_results": [],
        }
        result = run_async(graph.ainvoke(state))
        # Should default to check_health without raising
        assert "result" in result

    def test_missing_run_dir_sets_error(self) -> None:
        from src.graph.diagnostics_graph import build_diagnostics_graph

        graph = build_diagnostics_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "diagnostics",
            "task": {"action": "analyze_failure", "run_dir": "/nonexistent/path"},
            "context": {},
            "error": None,
            "result": None,
            "diagnostics_results": [],
        }
        result = run_async(graph.ainvoke(state))
        # Either error is set or result has 0 findings
        report = result.get("result") or {}
        error = result.get("error")
        assert error is not None or report.get("total_findings", 0) == 0

    def test_report_contains_severity_counts(self, tmp_path: Path) -> None:
        from src.graph.diagnostics_graph import build_diagnostics_graph

        _make_run_dir(tmp_path, success=False)
        graph = build_diagnostics_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "diagnostics",
            "task": {"action": "analyze_failure", "run_dir": str(tmp_path)},
            "context": {},
            "error": None,
            "result": None,
            "diagnostics_results": [],
        }
        result = run_async(graph.ainvoke(state))
        report = result.get("result") or {}
        assert "severity_counts" in report
        assert isinstance(report["severity_counts"], dict)

    def test_report_contains_findings_list(self, tmp_path: Path) -> None:
        from src.graph.diagnostics_graph import build_diagnostics_graph

        _make_run_dir(tmp_path, success=False)
        graph = build_diagnostics_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "diagnostics",
            "task": {"action": "analyze_failure", "run_dir": str(tmp_path)},
            "context": {},
            "error": None,
            "result": None,
            "diagnostics_results": [],
        }
        result = run_async(graph.ainvoke(state))
        report = result.get("result") or {}
        assert "findings" in report
        assert isinstance(report["findings"], list)


# ── diagnostics_nodes unit tests ──────────────────────────────────────────────

class TestRoutesDiagnosticsNodes:
    def test_route_diagnostics_analyze_failure(self) -> None:
        from src.agents.diagnostics_nodes import route_diagnostics

        state = {"task": {"action": "analyze_failure"}}
        assert route_diagnostics(state) == "analyze_failure"

    def test_route_diagnostics_check_health(self) -> None:
        from src.agents.diagnostics_nodes import route_diagnostics

        state = {"task": {"action": "check_health"}}
        assert route_diagnostics(state) == "check_health"

    def test_route_diagnostics_default(self) -> None:
        from src.agents.diagnostics_nodes import route_diagnostics

        state = {"task": {"action": "anything_else"}}
        assert route_diagnostics(state) == "check_health"

    def test_generate_diagnosis_report(self) -> None:
        from src.agents.diagnostics_nodes import generate_diagnosis_report

        findings = [
            {"severity": "error", "message": "pump failure"},
            {"severity": "warning", "message": "low pressure"},
            {"severity": "error", "message": "no signal"},
        ]
        state = {
            "diagnostics_results": findings,
            "task": {"action": "analyze_failure"},
        }
        result = run_async(generate_diagnosis_report(state))
        report = result["result"]
        assert report["total_findings"] == 3
        assert report["severity_counts"]["error"] == 2
        assert report["severity_counts"]["warning"] == 1
        assert len(report["findings"]) == 3


# ── Diagnostics API route tests ───────────────────────────────────────────────

class TestDiagnosticsAPIRoute:
    def test_import_router(self) -> None:
        from src.api.routes.diagnostics import router
        from fastapi import APIRouter

        assert isinstance(router, APIRouter)
        assert router.prefix == "/diagnostics"

    def test_router_registered_in_app(self) -> None:
        from src.api.main import app

        routes = [r.path for r in app.routes]
        # /diagnostics/invoke should be registered
        assert any("diagnostics" in r for r in routes)

    def test_invoke_check_health(self, tmp_path: Path) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.post(
            "/diagnostics/invoke",
            json={
                "action": "check_health",
                "data_dir": str(tmp_path),
                "recent_n": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "action" in data
        assert data["action"] == "check_health"

    def test_invoke_analyze_failure(self, tmp_path: Path) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app

        _make_run_dir(tmp_path, success=False)
        client = TestClient(app)
        response = client.post(
            "/diagnostics/invoke",
            json={
                "action": "analyze_failure",
                "run_dir": str(tmp_path),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "analyze_failure"

    def test_invoke_default_action_is_check_health(self, tmp_path: Path) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.post(
            "/diagnostics/invoke",
            json={"data_dir": str(tmp_path)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "check_health"

    def test_result_has_report_structure(self, tmp_path: Path) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.post(
            "/diagnostics/invoke",
            json={"action": "check_health", "data_dir": str(tmp_path)},
        )
        assert response.status_code == 200
        data = response.json()
        result = data.get("result") or {}
        # Report structure from generate_diagnosis_report node
        assert "total_findings" in result
        assert "severity_counts" in result
        assert "findings" in result

    def test_health_endpoint_still_works(self) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ── Import smoke tests for Phase 3 ───────────────────────────────────────────

class TestPhase3Imports:
    def test_diagnostics_graph_module(self) -> None:
        import src.graph.diagnostics_graph  # noqa: F401

    def test_diagnostics_nodes_module(self) -> None:
        import src.agents.diagnostics_nodes  # noqa: F401

    def test_diagnostics_api_route_module(self) -> None:
        import src.api.routes.diagnostics  # noqa: F401

    def test_graph_package_exports(self) -> None:
        from src.graph import build_diagnostics_graph, get_diagnostics_graph

        assert callable(build_diagnostics_graph)
        assert callable(get_diagnostics_graph)


# ── D3 InteractiveTroubleshootingSkill tests ──────────────────────────────────

class TestInteractiveTroubleshootingSkill:
    """Cover D3 decision-tree troubleshooting for all 4 fault categories."""

    def test_import_singleton(self) -> None:
        from src.skills.diagnostics import (
            InteractiveTroubleshootingSkill,
            interactive_troubleshooting_skill,
        )
        assert isinstance(interactive_troubleshooting_skill, InteractiveTroubleshootingSkill)

    def test_exported_from_skills_package(self) -> None:
        from src.skills import InteractiveTroubleshootingSkill, interactive_troubleshooting_skill
        assert InteractiveTroubleshootingSkill is not None
        assert interactive_troubleshooting_skill is not None

    # ── error paths ───────────────────────────────────────────────────────────

    def test_empty_symptom_returns_failure(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom=""))
        assert result.success is False
        assert "available" in result.message.lower()

    def test_unknown_symptom_returns_failure(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="nonexistent_issue"))
        assert result.success is False
        assert "nonexistent_issue" in result.message

    def test_no_symptom_kwarg_returns_failure(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute())
        assert result.success is False

    # ── 4 fault tree categories ───────────────────────────────────────────────

    def test_pump_not_running(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="pump_not_running"))
        assert result.success is True
        assert result.data["symptom"] == "pump_not_running"
        assert len(result.data["steps"]) >= 3
        assert len(result.data["possible_causes"]) >= 3

    def test_echem_no_signal(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="echem_no_signal"))
        assert result.success is True
        assert result.data["symptom"] == "echem_no_signal"
        assert "title" in result.data

    def test_communication_timeout(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="communication_timeout"))
        assert result.success is True
        assert len(result.data["steps"]) >= 3
        assert result.data["symptom"] == "communication_timeout"

    def test_data_anomaly(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="data_anomaly"))
        assert result.success is True
        assert result.data["symptom"] == "data_anomaly"
        assert len(result.data["possible_causes"]) >= 3

    # ── response structure ────────────────────────────────────────────────────

    def test_result_contains_diagnostic_dict(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="pump_not_running"))
        assert "diagnostic" in result.data
        diag = result.data["diagnostic"]
        assert diag["severity"] == "warning"
        assert diag["category"] == "troubleshooting"
        assert "suggestion" in diag
        assert "evidence" in diag

    def test_all_known_symptoms_succeed(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        for symptom in ("pump_not_running", "echem_no_signal",
                        "communication_timeout", "data_anomaly"):
            result = run_async(skill.execute(symptom=symptom))
            assert result.success is True, f"Failed for symptom={symptom}"
            assert result.data["symptom"] == symptom

    def test_message_references_title(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="pump_not_running"))
        assert result.message  # non-empty
        assert "guide" in result.message.lower() or "troubleshooting" in result.message.lower() \
            or "泵" in result.message  # title appears in message

    def test_get_schema_contains_symptom_enum(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        schema = skill.get_schema()
        assert isinstance(schema, dict)
        assert "symptom" in schema["properties"]
        enum_values = schema["properties"]["symptom"]["enum"]
        assert set(enum_values) == {
            "pump_not_running", "echem_no_signal",
            "communication_timeout", "data_anomaly",
        }

    def test_artifacts_empty_for_troubleshooting(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="echem_no_signal"))
        assert result.artifacts == []
