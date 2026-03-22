"""Tests for KnowledgeArchiveSkill (formerly KnowledgeManagerAgent).

After the 7→4 agent consolidation, knowledge management is a skill of
the Orchestrator.  These tests verify the skill directly.
"""

from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from typing import Any


class TestKnowledgeArchive(unittest.TestCase):
    """Test experiment archival."""

    def test_archive_experiment(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        result = asyncio.run(skill.archive_experiment(
            run_id="test_001",
            params={"Fe": 0.5, "Co": 0.3, "Ni": 0.2},
            metrics={"overpotential_mV": 200},
            round_num=1,
        ))
        assert result["status"] == "archived"
        assert result["total_records"] == 1
        assert result["knowledge_write"]["partition"] == "experiments"

    def test_archive_multiple(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        for i in range(3):
            asyncio.run(skill.archive_experiment(
                run_id=f"test_{i:03d}",
                params={"Fe": 0.3 + i * 0.1, "Co": 0.4 - i * 0.05, "Ni": 0.3 - i * 0.05},
                metrics={"overpotential_mV": 250 - i * 20},
                round_num=i,
            ))
        assert len(skill._archive) == 3

    def test_get_experiment_history(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        asyncio.run(skill.archive_experiment(
            run_id="test_001",
            params={"Fe": 0.5},
            metrics={"ovp": 200},
        ))
        history = skill.get_experiment_history()
        assert len(history) == 1
        assert history[0]["run_id"] == "test_001"

    def test_archive_experiment_records_environment_snapshot(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        result = asyncio.run(skill.archive_experiment(
            run_id="test_env_001",
            params={"Fe": 0.4, "Co": 0.4, "Ni": 0.2},
            metrics={"overpotential_mV": 195.0},
            environment_snapshot={"template_id": "tpl_her_standard", "config_hash": "abc123"},
        ))

        assert result["environment_snapshot"]["template_id"] == "tpl_her_standard"
        assert skill._archive[0]["environment_snapshot"]["config_hash"] == "abc123"

    def test_archive_operation_writes_to_operations_partition(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        result = asyncio.run(skill.archive_operation(
            event_type="communication_timeout",
            severity="error",
            message="RS485 timeout on COM3",
            component="executor",
            run_id="run_001",
            action_taken="disconnect and reconnect",
            resolved=True,
            environment_snapshot={"port": "COM3"},
        ))

        assert result["status"] == "archived"
        assert result["partition"] == "operations"
        assert result["knowledge_write"]["partition"] == "operations"
        hits = skill._viking_client.search("communication_timeout", partition="operations", top_k=5)
        assert len(hits) >= 1


class TestKnowledgeBestExperiments(unittest.TestCase):
    """Test best experiment retrieval."""

    def _make_skill(self) -> Any:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill
        skill = KnowledgeArchiveSkill()
        for i, (ovp, fe) in enumerate([(250, 0.3), (200, 0.5), (180, 0.6)]):
            asyncio.run(skill.archive_experiment(
                run_id=f"r_{i}",
                params={"Fe": fe},
                metrics={"overpotential_mV": ovp},
                round_num=i,
            ))
        return skill

    def test_best_minimize(self) -> None:
        skill = self._make_skill()
        best = skill.get_best_experiments("overpotential_mV", "minimize", top_k=1)
        assert len(best) == 1
        assert best[0]["metrics"]["overpotential_mV"] == 180

    def test_best_maximize(self) -> None:
        skill = self._make_skill()
        best = skill.get_best_experiments("overpotential_mV", "maximize", top_k=1)
        assert len(best) == 1
        assert best[0]["metrics"]["overpotential_mV"] == 250

    def test_best_top_k(self) -> None:
        skill = self._make_skill()
        best = skill.get_best_experiments("overpotential_mV", "minimize", top_k=2)
        assert len(best) == 2


class TestKnowledgeSearch(unittest.TestCase):
    """Test search functionality."""

    def test_search_literature(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        results = skill._search_literature("Fe-Co-Ni HER \u50ac\u5316\u5242", top_k=5)
        assert len(results) > 0
        assert results[0]["source"] == "literature"

    def test_search_experiments(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        asyncio.run(skill.archive_experiment(
            run_id="exp_fe60",
            params={"Fe": 0.6, "Co": 0.25, "Ni": 0.15},
            metrics={"overpotential_mV": 190},
        ))
        results = skill._search_experiments(
            query="Fe overpotential",
            elements=["Fe", "Co", "Ni"],
            top_k=5,
        )
        assert len(results) > 0

    def test_search_empty_archive(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        results = skill._search_experiments("anything", None, 5)
        assert len(results) == 0


class TestKnowledgeRetrieval(unittest.TestCase):
    """Test full retrieve flow."""

    def test_retrieve_literature_only(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        result = asyncio.run(skill.retrieve(
            query="HER \u50ac\u5316\u5242\u6027\u80fd",
            search_type="literature",
            top_k=3,
        ))
        assert result["status"] == "retrieved"
        assert len(result["results"]) > 0

    def test_retrieve_both(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        skill = KnowledgeArchiveSkill()
        asyncio.run(skill.archive_experiment(
            run_id="exp1",
            params={"Fe": 0.5},
            metrics={"overpotential_mV": 200},
        ))
        result = asyncio.run(skill.retrieve(
            query="Fe \u8fc7\u7535\u4f4d",
            search_type="both",
            top_k=5,
        ))
        assert result["status"] == "retrieved"


class TestKnowledgePersistence(unittest.TestCase):
    """Test archive file persistence."""

    def test_save_and_load(self) -> None:
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill

        tmpdir = Path("tests/_tmp_persistence")
        tmpdir.mkdir(parents=True, exist_ok=True)
        path = tmpdir / "archive.json"
        try:
            skill1 = KnowledgeArchiveSkill(archive_path=str(path))
            asyncio.run(skill1.archive_experiment(
                run_id="test1",
                params={"Fe": 0.5},
                metrics={"ovp": 200},
            ))
            assert path.exists()

            skill2 = KnowledgeArchiveSkill(archive_path=str(path))
            assert len(skill2._archive) == 1
            assert skill2._archive[0]["run_id"] == "test1"
        finally:
            if path.exists():
                path.unlink()
            if tmpdir.exists():
                tmpdir.rmdir()


class TestKnowledgeRouting(unittest.TestCase):
    """Test routing: knowledge/literature keywords now go to orchestrator."""

    def test_literature_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "search literature for Fe-Co-Ni"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"

    def test_paper_routes_to_orchestrator(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "find relevant paper"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "orchestrator"


if __name__ == "__main__":
    unittest.main()
