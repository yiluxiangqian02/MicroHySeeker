@echo off
chcp 65001 >nul 2>&1
title MicroHySeeker

REM ── 使用项目内 .venv 环境直接启动，无需 conda ──
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到 .venv 环境，正在自动创建...
    where uv >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未安装 uv，请先运行: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        pause
        exit /b 1
    )
    uv venv .venv
    set UV_INDEX_URL=https://mirrors.zju.edu.cn/pypi/web/simple
    uv pip install -r requirements.txt --python .venv\Scripts\python.exe
)

.venv\Scripts\python.exe run_ui.py %*
