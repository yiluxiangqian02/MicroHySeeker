#!/usr/bin/env python
"""Python syntax compilation checker for multiple files."""

import py_compile
import sys
from pathlib import Path

# Files to check
files_to_check = [
    r"src\echem_sdl\utils\constants.py",
    r"src\echem_sdl\hardware\pump_manager.py",
    r"src\echem_sdl\hardware\rs485_protocol.py",
    r"src\echem_sdl\hardware\flusher.py",
    r"src\echem_sdl\hardware\diluter.py",
]

results = {}
print("=" * 70)
print("Python Syntax Compilation Checks")
print("=" * 70)

for file_path in files_to_check:
    try:
        py_compile.compile(file_path, doraise=True)
        results[file_path] = "✓ PASS"
        print(f"\n✓ PASS: {file_path}")
    except py_compile.PyCompileError as e:
        results[file_path] = f"✗ FAIL: {str(e)}"
        print(f"\n✗ FAIL: {file_path}")
        print(f"Error: {e}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
passed = sum(1 for result in results.values() if "PASS" in result)
failed = sum(1 for result in results.values() if "FAIL" in result)

for file_path, result in results.items():
    print(f"{result}")

print(f"\nTotal: {passed} passed, {failed} failed")
print("=" * 70)

sys.exit(0 if failed == 0 else 1)
