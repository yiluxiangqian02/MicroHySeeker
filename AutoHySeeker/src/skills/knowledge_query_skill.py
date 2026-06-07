"""Shared read-only knowledge query skill backed by OpenViking partitions."""

from __future__ import annotations

import json
from typing import Any

from src.common.config import get_knowledge_config
from src.knowledge.schema import KnowledgePartition
from src.knowledge.viking_client import OpenVikingClient, get_shared_openviking_client
from src.skills.base import BaseSkill, SkillResult


class KnowledgeQuerySkill(BaseSkill):
    """Read-only access layer for literature, experiments, and operations."""

    name = "knowledge_query"
    description = "Query the shared knowledge base across partitions."
    required_tools: list[str] = []

    def __init__(self, client: OpenVikingClient | None = None) -> None:
        config = get_knowledge_config()
        workspace_path = config.get("workspace_path")
        self._default_top_k = int(config.get("default_top_k", 5))
        self._read_level = str(config.get("read_level", "overview"))
        self._client = client or get_shared_openviking_client(workspace_path=workspace_path)

    async def execute(self, **kwargs: Any) -> SkillResult:
        action = kwargs.get("action", "search")

        if action == "search":
            result = await self.search(
                query=kwargs.get("query", ""),
                partitions=kwargs.get("partitions"),
                top_k=int(kwargs.get("top_k", self._default_top_k)),
            )
        elif action == "get_similar_experiments":
            result = await self.get_similar_experiments(
                params=kwargs.get("params", {}),
                threshold=float(kwargs.get("threshold", 0.8)),
                top_k=int(kwargs.get("top_k", self._default_top_k)),
            )
        elif action == "get_fault_history":
            result = await self.get_fault_history(
                fault_type=kwargs.get("fault_type", ""),
                top_k=int(kwargs.get("top_k", self._default_top_k)),
            )
        elif action == "get_literature_insights":
            result = await self.get_literature_insights(
                topic=kwargs.get("topic", ""),
                top_k=int(kwargs.get("top_k", self._default_top_k)),
            )
        else:
            return SkillResult(
                success=False,
                data={},
                message=f"Unknown action: {action}",
                artifacts=[],
            )

        return SkillResult(
            success=True,
            data=result,
            message=f"Knowledge query action completed: {action}",
            artifacts=[],
        )

    async def search(
        self,
        query: str,
        partitions: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Semantic/keyword search across one or more knowledge partitions."""
        target_partitions = _normalise_partitions(partitions)
        if not target_partitions:
            target_partitions = None

        if target_partitions is None:
            hits = self._client.search(query=query, partition=None, top_k=top_k)
            return [self._normalise_hit(item) for item in hits]

        merged: list[dict[str, Any]] = []
        for partition in target_partitions:
            hits = self._client.search(query=query, partition=partition, top_k=top_k)
            merged.extend(self._normalise_hit(item) for item in hits)

        merged.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return merged[:top_k]

    async def get_similar_experiments(
        self,
        params: dict[str, float],
        threshold: float = 0.8,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return experiment records whose composition is similar to the target."""
        candidates = self._client.search(
            query="",
            partition=KnowledgePartition.EXPERIMENTS,
            top_k=max(top_k * 5, 50),
        )

        results: list[dict[str, Any]] = []
        for item in candidates:
            normalised = self._normalise_hit(item)
            payload = normalised.get("payload", {})
            experiment_params = payload.get("params", {})
            if not isinstance(experiment_params, dict) or not experiment_params:
                continue

            similarity = _composition_similarity(params, experiment_params)
            if similarity < threshold:
                continue

            results.append(
                {
                    "run_id": payload.get("run_id"),
                    "project_id": payload.get("project_id"),
                    "round_num": payload.get("round_num"),
                    "params": experiment_params,
                    "metrics": payload.get("metrics", {}),
                    "similarity": round(similarity, 3),
                    "uri": normalised.get("uri", ""),
                    "partition": normalised.get("partition", "experiments"),
                }
            )

        results.sort(key=lambda item: float(item["similarity"]), reverse=True)
        return results[:top_k]

    async def get_fault_history(
        self,
        fault_type: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return historical operation records matching a fault type."""
        hits = self._client.search(
            query=fault_type,
            partition=KnowledgePartition.OPERATIONS,
            top_k=max(top_k * 2, 10),
        )

        results: list[dict[str, Any]] = []
        fault_lower = fault_type.lower().strip()
        for item in hits:
            normalised = self._normalise_hit(item)
            payload = normalised.get("payload", {})
            haystack = json.dumps(payload, ensure_ascii=False).lower()
            if fault_lower and fault_lower not in haystack:
                continue

            results.append(
                {
                    "event_type": payload.get("event_type", ""),
                    "severity": payload.get("severity", ""),
                    "message": payload.get("message", ""),
                    "action_taken": payload.get("action_taken", ""),
                    "resolved": payload.get("resolved"),
                    "run_id": payload.get("run_id"),
                    "uri": normalised.get("uri", ""),
                    "partition": normalised.get("partition", "operations"),
                    "score": normalised.get("score", 0.0),
                }
            )

        results.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return results[:top_k]

    async def get_literature_insights(
        self,
        topic: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return literature findings relevant to a topic."""
        hits = self._client.search(
            query=topic,
            partition=KnowledgePartition.LITERATURE,
            top_k=top_k,
        )

        results: list[dict[str, Any]] = []
        for item in hits:
            normalised = self._normalise_hit(item)
            payload = normalised.get("payload", {})
            results.append(
                {
                    "title": payload.get("title", ""),
                    "authors": payload.get("authors", []),
                    "year": payload.get("year"),
                    "doi": payload.get("doi"),
                    "summary": payload.get("abstract") or payload.get("content", ""),
                    "keywords": payload.get("keywords", []),
                    "uri": normalised.get("uri", ""),
                    "partition": normalised.get("partition", "literature"),
                    "score": normalised.get("score", 0.0),
                }
            )

        return results[:top_k]

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "search",
                        "get_similar_experiments",
                        "get_fault_history",
                        "get_literature_insights",
                    ],
                },
                "query": {"type": "string"},
                "partitions": {"type": "array"},
                "params": {"type": "object"},
                "fault_type": {"type": "string"},
                "topic": {"type": "string"},
                "threshold": {"type": "number"},
                "top_k": {"type": "integer"},
            },
            "required": ["action"],
        }

    def _normalise_hit(self, item: dict[str, Any]) -> dict[str, Any]:
        uri = str(item.get("uri", ""))
        payload = _parse_payload(item.get("content", ""))
        return {
            "uri": uri,
            "partition": _partition_from_uri(uri),
            "content": item.get("content", ""),
            "score": float(item.get("score", 0.0)),
            "metadata": item.get("metadata", {}),
            "payload": payload,
        }


def _normalise_partitions(partitions: list[str] | None) -> list[KnowledgePartition]:
    if not partitions:
        return []
    normalised: list[KnowledgePartition] = []
    for item in partitions:
        try:
            normalised.append(KnowledgePartition(item))
        except ValueError:
            continue
    return normalised


def _parse_payload(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str) or not content.strip():
        return {}
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {"content": content}


def _partition_from_uri(uri: str) -> str:
    for partition in KnowledgePartition:
        marker = f"/{partition.value}/"
        if marker in uri:
            return partition.value
    return "unknown"


def _composition_similarity(query: dict[str, float], candidate: dict[str, Any]) -> float:
    shared_keys = set(query) | set(candidate)
    if not shared_keys:
        return 0.0

    total_difference = 0.0
    for key in shared_keys:
        query_value = _to_float(query.get(key)) or 0.0
        candidate_value = _to_float(candidate.get(key)) or 0.0
        total_difference += abs(query_value - candidate_value)

    return max(0.0, 1.0 - total_difference / len(shared_keys))


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
