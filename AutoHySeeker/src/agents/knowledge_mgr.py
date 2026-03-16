"""Knowledge manager agent — experiment archival and retrieval.

The knowledge manager maintains two stores:

1. **Experiment archive** (in-memory → future ChromaDB): all completed
   experiment results indexed by element ratios and metrics.
2. **Literature knowledge** (future ChromaDB): reference papers and known
   performance ranges for catalysts.

For now, the archive is kept in a simple JSON file for persistence and an
in-memory list for fast queries.  ChromaDB integration will replace this
when the embedding infrastructure is ready.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent

_logger = logging.getLogger("autohyseeker.knowledge_mgr")

KNOWLEDGE_SYSTEM_PROMPT = """\
你是知识管理 Agent（Knowledge Manager），负责实验知识的归档、检索和总结。

## 职责
1. 归档每轮实验结果（参数、指标、质量评估）
2. 检索历史实验中与当前查询相关的记录
3. 提供文献参考范围（已知 HER 催化剂性能基线）
4. 生成知识总结供其他 Agent 参考

## 查询类型
- experiment_history: 检索历史实验记录
- literature: 检索文献参考（当前为内置知识库）
- both: 同时检索两者

## 输出格式（严格 JSON）
```json
{
  "status": "retrieved",
  "results": [
    {
      "source": "experiment_history|literature",
      "title": "描述",
      "content": "详细内容",
      "relevance": 0.92
    }
  ],
  "summary": "综合总结"
}
```
"""

# ── Built-in literature reference data ────────────────────────────────────────

_LITERATURE_KNOWLEDGE: list[dict[str, Any]] = [
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


class KnowledgeManagerAgent(BaseAgent):
    """Knowledge manager — archives experiments and retrieves knowledge."""

    def __init__(self, archive_path: str | None = None) -> None:
        super().__init__(
            name="knowledge_mgr",
            system_prompt=KNOWLEDGE_SYSTEM_PROMPT,
        )
        self._archive: list[dict[str, Any]] = []
        self._archive_path = Path(archive_path) if archive_path else None
        if self._archive_path and self._archive_path.exists():
            self._load_archive()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def archive_experiment(
        self,
        run_id: str,
        params: dict[str, float],
        metrics: dict[str, float],
        data_quality: dict[str, Any] | None = None,
        round_num: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Archive a completed experiment result.

        Returns confirmation with the total archive size.
        """
        record: dict[str, Any] = {
            "run_id": run_id,
            "params": params,
            "metrics": metrics,
            "data_quality": data_quality or {},
            "round": round_num,
        }
        if extra:
            record.update(extra)

        self._archive.append(record)
        self._save_archive()

        _logger.info(
            "KnowledgeManagerAgent: archived run_id=%s (total=%d)",
            run_id, len(self._archive),
        )
        return {
            "status": "archived",
            "run_id": run_id,
            "total_records": len(self._archive),
        }

    async def retrieve(
        self,
        query: str,
        search_type: str = "both",
        top_k: int = 5,
        elements: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve relevant knowledge for a query.

        Args:
            query: Natural language query.
            search_type: ``"experiment_history"``, ``"literature"``, or ``"both"``.
            top_k: Maximum results to return.
            elements: Optional element filter for experiment history.

        Returns:
            Dict with ``results`` list and ``summary``.
        """
        results: list[dict[str, Any]] = []

        if search_type in ("experiment_history", "both"):
            exp_results = self._search_experiments(query, elements, top_k)
            results.extend(exp_results)

        if search_type in ("literature", "both"):
            lit_results = self._search_literature(query, top_k)
            results.extend(lit_results)

        # Sort by relevance, take top_k
        results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
        results = results[:top_k]

        # Generate summary
        summary = await self._summarize(query, results)

        return {
            "status": "retrieved",
            "results": results,
            "summary": summary,
            "total_archive_size": len(self._archive),
        }

    def get_experiment_history(self) -> list[dict[str, Any]]:
        """Return the full experiment archive (for Orchestrator/Designer)."""
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
        valid.sort(
            key=lambda r: r["metrics"][target_metric],
            reverse=reverse,
        )
        return valid[:top_k]

    # ── Private: Search ───────────────────────────────────────────────────────

    def _search_experiments(
        self,
        query: str,
        elements: list[str] | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Simple keyword-based search over experiment archive."""
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for record in self._archive:
            relevance = 0.0
            content_parts: list[str] = []

            # Check element match
            params = record.get("params", {})
            if elements:
                matching = sum(1 for e in elements if e in params)
                relevance += matching / len(elements) * 0.5

            # Keyword matching in params/metrics
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

    def _search_literature(
        self,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Search built-in literature knowledge base."""
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for entry in _LITERATURE_KNOWLEDGE:
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

    # ── Private: Summary ──────────────────────────────────────────────────────

    async def _summarize(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> str:
        """Generate a summary of search results using LLM."""
        if not results:
            return "未找到相关记录。"

        try:
            task = {
                "type": "summarize_knowledge",
                "query": query,
                "result_count": len(results),
            }
            context = {"results": results[:5]}
            result = await self.invoke(task=task, context=context)
            return result.get("content", "")[:500]
        except Exception as exc:
            _logger.debug("LLM summary failed: %s", exc)
            # Fallback: simple concatenation
            summaries = [r.get("title", "") for r in results[:3]]
            return f"找到 {len(results)} 条相关记录: {'; '.join(summaries)}"

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
                "KnowledgeManagerAgent: loaded %d records from %s",
                len(self._archive), self._archive_path,
            )
        except Exception as exc:
            _logger.warning("Archive load failed: %s", exc)
            self._archive = []


