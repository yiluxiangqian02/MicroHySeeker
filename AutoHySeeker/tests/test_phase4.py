"""Phase 4 tests — C1 ContextualizeExperiment, C2 SuggestNextExperiment,
supervisor graph extensions, and /context API routes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_run_dir(tmp_path: Path, metrics: dict[str, Any] | None = None) -> Path:
    """Create a minimal run directory with metadata and an optional CSV."""
    meta = {"run_id": "run_test", "success": True, **(metrics or {})}
    (tmp_path / "run_summary.json").write_text(json.dumps(meta))
    return tmp_path


# ── C1 ContextualizeExperimentSkill ──────────────────────────────────────────

class TestContextualizeExperimentSkill:
    def test_import(self) -> None:
        from src.skills.contextualize_experiment import (
            ContextualizeExperimentSkill,
            contextualize_experiment_skill,
        )
        assert isinstance(contextualize_experiment_skill, ContextualizeExperimentSkill)

    def test_exported_from_skills_init(self) -> None:
        from src.skills import ContextualizeExperimentSkill, contextualize_experiment_skill
        assert ContextualizeExperimentSkill is not None
        assert contextualize_experiment_skill is not None

    def test_missing_run_dir_returns_failure(self) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute())
        assert result.success is False
        assert "run_dir" in result.message.lower()

    def test_nonexistent_run_dir_returns_failure(self) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir="/nonexistent/run_dir"))
        assert result.success is False

    def test_empty_run_dir_no_metrics(self, tmp_path: Path) -> None:
        """A run dir with no numeric metadata → success with empty comparison."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        # Write summary with no numeric fields
        (tmp_path / "run_summary.json").write_text(json.dumps({"run_id": "r1"}))
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert result.data["comparison"] == {}

    def test_run_dir_with_numeric_metrics(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        _make_run_dir(tmp_path, {"peak_current": 0.05, "onset_potential": -0.25})
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert "peak_current" in result.data["comparison"] or len(result.data["comparison"]) == 0

    def test_previous_results_provide_history(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        _make_run_dir(tmp_path, {"peak_current": 0.06})
        prev = [{"peak_current": 0.04}, {"peak_current": 0.045}, {"peak_current": 0.05}]
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(tmp_path),
            previous_results=prev,
        ))
        assert result.success is True
        data = result.data
        assert data["n_history"] == 3
        if "peak_current" in data["comparison"]:
            cmp = data["comparison"]["peak_current"]
            assert "historical_mean" in cmp
            assert "delta" in cmp

    def test_anomaly_detection(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        # Value far from history → should be flagged
        _make_run_dir(tmp_path, {"metric_x": 100.0})
        prev = [{"metric_x": 1.0}, {"metric_x": 1.1}, {"metric_x": 0.9},
                {"metric_x": 1.05}, {"metric_x": 0.95}]
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(tmp_path),
            previous_results=prev,
            threshold_sigma=2.0,
        ))
        assert result.success is True
        assert "metric_x" in result.data.get("anomalies", [])

    def test_get_schema(self) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        schema = ContextualizeExperimentSkill().get_schema()
        assert schema["type"] == "object"
        assert "run_dir" in schema["properties"]
        assert "run_dir" in schema["required"]

    def test_result_data_keys(self, tmp_path: Path) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        _make_run_dir(tmp_path)
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        for key in ("run_dir", "comparison", "trend", "anomalies", "literature", "knowledge_chunks", "n_history", "summary"):
            assert key in result.data, f"Missing key: {key}"


# ── C2 SuggestNextExperimentSkill ─────────────────────────────────────────────

