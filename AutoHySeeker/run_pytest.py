#!/usr/bin/env python
"""Finish script for Backend Tasks 7-8: run tests then send completion event."""
import subprocess
import sys

WORKDIR = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker'
PYTHON = r'C:\Users\25922\miniforge3\python.exe'

# ------------------------------------------------------------------
print("=" * 70)
print("STEP 1: Run tests/test_control_api.py")
print("=" * 70)
result = subprocess.run(
    [PYTHON, '-m', 'pytest', 'tests/test_control_api.py', '-v'],
    cwd=WORKDIR,
)
if result.returncode != 0:
    print("\n[WARN] Some tests failed — see output above.")
else:
    print("\n[OK] All tests passed.")

# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("STEP 2: Send openclaw completion event")
print("=" * 70)
event_result = subprocess.run(
    ['openclaw', 'system', 'event',
     '--text', 'Done: Backend Tasks 7-8 completed',
     '--mode', 'now'],
    cwd=WORKDIR,
)
print("openclaw exit code:", event_result.returncode)

sys.exit(result.returncode)
