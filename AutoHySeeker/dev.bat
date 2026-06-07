@echo off
title AutoHySeeker Dev Launcher
chcp 65001 >nul 2>&1

echo ============================================
echo   AutoHySeeker Development Server Launcher
echo ============================================
echo.

set "AHS_DIR=%~dp0"
set "MHS_DIR=%~dp0..\MicroHySeeker"
set "BACKEND_PORT=8200"
set "FRONTEND_PORT=5173"
set "MHS_PORT=8100"

REM --- Check AHS .venv ---
if not exist "%AHS_DIR%.venv\Scripts\python.exe" (
    echo [ERROR] AHS .venv not found. Please run: uv sync
    pause
    exit /b 1
)

REM --- Check MHS .venv (warning only, AHS auto-launches MHS) ---
if not exist "%MHS_DIR%\.venv\Scripts\python.exe" (
    echo [WARN]  MHS .venv not found at %MHS_DIR%\.venv
    echo         AHS will try to auto-launch MHS using fallback Python.
    echo.
)

REM --- Check node_modules ---
if not exist "%AHS_DIR%frontend\node_modules" (
    echo [INFO]  Installing frontend dependencies...
    cd /d "%AHS_DIR%frontend"
    call npm install
    cd /d "%AHS_DIR%"
)

REM --- Check MHS port and code version ---
netstat -ano | findstr "LISTENING" | findstr ":%MHS_PORT% " >nul 2>&1
if not errorlevel 1 (
    echo [INFO]  MHS is running on port %MHS_PORT%. Checking if code was updated...
    python -c "
import subprocess, os, sys
runner = os.path.join(os.path.dirname(os.path.abspath('%~dpf0')), '..', 'MicroHySeeker', 'src', 'engine', 'runner.py')
runner = os.path.normpath(runner)
if not os.path.exists(runner):
    sys.exit(0)
runner_mtime = os.path.getmtime(runner)
try:
    r = __import__('urllib.request', fromlist=['urlopen']).urlopen('http://127.0.0.1:8100/api/system/health', timeout=2)
    import json
    d = json.loads(r.read())
    uptime = d.get('uptime_seconds', 0)
    import time
    proc_start = time.time() - uptime
    if runner_mtime > proc_start:
        print('OUTDATED')
    else:
        print('OK')
except Exception:
    print('OK')
" 2>nul | findstr /c:"OUTDATED" >nul 2>&1
    if not errorlevel 1 (
        echo [WARN]  MHS runner.py has been updated but MHS is running old code!
        echo         Recommend: restart MHS to apply fixes.
        echo.
        choice /c YN /t 10 /d N /m "Restart MHS now? [Y=Yes, N=Skip, auto-N in 10s]"
        if errorlevel 2 (
            echo         Skipping MHS restart.
        ) else (
            echo         Stopping old MHS...
            for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%MHS_PORT% "') do (
                taskkill /PID %%p /F >nul 2>&1
            )
            echo         Starting new MHS...
            start "MHS-Server [:8100]" cmd /k "cd /d %MHS_DIR% && C:\Users\25922\miniforge3\python.exe run_server.py --port %MHS_PORT%"
            timeout /t 5 /nobreak >nul
            echo         MHS restarted with updated code.
        )
    ) else (
        echo [INFO]  MHS code is up to date.
    )
    echo.
)

REM --- Check backend port ---
set "SKIP_BACKEND=0"
netstat -ano | findstr "LISTENING" | findstr ":%BACKEND_PORT% " >nul 2>&1
if not errorlevel 1 (
    echo [WARN]  Port %BACKEND_PORT% already in use - backend may already be running.
    set "SKIP_BACKEND=1"
)

REM --- Check frontend port ---
set "SKIP_FRONTEND=0"
netstat -ano | findstr "LISTENING" | findstr ":%FRONTEND_PORT% " >nul 2>&1
if not errorlevel 1 (
    echo [WARN]  Port %FRONTEND_PORT% already in use - frontend may already be running.
    set "SKIP_FRONTEND=1"
)

echo.

REM --- Start AHS Backend ---
if "%SKIP_BACKEND%"=="0" (
    echo [1/2] Starting AHS Backend on port %BACKEND_PORT%...
    echo       MHS will auto-start on port %MHS_PORT% if not already running.
    start "AHS-Backend [:8200]" cmd /k "cd /d %AHS_DIR% && .venv\Scripts\python -m uvicorn src.api.main:app --host 0.0.0.0 --port %BACKEND_PORT%"
    echo       Waiting 5s for backend to initialize...
    timeout /t 5 /nobreak >nul
) else (
    echo [1/2] Backend already on port %BACKEND_PORT%, skipped.
)

REM --- Start AHS Frontend ---
if "%SKIP_FRONTEND%"=="0" (
    echo [2/2] Starting AHS Frontend on port %FRONTEND_PORT%...
    start "AHS-Frontend [:5173]" cmd /k "cd /d %AHS_DIR%frontend && npm run dev"
    echo       Waiting 4s for frontend to initialize...
    timeout /t 4 /nobreak >nul
) else (
    echo [2/2] Frontend already on port %FRONTEND_PORT%, skipped.
)

REM --- Open Browser ---
echo.
echo ============================================
echo   All services started!
echo ============================================
echo.
echo   AHS Frontend : http://localhost:%FRONTEND_PORT%
echo   AHS Backend  : http://localhost:%BACKEND_PORT%/docs
echo   MHS API      : http://localhost:%MHS_PORT%/docs  (auto-started by AHS)
echo.
echo   Opening browser...
start "" "http://localhost:%FRONTEND_PORT%"

echo.
echo   Backend and Frontend run in their own windows.
echo   Close those windows to stop services.
echo   Press any key to close this launcher window.
pause >nul
