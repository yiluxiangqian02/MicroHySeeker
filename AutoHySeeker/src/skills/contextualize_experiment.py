"""C1 — ContextualizeExperimentSkill: analyse current run against history.

Reads the current run's ``run_summary.json``, compares numeric metrics against
historical runs, detects anomalies (z-score > *threshold_sigma*) and trends
(increasing / declining / stable), and optionally retrieves related literature
and knowledge chunks from the OpenViking knowledge base.

Result ``data`` contains:
* ``run_dir``           — echo of input path
* ``comparison``        — per-metric comparison dict
* ``trend``             — per-metric trend label
* ``anomalies``         — list of anomalous metric names
* ``literature``        — :class:`LiteratureRef` list from KB
* ``knowledge_chunks``  — raw chunks from KB
* ``n_history``         — number of historical data-points used
* ``summary``           — human-readable summary string
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill, SkillResult

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_run_metadata(run_dir: str) -> dict[str, Any] | None:
    """Load ``run_summary.json`` from *run_dir*, returning ``None`` on failure."""
    p = Path(run_dir) / "run_summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_numeric_metrics(
    meta: dict[str, Any],
    metric_keys: list[str] | None = None,
) -> dict[str, float]:
    """Return numeric (int/float) fields from *meta*, optionally filtered."""
    nums: dict[str, float] = {}
    for k, v in meta.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if metric_keys is None or k in metric_keys:
                nums[k] = float(v)
    return nums


def _compare_metrics(
    current: dict[str, float],
    history: list[dict[str, float]],
    threshold_sigma: float,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Compare *current* values to *history*.

    Returns ``(comparison, trend, anomalies)`` where comparison maps metric name
    to ``{current, historical_mean, historical_std, delta, z_score}`` etc.
    """
    comparison: dict[str, Any] = {}
    trend: dict[str, str] = {}
    anomalies: list[str] = []

    for metric, cur_val in current.items():
        hist_vals = [h[metric] for h in history if metric in h and isinstance(h[metric], (int, float))]
        if not hist_vals:
            comparison[metric] = {"current": cur_val}
            continue

        mean = sum(hist_vals) / len(hist_vals)
        variance = sum((v - mean) ** 2 for v in hist_vals) / len(hist_vals)
        std = math.sqrt(variance) if variance > 0 else 0.0
        delta = cur_val - mean
        z_score = abs(delta / std) if std > 0 else 0.0

        comparison[metric] = {
            "current": cur_val,
            "historical_mean": mean,
            "historical_std": std,
            "delta": delta,
            "z_score": z_score,
        }

        # Anomaly detection
        if z_score > threshold_sigma:
            anomalies.append(metric)

        # Trend detection (simple: compare last half vs first half)
        if len(hist_vals) >= 2:
            mid = len(hist_vals) // 2
            first_half_mean = sum(hist_vals[:mid]) / mid if mid else mean
            second_half_mean = sum(hist_vals[mid:]) / (len(hist_vals) - mid)
            if second_half_mean > first_half_mean * 1.05:
                trend[metric] = "increasing"
            elif second_half_mean < first_half_mean * 0.95:
                trend[metric] = "declining"
            else:
                trend[metric] = "stable"
        else:
            trend[metric] = "stable"

    return comparison, trend, anomalies


def _build_kb_query(
    metadata: dict[str, Any],
    current_metrics: dict[str, float],
    anomalies: list[str],
) -> str:
    """Build a KB search query from run metadata, metrics and anomalies."""
    parts: list[str] = []
    for key in ("exp_name", "experiment_name", "catalyst", "electrolyte"):
        val = metadata.get(key)
        if val:
            parts.append(str(val))
    for m in anomalies:
        parts.append(m)
    if not parts:
        parts.extend(str(k) for k in list(current_metrics)[:3])
    return " ".join(parts)


