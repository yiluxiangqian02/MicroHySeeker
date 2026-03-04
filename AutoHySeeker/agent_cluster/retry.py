#!/usr/bin/env python3
"""
retry.py — 智能重试失败的 Agent 任务
用法：
    python retry.py --task-id TASK_001
"""

import json
import subprocess
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

CLUSTER_DIR = Path(__file__).parent
TASKS_FILE = CLUSTER_DIR / "tasks" / "tasks.json"
REPO_ROOT = CLUSTER_DIR.parent.parent
MAX_RETRIES = 3


def load_tasks():
    if not TASKS_FILE.exists():
        return {"tasks": [], "completed": [], "meta": {}}
    return json.loads(TASKS_FILE.read_text(encoding="utf-8"))


def save_tasks(data):
    data["meta"] = data.get("meta", {})
    data["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    TASKS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _launch_agent(task: dict) -> int | None:
    """后台启动对应的 coding agent，返回 PID 或 None"""
    agent = task["agent"]
    task_id = task["id"]
    prompt_file = CLUSTER_DIR / "prompts" / f"{task_id}_retry_prompt.md"
    if not prompt_file.exists():
        prompt_file = CLUSTER_DIR / "prompts" / f"{task_id}_prompt.md"
    worktree = task.get("worktree", str(REPO_ROOT))

    if not prompt_file.exists():
        print(f"[retry] ERROR: prompt file not found: {prompt_file}")
        return None

    prompt_content = prompt_file.read_text(encoding="utf-8")

    try:
        if agent == "copilot":
            cmd = ["copilot", "--model", "claude-sonnet-4.6", "--allow-all", "-p", prompt_content]
        elif agent == "codex":
            cmd = ["codex", "--full-auto", "exec", prompt_content]
        elif agent == "claude-code":
            cmd = ["claude", "-p", prompt_content, "--allowedTools", "edit,bash,read,write"]
        else:
            print(f"[retry] Unknown agent: {agent}")
            return None

        proc = subprocess.Popen(
            cmd,
            cwd=str(worktree),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        print(f"[retry] Agent '{agent}' launched with PID {proc.pid}")
        return proc.pid
    except FileNotFoundError:
        print(f"[retry] WARNING: '{agent}' command not found. Start the agent manually.")
        print(f"   Enhanced prompt: {prompt_file}")
        return None
    except Exception as e:
        print(f"[retry] WARNING: failed to launch agent: {e}")
        return None


def build_enhanced_prompt(task: dict) -> str:
    """读取原始 prompt，附加失败原因和修正指令"""
    task_id = task["id"]
    fail_reason = task.get("fail_reason", "unknown error")
    retries = task.get("retries", 0)

    # 读取原始 prompt
    original_prompt_file = CLUSTER_DIR / "prompts" / f"{task_id}_prompt.md"
    original_prompt = ""
    if original_prompt_file.exists():
        original_prompt = original_prompt_file.read_text(encoding="utf-8")
    else:
        original_prompt = f"# Task {task_id}\n\n{task.get('description', '')}"

    # 读取 steer 文件（如果有）
    steer_file = CLUSTER_DIR / "prompts" / f"{task_id}_steer.md"
    steer_content = ""
    if steer_file.exists():
        steer_content = "\n\n" + steer_file.read_text(encoding="utf-8")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    enhanced = f"""{original_prompt}{steer_content}

---

## 🔁 自动重试指令 — Retry #{retries} @ {ts}

**上次失败原因**：
{fail_reason}

**修正要求**：
1. 请仔细阅读上述失败原因，避免重复同样的错误
2. 如果是代码错误，先运行测试确认问题所在
3. 如果是工具/命令问题，检查环境配置
4. 完成后确保提交代码并更新 `AGENT_COORD.md`
5. 如无法解决，在 `AGENT_COORD.md` 中详细记录阻塞原因

**注意**：这是第 {retries} 次重试（最多 {MAX_RETRIES} 次）。请专注解决核心问题。
"""
    return enhanced


def cmd_retry(task_id: str):
    data = load_tasks()
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if not task:
        print(f"[retry] Task {task_id} not found in active tasks.")
        sys.exit(1)

    retries = task.get("retries", 0)
    if retries >= MAX_RETRIES:
        print(f"[retry] ❌ Task {task_id} has already been retried {retries} times (max {MAX_RETRIES}).")
        print("   -> Consider switching agents or reviewing the task manually.")
        sys.exit(1)

    fail_reason = task.get("fail_reason", "unknown")
    print(f"[retry] Task: {task_id}")
    print(f"   Agent     : {task['agent']}")
    print(f"   Fail reason: {fail_reason}")
    print(f"   Retries so far: {retries}")

    # 生成增强 prompt
    enhanced_prompt = build_enhanced_prompt(task)
    retry_prompt_file = CLUSTER_DIR / "prompts" / f"{task_id}_retry_prompt.md"
    retry_prompt_file.write_text(enhanced_prompt, encoding="utf-8")
    print(f"[retry] Enhanced prompt written to: {retry_prompt_file}")

    # 更新任务状态
    task["retries"] = retries + 1
    task["status"] = "running"
    task["fail_reason"] = None
    task["started_at"] = datetime.now(timezone.utc).isoformat()
    task["last_retry_at"] = datetime.now(timezone.utc).isoformat()

    # 启动 Agent
    pid = _launch_agent(task)
    if pid:
        task["pid"] = pid

    save_tasks(data)

    print(f"\n[retry] ✅ Task {task_id} restarted (retry #{task['retries']})")
    if pid:
        print(f"   PID: {pid}")
    else:
        print(f"   -> Manually start the agent with: {retry_prompt_file}")


def main():
    parser = argparse.ArgumentParser(description="AutoHySeeker Agent Retry Tool")
    parser.add_argument("--task-id", required=True, help="Task ID to retry (e.g. TASK_001)")
    args = parser.parse_args()
    cmd_retry(args.task_id)


if __name__ == "__main__":
    main()
