"""Basic import smoke test for scaffolded modules."""

from __future__ import annotations


def test_core_imports() -> None:
    import src.api.main  # noqa: F401
    import src.graph.orchestrator  # noqa: F401
    import src.tools.echem_reader  # noqa: F401

