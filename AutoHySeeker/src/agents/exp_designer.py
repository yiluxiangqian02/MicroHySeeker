"""Experiment designer agent — generates next experiment parameters.

The designer proposes element ratios (Fe:Co:Ni) for the next experiment based
on the optimization history.  Three strategies are used depending on the
amount of available data:

1. **Initial sampling** (history == 0): evenly-spaced grid covering the
   search space.
2. **LLM-guided** (history < 5): ask the LLM to reason about trends and
   suggest the next point.
3. **Bayesian optimization** (history ≥ 5): use Optuna TPE sampler to propose
   the most promising point.

The output always includes ``step_overrides`` formatted for the Executor.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.agents.base import BaseAgent
from src.common.config import DESIGNER_CONFIG
from src.ml.performance_predictor import PerformancePredictor
from src.skills.knowledge_query_skill import KnowledgeQuerySkill

_logger = logging.getLogger("autohyseeker.exp_designer")

DESIGNER_SYSTEM_PROMPT = """\
你是实验设计 Agent（Experiment Designer），负责为 HER 电催化剂优化生成下一组实验参数。

## 工作流程
1. 分析已有实验历史（元素配比 → 过电位/电流密度等指标）
2. 根据优化方向（minimize/maximize）判断趋势
3. 在搜索空间约束内提出新配比
4. 输出标准化的 step_overrides 格式

## 搜索空间
- 元素: Fe, Co, Ni（可扩展）
- 约束: 所有配比之和 = 1.0，每个元素最小 0.05
- 参数格式: {"Fe": 0.6, "Co": 0.25, "Ni": 0.15}

## 策略选择
- 0 轮历史 → 初始采样（均匀网格）
- <5 轮历史 → 基于趋势推理
- ≥5 轮历史 → 贝叶斯优化辅助

## 输出格式（严格 JSON）
```json
{
  "params": {"Fe": 0.6, "Co": 0.25, "Ni": 0.15},
  "step_overrides": {
    "0": {
      "prep_sol_params": {
        "target_concentrations": {"Fe": 0.6, "Co": 0.25, "Ni": 0.15},
        "total_volume_ul": 1000
      }
    }
  },
  "strategy": "initial_sampling|llm_guided|bayesian",
  "reasoning": "选择原因",
  "expected_improvement": 10.0
}
```

