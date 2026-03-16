"""Tests for KnowledgeManagerAgent."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch


class TestKnowledgeArchive(unittest.TestCase):
    """Test experiment archival."""

    def test_archive_experiment(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        result = asyncio.run(agent.archive_experiment(
            run_id="test_001",
            params={"Fe": 0.5, "Co": 0.3, "Ni": 0.2},
            metrics={"overpotential_mV": 200},
            round_num=1,
        ))
        assert result["status"] == "archived"
        assert result["total_records"] == 1

    def test_archive_multiple(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        for i in range(3):
            asyncio.run(agent.archive_experiment(
                run_id=f"test_{i:03d}",
                params={"Fe": 0.3 + i * 0.1, "Co": 0.4 - i * 0.05, "Ni": 0.3 - i * 0.05},
                metrics={"overpotential_mV": 250 - i * 20},
                round_num=i,
            ))
        assert len(agent._archive) == 3

    def test_get_experiment_history(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        asyncio.run(agent.archive_experiment(
            run_id="test_001",
            params={"Fe": 0.5},
            metrics={"ovp": 200},
        ))
        history = agent.get_experiment_history()
        assert len(history) == 1
        assert history[0]["run_id"] == "test_001"


class TestKnowledgeBestExperiments(unittest.TestCase):
    """Test best experiment retrieval."""

    def _make_agent(self) -> Any:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent
        agent = KnowledgeManagerAgent()
        for i, (ovp, fe) in enumerate([(250, 0.3), (200, 0.5), (180, 0.6)]):
            asyncio.run(agent.archive_experiment(
                run_id=f"r_{i}",
                params={"Fe": fe},
                metrics={"overpotential_mV": ovp},
                round_num=i,
            ))
        return agent

    def test_best_minimize(self) -> None:
        agent = self._make_agent()
        best = agent.get_best_experiments("overpotential_mV", "minimize", top_k=1)
        assert len(best) == 1
        assert best[0]["metrics"]["overpotential_mV"] == 180

    def test_best_maximize(self) -> None:
        agent = self._make_agent()
        best = agent.get_best_experiments("overpotential_mV", "maximize", top_k=1)
        assert len(best) == 1
        assert best[0]["metrics"]["overpotential_mV"] == 250

    def test_best_top_k(self) -> None:
        agent = self._make_agent()
        best = agent.get_best_experiments("overpotential_mV", "minimize", top_k=2)
        assert len(best) == 2


class TestKnowledgeSearch(unittest.TestCase):
    """Test search functionality."""

    def test_search_literature(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        results = agent._search_literature("Fe-Co-Ni HER 催化剂", top_k=5)
        assert len(results) > 0
        assert results[0]["source"] == "literature"

    def test_search_experiments(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        asyncio.run(agent.archive_experiment(
            run_id="exp_fe60",
            params={"Fe": 0.6, "Co": 0.25, "Ni": 0.15},
            metrics={"overpotential_mV": 190},
        ))
        results = agent._search_experiments(
            query="Fe overpotential",
            elements=["Fe", "Co", "Ni"],
            top_k=5,
        )
        assert len(results) > 0

    def test_search_empty_archive(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        results = agent._search_experiments("anything", None, 5)
        assert len(results) == 0


class TestKnowledgeRetrieval(unittest.TestCase):
    """Test full retrieve flow."""

    def test_retrieve_literature_only(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        with patch.object(agent, "invoke", side_effect=Exception("no LLM")):
            result = asyncio.run(agent.retrieve(
                query="HER 催化剂性能",
                search_type="literature",
                top_k=3,
            ))
        assert result["status"] == "retrieved"
        assert len(result["results"]) > 0

    def test_retrieve_both(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        agent = KnowledgeManagerAgent()
        asyncio.run(agent.archive_experiment(
            run_id="exp1",
            params={"Fe": 0.5},
            metrics={"overpotential_mV": 200},
        ))
        with patch.object(agent, "invoke", side_effect=Exception("no LLM")):
            result = asyncio.run(agent.retrieve(
                query="Fe 过电位",
                search_type="both",
                top_k=5,
            ))
        assert result["status"] == "retrieved"


class TestKnowledgePersistence(unittest.TestCase):
    """Test archive file persistence."""

    def test_save_and_load(self) -> None:
        from src.agents.knowledge_mgr import KnowledgeManagerAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "archive.json")

            # Save
            agent1 = KnowledgeManagerAgent(archive_path=path)
            asyncio.run(agent1.archive_experiment(
                run_id="test1",
                params={"Fe": 0.5},
                metrics={"ovp": 200},
            ))
            assert Path(path).exists()

            # Load
            agent2 = KnowledgeManagerAgent(archive_path=path)
            assert len(agent2._archive) == 1
            assert agent2._archive[0]["run_id"] == "test1"


class TestKnowledgeRouting(unittest.TestCase):
    """Test routing to knowledge manager."""

    def test_literature_routes_to_km(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "search literature for Fe-Co-Ni"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "knowledge_mgr"

    def test_paper_routes_to_km(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [], "current_agent": "",
            "task": {"intent": "find relevant paper"},
            "context": {}, "error": None, "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "knowledge_mgr"


if __name__ == "__main__":
    unittest.main()
