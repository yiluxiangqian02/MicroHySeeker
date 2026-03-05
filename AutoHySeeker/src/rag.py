"""OpenViking knowledge-base client for AutoHySeeker.

Acts as ``src/rag/__init__.py`` equivalent (single-file module pattern).

OpenViking (https://github.com/volcengine/openviking) is ByteDance Volcano Engine's
AI Agent context database — it replaces the custom ChromaDB/RAG pipeline with a
higher-level ``add_resource`` / ``find`` API that handles chunking, embedding, and
hierarchical retrieval automatically.

This module wraps the OpenViking SDK with:
* A ``VikingKnowledgeBase`` class that provides ``search_literature`` and
  ``search_experiments`` helpers.
* Graceful fallback (returns empty lists) when the ``openviking`` package is
  not installed — this keeps the skill functional in offline / test environments.

Usage::

    from src.rag import get_viking_kb

    kb = get_viking_kb()                              # singleton
    refs  = kb.search_literature("HER Tafel slope", top_k=5)
    exps  = kb.search_experiments("0.3M Fe CV 50mV/s", top_k=3)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.common.logger import get_logger

logger = get_logger(__name__)

# ── OpenViking optional import ────────────────────────────────────────────────
try:
    import openviking as ov  # type: ignore[import-untyped]
    _OPENVIKING_AVAILABLE = True
except ImportError:  # pragma: no cover - availability dependent
    ov = None  # type: ignore[assignment]
    _OPENVIKING_AVAILABLE = False

# Default workspace path — override via VIKING_WORKSPACE env var
_DEFAULT_WORKSPACE = str(
    Path(__file__).resolve().parents[1] / "OpenViking"
)


class VikingKnowledgeBase:
    """AutoHySeeker wrapper around the OpenViking SDK.

    viking:// virtual-filesystem layout::

        viking://
        ├── resources/
        │   ├── literature/        # academic papers (PDFs / text)
        │   ├── experiments/       # archived experiment runs
        │   ├── manuals/           # instrument manuals
        │   ├── error_solutions/   # error-resolution knowledge
        │   └── domain_knowledge/  # electrochemistry theory
        └── agent/
            └── memories/          # accumulated agent experience

    When ``openviking`` is not installed every method returns an empty list,
    allowing skills to degrade gracefully instead of crashing.
    """

    def __init__(self, workspace_path: str | None = None) -> None:
        self._workspace = workspace_path or os.getenv(
            "VIKING_WORKSPACE", _DEFAULT_WORKSPACE
        )
        self._client: Any = None
        self._available = _OPENVIKING_AVAILABLE

        if self._available:
            try:
                self._client = ov.SyncOpenViking(path=self._workspace)
                self._client.initialize()
                logger.debug("OpenViking KB initialised at %s", self._workspace)
            except Exception as exc:  # pragma: no cover
                logger.warning("OpenViking init failed (%s) — using fallback", exc)
                self._available = False

    # ── Core search ──────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        target_uri: str = "viking://resources/",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Semantic search over a viking:// URI subtree.

        Args:
            query: Natural-language query string.
            target_uri: Restrict search to this virtual directory.
            top_k: Maximum number of results to return.

        Returns:
            List of resource dicts with keys ``uri``, ``content``, ``score``,
            and ``metadata``.  Returns ``[]`` when OpenViking is unavailable.
        """
        if not self._available or self._client is None:
            return []

        try:
            result = self._client.find(query, target_uri=target_uri, top_k=top_k)
            resources = getattr(result, "resources", result) if result else []
            return [_normalise_resource(r) for r in resources]
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenViking search failed (%s)", exc)
            return []

    # ── Domain-specific helpers ───────────────────────────────────────────────

    def search_literature(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Search academic literature stored in ``viking://resources/literature/``."""
        return self.search(
            query, target_uri="viking://resources/literature/", top_k=top_k
        )

    def search_experiments(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Search archived experiment records in ``viking://resources/experiments/``."""
        return self.search(
            query, target_uri="viking://resources/experiments/", top_k=top_k
        )

    def search_error_solutions(
        self, query: str, top_k: int = 3
    ) -> list[dict[str, Any]]:
        """Search error-resolution knowledge in ``viking://resources/error_solutions/``."""
        return self.search(
            query, target_uri="viking://resources/error_solutions/", top_k=top_k
        )

    def search_domain_knowledge(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Search electrochemistry theory in ``viking://resources/domain_knowledge/``."""
        return self.search(
            query, target_uri="viking://resources/domain_knowledge/", top_k=top_k
        )

    # ── Hierarchical context loading ─────────────────────────────────────────

    def get_abstract(self, uri: str) -> str:
        """Return L0 abstract (~100 tokens) for a resource URI."""
        if not self._available or self._client is None:
            return ""
        try:
            return str(self._client.abstract(uri))
        except Exception:  # pragma: no cover
            return ""

    def get_overview(self, uri: str) -> str:
        """Return L1 overview (~2k tokens) for a resource URI."""
        if not self._available or self._client is None:
            return ""
        try:
            return str(self._client.overview(uri))
        except Exception:  # pragma: no cover
            return ""

    # ── Ingest helpers ────────────────────────────────────────────────────────

    def ingest_document(
        self,
        path: str,
        target_dir: str = "resources/literature",
    ) -> dict[str, Any]:
        """Ingest a document (PDF / text / directory) into the knowledge base."""
        if not self._available or self._client is None:
            return {"ingested": False, "reason": "openviking_unavailable"}
        try:
            result = self._client.add_resource(
                path=path, uri=f"viking://{target_dir}/"
            )
            self._client.wait_processed()
            return dict(result) if result else {"ingested": True}
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenViking ingest failed (%s)", exc)
            return {"ingested": False, "reason": str(exc)}

    def ingest_experiment(self, run_dir: str) -> dict[str, Any]:
        """Archive an experiment run directory into the knowledge base."""
        return self.ingest_document(run_dir, target_dir="resources/experiments")

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def is_available(self) -> bool:
        """Return True if OpenViking SDK is installed and initialised."""
        return self._available

    def close(self) -> None:
        """Close the underlying OpenViking client."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover
                pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_resource(resource: Any) -> dict[str, Any]:
    """Convert an OpenViking resource object to a plain dict."""
    if isinstance(resource, dict):
        return resource
    result: dict[str, Any] = {}
    for attr in ("uri", "content", "score", "metadata"):
        val = getattr(resource, attr, None)
        if val is not None:
            result[attr] = val
    return result


# ── Singleton ─────────────────────────────────────────────────────────────────

_VIKING_KB: VikingKnowledgeBase | None = None


def get_viking_kb(workspace_path: str | None = None) -> VikingKnowledgeBase:
    """Return a cached :class:`VikingKnowledgeBase` instance."""
    global _VIKING_KB
    if _VIKING_KB is None:
        _VIKING_KB = VikingKnowledgeBase(workspace_path)
    return _VIKING_KB
