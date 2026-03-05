#!/usr/bin/env python
"""Git commands execution script"""
import subprocess
import os

os.chdir('D:\\AI4S\\MicroHySeeker\\MicroHySeeker\\AutoHySeeker')

# Stage files
files_to_stage = [
    'src/skills/contextualize_experiment.py',
    'src/skills/suggest_next_experiment.py',
    'src/skills/__init__.py',
    'src/graph/supervisor_graph.py',
    'src/api/routes/context.py',
    'src/api/main.py',
    'tests/test_phase4.py',
    '../agent_cluster/AGENT_COORD.md'
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
commit_msg = '''feat(phase4): implement C1/C2 skills, extend supervisor graph, add /context API

- C1: ContextualizeExperimentSkill (src/skills/contextualize_experiment.py)
- C2: SuggestNextExperimentSkill (src/skills/suggest_next_experiment.py)
- Supervisor graph: add contextualize/suggest nodes, fix deprecated set_conditional_entry_point
- API: POST /context/invoke, /context/contextualize, /context/suggest-next
- Tests: tests/test_phase4.py (42 test cases)

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
