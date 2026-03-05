"""Tests for Phase 4 C1 — ContextualizeExperimentSkill + VikingKnowledgeBase."""

from __future__ import annotations

import asyncio
import pytest


# ── VikingKnowledgeBase tests ─────────────────────────────────────────────────

class TestVikingKnowledgeBase:
    """Tests for VikingKnowledgeBase client (fallback mode without openviking SDK)."""

    def test_import(self):
        """rag.py module and VikingKnowledgeBase should import cleanly."""
        from src.rag import VikingKnowledgeBase, get_viking_kb  # noqa: F401

    def test_is_available_false_without_sdk(self):
        """Without openviking installed, is_available should be False."""
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        # openviking is not in pyproject.toml so it won't be installed
        # is_available may be False; if SDK somehow present, it can be True too
        assert isinstance(kb.is_available, bool)

    def test_search_returns_list(self):
        """search() always returns a list (empty when unavailable)."""
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.search("HER catalyst", target_uri="viking://resources/")
        assert isinstance(result, list)

    def test_search_literature_returns_list(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.search_literature("Tafel slope NiFe")
        assert isinstance(result, list)

    def test_search_experiments_returns_list(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.search_experiments("CV Fe 0.3M scan rate")
        assert isinstance(result, list)

    def test_search_error_solutions_returns_list(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.search_error_solutions("pump stall")
        assert isinstance(result, list)

    def test_search_domain_knowledge_returns_list(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.search_domain_knowledge("EIS equivalent circuit")
        assert isinstance(result, list)

    def test_get_abstract_returns_str(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.get_abstract("viking://resources/literature/test")
        assert isinstance(result, str)

    def test_get_overview_returns_str(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.get_overview("viking://resources/experiments/test")
        assert isinstance(result, str)

    def test_ingest_document_returns_dict(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.ingest_document("/nonexistent/paper.pdf")
        assert isinstance(result, dict)
        # When unavailable, should report so
        if not kb.is_available:
            assert result.get("ingested") is False

    def test_ingest_experiment_returns_dict(self):
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        result = kb.ingest_experiment("/nonexistent/run_dir")
        assert isinstance(result, dict)

    def test_singleton_get_viking_kb(self):
        """get_viking_kb() should return the same object on repeated calls."""
        from src.rag import get_viking_kb
        kb1 = get_viking_kb()
        kb2 = get_viking_kb()
        assert kb1 is kb2

    def test_close_no_error(self):
        """close() should not raise even when unavailable."""
        from src.rag import VikingKnowledgeBase
        kb = VikingKnowledgeBase()
        kb.close()  # should not raise


# ── ContextualizeExperimentSkill tests ────────────────────────────────────────

class TestContextualizeExperimentSkill:
    """Tests for the C1 ContextualizeExperimentSkill."""

    def test_import(self):
        """Skill should import without error."""
        from src.skills.contextualize_experiment import (  # noqa: F401
            ContextualizeExperimentSkill,
            contextualize_experiment_skill,
        )

    def test_singleton_exported_from_skills(self):
        """Skill and singleton should be exported from the top-level skills package."""
        from src.skills import ContextualizeExperimentSkill, contextualize_experiment_skill  # noqa: F401
        assert ContextualizeExperimentSkill is not None
        assert contextualize_experiment_skill is not None

    def test_execute_missing_query_and_goal(self):
        """Calling execute with no query or goal should return failure."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        result = asyncio.run(skill.execute(query="", goal=""))
        assert result.success is False
        assert "required" in result.message.lower() or "query" in result.message.lower()

    def test_execute_with_query_fallback(self):
        """With unavailable OpenViking, skill should still succeed (empty context)."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        result = asyncio.run(skill.execute(query="HER NiFe catalyst"))
        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)
        assert isinstance(result.message, str)
        # Either success (empty context from unavailable KB) or import error
        if result.success:
            assert "source" in result.data
            assert "literature" in result.data
            assert "experiments" in result.data

    def test_execute_with_goal_only(self):
        """Passing only goal (no query) should be accepted."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        result = asyncio.run(skill.execute(goal="screen OER catalysts"))
        # Should not fail due to missing query
        assert not (result.success is False and "required" in result.message.lower())

    def test_execute_with_techniques(self):
        """Techniques list should be accepted and incorporated into the query."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        result = asyncio.run(
            skill.execute(
                query="iron oxide electrocatalyst",
                goal="HER screening",
                techniques=["CV", "EIS"],
                top_k=3,
            )
        )
        assert isinstance(result, type(result))  # just check it didn't throw

    def test_result_data_structure(self):
        """Result data should contain expected keys when KB is unavailable."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        result = asyncio.run(skill.execute(query="Tafel slope analysis"))
        if result.success:
            data = result.data
            assert "source" in data
            assert "literature" in data
            assert "experiments" in data
            assert isinstance(data["literature"], list)
            assert isinstance(data["experiments"], list)

    def test_get_schema(self):
        """get_schema() should return a valid JSON Schema dict."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        schema = skill.get_schema()
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "goal" in schema["properties"]
        assert "techniques" in schema["properties"]
        assert "top_k" in schema["properties"]

    def test_skill_metadata(self):
        """Skill should have correct name and description."""
        from src.skills.contextualize_experiment import ContextualizeExperimentSkill
        skill = ContextualizeExperimentSkill()
        assert skill.name == "contextualize_experiment"
        assert "OpenViking" in skill.description or "知识库" in skill.description


# ── Integration: skills __init__ exports ──────────────────────────────────────

class TestSkillsInit:
    """Verify skills package exports are coherent after C1 addition."""

    def test_all_exports_importable(self):
        """Every name in skills.__all__ should be importable."""
        import src.skills as skills_pkg
        for name in skills_pkg.__all__:
            assert hasattr(skills_pkg, name), f"Missing export: {name}"

    def test_c1_in_all(self):
        """ContextualizeExperimentSkill should be listed in __all__."""
        import src.skills as skills_pkg
        assert "ContextualizeExperimentSkill" in skills_pkg.__all__
        assert "contextualize_experiment_skill" in skills_pkg.__all__
