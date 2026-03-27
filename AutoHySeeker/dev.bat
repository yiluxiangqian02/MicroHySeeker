@echo off
title AutoHySeeker Dev Launcher
chcp 65001 >nul 2>&1

echo ============================================
echo   AutoHySeeker Development Server Launcher
echo ============================================
echo.

REM ── Check .venv exists ──────────────────────────────────────────────────
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run: uv sync
    pause
    exit /b 1
)

REM ── Check node_modules exists ───────────────────────────────────────────
if not exist "%~dp0frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd /d "%~dp0frontend"
    call npm install
    cd /d "%~dp0"
)

echo [1/2] Starting Backend API (port 8200)...
start "AutoHySeeker-Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8200"

echo [2/2] Starting Frontend Dev Server (port 5173)...
start "AutoHySeeker-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo   Backend API : http://localhost:8200/docs
echo   Frontend    : http://localhost:5173
echo.
echo   Press any key to close this launcher window.
echo   (Backend and Frontend will keep running in their own windows)
pause >nul
