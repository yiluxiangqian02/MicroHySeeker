"""Git commit script for TASK_017 — feat/fix-b3-b7."""
import subprocess
import os

REPO = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-b3-b7'
os.chdir(REPO)

files = [
    'AutoHySeeker/tests/test_optimization.py',
    'AutoHySeeker/tests/test_experiment_execution.py',
    'AutoHySeeker/tests/test_d3_diagnostics.py',
    'AutoHySeeker/tests/test_llm_client.py',
    'AutoHySeeker/docs/dual_config_system.md',
    'AutoHySeeker/agent_cluster/AGENT_COORD.md',
]

# Add files
r = subprocess.run(['git', 'add'] + files, capture_output=True, text=True)
print("=== GIT ADD ===")
print(r.stdout)
print(r.stderr)
print("Return code:", r.returncode)

# Status check
r = subprocess.run(['git', '--no-pager', 'status', '--short'], capture_output=True, text=True)
print("\n=== STATUS ===")
print(r.stdout)

# Commit
msg = (
    "test(b3-b7): add tests for optimization, experiment_execution, D3, llm_client; add dual config docs\n\n"
    "- tests/test_optimization.py: ParameterDefinition, ParameterSpace, BayesianOptimizer,\n"
    "  MultiObjectiveBayesianOptimizer, PeakCurrentObjective, SignalToNoiseObjective,\n"
    "  MultiObjectiveFunction — 40 tests\n"
    "- tests/test_experiment_execution.py: SmartSchedulerSkill, ExecutionMonitorSkill — 21 tests\n"
    "- tests/test_d3_diagnostics.py: InteractiveTroubleshootingSkill (all 4 symptoms) — 12 tests\n"
    "- tests/test_llm_client.py: _extract_text, get_client, chat_completion retry/fallback — 12 tests\n"
    "- docs/dual_config_system.md: documents src/common/config.py vs src/configs.py dual system\n\n"
    "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
)
r = subprocess.run(['git', 'commit', '-m', msg], capture_output=True, text=True)
print("\n=== GIT COMMIT ===")
print(r.stdout)
print(r.stderr)
print("Return code:", r.returncode)

# Verify
r = subprocess.run(['git', '--no-pager', 'log', '--oneline', '-3'], capture_output=True, text=True)
print("\n=== LOG ===")
print(r.stdout)
