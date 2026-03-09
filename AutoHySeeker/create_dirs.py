"""
AutoHySeeker Frontend Setup Script
Run: python create_dirs.py
Creates the React+TypeScript frontend project under AutoHySeeker/frontend/
"""
import os

BASE = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\frontend'

directories = [
    fr'{BASE}\src\api',
    fr'{BASE}\src\components',
    fr'{BASE}\src\pages',
    fr'{BASE}\src\hooks',
    fr'{BASE}\src\stores',
]

print('Creating directories...')
for dir_path in directories:
    os.makedirs(dir_path, exist_ok=True)
    exists = os.path.exists(dir_path)
    status = 'EXISTS' if exists else 'FAILED'
    print(f'  {status}: {dir_path}')

print('\nAll directories created successfully!')
print('Run: python create_frontend.py   to write all source files.')
