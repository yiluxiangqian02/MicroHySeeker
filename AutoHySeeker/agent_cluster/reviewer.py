#!/usr/bin/env python3
"""
reviewer.py — 自动 Code Review
用法：
    python reviewer.py --task-id TASK_001
    python reviewer.py --branch feat/bayes-opt
"""

import json
import subprocess
import argparse
import sys
from pathlib import Path
from datetime import datetime

CLUSTER_DIR = Path(__file__).parent
TASKS_FILE = CLUSTER_DIR / "tasks" / "tasks.json"
REPO_ROOT = CLUSTER_DIR.parent.parent


def load_tasks():
    if not TASKS_FILE.exists():
        return {"tasks": [], "completed": []}
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def find_task(task_id: str | None, branch: str | None) -> dict | None:
    data = load_tasks()
    all_tasks = data.get("tasks", []) + data.get("completed", [])
    if task_id:
        return next((t for t in all_tasks if t["id"] == task_id), None)
    if branch:
        return next((t for t in all_tasks if t["branch"] == branch), None)
    return None


def find_pr(branch: str) -> dict | None:
    """通过 gh 找到分支对应的 PR"""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--json", "number,title,state,url,body"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            return prs[0] if prs else None
    except Exception as e:
        print(f"[reviewer] ERROR finding PR: {e}")
    return None


def get_pr_diff(pr_number: int) -> str:
    """获取 PR 的 diff 内容"""
    try:
        result = subprocess.run(
            ["gh", "pr", "diff", str(pr_number)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        print(f"[reviewer] ERROR getting diff: {e}")
    return ""


def run_codex_review(pr_number: int, pr_title: str, diff: str) -> str:
    """用 codex 做 code review，返回 review 内容"""
    # 截断过长的 diff（避免超出 token 限制）
    max_diff_chars = 8000
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n\n... [diff truncated for length] ..."

    prompt = f"""You are a senior software engineer performing a code review.

PR #{pr_number}: {pr_title}

Please review the following diff and provide:
1. **Summary** - What does this PR do?
2. **Issues** - Any bugs, logic errors, or security concerns (be specific with file/line refs)
3. **Suggestions** - Improvements for readability, performance, or maintainability
4. **Verdict** - APPROVE / REQUEST_CHANGES / COMMENT

Diff:
```diff
{diff}
```

Be concise and actionable. Focus on correctness and safety."""

    try:
        result = subprocess.run(
            ["codex", "--full-auto", "exec", prompt],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        # Fallback: try without --full-auto
        result2 = subprocess.run(
            ["codex", prompt],
            capture_output=True, text=True, timeout=120
        )
        if result2.returncode == 0 and result2.stdout.strip():
            return result2.stdout.strip()
    except subprocess.TimeoutExpired:
        return "⚠️ Code review timed out after 120 seconds."
    except FileNotFoundError:
        pass

    # Fallback to claude if codex not available
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools", ""],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "⚠️ Could not run automated review (codex/claude not available)."


def post_pr_comment(pr_number: int, comment: str) -> bool:
    """将 review 结果写入 PR comment"""
    try:
        result = subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--body", comment],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[reviewer] ERROR posting comment: {e}")
    return False


def cmd_review(task_id: str | None, branch: str | None):
    # 找到任务
    task = find_task(task_id, branch)
    if not task and not branch:
        print(f"[reviewer] Task {task_id} not found.")
        sys.exit(1)

    effective_branch = branch or (task["branch"] if task else None)
    if not effective_branch:
        print("[reviewer] No branch specified.")
        sys.exit(1)

    print(f"[reviewer] Looking for PR on branch: {effective_branch}")
    pr = find_pr(effective_branch)
    if not pr:
        print(f"[reviewer] No PR found for branch '{effective_branch}'.")
        print("   -> Create a PR first: gh pr create --head " + effective_branch)
        sys.exit(1)

    pr_number = pr["number"]
    pr_title = pr["title"]
    print(f"[reviewer] Found PR #{pr_number}: {pr_title}")

    print("[reviewer] Fetching diff...")
    diff = get_pr_diff(pr_number)
    if not diff:
        print("[reviewer] WARNING: empty diff, proceeding anyway.")

    print("[reviewer] Running code review with codex...")
    review_text = run_codex_review(pr_number, pr_title, diff)

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    comment = f"""## 🤖 AutoHySeeker Automated Code Review

*Generated by `reviewer.py` at {ts}*

{review_text}

---
*This review was generated automatically. Please verify all suggestions before acting on them.*"""

    print(f"\n[reviewer] Review result:\n{'='*60}")
    print(review_text)
    print('='*60)

    print(f"\n[reviewer] Posting review comment to PR #{pr_number}...")
    if post_pr_comment(pr_number, comment):
        print(f"[reviewer] ✅ Review comment posted to PR #{pr_number}")
        print(f"   URL: {pr.get('url', '')}")
    else:
        print("[reviewer] ❌ Failed to post PR comment. Review printed above.")


def main():
    parser = argparse.ArgumentParser(description="AutoHySeeker Automated Code Reviewer")
    parser.add_argument("--task-id", default=None, help="Task ID (e.g. TASK_001)")
    parser.add_argument("--branch", default=None, help="Branch name")
    args = parser.parse_args()

    if not args.task_id and not args.branch:
        parser.print_help()
        sys.exit(1)

    cmd_review(args.task_id, args.branch)


if __name__ == "__main__":
    main()
