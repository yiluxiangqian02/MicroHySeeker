"""Knowledge archive skill — experiment archival and retrieval.

Converted from the former KnowledgeManagerAgent.  This skill manages two
stores:

1. **Experiment archive** (in-memory + JSON file): all completed experiment
   results indexed by element ratios and metrics.
2. **Literature knowledge** (built-in + optional VikingKB): reference data
   and known performance ranges for catalysts.

No LLM calls — summaries are template-based.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.common.config import get_knowledge_config
from src.knowledge.schema import ExperimentRecord, KnowledgePartition, OperationRecord
from src.knowledge.viking_client import OpenVikingClient
from src.skills.base import BaseSkill, SkillResult

_logger = logging.getLogger("autohyseeker.skill.knowledge_archive")

# ── VikingKnowledgeBase optional integration ──────────────────────────────────
try:
    from src.rag import get_viking_kb as _get_viking_kb, VikingKnowledgeBase  # noqa: F401
    _VIKING_AVAILABLE = True
except ImportError:
    _VIKING_AVAILABLE = False
    _get_viking_kb = None  # type: ignore[assignment]

# ── Built-in literature reference data ────────────────────────────────────────

LITERATURE_KNOWLEDGE: list[dict[str, Any]] = [
    {
        "title": "Fe-Co-Ni 三元合金 HER 催化剂性能基线",
        "content": (
            "文献报道 Fe-Co-Ni 三元合金在碱性条件下 HER 过电位范围: 100-350 mV (10 mA/cm²)。"
            "最优配比通常 Ni 含量较高 (40-60%)，Co 次之 (20-35%)，Fe 最低 (10-25%)。"
            "Tafel 斜率: 50-120 mV/dec。"
        ),
        "category": "performance_baseline",
    },
    {
        "title": "HER 催化剂数据质量标准",
        "content": (
            "可靠的 HER 数据应满足: LSV 扫速 5 mV/s，iR 补偿后，"
            "至少 3 次重复。过电位偏差 < 10 mV 视为可重复。"
            "Tafel 拟合区间 R² > 0.99。"
        ),
        "category": "quality_standards",
    },
    {
        "title": "贝叶斯优化在催化剂配比中的应用",
        "content": (
            "TPE 采样在 10-20 轮实验后通常收敛。"
            "建议前 5 轮使用 Latin Hypercube 采样覆盖搜索空间。"
            "约束条件（配比之和=1）需在参数空间中显式处理。"
        ),
        "category": "optimization_strategy",
    },
]


class KnowledgeArchiveSkill(BaseSkill):
    """Archive experiments and retrieve knowledge.

    Uses VikingKnowledgeBase for semantic search when available,
    falling back to built-in keyword search otherwise.

    This is a stateful skill — it maintains an in-memory archive with
    optional JSON persistence.
    """

    name = "knowledge_archive"
    description = "Archive experiment results and retrieve historical knowledge."
    required_tools: list[str] = []

    def __init__(
        self,
        archive_path: str | None = None,
        viking_client: OpenVikingClient | None = None,
    ) -> None:
        self._archive: list[dict[str, Any]] = []
        self._archive_path = Path(archive_path) if archive_path else None
        if self._archive_path and self._archive_path.exists():
            self._load_archive()

        knowledge_config = get_knowledge_config()
        workspace_path = knowledge_config.get("workspace_path")
        self._viking_client = viking_client or OpenVikingClient(workspace_path=workspace_path)

        # VikingKnowledgeBase semantic search (optional)
        self._viking_kb: Any = None
        if _VIKING_AVAILABLE and _get_viking_kb is not None:
            try:
                self._viking_kb = _get_viking_kb()
                if self._viking_kb.is_available:
                    _logger.info("KnowledgeArchiveSkill: VikingKnowledgeBase enabled")
                else:
                    self._viking_kb = None
            except Exception as exc:
                _logger.debug("VikingKB unavailable: %s", exc)
                self._viking_kb = None

    # ── BaseSkill interface ───────────────────────────────────────────────────

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Dispatch to archive or retrieve based on ``action`` kwarg.

        Keyword Args:
            action: ``"archive"``, ``"archive_operation"``, or ``"retrieve"``
                (default: ``"archive"``).
            For archive: run_id, params, metrics, data_quality, round_num,
                interpretation, environment_snapshot, extra.
            For archive_operation: event_type, severity, message, component,
                run_id, action_taken, resolved, environment_snapshot, extra.
            For retrieve: query, search_type, top_k, elements.
        """
        action = kwargs.get("action", "archive")

        if action == "archive":
            result = await self.archive_experiment(
                run_id=kwargs.get("run_id", ""),
                params=kwargs.get("params", {}),
                metrics=kwargs.get("metrics", {}),
                data_quality=kwargs.get("data_quality"),
                round_num=kwargs.get("round_num"),
                interpretation=kwargs.get("interpretation", ""),
                environment_snapshot=kwargs.get("environment_snapshot"),
                extra=kwargs.get("extra"),
            )
            return SkillResult(
                success=True, data=result,
                message=f"Archived {kwargs.get('run_id', '')}", artifacts=[],
            )

        if action == "archive_operation":
            result = await self.archive_operation(
                event_type=kwargs.get("event_type", ""),
                severity=kwargs.get("severity", "info"),
                message=kwargs.get("message", ""),
                component=kwargs.get("component", "system"),
                run_id=kwargs.get("run_id"),
                action_taken=kwargs.get("action_taken", ""),
                resolved=kwargs.get("resolved", False),
                environment_snapshot=kwargs.get("environment_snapshot"),
                extra=kwargs.get("extra"),
            )
            return SkillResult(
                success=True,
                data=result,
                message=f"Archived operation {kwargs.get('event_type', '')}",
                artifacts=[],
            )

        if action == "retrieve":
            result = await self.retrieve(
                query=kwargs.get("query", ""),
                search_type=kwargs.get("search_type", "both"),
                top_k=kwargs.get("top_k", 5),
                elements=kwargs.get("elements"),
            )
            return SkillResult(
                success=True, data=result,
                message=f"Retrieved {len(result.get('results', []))} results",
                artifacts=[],
            )

        return SkillResult(
            success=False, data={},
            message=f"Unknown action: {action}", artifacts=[],
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def archive_experiment(
        self,
        run_id: str,
        params: dict[str, float],
        metrics: dict[str, float],
        data_quality: dict[str, Any] | None = None,
        round_num: int | None = None,
        interpretation: str = "",
        environment_snapshot: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Archive a completed experiment result."""
        record_model = ExperimentRecord(
            run_id=run_id,
            params=params,
            metrics=metrics,
            data_quality=data_quality or {},
            round_num=round_num,
            interpretation=interpretation,
            environment_snapshot=environment_snapshot or {},
        )
        record: dict[str, Any] = record_model.model_dump(mode="json")
        if extra:
            record.update(extra)

        self._archive.append(record)
        self._save_archive()

        knowledge_write = self._viking_client.write_json(
            partition=KnowledgePartition.EXPERIMENTS,
            payload=record,
            resource_name=f"{run_id}.json",
        )

        # Ingest into VikingKB when available
        if self._viking_kb is not None:
            try:
                import tempfile
                import os

                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                )
                json.dump(record, tmp, ensure_ascii=False, indent=2)
                tmp.close()
                self._viking_kb.ingest_experiment(tmp.name)
                os.unlink(tmp.name)
            except Exception as exc:
                _logger.debug("VikingKB ingest failed: %s", exc)

        _logger.info(
            "KnowledgeArchiveSkill: archived run_id=%s (total=%d)",
            run_id, len(self._archive),
        )
        return {
            "status": "archived",
            "run_id": run_id,
            "total_records": len(self._archive),
            "knowledge_write": knowledge_write,
            "environment_snapshot": record.get("environment_snapshot", {}),
        }

    async def archive_operation(
        self,
        event_type: str,
        severity: str,
        message: str,
        component: str = "system",
        run_id: str | None = None,
        action_taken: str = "",
        resolved: bool = False,
        environment_snapshot: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Archive an operational event into the operations partition."""
        record_model = OperationRecord(
            event_type=event_type,
            severity=severity,
            message=message,
            component=component,
            run_id=run_id,
            action_taken=action_taken,
            resolved=resolved,
            environment_snapshot=environment_snapshot or {},
        )
        record = record_model.model_dump(mode="json")
        if extra:
            record.update(extra)

        knowledge_write = self._viking_client.write_json(
            partition=KnowledgePartition.OPERATIONS,
            payload=record,
            resource_name=f"{event_type}_{record['record_id'][:8]}.json",
        )

        return {
            "status": "archived",
            "partition": KnowledgePartition.OPERATIONS.value,
            "event_type": event_type,
            "knowledge_write": knowledge_write,
            "environment_snapshot": record.get("environment_snapshot", {}),
        }

    async def retrieve(
        self,
        query: str,
        search_type: str = "both",
        top_k: int = 5,
        elements: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve relevant knowledge for a query."""
        results: list[dict[str, Any]] = []

        if search_type in ("experiment_history", "both"):
            results.extend(self._search_experiments(query, elements, top_k))

        if search_type in ("literature", "both"):
            results.extend(self._search_literature(query, top_k))

        results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
        results = results[:top_k]

        # Simple summary (no LLM)
        if not results:
            summary = "未找到相关记录。"
        else:
            titles = [r.get("title", "") for r in results[:3]]
            summary = f"找到 {len(results)} 条相关记录: {'; '.join(titles)}"

        return {
            "status": "retrieved",
            "results": results,
            "summary": summary,
            "total_archive_size": len(self._archive),
        }

    def get_experiment_history(self) -> list[dict[str, Any]]:
        """Return the full experiment archive."""
        return list(self._archive)

    def get_best_experiments(
        self,
        target_metric: str = "overpotential_mV",
        direction: str = "minimize",
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Return the top-k best experiments by a given metric."""
        valid = [
            r for r in self._archive
            if r.get("metrics", {}).get(target_metric) is not None
        ]
        reverse = direction == "maximize"
        valid.sort(key=lambda r: r["metrics"][target_metric], reverse=reverse)
        return valid[:top_k]

    # ── Private: Search ───────────────────────────────────────────────────────

    def _search_experiments(
        self, query: str, elements: list[str] | None, top_k: int
    ) -> list[dict[str, Any]]:
        """Simple keyword-based search over experiment archive."""
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for record in self._archive:
            relevance = 0.0
            content_parts: list[str] = []

            params = record.get("params", {})
            if elements:
                matching = sum(1 for e in elements if e in params)
                relevance += matching / len(elements) * 0.5

            record_str = json.dumps(record, ensure_ascii=False).lower()
            keywords = query_lower.split()
            keyword_hits = sum(1 for kw in keywords if kw in record_str)
            if keywords:
                relevance += keyword_hits / len(keywords) * 0.5

            content_parts.append(f"params: {params}")
            content_parts.append(f"metrics: {record.get('metrics', {})}")

            if relevance > 0:
                results.append({
                    "source": "experiment_history",
                    "title": f"实验 {record.get('run_id', 'unknown')}",
                    "content": "; ".join(content_parts),
                    "relevance": round(relevance, 2),
                    "run_id": record.get("run_id"),
                    "round": record.get("round"),
                })

        results.sort(key=lambda r: r["relevance"], reverse=True)
        return results[:top_k]

    def _search_literature(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Search literature knowledge base."""
        # VikingKB semantic search (preferred)
        if self._viking_kb is not None:
            try:
                viking_results = self._viking_kb.search_literature(query, top_k=top_k)
                if viking_results:
                    return [
                        {
                            "source": "literature",
                            "title": r.get("uri", "VikingKB Resource"),
                            "content": r.get("content", ""),
                            "relevance": round(float(r.get("score", 0.5)), 2),
                            "category": "semantic_search",
                        }
                        for r in viking_results
                    ]
            except Exception as exc:
                _logger.debug("VikingKB literature search failed: %s", exc)

        # Fallback: built-in keyword search
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for entry in LITERATURE_KNOWLEDGE:
            text = (entry["title"] + " " + entry["content"]).lower()
            keywords = query_lower.split()
            hits = sum(1 for kw in keywords if kw in text)
            relevance = hits / max(len(keywords), 1)

            if relevance > 0:
                results.append({
                    "source": "literature",
                    "title": entry["title"],
                    "content": entry["content"],
                    "relevance": round(min(relevance, 1.0), 2),
                    "category": entry.get("category"),
                })

        results.sort(key=lambda r: r["relevance"], reverse=True)
        return results[:top_k]

    # ── Private: Persistence ──────────────────────────────────────────────────

    def _save_archive(self) -> None:
        """Persist archive to JSON file if path configured."""
        if not self._archive_path:
            return
        try:
            self._archive_path.parent.mkdir(parents=True, exist_ok=True)
            self._archive_path.write_text(
                json.dumps(self._archive, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            _logger.warning("Archive save failed: %s", exc)

    def _load_archive(self) -> None:
        """Load archive from JSON file."""
        if not self._archive_path or not self._archive_path.exists():
            return
        try:
            text = self._archive_path.read_text(encoding="utf-8")
            self._archive = json.loads(text)
            _logger.info(
                "KnowledgeArchiveSkill: loaded %d records from %s",
                len(self._archive), self._archive_path,
            )
        except Exception as exc:
            _logger.warning("Archive load failed: %s", exc)
            self._archive = []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["archive", "archive_operation", "retrieve"],
                },
                "run_id": {"type": "string"},
                "params": {"type": "object"},
                "metrics": {"type": "object"},
                "event_type": {"type": "string"},
                "severity": {"type": "string"},
                "message": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["action"],
        }
