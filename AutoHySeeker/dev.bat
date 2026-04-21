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
echo   Press any key to close this launcher.
pause >nul
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
