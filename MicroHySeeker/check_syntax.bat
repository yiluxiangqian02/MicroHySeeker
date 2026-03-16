@echo off
cd /d d:\AI4S\MicroHySeeker\MicroHySeeker\MicroHySeeker

echo Checking constants.py...
.venv\Scripts\python.exe -m py_compile src\echem_sdl\utils\constants.py
if %errorlevel% equ 0 (echo ✓ constants.py: OK) else (echo ✗ constants.py: FAILED)

echo.
echo Checking pump_manager.py...
.venv\Scripts\python.exe -m py_compile src\echem_sdl\hardware\pump_manager.py
if %errorlevel% equ 0 (echo ✓ pump_manager.py: OK) else (echo ✗ pump_manager.py: FAILED)

echo.
echo Checking rs485_protocol.py...
.venv\Scripts\python.exe -m py_compile src\echem_sdl\hardware\rs485_protocol.py
if %errorlevel% equ 0 (echo ✓ rs485_protocol.py: OK) else (echo ✗ rs485_protocol.py: FAILED)

echo.
echo Checking flusher.py...
.venv\Scripts\python.exe -m py_compile src\echem_sdl\hardware\flusher.py
if %errorlevel% equ 0 (echo ✓ flusher.py: OK) else (echo ✗ flusher.py: FAILED)

echo.
echo Checking diluter.py...
.venv\Scripts\python.exe -m py_compile src\echem_sdl\hardware\diluter.py
if %errorlevel% equ 0 (echo ✓ diluter.py: OK) else (echo ✗ diluter.py: FAILED)
