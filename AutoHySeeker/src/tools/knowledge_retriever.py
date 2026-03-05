"""Knowledge retriever — OpenViking knowledge-base integration.

Provides two helper functions that wrap the OpenViking ``find()`` API to
retrieve literature references and experiment-related knowledge chunks.
When OpenViking is not installed or the knowledge-base path does not exist,
the functions return empty lists gracefully.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.common.types import KnowledgeChunk, LiteratureRef

logger = logging.getLogger(__name__)

# Lazy import guard — OpenViking may not be installed in every environment.
_ov_available: bool | None = None


def _get_openviking_client(kb_path: str) -> Any | None:
    """Return an initialised OpenViking client or ``None``."""
    global _ov_available
    if _ov_available is False:
        return None
    try:
        from openviking import OpenViking  # type: ignore[import-untyped]

        client = OpenViking(path=kb_path)
        client.initialize()
        _ov_available = True
        return client
    except Exception as exc:  # noqa: BLE001
        logger.debug("OpenViking unavailable: %s", exc)
        _ov_available = False
        return None


def _parse_literature_from_chunk(chunk: dict[str, Any]) -> LiteratureRef | None:
    """Best-effort extraction of a :class:`LiteratureRef` from a chunk dict."""
    meta = chunk.get("metadata") or {}
    content = chunk.get("content", "")
    title = meta.get("title", "")
    if not title:
        # Use first non-empty line as title
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped:
                title = stripped[:200]
                break
    if not title:
        return None

    authors_raw = meta.get("authors", [])
    if isinstance(authors_raw, str):
        authors_raw = [a.strip() for a in authors_raw.split(",") if a.strip()]

    year = meta.get("year")
    if isinstance(year, str):
        m = re.search(r"\b(19|20)\d{2}\b", year)
        year = int(m.group()) if m else None

    return LiteratureRef(
        title=title,
        authors=authors_raw,
        year=year,
        doi=meta.get("doi"),
        abstract=meta.get("abstract", ""),
        keywords=meta.get("keywords", []),
        source_file=chunk.get("source"),
    )


def retrieve_knowledge(
    query: str,
    kb_path: str,
    limit: int = 10,
    score_threshold: float = 0.3,
) -> list[KnowledgeChunk]:
    """Retrieve knowledge chunks from OpenViking.

    Args:
        query: Natural-language search query.
        kb_path: Path to the OpenViking data directory.
        limit: Maximum number of results.
        score_threshold: Minimum similarity score.

    Returns:
        List of :class:`KnowledgeChunk` (empty if OpenViking is unavailable).
    """
    if not query or not kb_path:
        return []

    kb = Path(kb_path)
    if not kb.exists():
        logger.debug("Knowledge base path does not exist: %s", kb_path)
        return []

    client = _get_openviking_client(kb_path)
    if client is None:
        return []

    try:
        raw_results = client.find(
            query=query,
            limit=limit,
            score_threshold=score_threshold,
        )
        # Normalise raw results into KnowledgeChunk objects
        chunks: list[KnowledgeChunk] = []
        items = raw_results if isinstance(raw_results, list) else (raw_results or {}).get("results", [])
        for item in items:
            if isinstance(item, dict):
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=str(item.get("id", item.get("chunk_id", ""))),
                        content=str(item.get("content", "")),
                        source=str(item.get("source", item.get("uri", ""))),
                        score=float(item.get("score", 0.0)),
                        metadata=item.get("metadata") or {},
                    )
                )
        return chunks
    except Exception as exc:  # noqa: BLE001
        logger.warning("Knowledge retrieval failed: %s", exc)
        return []
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass


def retrieve_literature(
    query: str,
    kb_path: str,
    limit: int = 5,
    score_threshold: float = 0.3,
) -> list[LiteratureRef]:
    """Retrieve literature references related to *query* from OpenViking.

    Internally calls :func:`retrieve_knowledge` and then extracts
    :class:`LiteratureRef` objects from chunks whose metadata resembles a
    literature entry (has a title, DOI, or author list).

    Args:
        query: Natural-language search query.
        kb_path: Path to the OpenViking data directory.
        limit: Maximum number of results to retrieve.
        score_threshold: Minimum similarity score.

    Returns:
        List of :class:`LiteratureRef` (may be empty).
    """
    chunks = retrieve_knowledge(query, kb_path, limit=limit, score_threshold=score_threshold)
    refs: list[LiteratureRef] = []
    for chunk in chunks:
        raw = {
            "content": chunk.content,
            "source": chunk.source,
            "metadata": chunk.metadata,
        }
        ref = _parse_literature_from_chunk(raw)
        if ref is not None:
            refs.append(ref)
    return refs
