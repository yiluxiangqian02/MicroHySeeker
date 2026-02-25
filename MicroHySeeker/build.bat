@echo off
chcp 65001 >nul 2>&1
title MicroHySeeker 打包

cd /d "%~dp0"

echo === MicroHySeeker 打包工具 ===
echo.

REM 检查 .venv
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到 .venv 环境，请先运行 start.bat 初始化
    pause
    exit /b 1
)

REM 确保 pyinstaller 已安装
.venv\Scripts\python.exe -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [信息] 正在安装 PyInstaller...
    set UV_INDEX_URL=https://mirrors.zju.edu.cn/pypi/web/simple
    uv pip install pyinstaller --python .venv\Scripts\python.exe
)

echo [信息] 开始打包...
.venv\Scripts\pyinstaller.exe MicroHySeeker.spec --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ✅ 打包完成！产物位于: dist\MicroHySeeker\MicroHySeeker.exe
) else (
    echo.
    echo ❌ 打包失败，请检查错误信息
)

pause
