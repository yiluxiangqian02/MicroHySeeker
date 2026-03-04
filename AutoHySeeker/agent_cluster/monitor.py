# AutoHySeeker Agent 集群监控脚本
# 用法: python monitor.py [--once]
# 功能: 每隔 N 秒检查所有任务状态，输出摘要

import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

CLUSTER_DIR = Path(__file__).parent
TASKS_FILE = CLUSTER_DIR / "tasks" / "tasks.json"
LOGS_DIR = CLUSTER_DIR / "logs"
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


def check_process_alive(pid: int | None) -> bool:
    """检查 Agent 进程是否还活着"""
    if not pid:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True
        )
        return str(pid) in result.stdout
    except Exception:
        return False


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


def check_branch_pr(branch: str) -> dict | None:
    """检查分支是否已有 PR，返回 PR 信息或 None"""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--json", "number,title,state,url"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            return prs[0] if prs else None
    except Exception:
        pass
    return None


def check_pr_ci(pr_number: int) -> str:
    """检查 PR 的 CI 状态，返回 'pass'/'fail'/'pending'/'unknown'"""
    try:
        result = subprocess.run(
            ["gh", "pr", "checks", str(pr_number), "--json", "name,state,conclusion"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return "unknown"
        checks = json.loads(result.stdout)
        if not checks:
            return "unknown"
        conclusions = [c.get("conclusion", "") for c in checks]
        if any(c in ("failure", "cancelled", "timed_out") for c in conclusions):
            return "fail"
        if all(c == "success" for c in conclusions):
            return "pass"
        return "pending"
    except Exception:
        return "unknown"


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


def write_log(lines: list[str], now: datetime):
    """将监控结果追加写入日志文件"""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"monitor_{now.strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{now.isoformat()}Z]\n")
        for line in lines:
            f.write(f"  {line}\n")


def run_monitor_once():
    data = load_tasks()
    tasks = data.get("tasks", [])
    now = datetime.utcnow()
    print(f"\n{'='*60}")
    print(f"[Monitor] {now.strftime('%Y-%m-%d %H:%M:%S UTC')} — {len(tasks)} active tasks")
    print('='*60)

    alerts = []
    log_lines = []
    changed = False

    for task in tasks:
        tid = task["id"]
        agent = task["agent"]
        branch = task["branch"]
        worktree = task.get("worktree", "")
        status = task.get("status", "unknown")
        pid = task.get("pid")

        # 检查 worktree 是否存在
        alive = check_worktree_alive(worktree)
        commits = check_branch_has_new_commits(branch) if alive else 0

        # 检查 Agent 进程
        proc_alive = check_process_alive(pid) if pid else None

        # 检查 PR
        pr_info = check_branch_pr(branch)
        ci_status = "unknown"
        if pr_info:
            ci_status = check_pr_ci(pr_info["number"])

        # 安全检查
        violations = check_safety(worktree) if alive else []

        icon = "✅" if alive else "❌"
        proc_icon = "🟢" if proc_alive else ("🔴" if proc_alive is False else "⚪")
        print(f"\n{icon} {tid} | {agent} | {branch}")
        print(f"   Status  : {status}")
        print(f"   Commits : {commits} new commits")
        print(f"   Worktree: {'alive' if alive else 'MISSING'}")
        if pid:
            print(f"   Process : {proc_icon} PID {pid} {'alive' if proc_alive else 'DEAD'}")
        if pr_info:
            print(f"   PR      : #{pr_info['number']} {pr_info['title']} | CI: {ci_status}")

        log_lines.append(f"{tid} | {agent} | {branch} | status={status} | worktree={'alive' if alive else 'MISSING'} | pid={pid} proc={'alive' if proc_alive else 'dead'} | ci={ci_status}")

        if violations:
            print(f"   ⚠️  SAFETY VIOLATION — protected files changed:")
            for v in violations:
                print(f"      - {v}")
            msg = f"SAFETY: {tid} touched protected files: {violations}"
            alerts.append(msg)
            log_lines.append(f"  ALERT: {msg}")

        if not alive and status == "running":
            print(f"   ⚠️  Worktree missing but task still marked running!")
            msg = f"MISSING_WORKTREE: {tid}"
            alerts.append(msg)
            log_lines.append(f"  ALERT: {msg}")

        # Agent 进程死了但任务未完成 → 自动标记 failed
        if pid and not proc_alive and status == "running":
            print(f"   ⚠️  Agent process {pid} died! Auto-marking as failed.")
            task["status"] = "failed"
            task["fail_reason"] = f"Agent process {pid} died unexpectedly"
            changed = True
            msg = f"DEAD_PROCESS: {tid} agent PID {pid} died, marked failed"
            alerts.append(msg)
            log_lines.append(f"  ALERT: {msg}")

        # PR 已创建且 CI 通过 → 自动标记为 review
        if pr_info and ci_status == "pass" and status == "running":
            print(f"   🎉 PR CI passed! Auto-marking as review.")
            task["status"] = "review"
            task["pr_number"] = pr_info["number"]
            task["pr_url"] = pr_info["url"]
            changed = True
            msg = f"CI_PASS: {tid} PR #{pr_info['number']} CI passed, marked review"
            log_lines.append(f"  INFO: {msg}")

    if changed:
        save_tasks(data)

    if alerts:
        print(f"\n🚨 ALERTS ({len(alerts)}):")
        for a in alerts:
            print(f"   • {a}")
    else:
        print("\n✅ All clear. No safety violations.")

    write_log(log_lines, now)
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="AutoHySeeker Agent Cluster Monitor")
    parser.add_argument("--once", action="store_true", help="Run monitor check once and exit")
    args = parser.parse_args()

    if args.once:
        try:
            run_monitor_once()
        except Exception as e:
            print(f"[Monitor] ERROR: {e}")
        return

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
