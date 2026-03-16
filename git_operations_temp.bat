@echo off
cd /d "d:\AI4S\MicroHySeeker\MicroHySeeker"

echo ===== STEP 1: Git Status =====
git --no-pager status

echo.
echo ===== STEP 2: Staging files =====
git add "MicroHySeeker/src/echem_sdl/utils/constants.py"
git add "MicroHySeeker/src/echem_sdl/hardware/pump_manager.py"
git add "MicroHySeeker/src/echem_sdl/hardware/rs485_protocol.py"
git add "MicroHySeeker/src/echem_sdl/hardware/flusher.py"
git add "MicroHySeeker/src/echem_sdl/hardware/diluter.py"
git add "MicroHySeeker/src/api/routes/device.py"
git add "MicroHySeeker/src/api/bridge.py"
git add "MicroHySeeker/src/api/server.py"
git add "MicroHySeeker/src/services/rs485_wrapper.py"
git add "AutoHySeeker/src/tools/experiment_ctrl.py"

echo Staged files successfully.

echo.
echo ===== STEP 3: Committing =====
git commit -m "feat: 300RPM safety enforcement + device-level REST API for agents

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

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

echo.
echo ===== STEP 4: Final commit statistics =====
git --no-pager log -1 --stat
