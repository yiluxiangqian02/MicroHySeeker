"""C1 — ContextualizeExperimentSkill: compare a run against historical data.

Loads the latest analysis result from *run_dir* and scans *history_dir* for
comparable previous runs (or uses *previous_results* supplied directly).
Optionally queries the **OpenViking** knowledge base for relevant literature
and experiment records, enriching the context with retrieval-augmented data.

Produces a structured context summary containing:

* ``comparison``       — per-metric delta vs. historical mean
* ``trend``            — direction of each metric over the history window
* ``anomalies``        — metrics that deviate more than *threshold_sigma* σ
* ``literature``       — relevant literature references from OpenViking KB
* ``knowledge_chunks`` — related knowledge snippets from OpenViking KB
* ``summary``          — human-readable contextualisation string
"""

from __future__ import annotations

import logging
import statistics
from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill, SkillResult
from src.tools.data_reader import load_run_echem_files, read_run_metadata
from src.tools.knowledge_retriever import retrieve_knowledge, retrieve_literature

logger = logging.getLogger(__name__)


def _collect_metric_history(
    history_dir: str,
    metric_key: str,
    max_runs: int = 20,
) -> list[float]:
    """Walk *history_dir* and collect a single numeric metric from each run."""
    h_path = Path(history_dir)
    if not h_path.is_dir():
        return []

    values: list[float] = []
    for run_path in sorted(h_path.iterdir()):
        if not run_path.is_dir():
            continue
        try:
            meta = read_run_metadata(str(run_path))
            val = meta.get(metric_key)
            if isinstance(val, (int, float)):
                values.append(float(val))
        except Exception:
            pass
        if len(values) >= max_runs:
            break
    return values


def _compute_context(
    current_metrics: dict[str, float],
    history: dict[str, list[float]],
    threshold_sigma: float,
) -> dict[str, Any]:
    """Build comparison / trend / anomaly dicts from current metrics + history."""
    comparison: dict[str, dict[str, Any]] = {}
    trend: dict[str, str] = {}
    anomalies: list[str] = []

    for key, current_val in current_metrics.items():
        hist_vals = history.get(key, [])
        entry: dict[str, Any] = {"current": current_val}

        if hist_vals:
            mean_h = statistics.mean(hist_vals)
            delta = current_val - mean_h
            entry["historical_mean"] = round(mean_h, 6)
            entry["delta"] = round(delta, 6)

            # Trend: compare last half vs first half of history
            mid = len(hist_vals) // 2
            if mid > 0:
                first_mean = statistics.mean(hist_vals[:mid])
                last_mean = statistics.mean(hist_vals[mid:])
                if last_mean > first_mean * 1.02:
                    trend[key] = "improving"
                elif last_mean < first_mean * 0.98:
                    trend[key] = "declining"
                else:
                    trend[key] = "stable"

            # Anomaly detection
            if len(hist_vals) >= 2:
                stdev = statistics.stdev(hist_vals)
                if stdev > 0 and abs(delta) > threshold_sigma * stdev:
                    anomalies.append(key)
                    entry["anomaly"] = True
        comparison[key] = entry

    return {"comparison": comparison, "trend": trend, "anomalies": anomalies}


def _build_kb_query(
    meta: dict[str, Any],
    current_metrics: dict[str, float],
    anomalies: list[str],
) -> str:
    """Construct an automatic KB query from run metadata and analysis results."""
    parts: list[str] = []
    exp_name = meta.get("exp_name", "")
    if exp_name:
        parts.append(exp_name)
    # Include anomalous metric names for targeted retrieval
    if anomalies:
        parts.append("anomaly " + " ".join(anomalies[:3]))
    # Include top metric names for broader context
    metric_names = list(current_metrics.keys())[:5]
    if metric_names:
        parts.append(" ".join(metric_names))
    return " ".join(parts) if parts else "electrochemistry experiment analysis"


