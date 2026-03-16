#!/usr/bin/env python3
"""
Git operations script for committing safety enforcement and device API changes.
"""
import subprocess
import os
import sys

def run_command(cmd, description=""):
    """Run a git command and return output."""
    if description:
        print(f"\n{'='*60}")
        print(f"{description}")
        print(f"{'='*60}")
    print(f"Running: {cmd}\n")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    os.chdir("d:\\AI4S\\MicroHySeeker\\MicroHySeeker")
    
    # Step 1: Check git status
    run_command(
        "git --no-pager status",
        "STEP 1: Check git status"
    )
    
    # Step 2: Stage all specified files
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
        "AutoHySeeker/src/tools/experiment_ctrl.py",
    ]
    
    print("\n" + "="*60)
    print("STEP 2: Stage specified files")
    print("="*60)
    
    for file in files_to_stage:
        print(f"\nStaging: {file}")
        run_command(f"git add \"{file}\"")
    
    # Verify what was staged
    print("\n" + "="*60)
    print("STEP 3: Verify staged files")
    print("="*60)
    run_command("git --no-pager diff --cached --name-only")
    
    # Step 4: Commit with the specified message
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

    print("\n" + "="*60)
    print("STEP 4: Commit with message")
    print("="*60)
    
    # Create a temporary file with the commit message to avoid shell escaping issues
    msg_file = "commit_msg.txt"
    with open(msg_file, 'w', encoding='utf-8') as f:
        f.write(commit_message)
    
    run_command(
        f"git commit -F {msg_file}",
        "Committing changes"
    )
    
    # Clean up
    if os.path.exists(msg_file):
        os.remove(msg_file)
    
    # Show the commit
    print("\n" + "="*60)
    print("STEP 5: Show commit details")
    print("="*60)
    run_command("git --no-pager show --stat")
    
    print("\n" + "="*60)
    print("✓ Git operations completed successfully!")
    print("="*60)

if __name__ == "__main__":
    main()
