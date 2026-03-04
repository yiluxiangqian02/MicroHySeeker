#!/usr/bin/env python3
"""CLI entry point for AutoHySeeker tools."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from src.common.config import DATA_ROOT
from src.skills.diagnostics.interactive_troubleshooting import (
    InteractiveTroubleshootingSkill,
)
from src.skills.experiment_execution.execution_monitor import ExecutionMonitorSkill
from src.skills.experiment_execution.smart_scheduler import SmartSchedulerSkill
from src.tools.report_generator import generate_health_report
from src.common.types import HealthStatus
from datetime import datetime


async def cmd_diagnose(args: argparse.Namespace) -> int:
    """Run interactive troubleshooting."""
    skill = InteractiveTroubleshootingSkill()
    result = await skill.execute(symptom=args.symptom)

    if result.success:
        print(f"✅ {result.message}\n")
        guide = result.data
        print(f"问题: {guide['title']}")
        print("\n排查步骤:")
        for i, step in enumerate(guide["steps"], 1):
            print(f"  {i}. {step}")
        print("\n可能原因:")
        for cause in guide["possible_causes"]:
            print(f"  - {cause}")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(guide, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n已保存到: {output_path}")
        return 0
    else:
        print(f"❌ {result.message}", file=sys.stderr)
        return 1


async def cmd_review(args: argparse.Namespace) -> int:
    """Review completed experiment run."""
    skill = ExecutionMonitorSkill()
    result = await skill.execute(run_dir=args.run_dir)

    if result.success:
        assessment = result.data
        print(f"✅ {result.message}\n")
        print(f"运行 ID: {assessment['run_id']}")
        print(f"状态: {'✅ 成功' if assessment['success'] else '❌ 失败'}")
        print(f"步骤成功率: {assessment['success_rate']:.1%} ({assessment['successful_steps']}/{assessment['total_steps']})")
        print(f"错误数: {assessment['error_count']}")
        print(f"警告数: {assessment['warning_count']}")

        if assessment["diagnostics"]:
            print("\n诊断结果:")
            for diag in assessment["diagnostics"]:
                severity_icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔥"}.get(diag["severity"], "•")
                print(f"  {severity_icon} [{diag['category']}] {diag['message']}")
                print(f"     建议: {diag['suggestion']}")

        print(f"\n质量报告: {assessment['report_path']}")
        return 0
    else:
        print(f"❌ {result.message}", file=sys.stderr)
        return 1


async def cmd_schedule(args: argparse.Namespace) -> int:
    """Schedule multiple experiments."""
    # Load experiments from JSON file
    exp_file = Path(args.experiments_file)
    if not exp_file.exists():
        print(f"❌ Experiments file not found: {args.experiments_file}", file=sys.stderr)
        return 1

    with exp_file.open("r", encoding="utf-8") as f:
        experiments = json.load(f)

    skill = SmartSchedulerSkill()
    result = await skill.execute(experiments=experiments)

    if result.success:
        schedule = result.data
        print(f"✅ {result.message}\n")
        print(f"总实验数: {schedule['total_experiments']}")
        print(f"批次数: {schedule['batches']}")
        print(f"预计总时长: {schedule['total_duration_hours']:.1f} 小时 ({schedule['total_duration_min']:.0f} 分钟)\n")

        print("执行顺序:")
        for i, exp in enumerate(schedule["scheduled_experiments"], 1):
            deps = f" (依赖: {', '.join(exp['depends_on'])})" if exp["depends_on"] else ""
            equipment = f" [设备: {', '.join(exp['equipment'])}]" if exp["equipment"] else ""
            print(f"  {i}. {exp['id']} ({exp['type']}) - {exp['estimated_duration_min']:.0f}分钟{deps}{equipment}")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n已保存到: {output_path}")
        return 0
    else:
        print(f"❌ {result.message}", file=sys.stderr)
        return 1


async def cmd_health_check(args: argparse.Namespace) -> int:
    """Perform system health check."""
    # Mock health check - in real implementation, check actual hardware
    statuses = [
        HealthStatus(
            component="CHI660F",
            status="ok",
            message="电化学工作站连接正常",
            last_checked=datetime.now(),
        ),
        HealthStatus(
            component="Pump_1",
            status="ok",
            message="蠕动泵 1 响应正常",
            last_checked=datetime.now(),
        ),
        HealthStatus(
            component="Pump_2",
            status="warning",
            message="蠕动泵 2 响应延迟",
            last_checked=datetime.now(),
        ),
        HealthStatus(
            component="RS485",
            status="ok",
            message="RS485 通信正常",
            last_checked=datetime.now(),
        ),
    ]

    print("系统健康检查\n")
    for status in statuses:
        status_icon = {"ok": "✅", "warning": "⚠️", "error": "❌", "unknown": "❓"}.get(status.status, "•")
        print(f"{status_icon} {status.component}: {status.message}")

    if args.output:
        output_path = Path(args.output)
        generate_health_report(statuses, str(output_path))
        print(f"\n健康报告已保存到: {output_path}")

    # Return error code if any component has error status
    has_error = any(s.status == "error" for s in statuses)
    return 1 if has_error else 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AutoHySeeker CLI - 实验监控与诊断工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # diagnose command
    diagnose_parser = subparsers.add_parser("diagnose", help="交互式故障排查")
    diagnose_parser.add_argument(
        "symptom",
        choices=["pump_not_running", "echem_no_signal", "communication_timeout", "data_anomaly"],
        help="故障症状",
    )
    diagnose_parser.add_argument("-o", "--output", help="输出文件路径")

    # review command
    review_parser = subparsers.add_parser("review", help="分析实验运行质量")
    review_parser.add_argument("run_dir", help="实验运行目录路径")

    # schedule command
    schedule_parser = subparsers.add_parser("schedule", help="优化多实验排程")
    schedule_parser.add_argument("experiments_file", help="实验列表 JSON 文件")
    schedule_parser.add_argument("-o", "--output", help="输出文件路径")

    # health-check command
    health_parser = subparsers.add_parser("health-check", help="系统健康检查")
    health_parser.add_argument("-o", "--output", help="输出报告路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate command handler
    if args.command == "diagnose":
        return asyncio.run(cmd_diagnose(args))
    elif args.command == "review":
        return asyncio.run(cmd_review(args))
    elif args.command == "schedule":
        return asyncio.run(cmd_schedule(args))
    elif args.command == "health-check":
        return asyncio.run(cmd_health_check(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
