#!/usr/bin/env python3
"""Git commit script for TASK_019."""
import subprocess
import sys

work_dir = r"D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-c1-c4"

files_to_add = [
    "AutoHySeeker/.gitignore",
    "AutoHySeeker/tests/conftest.py",
    "AutoHySeeker/tests/test_tools_extended.py",
    "AutoHySeeker/tests/test_config.py",
    "AutoHySeeker/pyproject.toml",
    "AutoHySeeker/VALIDATION.md",
    "AutoHySeeker/agent_cluster/AGENT_COORD.md",
]

commit_message = """TASK_019: Add extended tests (C1-C4), .gitignore, fixtures, verify scipy

- tests/conftest.py: shared pytest fixtures (cv/lsv/eis DataFrames, mock_run_dir)
- tests/test_tools_extended.py: extended tests for echem_reader, log_analysis,
  registry, report_generator, file_watcher, visualization (~35 tests)
- tests/test_config.py: TOML loading edge cases, missing files, env overrides,
  singleton behaviour, _expand_path and _load_toml helpers (~20 tests)
- AutoHySeeker/.gitignore: project-level gitignore for Python/env artifacts
- pyproject.toml: add jinja2>=3.1 and matplotlib>=3.8 (used in src but missing);
  fix duplicate [project.optional-dependencies] section
- VALIDATION.md: mark C1/C2/C3/C4/C6 as done
- AGENT_COORD.md: mark TASK_019 done, add 4 experience entries

C4 verification: echem_analysis.py uses only numpy/pandas; scipy NOT required.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"""

try:
    print("Step 1: Adding files...")
    add_cmd = ["git", "-C", work_dir, "add"] + files_to_add
    result = subprocess.run(add_cmd, capture_output=True, text=True, check=True)
    print("Files added successfully")

    print("\nStep 2: Creating commit...")
    commit_cmd = ["git", "-C", work_dir, "commit", "-m", commit_message]
    result = subprocess.run(commit_cmd, capture_output=True, text=True, check=True)
    print("Commit created successfully")
    print(result.stdout)

    print("\nStep 3: Verifying...")
    log_cmd = ["git", "-C", work_dir, "log", "--oneline", "-3"]
    result = subprocess.run(log_cmd, capture_output=True, text=True)
    print(result.stdout)

except subprocess.CalledProcessError as e:
    print(f"ERROR: {e}")
    print(f"stdout: {e.stdout}")
    print(f"stderr: {e.stderr}")
    sys.exit(1)
