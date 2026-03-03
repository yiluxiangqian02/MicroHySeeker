#!/usr/bin/env python3
"""
dispatch.py — Pi 调用的任务分发器
用法：
    python dispatch.py create --agent copilot --desc "实现贝叶斯优化模块" --branch feat/bayes-opt
    python dispatch.py status
    python dispatch.py done --task-id TASK_001
    python dispatch.py steer --task-id TASK_001 --msg "先做 API 层，别管 UI"
"""

import json
import sys
import os
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent  # MicroHySeeker/MicroHySeeker/
CLUSTER_DIR = Path(__file__).parent
TASKS_FILE = CLUSTER_DIR / "tasks" / "tasks.json"
WORKTREES_DIR = CLUSTER_DIR / "worktrees"
LOGS_DIR = CLUSTER_DIR / "logs"

# ===== 安全保护：禁止触碰的路径 =====
PROTECTED_PATHS = [
    "MicroHySeeker/src",
    "MicroHySeeker/config/system.json",
    "data/",
    "logs/",
    "AutoHySeeker/OpenViking",
    ".git/",
]

AGENT_CMDS = {
    "codex": "codex",
    "claude-code": "claude",
    "copilot": None,  # copilot 通过 VS Code / CLI 手动启动
}


def load_tasks():
    if not TASKS_FILE.exists():
        return {"version": "1.0", "tasks": [], "completed": [], "meta": {}}
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def save_tasks(data):
    data["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    data["meta"]["updated_by"] = "Pi"
    TASKS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def new_task_id(tasks):
    existing = [t["id"] for t in tasks.get("tasks", []) + tasks.get("completed", [])]
    n = len(existing) + 1
    return f"TASK_{n:03d}"


def cmd_create(args):
    data = load_tasks()
    task_id = new_task_id(data)
    branch = args.branch or f"feat/{task_id.lower()}"
    worktree_path = WORKTREES_DIR / branch.replace("/", "_")

    task = {
        "id": task_id,
        "agent": args.agent,
        "branch": branch,
        "worktree": str(worktree_path),
        "description": args.desc,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "retries": 0,
        "notes": args.notes or "",
    }

    # 创建 git worktree
    print(f"[dispatch] Creating worktree: {worktree_path} on branch {branch}")
    try:
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", branch],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True
        )
        task["status"] = "running"
        task["started_at"] = datetime.now(timezone.utc).isoformat()
        print(f"[dispatch] Worktree created: {worktree_path}")
    except subprocess.CalledProcessError as e:
        print(f"[dispatch] WARNING: worktree creation failed: {e.stderr.strip()}")
        print(f"[dispatch] Task created as 'pending', create worktree manually if needed.")

    data["tasks"].append(task)
    save_tasks(data)

    # 生成 Agent 专属 prompt 文件
    _write_prompt(task)

    print(f"\n[OK] Task {task_id} created")
    print(f"   Agent   : {args.agent}")
    print(f"   Branch  : {branch}")
    print(f"   Worktree: {worktree_path}")
    print(f"   Prompt  : {CLUSTER_DIR / 'prompts' / f'{task_id}_prompt.md'}")
    print(f"\n-> Next: Open the prompt file and paste it to {args.agent}")


def cmd_status(args):
    data = load_tasks()
    tasks = data.get("tasks", [])
    if not tasks:
        print("[dispatch] No active tasks.")
        return
    print(f"\n{'ID':<12} {'Agent':<12} {'Branch':<30} {'Status':<10} {'Description'}")
    print("-" * 90)
    for t in tasks:
        print(f"{t['id']:<12} {t['agent']:<12} {t['branch']:<30} {t['status']:<10} {t['description'][:40]}")


def cmd_done(args):
    data = load_tasks()
    task = next((t for t in data["tasks"] if t["id"] == args.task_id), None)
    if not task:
        print(f"[dispatch] Task {args.task_id} not found.")
        return
    task["status"] = "done"
    task["finished_at"] = datetime.now(timezone.utc).isoformat()
    data["tasks"].remove(task)
    data["completed"].append(task)
    # 清理 worktree
    if task.get("worktree") and Path(task["worktree"]).exists():
        try:
            subprocess.run(["git", "worktree", "remove", task["worktree"], "--force"],
                           cwd=str(REPO_ROOT), check=True)
            print(f"[dispatch] Worktree removed: {task['worktree']}")
        except Exception as e:
            print(f"[dispatch] Worktree cleanup warning: {e}")
    save_tasks(data)
    print(f"[OK] Task {args.task_id} marked as done.")