class ContextualizeExperimentSkill(BaseSkill):
    """Contextualise a single experiment run against historical data and knowledge base.

    This skill is **LLM-free**.  It:

    1. Loads metadata / echem summary from *run_dir*.
    2. Reads historical metric values from *history_dir* (or uses
       *previous_results* provided directly).
    3. Computes per-metric delta, trend, and σ-based anomaly flags.
    4. Optionally retrieves relevant literature and knowledge chunks from
       the OpenViking knowledge base (when *kb_path* is provided).
    5. Returns a :class:`~src.skills.base.SkillResult` whose ``data`` is a
       structured context dict.

    Typical usage::

        skill = ContextualizeExperimentSkill()
        result = await skill.execute(
            run_dir="data/runs/run_042",
            history_dir="data/runs",
            kb_path="path/to/openviking/data",
        )
        context = result.data  # dict with comparison / trend / anomalies / literature
    """

    name = "contextualize_experiment"
    description = "将单次实验结果与历史数据对比，检索知识库文献，生成趋势/异常/对比上下文"
    required_tools = ["load_run_echem_files", "read_run_metadata", "retrieve_knowledge", "retrieve_literature"]

    async def execute(
        self,
        run_dir: str = "",
        history_dir: str = "",
        previous_results: list[dict[str, Any]] | None = None,
        metrics: list[str] | None = None,
        threshold_sigma: float = 2.0,
        max_history: int = 20,
        kb_path: str = "",
        kb_query: str = "",
        kb_limit: int = 5,
        kb_score_threshold: float = 0.3,
        **kwargs: Any,
    ) -> SkillResult:
        """Contextualise *run_dir* against historical data and knowledge base.

        Args:
            run_dir: Path to the current experiment run directory.
            history_dir: Parent directory containing historical run directories.
                         Used when *previous_results* is not provided.
            previous_results: Optional list of pre-computed metric dicts from
                              previous runs (overrides *history_dir* scanning).
            metrics: Metric keys to contextualise.  If ``None``, all numeric
                     keys found in run metadata are used.
            threshold_sigma: Number of standard deviations for anomaly detection
                             (default 2.0).
            max_history: Maximum number of historical runs to load (default 20).
            kb_path: Path to the OpenViking knowledge-base data directory.
                     When provided, the skill retrieves relevant literature and
                     knowledge chunks to enrich the context.
            kb_query: Custom query string for the knowledge base.  If empty,
                      an automatic query is built from run metadata.
            kb_limit: Maximum number of knowledge-base results (default 5).
            kb_score_threshold: Minimum similarity score for KB retrieval
                                (default 0.3).
            **kwargs: Ignored.

        Returns:
            :class:`~src.skills.base.SkillResult` where ``data`` is::

                {
                    "run_dir": str,
                    "comparison": {metric: {current, historical_mean, delta}},
                    "trend":      {metric: "improving" | "declining" | "stable"},
                    "anomalies":  [metric, ...],
                    "literature": [LiteratureRef, ...],
                    "knowledge_chunks": [KnowledgeChunk, ...],
                    "n_history":  int,
                    "summary":    str,
                }
        """
        if not run_dir:
            return SkillResult(
                success=False,
                data={},
                message="run_dir parameter is required",
                artifacts=[],
            )

        run_path = Path(run_dir)
        if not run_path.exists():
            return SkillResult(
                success=False,
                data={},
                message=f"Run directory not found: {run_dir}",
                artifacts=[],
            )

        # ── Step 1: Load current run metrics ─────────────────────────────────
        try:
            meta = read_run_metadata(run_dir)
        except Exception:
            meta = {"run_dir": run_dir}

        # Supplement meta with echem summary statistics
        try:
            echem_files = load_run_echem_files(run_dir)
            for ef in echem_files:
                df = ef.data
                for col in df.select_dtypes(include="number").columns:
                    key = f"{ef.technique}_{col}_mean"
                    try:
                        meta[key] = float(df[col].mean())
                    except Exception:
                        pass
        except Exception:
            pass

        # Filter to requested metrics or all numeric keys
        current_metrics: dict[str, float] = {}
        for k, v in meta.items():
            if metrics and k not in metrics:
                continue
            if isinstance(v, (int, float)):
                current_metrics[k] = float(v)

        if not current_metrics:
            # Even without numeric metrics, attempt KB retrieval if configured
            lit_refs: list[dict[str, Any]] = []
            kb_chunks: list[dict[str, Any]] = []
            if kb_path:
                auto_query = kb_query or meta.get("exp_name", "") or "experiment context"
                lit_refs = [r.model_dump() for r in retrieve_literature(auto_query, kb_path, limit=kb_limit, score_threshold=kb_score_threshold)]
                kb_chunks = [c.model_dump() for c in retrieve_knowledge(auto_query, kb_path, limit=kb_limit, score_threshold=kb_score_threshold)]
            return SkillResult(
                success=True,
                data={
                    "run_dir": run_dir,
                    "comparison": {},
                    "trend": {},
                    "anomalies": [],
                    "literature": lit_refs,
                    "knowledge_chunks": kb_chunks,
                    "n_history": 0,
                    "summary": "No numeric metrics found in run metadata.",
                },
                message="No numeric metrics available for contextualisation",
                artifacts=[],
            )

        # ── Step 2: Build historical metric lists ─────────────────────────────
        history: dict[str, list[float]] = {}
        n_history = 0

        if previous_results:
            # Use supplied dicts
            n_history = len(previous_results)
            for key in current_metrics:
                history[key] = [
                    float(r[key]) for r in previous_results
                    if key in r and isinstance(r[key], (int, float))
                ]
        elif history_dir:
            for key in current_metrics:
                hist_vals = _collect_metric_history(history_dir, key, max_runs=max_history)
                if hist_vals:
                    history[key] = hist_vals
                    n_history = max(n_history, len(hist_vals))

        # ── Step 3: Compute context ───────────────────────────────────────────
        ctx = _compute_context(current_metrics, history, threshold_sigma)

        # ── Step 3b: Knowledge base retrieval ─────────────────────────────────
        lit_refs_dicts: list[dict[str, Any]] = []
        kb_chunks_dicts: list[dict[str, Any]] = []
        if kb_path:
            auto_query = kb_query or _build_kb_query(meta, current_metrics, ctx["anomalies"])
            lit_refs_dicts = [
                r.model_dump() for r in retrieve_literature(
                    auto_query, kb_path, limit=kb_limit, score_threshold=kb_score_threshold,
                )
            ]
            kb_chunks_dicts = [
                c.model_dump() for c in retrieve_knowledge(
                    auto_query, kb_path, limit=kb_limit, score_threshold=kb_score_threshold,
                )
            ]

        # ── Step 4: Build summary string ──────────────────────────────────────
        n_anomalies = len(ctx["anomalies"])
        n_trending = sum(1 for t in ctx["trend"].values() if t != "stable")
        summary_parts = [
            f"Contextualised {len(current_metrics)} metric(s) "
            f"against {n_history} historical run(s).",
        ]
        if n_anomalies:
            summary_parts.append(
                f"{n_anomalies} anomalous metric(s): {', '.join(ctx['anomalies'][:5])}."
            )
        if n_trending:
            improving = [k for k, v in ctx["trend"].items() if v == "improving"]
            declining = [k for k, v in ctx["trend"].items() if v == "declining"]
            if improving:
                summary_parts.append(f"Improving: {', '.join(improving[:3])}.")
            if declining:
                summary_parts.append(f"Declining: {', '.join(declining[:3])}.")
        if lit_refs_dicts:
            summary_parts.append(f"Found {len(lit_refs_dicts)} relevant literature reference(s).")
        if kb_chunks_dicts:
            summary_parts.append(f"Retrieved {len(kb_chunks_dicts)} knowledge chunk(s) from KB.")

        result_data: dict[str, Any] = {
            "run_dir": run_dir,
            "comparison": ctx["comparison"],
            "trend": ctx["trend"],
            "anomalies": ctx["anomalies"],
            "literature": lit_refs_dicts,
            "knowledge_chunks": kb_chunks_dicts,
            "n_history": n_history,
            "summary": " ".join(summary_parts),
        }

        return SkillResult(
            success=True,
            data=result_data,
            message=result_data["summary"],
            artifacts=[],
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the current experiment run directory",
                },
                "history_dir": {
                    "type": "string",
                    "description": "Parent directory containing historical run directories",
                },
                "previous_results": {
                    "type": "array",
                    "description": "Pre-computed metric dicts from previous runs",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific metric keys to contextualise (default: all numeric)",
                },
                "threshold_sigma": {
                    "type": "number",
                    "description": "σ threshold for anomaly detection (default 2.0)",
                },
                "max_history": {
                    "type": "integer",
                    "description": "Maximum historical runs to load (default 20)",
                },
                "kb_path": {
                    "type": "string",
                    "description": "Path to OpenViking knowledge-base data directory",
                },
                "kb_query": {
                    "type": "string",
                    "description": "Custom knowledge-base query (auto-generated if empty)",
                },
                "kb_limit": {
                    "type": "integer",
                    "description": "Maximum KB results to retrieve (default 5)",
                },
                "kb_score_threshold": {
                    "type": "number",
                    "description": "Minimum similarity score for KB retrieval (default 0.3)",
                },
            },
            "required": ["run_dir"],
        }


# Convenience singleton
contextualize_experiment_skill = ContextualizeExperimentSkill()
