import subprocess, sys, os
os.chdir(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-c1-c4')

# Check status
r = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
print('STATUS:', r.stdout)

# Stage all changes
r = subprocess.run(['git', 'add', 'AutoHySeeker/'], capture_output=True, text=True)
print('ADD:', r.returncode, r.stderr)

# Check what's staged
r = subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, text=True)
print('STAGED:', r.stdout)

# Commit
msg = """TASK_019: Add extended tests (C1-C4), .gitignore, fixtures, verify scipy

- tests/conftest.py: shared pytest fixtures (cv/lsv/eis DataFrames, mock_run_dir)
- tests/test_tools_extended.py: extended tests for echem_reader, log_analysis,
  registry, report_generator, file_watcher, visualization
- tests/test_config.py: TOML loading edge cases, missing files, env overrides,
  singleton behaviour, _expand_path helper tests
- AutoHySeeker/.gitignore: project-level gitignore for Python artifacts
- pyproject.toml: add jinja2>=3.1 and matplotlib>=3.8 (used in src but missing);
  fix duplicate [project.optional-dependencies] section
- VALIDATION.md: mark C1/C2/C3/C4/C6 as done
- AGENT_COORD.md: mark TASK_019 done, add 4 experience entries

C4 (scipy): echem_analysis.py uses only numpy/pandas; scipy NOT required.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"""

r = subprocess.run(['git', 'commit', '-m', msg], capture_output=True, text=True)
print('COMMIT:', r.returncode)
print(r.stdout)
print(r.stderr)
