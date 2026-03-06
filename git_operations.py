#!/usr/bin/env python3
import subprocess
import sys

# Define the working directory
work_dir = r"D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-b3-b7"

# Files to add
files_to_add = [
    "AutoHySeeker/tests/test_optimization.py",
    "AutoHySeeker/tests/test_experiment_execution.py",
    "AutoHySeeker/tests/test_d3_diagnostics.py",
    "AutoHySeeker/tests/test_llm_client.py",
    "AutoHySeeker/docs/dual_config_system.md",
    "AutoHySeeker/agent_cluster/AGENT_COORD.md"
]

# Commit message
commit_message = """test(b3-b7): add tests for optimization, experiment_execution, D3, llm_client; add dual config docs

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"""

try:
    # Step 1: Add files
    print("Step 1: Adding files...")
    add_cmd = ["git", "-C", work_dir, "add"] + files_to_add
    result = subprocess.run(add_cmd, capture_output=True, text=True, check=True)
    print(f"✓ Files added successfully")
    if result.stdout:
        print(f"  stdout: {result.stdout}")
    if result.stderr:
        print(f"  stderr: {result.stderr}")
    
    # Step 2: Commit
    print("\nStep 2: Creating commit...")
    commit_cmd = ["git", "-C", work_dir, "commit", "-m", commit_message]
    result = subprocess.run(commit_cmd, capture_output=True, text=True, check=True)
    print(f"✓ Commit created successfully")
    print(f"  {result.stdout}")
    if result.stderr:
        print(f"  stderr: {result.stderr}")
    
    print("\n✓ All git operations completed successfully!")
    
except subprocess.CalledProcessError as e:
    print(f"✗ Error executing git command: {e}", file=sys.stderr)
    print(f"  Return code: {e.returncode}", file=sys.stderr)
    if e.stdout:
        print(f"  stdout: {e.stdout}", file=sys.stderr)
    if e.stderr:
        print(f"  stderr: {e.stderr}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