class TestSuggestNextExperimentSkill:
    def test_import(self) -> None:
        from src.skills.suggest_next_experiment import (
            SuggestNextExperimentSkill,
            suggest_next_experiment_skill,
        )
        assert isinstance(suggest_next_experiment_skill, SuggestNextExperimentSkill)

    def test_exported_from_skills_init(self) -> None:
        from src.skills import SuggestNextExperimentSkill, suggest_next_experiment_skill
        assert SuggestNextExperimentSkill is not None
        assert suggest_next_experiment_skill is not None

    def test_no_context_no_goal_returns_generic(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute())
        assert result.success is True
        assert result.data["intent"] == "generic"

    def test_anomalies_trigger_diagnostic_run(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        ctx = {"anomalies": ["peak_current", "onset_potential"], "trend": {}, "comparison": {}}
        result = run_async(skill.execute(context_data=ctx))
        assert result.success is True
        assert result.data["intent"] == "diagnostic_run"

    def test_declining_trend_triggers_stability_run(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        ctx = {
            "anomalies": [],
            "trend": {"peak_current": "declining"},
            "comparison": {},
        }
        result = run_async(skill.execute(context_data=ctx))
        assert result.success is True
        assert result.data["intent"] == "stability_run"

    def test_optimisation_goal_triggers_optimisation_run(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(goal="optimise HER scan rate sweep"))
        assert result.success is True
        assert result.data["intent"] == "optimisation_run"

    def test_stability_goal(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(goal="durability test"))
        assert result.success is True
        assert result.data["intent"] == "stability_run"

    def test_result_data_keys(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute())
        for key in ("intent", "rationale", "plan", "valid"):
            assert key in result.data, f"Missing key: {key}"

    def test_plan_has_steps(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute())
        assert len(result.data["plan"]["steps"]) > 0

    def test_custom_name_applied(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute(name="my_custom_run"))
        assert result.data["plan"]["name"] == "my_custom_run"

    def test_rationale_is_string(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        skill = SuggestNextExperimentSkill()
        result = run_async(skill.execute())
        assert isinstance(result.data["rationale"], str)
        assert len(result.data["rationale"]) > 0

    def test_get_schema(self) -> None:
        from src.skills.suggest_next_experiment import SuggestNextExperimentSkill
        schema = SuggestNextExperimentSkill().get_schema()
        assert schema["type"] == "object"
        assert "context_data" in schema["properties"]
        assert "goal" in schema["properties"]


# ── Supervisor Graph extensions ───────────────────────────────────────────────

class TestSupervisorGraphExtensions:
    def test_build_supervisor_graph_returns_graph(self) -> None:
        from src.graph.supervisor_graph import build_supervisor_graph
        graph = build_supervisor_graph()
        assert graph is not None

    def test_get_supervisor_graph_cached(self) -> None:
        from src.graph.supervisor_graph import get_supervisor_graph
        g1 = get_supervisor_graph()
        g2 = get_supervisor_graph()
        assert g1 is g2

    def test_route_task_contextualize(self) -> None:
        from src.graph.supervisor_graph import route_task
        state: dict[str, Any] = {
            "messages": [], "current_agent": "", "task": {"type": "contextualize"},
            "context": {}, "error": None, "result": None,
        }
        assert route_task(state) == "contextualize"  # type: ignore[arg-type]

    def test_route_task_suggest(self) -> None:
        from src.graph.supervisor_graph import route_task
        state: dict[str, Any] = {
            "messages": [], "current_agent": "", "task": {"type": "suggest"},
            "context": {}, "error": None, "result": None,
        }
        assert route_task(state) == "suggest"  # type: ignore[arg-type]

    def test_route_task_default_is_monitor(self) -> None:
        from src.graph.supervisor_graph import route_task
        state: dict[str, Any] = {
            "messages": [], "current_agent": "", "task": {"type": "unknown_xyz"},
            "context": {}, "error": None, "result": None,
        }
        assert route_task(state) == "monitor"  # type: ignore[arg-type]

    def test_supervisor_graph_invoke_contextualize(self, tmp_path: Path) -> None:
        from src.graph.supervisor_graph import build_supervisor_graph
        _make_run_dir(tmp_path)
        graph = build_supervisor_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "supervisor",
            "task": {"type": "contextualize", "run_dir": str(tmp_path)},
            "context": {},
            "error": None,
            "result": None,
        }
        result = run_async(graph.ainvoke(state))
        assert "result" in result
        assert result["result"] is not None

    def test_supervisor_graph_invoke_suggest(self) -> None:
        from src.graph.supervisor_graph import build_supervisor_graph
        graph = build_supervisor_graph()
        state: dict[str, Any] = {
            "messages": [],
            "current_agent": "supervisor",
            "task": {"type": "suggest", "goal": "optimise HER"},
            "context": {},
            "error": None,
            "result": None,
        }
        result = run_async(graph.ainvoke(state))
        assert "result" in result
        r = result["result"]
        assert r is not None
        # SkillResult serialised via model_dump
        assert r.get("success") is True


# ── Context API routes ────────────────────────────────────────────────────────

class TestContextAPIRoute:
    def test_import_router(self) -> None:
        from src.api.routes.context import router
        from fastapi import APIRouter
        assert isinstance(router, APIRouter)
        assert router.prefix == "/context"

    def test_router_registered_in_app(self) -> None:
        from src.api.main import app
        routes = [r.path for r in app.routes]
        assert any("context" in r for r in routes)

    def test_invoke_suggest_no_args(self) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        response = client.post(
            "/context/invoke",
            json={"action": "suggest"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert data["action"] == "suggest"

    def test_invoke_contextualize_missing_run_dir(self) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        response = client.post(
            "/context/invoke",
            json={"action": "contextualize", "run_dir": ""},
        )
        assert response.status_code == 200
        data = response.json()
        # Should return ok=False (skill fails gracefully on missing run_dir)
        assert data["ok"] is False

    def test_suggest_next_shortcut_endpoint(self) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        response = client.post("/context/suggest-next?goal=HER+optimisation")
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "suggest"
        result = data.get("result") or {}
        assert result.get("success") is True

    def test_contextualize_shortcut_nonexistent_dir(self) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        response = client.post(
            "/context/contextualize",
            params={"run_dir": "/nonexistent/path"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False

    def test_invoke_suggest_with_context_data(self) -> None:
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        ctx = {"anomalies": ["peak_current"], "trend": {}, "comparison": {}}
        response = client.post(
            "/context/invoke",
            json={"action": "suggest", "context_data": ctx},
        )
        assert response.status_code == 200
        data = response.json()
        result = data.get("result") or {}
        assert result.get("success") is True
        # Anomalies should trigger diagnostic_run
        suggest_data = result.get("data") or {}
        assert suggest_data.get("intent") == "diagnostic_run"


# ── Phase 4 import smoke tests ────────────────────────────────────────────────

class TestPhase4Imports:
    def test_contextualize_experiment_module(self) -> None:
        import src.skills.contextualize_experiment  # noqa: F401

    def test_suggest_next_experiment_module(self) -> None:
        import src.skills.suggest_next_experiment  # noqa: F401

    def test_context_api_route_module(self) -> None:
        import src.api.routes.context  # noqa: F401

    def test_supervisor_graph_module(self) -> None:
        import src.graph.supervisor_graph  # noqa: F401

    def test_skills_init_exports_c1_c2(self) -> None:
        from src.skills import (
            ContextualizeExperimentSkill,
            contextualize_experiment_skill,
            SuggestNextExperimentSkill,
            suggest_next_experiment_skill,
        )
        assert ContextualizeExperimentSkill is not None
        assert contextualize_experiment_skill is not None
        assert SuggestNextExperimentSkill is not None
        assert suggest_next_experiment_skill is not None


# ── Knowledge Retriever tests ─────────────────────────────────────────────────

class TestKnowledgeRetriever:
    def test_import(self) -> None:
        from src.tools.knowledge_retriever import retrieve_knowledge, retrieve_literature
        assert callable(retrieve_knowledge)
        assert callable(retrieve_literature)

    def test_exported_from_tools_init(self) -> None:
        from src.tools import retrieve_knowledge, retrieve_literature
        assert callable(retrieve_knowledge)
        assert callable(retrieve_literature)

    def test_retrieve_knowledge_empty_query_returns_empty(self) -> None:
        from src.tools.knowledge_retriever import retrieve_knowledge
        assert retrieve_knowledge("", "/some/path") == []

    def test_retrieve_knowledge_empty_path_returns_empty(self) -> None:
        from src.tools.knowledge_retriever import retrieve_knowledge
        assert retrieve_knowledge("some query", "") == []

    def test_retrieve_knowledge_nonexistent_path_returns_empty(self) -> None:
        from src.tools.knowledge_retriever import retrieve_knowledge
        assert retrieve_knowledge("query", "/nonexistent/kb/path") == []

    def test_retrieve_literature_empty_returns_empty(self) -> None:
        from src.tools.knowledge_retriever import retrieve_literature
        assert retrieve_literature("", "") == []

    def test_parse_literature_from_chunk(self) -> None:
        from src.tools.knowledge_retriever import _parse_literature_from_chunk
        chunk = {
            "content": "Some paper content",
            "source": "doi:10.1234/example",
            "metadata": {
                "title": "HER Catalyst Study",
                "authors": "Smith J, Doe A",
                "year": "2024",
                "doi": "10.1234/example",
                "abstract": "A study on HER catalysts.",
                "keywords": ["HER", "catalyst"],
            },
        }
        ref = _parse_literature_from_chunk(chunk)
        assert ref is not None
        assert ref.title == "HER Catalyst Study"
        assert len(ref.authors) == 2
        assert ref.year == 2024
        assert ref.doi == "10.1234/example"

    def test_parse_literature_no_title_uses_content(self) -> None:
        from src.tools.knowledge_retriever import _parse_literature_from_chunk
        chunk = {"content": "First line as title\nMore content", "metadata": {}}
        ref = _parse_literature_from_chunk(chunk)
        assert ref is not None
        assert ref.title == "First line as title"

    def test_parse_literature_empty_chunk_returns_none(self) -> None:
        from src.tools.knowledge_retriever import _parse_literature_from_chunk
        chunk = {"content": "", "metadata": {}}
        ref = _parse_literature_from_chunk(chunk)
        assert ref is None

    def test_build_kb_query(self) -> None:
        from src.skills.contextualize_experiment import _build_kb_query
        q = _build_kb_query(
            {"exp_name": "HER_test"},
            {"peak_current": 0.05, "onset_potential": -0.3},
            ["peak_current"],
        )
        assert "HER_test" in q
        assert "peak_current" in q


# ── C1 + Knowledge Base integration tests ─────────────────────────────────────

class TestContextualizeWithKB:
    def test_result_includes_literature_and_chunks_keys(self, tmp_path: Path) -> None:
        """Output always includes literature and knowledge_chunks keys."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        _make_run_dir(tmp_path, {"peak_current": 0.05})
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        for key in ("literature", "knowledge_chunks"):
            assert key in result.data, f"Missing key: {key}"

    def test_no_kb_path_returns_empty_kb_fields(self, tmp_path: Path) -> None:
        """Without kb_path, literature and knowledge_chunks are empty lists."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        _make_run_dir(tmp_path, {"peak_current": 0.05})
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.data["literature"] == []
        assert result.data["knowledge_chunks"] == []

    def test_nonexistent_kb_path_returns_empty_kb_fields(self, tmp_path: Path) -> None:
        """Non-existent kb_path gracefully returns empty KB results."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        _make_run_dir(tmp_path, {"peak_current": 0.05})
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(tmp_path),
            kb_path="/nonexistent/kb",
        ))
        assert result.success is True
        assert result.data["literature"] == []
        assert result.data["knowledge_chunks"] == []

    def test_schema_includes_kb_params(self) -> None:
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        schema = ContextualizeExperimentSkill().get_schema()
        for param in ("kb_path", "kb_query", "kb_limit", "kb_score_threshold"):
            assert param in schema["properties"], f"Missing schema property: {param}"

    def test_no_metrics_with_kb_path_still_returns_kb_fields(self, tmp_path: Path) -> None:
        """Even with no numeric metrics, KB fields should be present."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        (tmp_path / "run_summary.json").write_text(json.dumps({"run_id": "r1"}))
        skill = ContextualizeExperimentSkill()
        result = run_async(skill.execute(
            run_dir=str(tmp_path),
            kb_path="/nonexistent/kb",
        ))
        assert result.success is True
        assert "literature" in result.data
        assert "knowledge_chunks" in result.data
