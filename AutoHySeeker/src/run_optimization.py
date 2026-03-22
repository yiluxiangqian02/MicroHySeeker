"""CLI entry point for running closed-loop optimization."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Callable

from src.common.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def _check_microhyseeker() -> bool:
    """Verify MicroHySeeker API is reachable."""
    try:
        from src.tools.experiment_ctrl import health_check, is_microhyseeker_available

        if not is_microhyseeker_available():
            logger.error("MicroHySeeker API is not reachable")
            return False

        health = health_check()
        if health.get("status") != "ok":
            logger.error("MicroHySeeker health check failed: %s", health)
            return False

        logger.info("MicroHySeeker API is healthy")
        return True
    except Exception as exc:
        logger.error("MicroHySeeker connectivity check failed: %s", exc)
        return False


async def run_optimization(
    goal: str,
    max_rounds: int = 10,
    target_metric: str = "overpotential_mV",
    direction: str = "minimize",
    template_id: str = "tpl_her_standard",
    elements: list[str] | None = None,
    dry_run: bool = False,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Run the full optimization loop."""
    from src.agents.exp_designer import ExperimentDesignerAgent
    from src.agents.exp_executor import ExperimentExecutorAgent
    from src.agents.orchestrator_shared import get_shared_orchestrator_agent

    elements = elements or ["Fe", "Co", "Ni"]
    search_space = {element: {"min": 0.05, "max": 0.9} for element in elements}

    orchestrator = get_shared_orchestrator_agent()
    designer = ExperimentDesignerAgent()
    executor = ExperimentExecutorAgent()

    optimization = {
        "goal": goal,
        "target_metric": target_metric,
        "optimization_direction": direction,
        "max_rounds": max_rounds,
        "search_space": search_space,
        "template_id": template_id,
    }

    history: list[dict[str, Any]] = []
    best_result: dict[str, Any] | None = None
    current_round = 0
    final_action = "max_rounds"
    run_status = "running"
    latest_decision: dict[str, Any] | None = None

    def publish(status: str, **extra: Any) -> None:
        if progress_callback is None:
            return
        snapshot = {
            "status": status,
            "current_round": current_round,
            "best_result": best_result,
            "experiment_history": list(history),
            "optimization": optimization,
            "final_decision": final_action,
            "latest_decision": latest_decision,
        }
        snapshot.update(extra)
        progress_callback(snapshot)

    def apply_approval_resolution(
        decision: dict[str, Any],
        approval: dict[str, Any],
    ) -> dict[str, Any]:
        actionable = dict(decision.get("original_decision") or decision)
        actionable.pop("pending_approval", None)
        actionable.pop("work_mode", None)
        actionable["human_approval"] = approval

        if approval.get("approved"):
            return actionable

        action = actionable.get("action")
        if action == "stop":
            return {"action": "continue", "reason": "human_rejected_stop_decision", "human_approval": approval}
        if action == "adjust_strategy":
            return {"action": "continue", "reason": "human_rejected_strategy_change", "human_approval": approval}
        if action == "retry":
            return {"action": "continue", "reason": "human_rejected_retry", "human_approval": approval}
        if action == "diagnose":
            return {"action": "log_and_continue", "reason": "human_rejected_anomaly_diagnosis", "human_approval": approval}
        if action == "emergency_stop":
            return {
                "action": "stop",
                "reason": "critical_anomaly_requires_manual_intervention",
                "status_override": "blocked",
                "human_approval": approval,
            }
        return {"action": "continue", "reason": "human_rejected_pause_request", "human_approval": approval}

    async def resolve_human_gate(decision: dict[str, Any]) -> dict[str, Any]:
        nonlocal latest_decision, run_status, final_action

        pending = decision.get("pending_approval")
        if decision.get("action") != "pause_for_human" and not pending:
            return decision

        approval_id = (pending or {}).get("approval_id")
        if not approval_id:
            return decision

        latest_decision = decision
        run_status = "paused"
        final_action = "pause_for_human"
        publish(
            "paused",
            pending_approval=pending,
            pause_reason=decision.get("reason", "human_approval"),
        )

        while True:
            if should_stop and should_stop():
                return {
                    "action": "stop",
                    "reason": "loop_stopped_while_waiting_for_human",
                    "status_override": "stopped",
                }

            approval = orchestrator.get_approval_status(approval_id)
            if approval and approval.get("status") in {"approved", "rejected"}:
                run_status = "running"
                resolved = apply_approval_resolution(decision, approval)
                latest_decision = resolved
                publish("running", last_approval=approval)
                return resolved

            await asyncio.sleep(0.1)

    logger.info("=" * 60)
    logger.info("Optimization loop starting")
    logger.info("  Goal: %s", goal)
    logger.info("  Metric: %s (%s)", target_metric, direction)
    logger.info("  Max rounds: %d", max_rounds)
    logger.info("  Template: %s", template_id)
    logger.info("  Elements: %s", elements)
    logger.info("=" * 60)
    publish("running")

    while current_round < max_rounds:
        if should_stop and should_stop():
            logger.info("Stop requested; terminating optimization loop")
            final_action = "stopped"
            run_status = "stopped"
            break

        current_round += 1
        logger.info("--- Round %d/%d ---", current_round, max_rounds)
        publish("designing")

        design = await designer.design_experiment(
            history=history,
            search_space=search_space,
            target_metric=target_metric,
            optimization_direction=direction,
        )
        logger.info("Design strategy=%s params=%s", design["strategy"], design["params"])
        publish("executing", latest_design=design)

        if dry_run:
            exec_result = {
                "status": "completed",
                "run_id": f"dry_run_{current_round:03d}",
                "data_path": "",
            }
        else:
            exec_task = {
                "template_id": template_id,
                "step_overrides": design["step_overrides"],
                "exp_name": f"opt_round_{current_round:03d}",
                "pre_check": current_round == 1,
                "monitor_interval_s": 5,
            }
            exec_result = await executor.execute_experiment(exec_task)

        logger.info(
            "Execution status=%s run_id=%s",
            exec_result.get("status"),
            exec_result.get("run_id"),
        )

        if exec_result.get("status") != "completed":
            anomaly = exec_result.get(
                "anomaly",
                {
                    "type": "execution_failure",
                    "severity": "high",
                    "details": exec_result.get("error", "unknown"),
                },
            )
            blocking_statuses = {"pre_check_failed", "validation_failed"}
            if exec_result.get("status") in blocking_statuses:
                logger.error("Blocking execution failure: %s", exec_result)
                history.append(
                    {
                        "round": current_round,
                        "params": design["params"],
                        "metrics": {},
                        "status": "failed",
                        "data_quality": {"reliable": False, "score": 0},
                    }
                )
                final_action = "blocked"
                run_status = "blocked"
                publish(run_status, last_execution=exec_result)
                break

            decision = await orchestrator.handle_anomaly(
                anomaly=anomaly,
                optimization=optimization,
                current_round=current_round,
            )
            decision = await resolve_human_gate(decision)
            latest_decision = decision
            logger.warning("Anomaly action: %s", decision["action"])

            if decision["action"] == "emergency_stop":
                logger.critical("Emergency stop triggered")
                final_action = "emergency_stop"
                run_status = decision.get("status_override", "blocked")
                publish(run_status, latest_decision=decision)
                break
            if decision["action"] == "stop":
                final_action = decision.get("action", "stop")
                run_status = decision.get("status_override", "stopped")
                publish(run_status, latest_decision=decision)
                break

            history.append(
                {
                    "round": current_round,
                    "params": design["params"],
                    "metrics": {},
                    "status": "failed",
                    "data_quality": {"reliable": False, "score": 0},
                }
            )
            publish("running", last_execution=exec_result, latest_decision=decision)
            continue

        if should_stop and should_stop():
            logger.info("Stop requested after execution; terminating optimization loop")
            final_action = "stopped"
            run_status = "stopped"
            break

        publish("analyzing", last_execution=exec_result)
        if dry_run:
            analysis = _simulate_dry_run_analysis(
                params=design["params"],
                current_round=current_round,
                target_metric=target_metric,
                direction=direction,
                orchestrator=orchestrator,
                best_result=best_result,
            )
        else:
            analysis = await orchestrator.analyze_experiment(
                run_id=exec_result.get("run_id", ""),
                data_path=exec_result.get("data_path", ""),
                params=design["params"],
                target_metric=target_metric,
                best_result=best_result,
            )
        logger.info(
            "Analysis metrics=%s quality=%.2f reliable=%s",
            analysis.get("metrics", {}),
            analysis.get("data_quality", {}).get("score", 0),
            analysis.get("data_quality", {}).get("reliable", False),
        )

        entry = {
            "round": current_round,
            "params": design["params"],
            "metrics": analysis.get("metrics", {}),
            "data_quality": analysis.get("data_quality", {}),
            "run_id": exec_result.get("run_id"),
            "status": "completed",
        }
        history.append(entry)

        await orchestrator.archive_experiment(
            run_id=exec_result.get("run_id", ""),
            params=design["params"],
            metrics=analysis.get("metrics", {}),
            data_quality=analysis.get("data_quality"),
            round_num=current_round,
        )

        publish("evaluating", latest_analysis=analysis)
        best_result = orchestrator.update_best_result(history, optimization)
        decision = await orchestrator.evaluate_and_decide(
            optimization=optimization,
            experiment_history=history,
            current_result=analysis,
            best_result=best_result,
            current_round=current_round,
        )
        decision = await resolve_human_gate(decision)
        latest_decision = decision
        logger.info(
            "Decision action=%s confidence=%.2f reason=%s",
            decision["action"],
            decision.get("confidence", 0),
            decision.get("reason", "")[:100],
        )

        if decision["action"] == "stop":
            logger.info("Optimization stopping: %s", decision.get("reason"))
            final_action = decision["action"]
            run_status = decision.get("status_override", "completed")
            break
        if decision["action"] == "retry":
            history.pop()
            current_round -= 1
            final_action = "retry"
            publish("running", latest_decision=decision)
            continue

        final_action = decision["action"]
        publish("running", latest_decision=decision)

    logger.info("=" * 60)
    logger.info("Optimization loop finished")
    logger.info("  Total rounds: %d", current_round)
    if best_result:
        logger.info("  Best params: %s", best_result.get("params"))
        logger.info("  Best metrics: %s", best_result.get("metrics"))
        logger.info("  Best round: %s", best_result.get("round"))
    logger.info("=" * 60)

    if run_status == "running":
        run_status = "completed"
    publish(run_status)

    return {
        "status": run_status,
        "total_rounds": current_round,
        "best_result": best_result,
        "experiment_history": history,
        "history_count": len(history),
        "final_decision": final_action,
        "latest_decision": latest_decision,
    }


