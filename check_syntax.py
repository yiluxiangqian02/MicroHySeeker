#!/usr/bin/env python
import ast
import sys

files = [
    r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\src\configs.py',
    r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\src\common\types.py',
    r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\src\common\tool_registry.py',
    r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\src\skills\diagnostics\__init__.py',
    r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\src\skills\__init__.py',
]

errors = []
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            ast.parse(file.read())
        print(f, 'OK')
    except Exception as e:
        errors.append((f, str(e)))
        print(f, 'ERROR:', str(e))

if errors:
    sys.exit(1)