def cmd_fail(args):
    data = load_tasks()
    task = next((t for t in data["tasks"] if t["id"] == args.task_id), None)
    if not task:
        print(f"[dispatch] Task {args.task_id} not found.")
        return
    task["retries"] = task.get("retries", 0) + 1
    task["status"] = "failed"
    task["fail_reason"] = args.reason or "unknown"
    # 自动升级模型提示
    if task["agent"] == "copilot" and task["retries"] >= 2:
        print(f"[WARN] Task {args.task_id} failed {task['retries']} times with copilot.")
        print("   -> Consider switching to claude-opus-4.6 for next retry.")
        task["notes"] = (task.get("notes", "") + " [AUTO: 建议切换 opus]").strip()
    save_tasks(data)
    print(f"[FAIL] Task {args.task_id} marked as failed (retry #{task['retries']}).")


def cmd_steer(args):
    """向运行中的 Agent 发送临时指令（写入 prompt 附录）"""
    steer_file = CLUSTER_DIR / "prompts" / f"{args.task_id}_steer.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"\n\n---\n## 🔀 Pi 指令 @ {ts}\n\n{args.msg}\n"
    with open(steer_file, "a", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Steer written to: {steer_file}")
    print(f"   -> Paste this message to {args.task_id}'s Agent session")


def _write_prompt(task):
    """生成给 Agent 的任务 prompt 文件"""
    prompt_path = CLUSTER_DIR / "prompts" / f"{task['id']}_prompt.md"
    agent_rules = {
        "copilot": "- 按次数计费，请尽量在一次会话中完成更多工作\n- 默认使用 claude-sonnet-4.6，连续2次失败切 claude-opus-4.6\n- 适合复杂算法、大重构、跨文件任务",
        "codex": "- 按 token 计费，保持 prompt 简洁\n- 适合小型修复、单文件改动、快速 debug",
        "claude-code": "- 按 token 计费\n- 适合硬件驱动代码、后端逻辑、测试编写",
    }
    rules = agent_rules.get(task["agent"], "")

    content = f"""# Task {task['id']} — {task['description']}

> **分配 Agent**: {task['agent']}
> **工作分支**: `{task['branch']}`
> **Worktree**: `{task['worktree']}`
> **创建时间**: {task['created_at']}

## Agent 规则

{rules}

## 安全规则（必须遵守）

以下路径**禁止删除或破坏性修改**：
- `MicroHySeeker/src/` — 核心源码
- `MicroHySeeker/config/system.json` — 系统配置
- `data/` — 实验数据（只读）
- `logs/` — 日志（只读）
- `AutoHySeeker/OpenViking/` — 知识库
- `.git/` — git 历史

操作原则：优先在 `{task['branch']}` 分支上操作，不直接修改 main/autohyseeker。

## 协作文件

完成任务后，请更新 `AutoHySeeker/agent_cluster/AGENT_COORD.md`：
- 将任务状态改为 `done`
- 在"经验库"中记录有效做法

## 任务描述

{task['description']}

{f"**备注**: {task['notes']}" if task.get('notes') else ""}

## 完成标准

- [ ] 代码已在 `{task['branch']}` 分支提交
- [ ] 相关测试通过（如有）
- [ ] 已更新 AGENT_COORD.md
- [ ] 如有 UI 变化，附截图描述

---
*此文件由 dispatch.py 自动生成 | 如需指令更新，查看同目录 {task['id']}_steer.md*
"""
    prompt_path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="AutoHySeeker Agent Cluster Dispatcher")
    sub = parser.add_subparsers(dest="cmd")

    p_create = sub.add_parser("create", help="Create a new agent task")
    p_create.add_argument("--agent", required=True, choices=["copilot", "codex", "claude-code"])
    p_create.add_argument("--desc", required=True, help="Task description")
    p_create.add_argument("--branch", default=None, help="Git branch name")
    p_create.add_argument("--notes", default=None, help="Extra notes")

    sub.add_parser("status", help="Show active tasks")

    p_done = sub.add_parser("done", help="Mark task as done")
    p_done.add_argument("--task-id", required=True)

    p_fail = sub.add_parser("fail", help="Mark task as failed")
    p_fail.add_argument("--task-id", required=True)
    p_fail.add_argument("--reason", default=None)

    p_steer = sub.add_parser("steer", help="Send steering message to agent")
    p_steer.add_argument("--task-id", required=True)
    p_steer.add_argument("--msg", required=True)

    args = parser.parse_args()
    if args.cmd == "create":
        cmd_create(args)
    elif args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "done":
        cmd_done(args)
    elif args.cmd == "fail":
        cmd_fail(args)
    elif args.cmd == "steer":
        cmd_steer(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
