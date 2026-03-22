"""Partition-aware OpenViking client wrapper.

Provides a stable CRUD-like facade for downstream skills/APIs while keeping
OpenViking optional in local/offline test environments.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.common.logger import get_logger
from src.knowledge.schema import PARTITION_URIS, KnowledgePartition

logger = get_logger(__name__)

_DEFAULT_WORKSPACE = str(Path(__file__).resolve().parents[2] / "OpenViking")
_DEFAULT_OPENVIKING_SRC = Path(__file__).resolve().parents[2] / "OpenViking"
_DEFAULT_PYAGFS_SRC = _DEFAULT_OPENVIKING_SRC / "third_party" / "agfs" / "agfs-sdk" / "python"
_DEFAULT_OPENVIKING_CONFIG = _DEFAULT_OPENVIKING_SRC / ".local_dev" / "ov.conf"


def _load_openviking_module() -> tuple[Any | None, bool, str | None]:
    try:
        return importlib.import_module("openviking"), True, None
    except ImportError as exc:
        initial_error = str(exc)

    openviking_src = Path(os.getenv("AUTOHYSEEKER_OPENVIKING_SRC", str(_DEFAULT_OPENVIKING_SRC)))
    pyagfs_src = Path(os.getenv("AUTOHYSEEKER_PYAGFS_SRC", str(_DEFAULT_PYAGFS_SRC)))

    extra_paths: list[str] = []
    if pyagfs_src.exists():
        extra_paths.append(str(pyagfs_src))
    if openviking_src.exists():
        extra_paths.append(str(openviking_src))

    inserted = False
    for path in reversed(extra_paths):
        if path not in sys.path:
            sys.path.insert(0, path)
            inserted = True

    if inserted:
        try:
            return importlib.import_module("openviking"), True, None
        except ImportError as exc:
            return None, False, str(exc)

    return None, False, initial_error


ov, _OPENVIKING_AVAILABLE, _OPENVIKING_IMPORT_ERROR = _load_openviking_module()


class OpenVikingClient:
    """OpenViking facade with partition-level helpers."""

    def __init__(self, workspace_path: str | None = None) -> None:
        self._workspace = workspace_path or os.getenv("VIKING_WORKSPACE", _DEFAULT_WORKSPACE)
        self._client: Any = None
        self._available = False
        self._init_error: str | None = None
        self._fallback_store: dict[str, list[dict[str, Any]]] = {
            partition.value: [] for partition in KnowledgePartition
        }
        self.initialize()

    def initialize(self) -> bool:
        """Initialize OpenViking SDK; fallback to in-memory mode when unavailable."""
        if not _OPENVIKING_AVAILABLE:
            self._available = False
            self._init_error = _OPENVIKING_IMPORT_ERROR
            logger.info(
                "OpenViking SDK unavailable, using fallback store (%s)",
                _OPENVIKING_IMPORT_ERROR or "import failed",
            )
            return False

        try:
            if "OPENVIKING_CONFIG_FILE" not in os.environ and _DEFAULT_OPENVIKING_CONFIG.exists():
                os.environ["OPENVIKING_CONFIG_FILE"] = str(_DEFAULT_OPENVIKING_CONFIG)
            self._client = ov.SyncOpenViking(path=self._workspace)
            self._client.initialize()
            self._available = True
            self._init_error = None
            logger.info("OpenViking initialized: %s", self._workspace)
            return True
        except Exception as exc:  # pragma: no cover
            self._client = None
            self._available = False
            self._init_error = str(exc)
            logger.warning("OpenViking init failed (%s), using fallback store", exc)
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def workspace(self) -> str:
        return self._workspace

    @property
    def availability_reason(self) -> str | None:
        return None if self._available else (self._init_error or _OPENVIKING_IMPORT_ERROR)

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

        temp_dir: tempfile.TemporaryDirectory[str] | None = None
        tmp_path = ""
        try:
            temp_dir = tempfile.TemporaryDirectory()
            stem = Path(name).stem or f"{partition_enum.value}_{uuid4().hex[:8]}"
            tmp_path = str(Path(temp_dir.name) / f"{stem}.json")
            with open(tmp_path, "w", encoding="utf-8") as tmp:
                json.dump(payload, tmp, ensure_ascii=False, indent=2)
            result = self._client.add_resource(
                path=tmp_path,
                target=self.get_partition_uri(partition_enum),
            )
            self._client.wait_processed()
            result_dict = _to_plain_dict(result)
            actual_uri = result_dict.get("root_uri") or uri
            return {
                "written": True,
                "uri": actual_uri,
                "partition": partition_enum.value,
                "mode": "openviking",
                "verified_partition": actual_uri.startswith(self.get_partition_uri(partition_enum)),
                "result": result_dict,
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenViking write_json failed (%s)", exc)
            return {"written": False, "uri": uri, "partition": partition_enum.value, "error": str(exc)}
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()

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
            result = self._client.find(query, target_uri=target_uri, limit=top_k)
            resources = getattr(result, "resources", result) if result else []
            return [_normalise_resource(item) for item in resources]
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenViking search failed (%s)", exc)
            workspace_hits = self._workspace_search(
                query=query,
                partition=target_partition,
                top_k=top_k,
            )
            if workspace_hits:
                return workspace_hits
            return self._fallback_search(query=query, partition=target_partition, top_k=top_k)

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

    def _workspace_search(
        self,
        query: str,
        partition: KnowledgePartition | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        root = self._workspace_resource_root
        if root is None or not root.exists():
            return []

        query_lower = query.lower().strip()
        buckets = [partition.value] if partition else [item.value for item in KnowledgePartition]
        results: list[dict[str, Any]] = []

        for bucket in buckets:
            bucket_root = root / bucket
            if not bucket_root.exists():
                continue

            seen_uris: set[str] = set()
            for resource_file in bucket_root.rglob("*"):
                if not resource_file.is_file() or resource_file.name.startswith("."):
                    continue

                uri = self._workspace_resource_uri(resource_file, root)
                if not uri or uri in seen_uris:
                    continue
                seen_uris.add(uri)

                try:
                    content = resource_file.read_text(encoding="utf-8")
                except Exception:
                    continue

                score = self._keyword_score(
                    query_lower=query_lower,
                    haystack=f"{uri} {content}".lower(),
                )
                if score <= 0:
                    continue

                results.append(
                    {
                        "uri": uri,
                        "content": content,
                        "score": score,
                        "metadata": {
                            "partition": bucket,
                            "resource_name": resource_file.name,
                            "mode": "workspace_fallback",
                        },
                    }
                )

        results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return results[:top_k]

    @property
    def _workspace_resource_root(self) -> Path | None:
        root = Path(self._workspace)
        if not root.exists():
            return None

        direct_root = root / "default" / "resources"
        if direct_root.exists():
            return direct_root

        configured_root = root / "resources"
        if configured_root.exists():
            return configured_root

        return None

    @staticmethod
    def _workspace_resource_uri(resource_file: Path, root: Path) -> str | None:
        try:
            relative_parent = resource_file.parent.relative_to(root)
        except ValueError:
            return None

        relative_text = relative_parent.as_posix().strip(".")
        if not relative_text:
            return "viking://resources/"
        return f"viking://resources/{relative_text}"

    @staticmethod
    def _keyword_score(query_lower: str, haystack: str) -> float:
        if not query_lower:
            return 0.5

        keywords = [item for item in query_lower.split() if item]
        if not keywords:
            return 0.5

        hits = sum(1 for keyword in keywords if keyword in haystack)
        return hits / len(keywords)

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
