"""Closed-loop optimization sub-graph.

Implements the core cycle:
    design → execute → analyse → evaluate → (loop or stop)

This module provides *both* a LangGraph-based implementation (when available)
and a plain-async fallback so that AutoHySeeker works without LangGraph.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.agents.orchestrator import OrchestratorAgent
from src.graph.state import AutoHySeekerState, make_initial_optimization

_logger = logging.getLogger("autohyseeker.optimization_loop")


class OptimizationLoop:
    """Runs the full optimisation loop without requiring LangGraph.

    Usage::

        loop = OptimizationLoop()
        final_state = await loop.run(
            goal="最小化 HER 过电位",
            target_metric="overpotential_mV",
            optimization_direction="minimize",
            search_space={"Fe": {"min": 0.05, "max": 0.8}, ...},
            template_id="tpl_her_standard",
            max_rounds=20,
        )
    """

    def __init__(self) -> None:
        self._orchestrator = OrchestratorAgent()
        self._running = False
        self._current_state: dict[str, Any] | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_state(self) -> dict[str, Any] | None:
        return self._current_state

    def stop(self) -> None:
        """Request the loop to stop after the current step finishes."""
        self._running = False
        _logger.info("OptimizationLoop: stop requested")

    async def run(
        self,
        goal: str,
        target_metric: str,
        optimization_direction: str = "minimize",
        search_space: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
        template_id: str = "",
        total_volume_ul: float = 1000.0,
        max_rounds: int = 20,
    ) -> dict[str, Any]:
        """Run the full optimization loop.

        Returns the final state dict with experiment_history, best_result, etc.
        """
        optimization = make_initial_optimization(
            goal=goal,
            target_metric=target_metric,
            optimization_direction=optimization_direction,
            search_space=search_space or {},
            constraints=constraints,
            template_id=template_id,
            total_volume_ul=total_volume_ul,
            max_rounds=max_rounds,
        )

        state: dict[str, Any] = {
            "optimization": optimization,
            "experiment_history": [],
            "current_round": 0,
            "best_result": None,
            "status": "running",
            "errors": [],
        }
        self._current_state = state
        self._running = True

        _logger.info(
            "OptimizationLoop: starting — goal=%r metric=%s direction=%s max_rounds=%d",
            goal, target_metric, optimization_direction, max_rounds,
        )

        try:
            while self._running and state["current_round"] < max_rounds:
                round_num = state["current_round"] + 1
                state["current_round"] = round_num
                optimization["status"] = "designing"

                _logger.info("OptimizationLoop: ═══ Round %d/%d ═══", round_num, max_rounds)

                # ── Step 1: Design ──────────────────────────────────────────
                design_result = await self._step_design(state)
                if design_result is None:
                    state["errors"].append(f"Round {round_num}: design failed")
                    _logger.error("Design failed at round %d", round_num)
                    continue

                if not self._running:
                    break

                # ── Step 2: Execute ─────────────────────────────────────────
                optimization["status"] = "executing"
                exec_result = await self._step_execute(state, design_result)

                if exec_result is None or exec_result.get("status") == "failed":
                    anomaly = (exec_result or {}).get("anomaly")
                    if anomaly:
                        handling = await self._orchestrator.handle_anomaly(
                            anomaly, optimization, round_num,
                        )
                        if handling["action"] == "emergency_stop":
                            state["errors"].append(f"Round {round_num}: emergency stop")
                            state["status"] = "emergency_stopped"
                            self._running = False
                            break
                        elif handling["action"] == "diagnose":
                            # In future: dispatch to Diagnostics agent
                            state["errors"].append(
                                f"Round {round_num}: anomaly needs diagnosis — "
                                f"{anomaly.get('type', 'unknown')}"
                            )
                    else:
                        state["errors"].append(f"Round {round_num}: execution failed")
                    continue

                if not self._running:
                    break

                # ── Step 3: Analyse ─────────────────────────────────────────
                optimization["status"] = "analyzing"
                analysis = await self._step_analyse(state, exec_result)

                round_record = {
                    "round": round_num,
                    "params": design_result.get("params", {}),
                    "run_id": exec_result.get("run_id", ""),
                    "metrics": analysis.get("metrics", {}),
                    "data_quality": analysis.get("data_quality", {}),
                }
                state["experiment_history"].append(round_record)

                # Update best
                state["best_result"] = self._orchestrator.update_best_result(
                    state["experiment_history"], optimization,
                )

                if not self._running:
                    break

                # ── Step 4: Evaluate ────────────────────────────────────────
                optimization["status"] = "evaluating"
                decision = await self._orchestrator.evaluate_and_decide(
                    optimization=optimization,
                    experiment_history=state["experiment_history"],
                    current_result=round_record,
                    best_result=state["best_result"],
                    current_round=round_num,
                )

                _logger.info(
                    "OptimizationLoop: decision=%s reason=%s confidence=%.2f",
                    decision.get("action"),
                    decision.get("reason", "")[:80],
                    decision.get("confidence", 0),
                )

                if decision["action"] == "stop":
                    state["status"] = "completed"
                    state["conclusion"] = decision.get("summary", "")
                    self._running = False
                    break
                elif decision["action"] == "retry":
                    # Retry uses same params — decrement round so it redoes
                    state["current_round"] -= 1
                    state["experiment_history"].pop()
                elif decision["action"] == "adjust_strategy":
                    # Store hint for designer
                    state["strategy_hint"] = decision.get("next_params_hint", {})

                # "continue" → loop back to design

        except Exception as exc:
            _logger.exception("OptimizationLoop: unhandled exception")
            state["status"] = "error"
            state["errors"].append(str(exc))
        finally:
            self._running = False
            if state["status"] == "running":
                state["status"] = "completed"
            optimization["status"] = "completed"
            self._current_state = state

        _logger.info(
            "OptimizationLoop: finished — rounds=%d best=%s status=%s",
            state["current_round"],
            state.get("best_result", {}).get("metrics") if state.get("best_result") else None,
            state["status"],
        )
        return state

    # ── Step implementations (delegate to agents via LLM) ──────────────────

    async def _step_design(self, state: dict[str, Any]) -> dict[str, Any] | None:
        """Ask the Designer agent for next experiment params."""
        from src.agents.exp_designer import ExperimentDesignerAgent

        optimization = state["optimization"]
        designer = ExperimentDesignerAgent()

        task = {
            "type": "design_next_experiment",
            "search_space": optimization.get("search_space", {}),
            "constraints": optimization.get("constraints", {}),
            "target_metric": optimization.get("target_metric", ""),
            "optimization_direction": optimization.get("optimization_direction", ""),
            "template_id": optimization.get("template_id", ""),
            "total_volume_ul": optimization.get("total_volume_ul", 1000),
            "history": state.get("experiment_history", [])[-10:],
            "hint": state.get("strategy_hint", {}),
        }

        try:
            result = await designer.invoke(task=task, context={
                "current_round": state["current_round"],
                "best_result": state.get("best_result"),
            })
            content = result.get("content", "")
            return self._parse_design_result(content, optimization)
        except Exception as exc:
            _logger.error("Design step failed: %s", exc)
            return None

    async def _step_execute(
        self, state: dict[str, Any], design: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Execute the designed experiment via ExperimentExecutorAgent."""
        from src.agents.exp_executor import ExperimentExecutorAgent

        template_id = design.get("template_id") or state["optimization"].get("template_id", "")
        step_overrides = design.get("step_overrides", {})
        exp_name = f"opt_round_{state['current_round']}"

        executor = ExperimentExecutorAgent()
        task = {
            "action": "execute_experiment",
            "template_id": template_id,
            "step_overrides": step_overrides,
            "exp_name": exp_name,
            "pre_check": True,
            "monitor_interval_s": 5,
        }

        try:
            result = await executor.execute_experiment(task)
            _logger.info(
                "Executor returned: status=%s run_id=%s",
                result.get("status"),
                result.get("run_id"),
            )
            return result
        except Exception as exc:
            _logger.error("Execute step failed: %s", exc)
            return {"status": "failed", "error": str(exc)}

    async def _step_analyse(
        self, state: dict[str, Any], exec_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyse completed experiment via Orchestrator's DataAnalysisSkill."""
        run_id = exec_result.get("run_id", "")
        optimization = state["optimization"]

        try:
            result = await self._orchestrator.analyze_experiment(
                run_id=run_id,
                data_path=exec_result.get("data_path", ""),
                params=exec_result.get("params", {}),
                target_metric=optimization.get("target_metric", ""),
                best_result=state.get("best_result"),
            )
            return {
                "metrics": result.get("metrics", {}),
                "data_quality": result.get("data_quality", {"reliable": True}),
                "interpretation": result.get("interpretation", ""),
            }
        except Exception as exc:
            _logger.error("Analysis step failed: %s", exc)
            return {"metrics": {}, "data_quality": {"reliable": False}}

    # ── Parsing helpers ────────────────────────────────────────────────────────

    def _parse_design_result(
        self, content: str, optimization: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract params and step_overrides from designer LLM output."""
        import re, json

        # Try JSON extraction
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                params = parsed.get("params") or parsed.get("target_concentrations", {})
                step_overrides = parsed.get("step_overrides", {})

                # If no step_overrides but we have params, build them
                if not step_overrides and params:
                    step_overrides = {
                        "0": {
                            "prep_sol_params": {
                                "target_concentrations": params,
                                "total_volume_ul": optimization.get("total_volume_ul", 1000),
                            }
                        }
                    }

                return {
                    "params": params,
                    "step_overrides": step_overrides,
                    "strategy": parsed.get("strategy", "llm_guided"),
                    "template_id": parsed.get("template_id", optimization.get("template_id", "")),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: couldn't parse — return empty (will trigger design retry)
        _logger.warning("Could not parse design result from LLM output")
        return {"params": {}, "step_overrides": {}, "strategy": "fallback"}

    def _parse_analysis_result(self, content: str) -> dict[str, Any]:
        """Extract metrics from analyst LLM output."""
        import re, json

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return {
                    "metrics": parsed.get("metrics", parsed),
                    "data_quality": parsed.get("data_quality", {"reliable": True}),
                    "interpretation": parsed.get("interpretation", ""),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        return {"metrics": {}, "data_quality": {"reliable": False}}
