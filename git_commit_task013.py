#!/usr/bin/env python
"""Git commit script for TASK_013 — A3-A6 tests."""
import subprocess
import os

os.chdir('D:\\AI4S\\MicroHySeeker\\MicroHySeeker\\AutoHySeeker\\agent_cluster\\worktrees\\feat_fix-a3-a6-tests')

files_to_stage = [
    'AutoHySeeker/tests/test_orchestrator.py',
    'AutoHySeeker/tests/test_agents.py',
    'AutoHySeeker/tests/test_pipeline_e2e.py',
    'AutoHySeeker/tests/test_api_routes.py',
    'AutoHySeeker/VALIDATION.md',
    'AutoHySeeker/agent_cluster/AGENT_COORD.md',
]

print('=== STAGING FILES ===')
result = subprocess.run(['git', 'add'] + files_to_stage, capture_output=True, text=True)
print(result.stdout if result.stdout else '(no output)')
if result.stderr:
    print('STDERR:', result.stderr)
print('Return code:', result.returncode)

print('\n=== GIT STATUS ===')
result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
print(result.stdout)

print('\n=== GIT COMMIT ===')
commit_msg = '''feat(tests): add A3-A6 critical tests with mocked LLM calls

- test_orchestrator.py: route_intent/select_agent_node/format_response/run_* node tests, _FallbackGraph, full ainvoke e2e (~30 tests)
- test_agents.py: BaseAgent.build_messages/invoke, all 5 specialist agents mocked chat_completion (~30 tests)
- test_pipeline_e2e.py: A1->C1->C2 full pipeline e2e with tmp_path fixtures (~20 tests)
- test_api_routes.py: /agents/invoke, /data/experiments, /tasks/create, /tasks/{id}/status, regression smoke tests (~25 tests)
- VALIDATION.md: update test file count (6->10), function count (~139->~230), coverage (~31%->~58%), mark A3-A6 done
- AGENT_COORD.md: mark TASK_013 done, add 3 new experience entries

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>'''

result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)
print('Return code:', result.returncode)

print('\n=== GIT LOG ===')
result = subprocess.run(['git', 'log', '-2', '--oneline'], capture_output=True, text=True)
print(result.stdout)
