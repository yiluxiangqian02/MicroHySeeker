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

        n_history = len(history)
        _logger.info(
            "DesignerAgent: design_experiment history=%d metric=%s dir=%s",
            n_history, target_metric, optimization_direction,
        )

        # ── Strategy selection ────────────────────────────────────────────────
        if n_history == 0:
            params = self._initial_design(elements, space)
            strategy = "initial_sampling"
            reasoning = "首轮实验，使用均匀初始采样"
            expected_improvement = 0.0
        elif n_history < 5:
            params = await self._llm_guided_design(
                history, elements, space, target_metric, optimization_direction,
            )
            strategy = "llm_guided"
            reasoning = f"历史数据 {n_history} 轮，使用 LLM 指导设计"
            expected_improvement = 0.0
        else:
            params = self._bayesian_design(
                history, elements, space, target_metric, optimization_direction,
            )
            strategy = "bayesian"
            reasoning = f"历史数据 {n_history} 轮，使用贝叶斯优化"
            expected_improvement = self._estimate_improvement(
                params, history, target_metric, optimization_direction,
            )

        # ── Apply constraints ─────────────────────────────────────────────────
        params = self._apply_constraints(params, elements, space)

        # ── Format output ─────────────────────────────────────────────────────
        step_overrides = self._format_step_overrides(params, total_volume_ul)

        return {
            "params": params,
            "step_overrides": step_overrides,
            "strategy": strategy,
            "reasoning": reasoning,
            "expected_improvement": expected_improvement,
        }

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
    ) -> dict[str, float]:
        """Use LLM to reason about trends and suggest next point."""
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
        }

        try:
            result = await self.invoke(task=task, context=context)
            content = result.get("content", "")
            return self._parse_params_from_llm(content, elements, space)
        except Exception as exc:
            _logger.warning("LLM design failed: %s — falling back to center", exc)
            return self._initial_design(elements, space)

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

    def _bayesian_design(
        self,
        history: list[dict[str, Any]],
        elements: list[str],
        space: dict[str, Any],
        target_metric: str,
        direction: str,
    ) -> dict[str, float]:
        """Use Optuna TPE to suggest the next point."""
        try:
            from src.optimization.bayesian_optimizer import (
                BayesianOptimizer,
                ParameterSpace,
            )
        except ImportError:
            _logger.warning("Optuna not available, falling back to LLM center")
            return self._initial_design(elements, space)

        # Build parameter space
        param_space = ParameterSpace()
        for e in elements:
            bounds = space.get(e, {"min": 0.05, "max": 0.9})
            param_space.add_float(
                e,
                low=float(bounds.get("min", 0.05)),
                high=float(bounds.get("max", 0.9)),
            )

        optimizer = BayesianOptimizer(
            parameter_space=param_space,
            direction="minimize" if direction == "minimize" else "maximize",
            seed=42,
        )

        # Feed historical data into Optuna study
        import optuna
        study = optimizer._create_study()
        optimizer._study = study

        for exp in history:
            metrics = exp.get("metrics", {})
            metric_val = metrics.get(target_metric)
            if metric_val is None:
                continue
            params = exp.get("params", {})
            if not all(e in params for e in elements):
                continue

            trial = optuna.trial.create_trial(
                params={e: float(params[e]) for e in elements},
                distributions={
                    e: optuna.distributions.FloatDistribution(
                        low=float(space.get(e, {}).get("min", 0.05)),
                        high=float(space.get(e, {}).get("max", 0.9)),
                    )
                    for e in elements
                },
                value=float(metric_val),  # single-objective: use value= not values=
            )
            study.add_trial(trial)

        # Suggest next point
        trial = study.ask()
        params = param_space.suggest(trial)
        return {e: round(float(params[e]), 4) for e in elements}

    # ── Constraints ───────────────────────────────────────────────────────────

    def _apply_constraints(
        self,
        params: dict[str, float],
        elements: list[str],
        space: dict[str, Any],
    ) -> dict[str, float]:
        """Normalize params so they sum to 1.0 and respect min/max bounds."""
        # Clamp to bounds
        for e in elements:
            bounds = space.get(e, {"min": 0.05, "max": 0.9})
            lo = float(bounds.get("min", 0.05))
            hi = float(bounds.get("max", 0.9))
            params[e] = max(lo, min(hi, params.get(e, lo)))

        # Normalize to sum = 1.0
        total = sum(params[e] for e in elements)
        if total > 0:
            params = {e: round(params[e] / total, 4) for e in elements}

        # Fix rounding residual
        residual = round(1.0 - sum(params.values()), 6)
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


