#!/usr/bin/env python3
import os
import sys

# Create the directory
target_dir = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\frontend\src\components\dashboard'
components_dir = r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\frontend\src\components'

try:
    os.makedirs(target_dir, exist_ok=True)
    print(f"✓ Directory created successfully: {target_dir}")
    
    # List the contents of the components directory
    print(f"\nContents of {components_dir}:")
    if os.path.exists(components_dir):
        items = os.listdir(components_dir)
        for item in items:
            full_path = os.path.join(components_dir, item)
            item_type = "DIR " if os.path.isdir(full_path) else "FILE"
            print(f"  {item_type}: {item}")
    else:
        print(f"  Error: {components_dir} does not exist")
        
except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    sys.exit(1)
