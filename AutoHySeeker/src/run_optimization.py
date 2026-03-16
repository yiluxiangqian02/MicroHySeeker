"""CLI entry point for running closed-loop optimization.

Usage:
    python -m src.run_optimization --goal "最小化 HER 过电位" --max-rounds 10
    python -m src.run_optimization --check-only     # verify connectivity only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

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

        logger.info("MicroHySeeker API is healthy ✓")
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
) -> dict[str, Any]:
    """Run the full optimization loop.

    Args:
        goal: Human-readable optimization goal.
        max_rounds: Maximum optimization rounds.
        target_metric: Metric to optimize.
        direction: ``"minimize"`` or ``"maximize"``.
        template_id: MicroHySeeker template ID.
        elements: Element list (default: ["Fe", "Co", "Ni"]).
        dry_run: If True, skip actual experiment execution.

    Returns:
        Final optimization state summary.
    """
    from src.agents.orchestrator import OrchestratorAgent
    from src.agents.exp_designer import ExperimentDesignerAgent
    from src.agents.exp_executor import ExperimentExecutorAgent
    from src.agents.data_analyst import DataAnalystAgent
    from src.agents.knowledge_mgr import KnowledgeManagerAgent

    elements = elements or ["Fe", "Co", "Ni"]
    search_space = {e: {"min": 0.05, "max": 0.9} for e in elements}

    orchestrator = OrchestratorAgent()
    designer = ExperimentDesignerAgent()
    executor = ExperimentExecutorAgent()
    analyst = DataAnalystAgent()
    knowledge = KnowledgeManagerAgent(archive_path="data/experiment_archive.json")

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

    logger.info("=" * 60)
    logger.info("优化循环启动")
    logger.info("  目标: %s", goal)
    logger.info("  指标: %s (%s)", target_metric, direction)
    logger.info("  最大轮次: %d", max_rounds)
    logger.info("  模板: %s", template_id)
    logger.info("  元素: %s", elements)
    logger.info("=" * 60)

    while current_round < max_rounds:
        current_round += 1
        logger.info("\n--- 第 %d/%d 轮 ---", current_round, max_rounds)

        # ── Step 1: Design ────────────────────────────────────────────────
        logger.info("[1/4] 设计实验参数...")
        design = await designer.design_experiment(
            history=history,
            search_space=search_space,
            target_metric=target_metric,
            optimization_direction=direction,
        )
        logger.info(
            "  策略: %s | 参数: %s",
            design["strategy"],
            design["params"],
        )

        # ── Step 2: Execute ───────────────────────────────────────────────
        logger.info("[2/4] 执行实验...")
        if dry_run:
            logger.info("  [DRY-RUN] 跳过实际执行")
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
                "pre_check": current_round == 1,  # only first round
                "monitor_interval_s": 5,
            }
            exec_result = await executor.execute_experiment(exec_task)

        logger.info(
            "  状态: %s | run_id: %s",
            exec_result.get("status"),
            exec_result.get("run_id"),
        )

        if exec_result.get("status") != "completed":
            # Handle failure
            anomaly = exec_result.get("anomaly", {
                "type": "execution_failure",
                "severity": "high",
                "details": exec_result.get("error", "unknown"),
            })
            decision = await orchestrator.handle_anomaly(
                anomaly=anomaly,
                optimization=optimization,
                current_round=current_round,
            )
            logger.warning("  异常处理: %s", decision["action"])

            if decision["action"] == "emergency_stop":
                logger.critical("紧急停止！中断优化循环。")
                break
            # Log failure and continue
            history.append({
                "round": current_round,
                "params": design["params"],
                "metrics": {},
                "status": "failed",
                "data_quality": {"reliable": False, "score": 0},
            })
            continue

        # ── Step 3: Analyse ───────────────────────────────────────────────
        logger.info("[3/4] 分析实验数据...")
        analysis = await analyst.analyze_experiment(
            run_id=exec_result.get("run_id", ""),
            data_path=exec_result.get("data_path", ""),
            params=design["params"],
            target_metric=target_metric,
            best_result=best_result,
        )
        logger.info(
            "  指标: %s | 质量: %.2f | 可靠: %s",
            analysis.get("metrics", {}),
            analysis.get("data_quality", {}).get("score", 0),
            analysis.get("data_quality", {}).get("reliable", False),
        )

        # Build history entry
        entry = {
            "round": current_round,
            "params": design["params"],
            "metrics": analysis.get("metrics", {}),
            "data_quality": analysis.get("data_quality", {}),
            "run_id": exec_result.get("run_id"),
            "status": "completed",
        }
        history.append(entry)

        # Archive to knowledge base
        await knowledge.archive_experiment(
            run_id=exec_result.get("run_id", ""),
            params=design["params"],
            metrics=analysis.get("metrics", {}),
            data_quality=analysis.get("data_quality"),
            round_num=current_round,
        )

        # ── Step 4: Evaluate & Decide ─────────────────────────────────────
        logger.info("[4/4] 评估结果...")
        best_result = orchestrator.update_best_result(history, optimization)
        decision = await orchestrator.evaluate_and_decide(
            optimization=optimization,
            experiment_history=history,
            current_result=analysis,
            best_result=best_result,
            current_round=current_round,
        )
        logger.info(
            "  决策: %s | 置信度: %.2f | 原因: %s",
            decision["action"],
            decision.get("confidence", 0),
            decision.get("reason", "")[:100],
        )

        if decision["action"] == "stop":
            logger.info("优化停止: %s", decision.get("reason"))
            final_action = decision["action"]
            break

        final_action = decision["action"]

    # ── Summary ───────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("优化循环完成")
    logger.info("  总轮次: %d", current_round)
    if best_result:
        logger.info("  最优参数: %s", best_result.get("params"))
        logger.info("  最优指标: %s", best_result.get("metrics"))
        logger.info("  来自第 %s 轮", best_result.get("round"))
    logger.info("=" * 60)

    return {
        "total_rounds": current_round,
        "best_result": best_result,
        "history_count": len(history),
        "final_decision": final_action,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AutoHySeeker 闭环优化 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--goal",
        default="最小化 Fe-Co-Ni 三元合金 HER 过电位",
        help="优化目标描述",
    )
    parser.add_argument(
        "--max-rounds", type=int, default=10,
        help="最大优化轮次 (default: 10)",
    )
    parser.add_argument(
        "--metric", default="overpotential_mV",
        help="目标指标 (default: overpotential_mV)",
    )
    parser.add_argument(
        "--direction", choices=["minimize", "maximize"], default="minimize",
        help="优化方向 (default: minimize)",
    )
    parser.add_argument(
        "--template", default="tpl_her_standard",
        help="MicroHySeeker 模板 ID",
    )
    parser.add_argument(
        "--elements", nargs="+", default=["Fe", "Co", "Ni"],
        help="优化元素列表 (default: Fe Co Ni)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="干跑模式：跳过实际实验执行",
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="仅检查 MicroHySeeker 连接状态",
    )

    args = parser.parse_args()

    if args.check_only:
        ok = _check_microhyseeker()
        sys.exit(0 if ok else 1)

    if not args.dry_run:
        if not _check_microhyseeker():
            logger.error("MicroHySeeker 不可达，请先启动 MicroHySeeker。")
            logger.info("提示：使用 --dry-run 可跳过实际硬件连接。")
            sys.exit(1)

    result = asyncio.run(run_optimization(
        goal=args.goal,
        max_rounds=args.max_rounds,
        target_metric=args.metric,
        direction=args.direction,
        template_id=args.template,
        elements=args.elements,
        dry_run=args.dry_run,
    ))

    print("\n结果摘要:")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