## 安全规则
- 配比之和必须等于 1.0
- 每个元素最小 0.05，最大 0.9
- 不要重复已测试过的配比（相似度 < 0.02 视为重复）
"""

# ── Default search space ──────────────────────────────────────────────────────

DEFAULT_SEARCH_SPACE: dict[str, dict[str, float]] = {
    "Fe": {"min": 0.05, "max": 0.9},
    "Co": {"min": 0.05, "max": 0.9},
    "Ni": {"min": 0.05, "max": 0.9},
}

DEFAULT_TOTAL_VOLUME_UL = 1000


class ExperimentDesignerAgent(BaseAgent):
    """Experiment designer — generates next experiment parameters."""

    def __init__(self) -> None:
        super().__init__(
            name="exp_designer",
            system_prompt=DESIGNER_SYSTEM_PROMPT,
        )
        self._knowledge_query_skill = KnowledgeQuerySkill()
        self._designer_config = dict(DESIGNER_CONFIG)
        self._constraints_config = self._designer_config.get("constraints", {})

    # ── Public API ─────────────────────────────────────────────────────────────

    async def design_experiment(
        self,
        history: list[dict[str, Any]],
        search_space: dict[str, Any] | None = None,
        target_metric: str = "overpotential_mV",
        optimization_direction: str = "minimize",
        constraints: dict[str, Any] | None = None,
        total_volume_ul: float = DEFAULT_TOTAL_VOLUME_UL,
    ) -> dict[str, Any]:
        """Design the next experiment.

        Args:
            history: List of previous experiment results, each with
                ``params`` and ``metrics`` dicts.
            search_space: Per-element min/max bounds.
            target_metric: Name of the metric to optimize.
            optimization_direction: ``"minimize"`` or ``"maximize"``.
            constraints: Extra constraints (e.g. ``{"sum_equals": 1.0}``).
            total_volume_ul: Total solution volume in µL.

        Returns:
            Dict with ``params``, ``step_overrides``, ``strategy``, etc.
        """
        space = search_space or DEFAULT_SEARCH_SPACE
        elements = sorted(space.keys())
        merged_constraints = dict(constraints or {})
        for key, value in self._constraints_config.items():
            merged_constraints.setdefault(key, value)
        if "min_component" not in merged_constraints and "min_fraction" in merged_constraints:
            merged_constraints["min_component"] = merged_constraints["min_fraction"]

        n_history = len(history)
        _logger.info(
            "DesignerAgent: design_experiment history=%d metric=%s dir=%s",
            n_history, target_metric, optimization_direction,
        )

        # ── Strategy selection ────────────────────────────────────────────────
        if n_history == 0:
            params, reasoning, confidence = await self._literature_guided_design(
                history=history,
                elements=elements,
                space=space,
                target_metric=target_metric,
                optimization_direction=optimization_direction,
            )
            strategy = "literature_guided"
            expected_improvement = 0.0
        elif n_history < int(self._designer_config.get("ml_switch_threshold", 5)):
            params, reasoning, confidence = await self._llm_guided_design(
                history, elements, space, target_metric, optimization_direction,
            )
            strategy = "llm_guided"
            expected_improvement = 0.0
        else:
            params, reasoning, confidence, strategy = await self._ml_hybrid_design(
                history=history,
                elements=elements,
                space=space,
                target_metric=target_metric,
                optimization_direction=optimization_direction,
            )
            expected_improvement = self._estimate_improvement(
                params, history, target_metric, optimization_direction,
            )

        # ── Apply constraints ─────────────────────────────────────────────────
        params = self._apply_constraints(params, elements, space, merged_constraints)

        # ── Format output ─────────────────────────────────────────────────────
        step_overrides = self._format_step_overrides(params, total_volume_ul)

        return {
            "params": params,
            "step_overrides": step_overrides,
            "strategy": strategy,
            "reasoning": reasoning,
            "confidence": confidence,
            "expected_improvement": expected_improvement,
        }

    async def _literature_guided_design(
        self,
        history: list[dict[str, Any]],
        elements: list[str],
        space: dict[str, Any],
        target_metric: str,
        optimization_direction: str,
    ) -> tuple[dict[str, float], str, float]:
        """Round 0: query literature and derive the initial composition."""
        topic = f"{'-'.join(elements)} {target_metric} {optimization_direction}"
        try:
            insights = await self._knowledge_query_skill.get_literature_insights(topic, top_k=3)
        except Exception as exc:
            _logger.warning("Knowledge query failed for literature-guided design: %s", exc)
            insights = []

        params = self._initial_design(elements, space)
        if insights:
            params = self._derive_params_from_literature(insights, elements, space)
            reasoning = "首轮实验，结合知识库文献线索生成初始配比"
            confidence = 0.75
        else:
            reasoning = "首轮实验未检索到可靠文献线索，回退到均匀初始采样"
            confidence = 0.55

        return params, reasoning, confidence

    # ── Strategy: Initial Sampling ────────────────────────────────────────────

    def _initial_design(
        self,
        elements: list[str],
        space: dict[str, Any],
    ) -> dict[str, float]:
        """Generate an initial design — center of the search space."""
        n = len(elements)
        equal_share = round(1.0 / n, 4)
        params = {e: equal_share for e in elements}
        # Adjust last element to ensure exact sum = 1.0
        total = sum(params.values())
        if total != 1.0:
            params[elements[-1]] = round(params[elements[-1]] + (1.0 - total), 4)
        return params

    # ── Strategy: LLM-Guided ─────────────────────────────────────────────────

    async def _llm_guided_design(
        self,
        history: list[dict[str, Any]],
        elements: list[str],
        space: dict[str, Any],
        target_metric: str,
        direction: str,
    ) -> tuple[dict[str, float], str, float]:
        """Use LLM to reason about trends and suggest next point."""
        literature_context = await self._safe_literature_context(elements, target_metric)
        task = {
            "type": "design_next_experiment",
            "elements": elements,
            "search_space": space,
            "target_metric": target_metric,
            "optimization_direction": direction,
            "history_count": len(history),
        }
        context = {
            "experiment_history": history[-10:],
            "literature_context": literature_context,
        }

        try:
            result = await self.invoke(task=task, context=context)
            content = result.get("content", "")
            params = self._parse_params_from_llm(content, elements, space)
            return params, f"历史数据 {len(history)} 轮，使用 LLM 结合历史趋势与知识库建议设计", 0.7
        except Exception as exc:
            _logger.warning("LLM design failed: %s — falling back to center", exc)
            return self._initial_design(elements, space), "LLM 不可用，回退到确定性中心点设计", 0.4

    def _parse_params_from_llm(
        self,
        content: str,
        elements: list[str],
        space: dict[str, Any],
    ) -> dict[str, float]:
        """Extract element ratios from LLM response."""
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                # Try "params" key first, then top-level
                params_data = parsed.get("params", parsed)
                params: dict[str, float] = {}
                for e in elements:
                    val = params_data.get(e)
                    if val is not None:
                        params[e] = float(val)
                if len(params) == len(elements):
                    return params
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # Fallback: center
        _logger.warning("Could not parse LLM params, using center point")
        return self._initial_design(elements, space)

    # ── Strategy: Bayesian Optimization ───────────────────────────────────────

    async def _ml_hybrid_design(
        self,
        history: list[dict[str, Any]],
        elements: list[str],
        space: dict[str, Any],
        target_metric: str,
        optimization_direction: str,
    ) -> tuple[dict[str, float], str, float, str]:
        """Use ML candidate generation with optional LLM review."""
        predictor = PerformancePredictor(
            target_metric=target_metric,
            direction=optimization_direction,
            model_type=str(self._designer_config.get("ml_model_type", "auto")),
        )
        fit_result = predictor.fit(history)
        if not fit_result["ready"]:
            params, reasoning, confidence = await self._llm_guided_design(
                history,
                elements,
                space,
                target_metric,
                optimization_direction,
            )
            return (
                params,
                f"{reasoning}；ML 数据点不足，暂不启用预测模型",
                min(confidence, 0.65),
                "llm_guided",
            )

        candidate_count = int(self._designer_config.get("ml_candidate_count", 10))
        candidates = predictor.predict_candidates(candidate_count)
        if not candidates:
            params, reasoning, confidence = await self._llm_guided_design(
                history,
                elements,
                space,
                target_metric,
                optimization_direction,
            )
            return params, f"{reasoning}；ML 未产出候选点，回退到 LLM 设计", min(confidence, 0.6), "llm_guided"

        literature_context = await self._safe_literature_context(elements, target_metric)
        try:
            reviewed = await self.invoke(
                task={
                    "type": "review_ml_candidates",
                    "target_metric": target_metric,
                    "optimization_direction": optimization_direction,
                    "candidates": candidates[:5],
                },
                context={
                    "experiment_history": history[-10:],
                    "literature_context": literature_context,
                },
            )
            params = self._select_candidate_from_llm(reviewed.get("content", ""), candidates, elements, space)
            reasoning = f"历史数据 {len(history)} 轮，使用 ML 候选点并由 LLM 审核选择"
            confidence = 0.82
        except Exception as exc:
            _logger.warning("ML candidate review failed: %s", exc)
            params = candidates[0]["params"]
            reasoning = f"历史数据 {len(history)} 轮，使用 ML 预测候选点直接选择最优"
            confidence = 0.72

        return params, reasoning, confidence, "ml_hybrid"

    # ── Constraints ───────────────────────────────────────────────────────────

    def _apply_constraints(
        self,
        params: dict[str, float],
        elements: list[str],
        space: dict[str, Any],
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        """Normalize params so they sum to 1.0 and respect min/max bounds."""
        constraints = constraints or {}
        # Clamp to bounds
        for e in elements:
            bounds = space.get(e, {"min": 0.05, "max": 0.9})
            lo = float(
                constraints.get("min_component", constraints.get("min_fraction", bounds.get("min", 0.05)))
            )
            hi = float(bounds.get("max", 0.9))
            params[e] = max(lo, min(hi, params.get(e, lo)))

        # Normalize to sum = 1.0
        target_sum = float(constraints.get("sum_equals", 1.0))
        total = sum(params[e] for e in elements)
        if total > 0:
            params = {e: round(params[e] / total * target_sum, 4) for e in elements}

        # Fix rounding residual
        residual = round(target_sum - sum(params.values()), 6)
        if residual != 0 and elements:
            params[elements[-1]] = round(params[elements[-1]] + residual, 4)

        return params

    # ── Output formatting ─────────────────────────────────────────────────────

    def _format_step_overrides(
        self,
        params: dict[str, float],
        total_volume_ul: float,
    ) -> dict[str, Any]:
        """Convert element ratios to step_overrides format for Executor."""
        return {
            "0": {
                "prep_sol_params": {
                    "target_concentrations": params,
                    "total_volume_ul": total_volume_ul,
                }
            }
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _estimate_improvement(
        self,
        params: dict[str, float],
        history: list[dict[str, Any]],
        target_metric: str,
        direction: str,
    ) -> float:
        """Rough estimate of expected improvement (EI) in percent."""
        values = [
            e["metrics"][target_metric]
            for e in history
            if e.get("metrics", {}).get(target_metric) is not None
        ]
        if not values:
            return 0.0

        if direction == "minimize":
            best = min(values)
            avg_recent = sum(values[-3:]) / len(values[-3:])
            return round((avg_recent - best) / max(abs(best), 1e-6) * 100, 1)
        else:
            best = max(values)
            avg_recent = sum(values[-3:]) / len(values[-3:])
            return round((best - avg_recent) / max(abs(best), 1e-6) * 100, 1)

    async def _safe_literature_context(
        self,
        elements: list[str],
        target_metric: str,
    ) -> list[dict[str, Any]]:
        try:
            return await self._knowledge_query_skill.get_literature_insights(
                f"{'-'.join(elements)} {target_metric}",
                top_k=3,
            )
        except Exception:
            return []

    def _derive_params_from_literature(
        self,
        insights: list[dict[str, Any]],
        elements: list[str],
        space: dict[str, Any],
    ) -> dict[str, float]:
        scores = {element: 0.0 for element in elements}
        for insight in insights:
            text = json.dumps(insight, ensure_ascii=False).lower()
            for element in elements:
                element_lower = element.lower()
                if f"{element_lower}>40" in text or f"{element_lower} > 40" in text:
                    scores[element] += 0.25
                if f"{element_lower}>60" in text or f"{element_lower} > 60" in text:
                    scores[element] += 0.4
                if f"{element_lower}高" in text or f"{element_lower}-rich" in text:
                    scores[element] += 0.3

        if not any(scores.values()):
            return self._initial_design(elements, space)

        baseline = 1.0 / len(elements)
        params = {element: baseline + scores[element] for element in elements}
        return self._apply_constraints(params, elements, space, {"sum_equals": 1.0})

    def _select_candidate_from_llm(
        self,
        content: str,
        candidates: list[dict[str, Any]],
        elements: list[str],
        space: dict[str, Any],
    ) -> dict[str, float]:
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if isinstance(parsed.get("params"), dict):
                    params = {
                        element: float(parsed["params"][element])
                        for element in elements
                        if element in parsed["params"]
                    }
                    if len(params) == len(elements):
                        return params
                candidate_index = parsed.get("candidate_index")
                if isinstance(candidate_index, int) and 0 <= candidate_index < len(candidates):
                    return dict(candidates[candidate_index]["params"])
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                pass

        return self._apply_constraints(dict(candidates[0]["params"]), elements, space, {"sum_equals": 1.0})


