"""Debug the staging step for the problem directory."""
import os, sys, shutil, traceback
from pathlib import Path

sys.path.insert(0, r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking\third_party\agfs\agfs-sdk\python')
sys.path.insert(0, r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking')

from openviking.pipeline.mineru_import import (
    stage_mineru_directory, select_preferred_mineru_payload, _copy_path, _make_unique_dir
)

mineru_dir = Path(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\10,000-h-stable intermittent alkaline seawater electrolysis')
stage_root = Path(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking\.tmp_debug_stage')
stage_root.mkdir(parents=True, exist_ok=True)

try:
    selection = select_preferred_mineru_payload(mineru_dir)
    print(f"Selection mode: {selection['mode']}")
    print(f"Files to copy:")
    for f in selection['files']:
        print(f"  {f.name} {'(dir)' if f.is_dir() else '(file)'} -> exists:{f.exists()}")
    
    target_dir = _make_unique_dir(stage_root, mineru_dir.name)
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nTarget dir: {target_dir}")
    print(f"Target dir exists: {target_dir.exists()}")
    
    for selected in selection['files']:
        destination = target_dir / selected.name
        print(f"\nCopying {selected.name} -> {destination}")
        print(f"  source is_dir: {selected.is_dir()}")
        print(f"  destination parent exists: {destination.parent.exists()}")
        try:
            _copy_path(selected, destination)
            print(f"  OK")
        except Exception as e:
            print(f"  FAILED: {e}")
except Exception as e:
    traceback.print_exc()
finally:
    shutil.rmtree(stage_root, ignore_errors=True)
