#!/usr/bin/env python
import py_compile
import sys
from pathlib import Path

files = [
    "src/agents/exp_executor.py",
    "src/agents/__init__.py",
    "src/graph/nodes.py",
    "src/graph/orchestrator.py",
    "src/common/llm_client.py",
    "tests/test_executor_agent.py",
    "tests/test_orchestrator_agent.py",
]

passed = 0
failed = 0
errors = []

print("Verifying Python syntax...")
print()

for file in files:
    try:
        py_compile.compile(file, doraise=True)
        print(f"[PASS] {file}")
        passed += 1
    except py_compile.PyCompileError as e:
        print(f"[FAIL] {file}")
        errors.append(f"{file}: {str(e)}")
        failed += 1

print()
print(f"Results: {passed} passed, {failed} failed")

if errors:
    print("\nErrors:")
    for error in errors:
        print(f"  {error}")
    sys.exit(1)

sys.exit(0)
