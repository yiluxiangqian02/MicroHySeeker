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
    'PROGRESS.md',
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
commit_msg = '''feat(phase4-c2): implement C2 SuggestNextExperiment, extend supervisor graph, add /context API

- C2: SuggestNextExperimentSkill (LLM-free rule-based next-experiment recommendation)
- skills/__init__.py: export SuggestNextExperimentSkill + singleton
- Supervisor graph: contextualize/suggest nodes, C1->C2 state["context"]["context_data"] flow
- API: POST /context/invoke, /context/contextualize, /context/suggest-next
- Tests: tests/test_phase4.py (C1/C2/supervisor graph/context API, 30+ cases)
- PROGRESS.md: Phase 4 C2 status updated
- AGENT_COORD.md: TASK_010 marked done

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
