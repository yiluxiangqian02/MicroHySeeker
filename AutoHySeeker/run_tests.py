#!/usr/bin/env python
import subprocess
import sys

# Change to working directory
import os
os.chdir(r"D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker")

# Install pytest-asyncio
print("=" * 80)
print("INSTALLING pytest-asyncio")
print("=" * 80)
result1 = subprocess.run([sys.executable, "-m", "pip", "install", "pytest-asyncio"], 
                         capture_output=False, text=True)

print("\n" + "=" * 80)
print("RUNNING INTEGRATION TESTS")
print("=" * 80)
result2 = subprocess.run([sys.executable, "-m", "pytest", 
                         "tests/integration/test_e2e.py", "-v", "--tb=short"],
                        capture_output=False, text=True)

sys.exit(result2.returncode)
