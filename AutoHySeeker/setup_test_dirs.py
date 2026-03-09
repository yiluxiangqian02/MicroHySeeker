import os

# Create directories
utils_dir = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\tests\utils'
integration_dir = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\tests\integration'

os.makedirs(utils_dir, exist_ok=True)
os.makedirs(integration_dir, exist_ok=True)

# Create __init__.py files
with open(os.path.join(utils_dir, '__init__.py'), 'w') as f:
    f.write('"""Test utilities for AutoHySeeker tests."""\n')

with open(os.path.join(integration_dir, '__init__.py'), 'w') as f:
    f.write('"""Integration tests for AutoHySeeker end-to-end scenarios."""\n')

print("Directories and __init__.py files created successfully!")
