#!/usr/bin/env python
"""Comprehensive syntax check for all Python files."""

import os
import py_compile
import sys
from pathlib import Path

def check_python_files(directory):
    """检查目录中的所有 Python 文件语法。"""
    errors = []
    success_count = 0
    
    for root, dirs, files in os.walk(directory):
        # 跳过特定目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.pytest_cache', 'venv', 'env']]
        
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                filepath = os.path.join(root, file)
                try:
                    py_compile.compile(filepath, doraise=True)
                    success_count += 1
                    print(f"✓ {filepath}")
                except py_compile.PyCompileError as e:
                    errors.append((filepath, str(e)))
                    print(f"✗ {filepath}: {e}")
    
    return success_count, errors

# 检查 src 和 run_ui.py
base_dir = Path(__file__).parent
src_dir = base_dir / 'src'

print("="*60)
print("检查 src 目录中的 Python 文件...")
print("="*60)
success, errors = check_python_files(str(src_dir))

print("\n" + "="*60)
print(f"检查 run_ui.py...")
print("="*60)
try:
    py_compile.compile(str(base_dir / 'run_ui.py'), doraise=True)
    print(f"✓ {base_dir / 'run_ui.py'}")
    success += 1
except py_compile.PyCompileError as e:
    errors.append((str(base_dir / 'run_ui.py'), str(e)))
    print(f"✗ {base_dir / 'run_ui.py'}: {e}")

print("\n" + "="*60)
print(f"结果: {success} 个文件通过, {len(errors)} 个错误")
print("="*60)

if errors:
    print("\n错误详情:")
    for filepath, error in errors:
        print(f"\n{filepath}:")
        print(f"  {error}")
    sys.exit(1)
else:
    print("\n✅ 所有文件语法检查通过！")
    sys.exit(0)
