#!/usr/bin/env python
"""Git commit script for TASK_014 — Fix B1 hardcoded paths."""
import subprocess
import os

os.chdir(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-b1-paths\AutoHySeeker')

files_to_stage = [
    'configs/microhyseeker.toml',
    'src/configs.py',
    'tests/test_validation.py',
    'agent_cluster/AGENT_COORD.md',
]

print('=== STAGING FILES ===')
result = subprocess.run(['git', 'add'] + files_to_stage, capture_output=True, text=True)
print(result.stdout if result.stdout else '(no output)')
if result.stderr:
    print('STDERR:', result.stderr)
print('Return code:', result.returncode)

print('\n=== GIT STATUS ===')
result = subprocess.run(['git', 'status'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)

print('\n=== GIT COMMIT ===')
commit_msg = '''fix(config): replace hardcoded absolute paths in microhyseeker.toml

- configs/microhyseeker.toml: replace D:/AI4S/... absolute paths with
  ${VAR:-default} env var placeholders (relative defaults: ../data,
  ../config, ../logs — relative to AutoHySeeker/)
- src/configs.py: add _expand_path() helper that expands ${VAR:-default}
  / ${VAR} env syntax then resolves relative paths against _CONFIGS_DIR.parent
  (AutoHySeeker/); wire into MicroHySeekerConfig.load()
- tests/test_validation.py: add VAL-CFG-03c (paths resolved) and
  VAL-CFG-04 (_expand_path default fallback) tests
- agent_cluster/AGENT_COORD.md: TASK_014 done, new experience entry

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>'''

result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)
print('Return code:', result.returncode)

print('\n=== GIT LOG ===')
result = subprocess.run(['git', 'log', '-2', '--oneline'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)
