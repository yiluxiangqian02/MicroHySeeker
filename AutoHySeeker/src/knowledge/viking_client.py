"""Partition-aware OpenViking client wrapper.

Provides a stable CRUD-like facade for downstream skills/APIs while keeping
OpenViking optional in local/offline test environments.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.common.logger import get_logger
from src.knowledge.schema import PARTITION_URIS, KnowledgePartition

logger = get_logger(__name__)

try:
    import openviking as ov  # type: ignore[import-untyped]

    _OPENVIKING_AVAILABLE = True
except ImportError:  # pragma: no cover
    ov = None  # type: ignore[assignment]
    _OPENVIKING_AVAILABLE = False

_DEFAULT_WORKSPACE = str(Path(__file__).resolve().parents[2] / "OpenViking")


class OpenVikingClient:
    """OpenViking facade with partition-level helpers."""

    def __init__(self, workspace_path: str | None = None) -> None:
        self._workspace = workspace_path or os.getenv("VIKING_WORKSPACE", _DEFAULT_WORKSPACE)
        self._client: Any = None
        self._available = False
        self._fallback_store: dict[str, list[dict[str, Any]]] = {
            partition.value: [] for partition in KnowledgePartition
        }
        self.initialize()

    def initialize(self) -> bool:
        """Initialize OpenViking SDK; fallback to in-memory mode when unavailable."""
        if not _OPENVIKING_AVAILABLE:
            self._available = False
            logger.info("OpenViking SDK unavailable, using fallback store")
            return False

        try:
            self._client = ov.SyncOpenViking(path=self._workspace)
            self._client.initialize()
            self._available = True
            logger.info("OpenViking initialized: %s", self._workspace)
            return True
        except Exception as exc:  # pragma: no cover
            self._client = None
            self._available = False
            logger.warning("OpenViking init failed (%s), using fallback store", exc)
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def workspace(self) -> str:
        return self._workspace

    def get_partition_uri(self, partition: KnowledgePartition | str) -> str:
        """Return viking URI for a partition."""
        partition_enum = self._to_partition(partition)
        return PARTITION_URIS[partition_enum]

    def write_json(
        self,
        partition: KnowledgePartition | str,
        payload: dict[str, Any],
        resource_name: str | None = None,
    ) -> dict[str, Any]:
        """Write a JSON record into a partition."""
        partition_enum = self._to_partition(partition)
        name = resource_name or f"{partition_enum.value}_{uuid4().hex[:8]}.json"
        uri = f"{self.get_partition_uri(partition_enum)}{name}"

        if not self._available or self._client is None:
            self._fallback_store[partition_enum.value].append(
                {
                    "uri": uri,
                    "content": json.dumps(payload, ensure_ascii=False),
                    "metadata": {"partition": partition_enum.value, "resource_name": name},
                }
            )
            return {"written": True, "uri": uri, "partition": partition_enum.value, "mode": "fallback"}

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
                json.dump(payload, tmp, ensure_ascii=False, indent=2)
                tmp_path = tmp.name
            result = self._client.add_resource(path=tmp_path, uri=self.get_partition_uri(partition_enum))
            self._client.wait_processed()
            return {
                "written": True,
                "uri": uri,
                "partition": partition_enum.value,
                "mode": "openviking",
                "result": _to_plain_dict(result),
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenViking write_json failed (%s)", exc)
            return {"written": False, "uri": uri, "partition": partition_enum.value, "error": str(exc)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def write_text(
        self,
        partition: KnowledgePartition | str,
        content: str,
        resource_name: str | None = None,
    ) -> dict[str, Any]:
        """Write a plain text resource into a partition."""
        return self.write_json(
            partition=partition,
            payload={"content": content},
            resource_name=resource_name,
        )

    def search(
        self,
        query: str,
        partition: KnowledgePartition | str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search across all partitions or within a specific partition."""
        target_uri = "viking://resources/"
        target_partition: KnowledgePartition | None = None
        if partition is not None:
            target_partition = self._to_partition(partition)
            target_uri = self.get_partition_uri(target_partition)

        if not self._available or self._client is None:
            return self._fallback_search(query=query, partition=target_partition, top_k=top_k)

        try:
            result = self._client.find(query, target_uri=target_uri, top_k=top_k)
            resources = getattr(result, "resources", result) if result else []
            return [_normalise_resource(item) for item in resources]
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenViking search failed (%s)", exc)
            return []

    def read(self, uri: str, level: str = "overview") -> dict[str, Any]:
        """Read resource context from OpenViking by URI.

        level: "abstract" | "overview"
        """
        if not self._available or self._client is None:
            for records in self._fallback_store.values():
                for item in records:
                    if item.get("uri") == uri:
                        return {"uri": uri, "content": item.get("content", ""), "mode": "fallback"}
            return {"uri": uri, "content": "", "mode": "fallback"}

        try:
            if level == "abstract":
                content = str(self._client.abstract(uri))
            else:
                content = str(self._client.overview(uri))
            return {"uri": uri, "content": content, "mode": "openviking"}
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenViking read failed (%s)", exc)
            return {"uri": uri, "content": "", "error": str(exc)}

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover
                pass

    def _fallback_search(
        self,
        query: str,
        partition: KnowledgePartition | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        query_lower = query.lower().strip()
        buckets = [partition.value] if partition else list(self._fallback_store.keys())
        results: list[dict[str, Any]] = []

        for bucket in buckets:
            for item in self._fallback_store[bucket]:
                content = str(item.get("content", ""))
                haystack = f"{item.get('uri', '')} {content}".lower()
                if not query_lower:
                    score = 0.5
                else:
                    score = 1.0 if query_lower in haystack else 0.0
                if score > 0:
                    results.append(
                        {
                            "uri": item.get("uri", ""),
                            "content": content,
                            "score": score,
                            "metadata": item.get("metadata", {}),
                        }
                    )

        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return results[:top_k]

    @staticmethod
    def _to_partition(partition: KnowledgePartition | str) -> KnowledgePartition:
        if isinstance(partition, KnowledgePartition):
            return partition
        return KnowledgePartition(partition)


def _normalise_resource(resource: Any) -> dict[str, Any]:
    if isinstance(resource, dict):
        return resource
    result: dict[str, Any] = {}
    for attr in ("uri", "content", "score", "metadata"):
        value = getattr(resource, attr, None)
        if value is not None:
            result[attr] = value
    return result


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for attr in ("uri", "id", "status", "message"):
        attr_value = getattr(value, attr, None)
        if attr_value is not None:
            result[attr] = attr_value
    return result