class ContextualizeExperimentSkill(BaseSkill):
    """C1 — Compare current run metrics to history and retrieve KB context.

    Workflow:

    1. Load ``run_summary.json`` from *run_dir*.
    2. Extract numeric metrics and compare to *previous_results* or historical
       runs found in *history_dir*.
    3. Detect anomalies (z-score > *threshold_sigma*) and trends.
    4. Optionally retrieve literature & knowledge chunks from OpenViking KB.
    5. Return :class:`~src.skills.base.SkillResult` with full context.
    """

    name = "contextualize_experiment"
    description = "分析当前实验运行，与历史数据对比，检测异常与趋势，检索相关文献"
    required_tools: list[str] = []

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
        """Contextualise the current experiment run.

        Args:
            run_dir: Path to the current run directory (must contain
                ``run_summary.json``).
            history_dir: Parent directory holding previous run subdirectories.
            previous_results: Pre-computed metric dicts from prior runs. If
                provided, *history_dir* is not scanned.
            metrics: Specific metric keys to analyse.  ``None`` = all numeric.
            threshold_sigma: Z-score threshold for anomaly flagging.
            max_history: Max historical runs to load from *history_dir*.
            kb_path: Path to the OpenViking knowledge base directory.
            kb_query: Override KB search query (auto-generated if empty).
            kb_limit: Max KB results to retrieve.
            kb_score_threshold: Minimum similarity score for KB results.
        """
        # ── Validate inputs ───────────────────────────────────────────────────
        if not run_dir:
            return SkillResult(
                success=False, data={},
                message="run_dir is required", artifacts=[],
            )

        run_path = Path(run_dir)
        if not run_path.exists():
            return SkillResult(
                success=False, data={},
                message=f"run_dir does not exist: {run_dir}", artifacts=[],
            )

        # ── Load current run metadata ─────────────────────────────────────────
        metadata = _load_run_metadata(run_dir) or {}
        current_metrics = _extract_numeric_metrics(metadata, metrics)

        # ── Gather history ────────────────────────────────────────────────────
        history: list[dict[str, float]] = []
        if previous_results:
            for pr in previous_results[:max_history]:
                history.append(
                    {k: float(v) for k, v in pr.items()
                     if isinstance(v, (int, float)) and not isinstance(v, bool)}
                )
        elif history_dir:
            hdir = Path(history_dir)
            if hdir.is_dir():
                subdirs = sorted(hdir.iterdir())[:max_history]
                for sd in subdirs:
                    if sd.is_dir() and str(sd) != run_dir:
                        hm = _load_run_metadata(str(sd))
                        if hm:
                            history.append(_extract_numeric_metrics(hm, metrics))

        # ── Compare & detect ──────────────────────────────────────────────────
        comparison, trend, anomalies = _compare_metrics(
            current_metrics, history, threshold_sigma,
        )

        # ── KB retrieval ──────────────────────────────────────────────────────
        literature: list[Any] = []
        knowledge_chunks: list[Any] = []
        if kb_path:
            effective_query = kb_query or _build_kb_query(metadata, current_metrics, anomalies)
            try:
                from src.tools.knowledge_retriever import (  # noqa: PLC0415
                    retrieve_knowledge,
                    retrieve_literature,
                )
                knowledge_chunks = retrieve_knowledge(
                    effective_query, kb_path, limit=kb_limit,
                    score_threshold=kb_score_threshold,
                )
                literature = retrieve_literature(
                    effective_query, kb_path, limit=kb_limit,
                    score_threshold=kb_score_threshold,
                )
            except Exception as exc:
                logger.warning("KB retrieval failed: %s", exc)

        # ── Build summary ─────────────────────────────────────────────────────
        parts: list[str] = []
        parts.append(f"Analysed run at {run_dir}.")
        if current_metrics:
            parts.append(f"{len(current_metrics)} metric(s) extracted.")
        if history:
            parts.append(f"Compared against {len(history)} historical run(s).")
        if anomalies:
            parts.append(f"Anomalies: {', '.join(anomalies)}.")
        summary = " ".join(parts)

        result_data: dict[str, Any] = {
            "run_dir": run_dir,
            "comparison": comparison,
            "trend": trend,
            "anomalies": anomalies,
            "literature": literature,
            "knowledge_chunks": knowledge_chunks,
            "n_history": len(history),
            "summary": summary,
        }

        return SkillResult(
            success=True,
            data=result_data,
            message=summary,
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
                    "description": "Parent directory with historical run sub-directories",
                },
                "previous_results": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Pre-computed metric dicts from previous runs",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific metric keys to analyse (default: all numeric)",
                },
                "threshold_sigma": {
                    "type": "number",
                    "description": "Z-score threshold for anomaly detection (default 2.0)",
                    "default": 2.0,
                },
                "max_history": {
                    "type": "integer",
                    "description": "Max historical runs to load (default 20)",
                    "default": 20,
                },
                "kb_path": {
                    "type": "string",
                    "description": "Path to the OpenViking knowledge base directory",
                },
                "kb_query": {
                    "type": "string",
                    "description": "Override KB search query (auto-generated if empty)",
                },
                "kb_limit": {
                    "type": "integer",
                    "description": "Max KB results to retrieve (default 5)",
                    "default": 5,
                },
                "kb_score_threshold": {
                    "type": "number",
                    "description": "Min similarity score for KB results (default 0.3)",
                    "default": 0.3,
                },
            },
            "required": ["run_dir"],
        }


# Convenience singleton
contextualize_experiment_skill = ContextualizeExperimentSkill()