def _simulate_dry_run_analysis(
    params: dict[str, float],
    current_round: int,
    target_metric: str,
    direction: str,
    orchestrator: Any,
    best_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Generate deterministic synthetic metrics for dry-run validation."""
    optimum = {"Fe": 0.5, "Co": 0.3, "Ni": 0.2}
    distance = sum(abs(params.get(element, 0.0) - optimum[element]) for element in optimum)
    overpotential = round(165 + distance * 180 + max(0, 12 - current_round * 2), 2)
    current_density = round(max(1.0, 24 - distance * 20 - current_round * 0.5), 2)
    tafel_slope = round(58 + distance * 65, 2)
    onset = round(-0.08 - distance * 0.18, 3)

    metrics = {
        "overpotential_mV": overpotential,
        "current_density_mA_cm2": current_density,
        "tafel_slope_mV_dec": tafel_slope,
        "onset_potential_V": onset,
    }
    if target_metric not in metrics:
        metrics[target_metric] = overpotential if direction == "minimize" else current_density

    analysis_skill = orchestrator._analysis_skill
    quality = analysis_skill.assess_quality(metrics, "dry_run")
    comparison = {}
    if best_result:
        comparison = analysis_skill.compare_with_best(metrics, best_result, target_metric)

    return {
        "status": "analyzed",
        "run_id": f"dry_run_{current_round:03d}",
        "params": params,
        "metrics": metrics,
        "data_quality": quality,
        "interpretation": "dry-run synthetic analysis",
        "comparison": comparison,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AutoHySeeker optimization CLI")
    parser.add_argument("--goal", default="Minimize Fe-Co-Ni HER overpotential")
    parser.add_argument("--max-rounds", type=int, default=10)
    parser.add_argument("--metric", default="overpotential_mV")
    parser.add_argument("--direction", choices=["minimize", "maximize"], default="minimize")
    parser.add_argument("--template", default="tpl_her_standard")
    parser.add_argument("--elements", nargs="+", default=["Fe", "Co", "Ni"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if args.check_only:
        sys.exit(0 if _check_microhyseeker() else 1)

    if not args.dry_run and not _check_microhyseeker():
        logger.error("MicroHySeeker is not reachable; use --dry-run to skip hardware")
        sys.exit(1)

    result = asyncio.run(
        run_optimization(
            goal=args.goal,
            max_rounds=args.max_rounds,
            target_metric=args.metric,
            direction=args.direction,
            template_id=args.template,
            elements=args.elements,
            dry_run=args.dry_run,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
