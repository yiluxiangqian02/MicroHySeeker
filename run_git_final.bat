@echo off
cd /d d:\AI4S\MicroHySeeker\MicroHySeeker

echo.
echo ============================================================
echo STEP 1: Check git status
echo ============================================================
git --no-pager status

echo.
echo ============================================================
echo STEP 2: Stage specified files
echo ============================================================

git add "MicroHySeeker/src/echem_sdl/utils/constants.py"
echo Added: MicroHySeeker/src/echem_sdl/utils/constants.py

git add "MicroHySeeker/src/echem_sdl/hardware/pump_manager.py"
echo Added: MicroHySeeker/src/echem_sdl/hardware/pump_manager.py

git add "MicroHySeeker/src/echem_sdl/hardware/rs485_protocol.py"
echo Added: MicroHySeeker/src/echem_sdl/hardware/rs485_protocol.py

git add "MicroHySeeker/src/echem_sdl/hardware/flusher.py"
echo Added: MicroHySeeker/src/echem_sdl/hardware/flusher.py

git add "MicroHySeeker/src/echem_sdl/hardware/diluter.py"
echo Added: MicroHySeeker/src/echem_sdl/hardware/diluter.py

git add "MicroHySeeker/src/api/routes/device.py"
echo Added: MicroHySeeker/src/api/routes/device.py

git add "MicroHySeeker/src/api/bridge.py"
echo Added: MicroHySeeker/src/api/bridge.py

git add "MicroHySeeker/src/api/server.py"
echo Added: MicroHySeeker/src/api/server.py

git add "MicroHySeeker/src/services/rs485_wrapper.py"
echo Added: MicroHySeeker/src/services/rs485_wrapper.py

git add "AutoHySeeker/src/tools/experiment_ctrl.py"
echo Added: AutoHySeeker/src/tools/experiment_ctrl.py

echo.
echo ============================================================
echo STEP 3: Verify staged files
echo ============================================================
git --no-pager diff --cached --name-only

echo.
echo ============================================================
echo STEP 4: Commit with message
echo ============================================================
git commit -F commit_msg.txt

echo.
echo ============================================================
echo STEP 5: Show commit details
echo ============================================================
git --no-pager show --stat

echo.
echo ============================================================
echo Git operations completed successfully!
echo ============================================================
pause
