@echo off
cd /d "D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_fix-b3-b7"

git add AutoHySeeker/tests/test_optimization.py AutoHySeeker/tests/test_experiment_execution.py AutoHySeeker/tests/test_d3_diagnostics.py AutoHySeeker/tests/test_llm_client.py AutoHySeeker/docs/dual_config_system.md AutoHySeeker/agent_cluster/AGENT_COORD.md

git commit -m "test(b3-b7): add tests for optimization, experiment_execution, D3, llm_client; add dual config docs

- tests/test_optimization.py: ParameterDefinition, ParameterSpace, BayesianOptimizer,
  MultiObjectiveBayesianOptimizer, PeakCurrentObjective, SignalToNoiseObjective,
  MultiObjectiveFunction — 40 tests
- tests/test_experiment_execution.py: SmartSchedulerSkill (dependency ordering,
  priority, equipment conflict, circular deps), ExecutionMonitorSkill (quality
  report, diagnostics generation) — 21 tests
- tests/test_d3_diagnostics.py: InteractiveTroubleshootingSkill — all 4 symptoms,
  schema, error paths — 12 tests
- tests/test_llm_client.py: _extract_text, get_client singleton, chat_completion
  retry/fallback logic with mocked AsyncOpenAI — 12 tests
- docs/dual_config_system.md: explains src/common/config.py (env-based) vs
  src/configs.py (TOML-based), interaction, priority, testing tips

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
