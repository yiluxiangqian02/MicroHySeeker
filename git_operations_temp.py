#!/usr/bin/env python3
import subprocess
import os
import sys

# Change to the working directory
os.chdir(r"d:\AI4S\MicroHySeeker\MicroHySeeker")

print("=" * 50)
print("STEP 1: Git Status")
print("=" * 50)
result = subprocess.run(["git", "--no-pager", "status"], capture_output=False, text=True)

print("\n" + "=" * 50)
print("STEP 2: Staging files")
print("=" * 50)

files_to_stage = [
    "MicroHySeeker/src/echem_sdl/utils/constants.py",
    "MicroHySeeker/src/echem_sdl/hardware/pump_manager.py",
    "MicroHySeeker/src/echem_sdl/hardware/rs485_protocol.py",
    "MicroHySeeker/src/echem_sdl/hardware/flusher.py",
    "MicroHySeeker/src/echem_sdl/hardware/diluter.py",
    "MicroHySeeker/src/api/routes/device.py",
    "MicroHySeeker/src/api/bridge.py",
    "MicroHySeeker/src/api/server.py",
    "MicroHySeeker/src/services/rs485_wrapper.py",
    "AutoHySeeker/src/tools/experiment_ctrl.py"
]

for file in files_to_stage:
    print(f"Staging: {file}")
    result = subprocess.run(["git", "add", file], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error: {result.stderr}")
    else:
        print(f"  ✓ Staged")

print("\n" + "=" * 50)
print("STEP 3: Committing")
print("=" * 50)

commit_message = """feat: 300RPM safety enforcement + device-level REST API for agents

Safety (CRITICAL):
- Add SAFETY_MAX_RPM=300 to constants.py as global safety limit
- Enforce 300 RPM limit in pump_manager.py (set_speed, start_pump,
  dispense_by_encoder, move_position_rel, move_position_abs)
- Enforce limit in rs485_protocol.py (encode_speed, build_position_*_frame)
- Add __post_init__ validation on FlusherPumpConfig and DiluterConfig
- Add runtime RPM check in Diluter.infuse()
- Multi-layer defense: config → manager → protocol (no bypass possible)

Device API (for AutoHySeeker agents):
- New /api/device/* endpoints: pump start/stop/status, flusher control,
  diluter control, emergency-stop, connection management, port listing
- Bridge methods: device_pump_start/stop, device_flusher_start/stop,
  device_diluter_start/stop, device_emergency_stop, etc.
- AutoHySeeker client functions in experiment_ctrl.py
- RPM passthrough for diluter start_dilution

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"""

result = subprocess.run(["git", "commit", "-m", commit_message], capture_output=False, text=True)

print("\n" + "=" * 50)
print("STEP 4: Final commit statistics")
print("=" * 50)
result = subprocess.run(["git", "--no-pager", "log", "-1", "--stat"], capture_output=False, text=True)
