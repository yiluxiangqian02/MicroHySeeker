# AutoHySeeker Agent 集群监控脚本
# 用法: python monitor.py
# 功能: 每隔 N 秒检查所有任务状态，输出摘要

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

CLUSTER_DIR = Path(__file__).parent
TASKS_FILE = CLUSTER_DIR / "tasks" / "tasks.json"
REPO_ROOT = CLUSTER_DIR.parent.parent
CHECK_INTERVAL = 300  # 5分钟

PROTECTED_PATHS = [
    "MicroHySeeker/src",
    "MicroHySeeker/config/system.json",
    "data/",
    "logs/",
    "AutoHySeeker/OpenViking",
    ".git/",
]


def load_tasks():
    if not TASKS_FILE.exists():
        return {"tasks": [], "completed": []}
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def save_tasks(data):
    data["meta"] = data.get("meta", {})
    data["meta"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    TASKS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def check_worktree_alive(worktree_path: str) -> bool:
    """检查 worktree 是否还在"""
    return Path(worktree_path).exists()


def check_branch_has_new_commits(branch: str) -> int:
    """返回该分支相比 autohyseeker 的新 commit 数"""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"autohyseeker..{branch}"],
            cwd=str(REPO_ROOT), capture_output=True, text=True
        )
        return int(result.stdout.strip()) if result.returncode == 0 else 0
    except Exception:
        return 0


def check_safety(worktree_path: str) -> list:
    """检查 worktree 中是否有对保护路径的变更"""
    violations = []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "autohyseeker"],
            cwd=worktree_path, capture_output=True, text=True
        )
        changed = result.stdout.strip().split("\n")
        for p in PROTECTED_PATHS:
            for f in changed:
                if f.startswith(p):
                    violations.append(f)
    except Exception:
        pass
    return violations


def run_monitor_once():
    data = load_tasks()
    tasks = data.get("tasks", [])
    now = datetime.utcnow()
    print(f"\n{'='*60}")
    print(f"[Monitor] {now.strftime('%Y-%m-%d %H:%M:%S UTC')} — {len(tasks)} active tasks")
    print('='*60)

    alerts = []
    for task in tasks:
        tid = task["id"]
        agent = task["agent"]
        branch = task["branch"]
        worktree = task.get("worktree", "")
        status = task.get("status", "unknown")

        # 检查 worktree 是否存在
        alive = check_worktree_alive(worktree)
        commits = check_branch_has_new_commits(branch) if alive else 0

        # 安全检查
        violations = check_safety(worktree) if alive else []

        icon = "✅" if alive else "❌"
        print(f"\n{icon} {tid} | {agent} | {branch}")
        print(f"   Status : {status}")
        print(f"   Commits: {commits} new commits")
        print(f"   Worktree: {'alive' if alive else 'MISSING'}")

        if violations:
            print(f"   ⚠️  SAFETY VIOLATION — protected files changed:")
            for v in violations:
                print(f"      - {v}")
            alerts.append(f"SAFETY: {tid} touched protected files: {violations}")

        if not alive and status == "running":
            print(f"   ⚠️  Worktree missing but task still marked running!")
            alerts.append(f"MISSING_WORKTREE: {tid}")

    if alerts:
        print(f"\n🚨 ALERTS ({len(alerts)}):")
        for a in alerts:
            print(f"   • {a}")
        # 写入日志
        log_file = CLUSTER_DIR / "logs" / f"monitor_{now.strftime('%Y%m%d')}.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{now.isoformat()}] ALERTS:\n")
            for a in alerts:
                f.write(f"  - {a}\n")
    else:
        print("\n✅ All clear. No safety violations.")

    print(f"\n{'='*60}\n")


def main():
    print("[Monitor] AutoHySeeker Agent Cluster Monitor started")
    print(f"[Monitor] Check interval: {CHECK_INTERVAL}s")
    while True:
        try:
            run_monitor_once()
        except Exception as e:
            print(f"[Monitor] ERROR: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
