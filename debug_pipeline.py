"""Debug the run_pipeline staging step."""
import os, sys, shutil, traceback
from pathlib import Path

sys.path.insert(0, r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking\third_party\agfs\agfs-sdk\python')
sys.path.insert(0, r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\OpenViking')

import time
from openviking.pipeline.mineru_import import (
    collect_pipeline_inputs, resolve_pdf_inputs, stage_mineru_directory,
    DEFAULT_STAGE_ROOT, _make_unique_dir, is_mineru_output_dir
)

input_paths = [Path(r'D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output')]
collected_inputs = collect_pipeline_inputs(input_paths, recursive=True)
print(f"Collected {len(collected_inputs)} inputs")

# Show first few
for i, item in enumerate(collected_inputs[:5]):
    print(f"  {i}: {item.name} is_dir={item.is_dir()}")

mineru_inputs = [path for path in collected_inputs if path.is_dir() and is_mineru_output_dir(path)]
print(f"\nMinerU dirs: {len(mineru_inputs)}")
for i, d in enumerate(mineru_inputs[:3]):
    print(f"  {i}: {d.name}")

# Test staging the first one
batch_name = time.strftime("mineru_batch_%Y%m%d_%H%M%S")
DEFAULT_STAGE_ROOT.mkdir(parents=True, exist_ok=True)
stage_dir = _make_unique_dir(DEFAULT_STAGE_ROOT, batch_name)
stage_dir.mkdir(parents=True, exist_ok=True)
print(f"\nStage dir: {stage_dir}")
print(f"Stage dir exists: {stage_dir.exists()}")

if mineru_inputs:
    first = mineru_inputs[0]
    print(f"\nTesting stage of: {first.name}")
    try:
        item = stage_mineru_directory(first, stage_root=stage_dir)
        print(f"OK: {item.staged_dir}")
    except Exception as e:
        traceback.print_exc()
        print(f"FAILED: {e}")

shutil.rmtree(stage_dir, ignore_errors=True)
