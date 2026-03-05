import sys
import os
import time
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Run a simulated agent task.")
    parser.add_argument("--task_id", required=True, help="ID of the agent task.")
    parser.add_argument("--worktree_path", required=True, help="Path to the agent's worktree.")
    parser.add_argument("--description", required=True, help="Description of the agent task.")
    parser.add_argument("--agent_type", required=True, help="Type of the agent (e.g., codex, claude_code).")

    args = parser.parse_args()

    print(f"Agent task {args.task_id} ({args.agent_type}) started in worktree: {args.worktree_path}")
    print(f"Task description: {args.description}")

    # Simulate agent work: create a dummy file and commit
    try:
        os.chdir(args.worktree_path)
        print(f"Changed current directory to: {os.getcwd()}")

        dummy_file_content = f"Task {args.task_id} executed by {args.agent_type} for '{args.description}' at {time.ctime()}."
        file_name = f"agent_output_{args.task_id}.txt"
        with open(file_name, "w") as f:
            f.write(dummy_file_content)
        print(f"Created dummy file: {file_name}")

        # Simulate git operations
        subprocess.run(["git", "add", file_name], check=True)
        subprocess.run(["git", "commit", "-m", f"feat: Add output for agent task {args.task_id}"], check=True)
        print("Committed changes.")

        # Simulate some delay
        time.sleep(5)
        print(f"Agent task {args.task_id} completed successfully.")
        sys.exit(0) # Indicate success

    except Exception as e:
        print(f"Agent task {args.task_id} failed: {e}", file=sys.stderr)
        sys.exit(1) # Indicate failure

if __name__ == "__main__":
    main()
