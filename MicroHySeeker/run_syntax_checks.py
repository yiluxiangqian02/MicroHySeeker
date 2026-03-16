#!/usr/bin/env python
"""Run Python syntax compilation checks on specified files."""

import py_compile
import sys

files_to_check = [
    "src/echem_sdl/utils/constants.py",
    "src/echem_sdl/hardware/pump_manager.py",
    "src/echem_sdl/hardware/rs485_protocol.py",
    "src/echem_sdl/hardware/flusher.py",
    "src/echem_sdl/hardware/diluter.py",
]

results = []
for i, filepath in enumerate(files_to_check, 1):
    try:
        py_compile.compile(filepath, doraise=True)
        results.append(f"{i}. {filepath}: PASSED")
        print(f"✓ {i}. {filepath}: PASSED")
    except py_compile.PyCompileError as e:
        results.append(f"{i}. {filepath}: FAILED\n   Error: {e}")
        print(f"✗ {i}. {filepath}: FAILED")
        print(f"   Error: {e}")

print("\n" + "="*70)
print("SUMMARY:")
print("="*70)
for result in results:
    print(result)
