#!/usr/bin/env python
"""Git commit script for TASK_011 validation plan."""
import subprocess
import os

os.chdir(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_validation-plan\AutoHySeeker')

files_to_stage = [
    'VALIDATION.md',
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
commit_msg = '''feat(validation): add VALIDATION.md and test_validation.py for TASK_011

- VALIDATION.md: full feature inventory (61 items across 8 categories),
  validation test plan (26+ VAL-* tests), dependency integrity check,
  known risks, and recommended improvements
- tests/test_validation.py: 26 new validation tests covering:
  configs (CFG), common types (CMN), RAG/KB (RAG), D3 skill (SK-D3),
  C2 suggestion rules (SK-C2), Bayesian optimizer (OPT),
  LangGraph supervisor graph (GRAPH), API routes (API),
  skills __init__ completeness (SKILL-INIT)
- agent_cluster/AGENT_COORD.md: TASK_011 marked done, experience added

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>'''

result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)
print('Return code:', result.returncode)

print('\n=== GIT LOG ===')
result = subprocess.run(['git', 'log', '-1', '--oneline'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr)
