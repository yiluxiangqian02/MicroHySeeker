@echo off
setlocal enabledelayedexpansion

cd /d "d:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker"

set PYTHON=C:\Users\25922\miniforge3\envs\MicroHySeeker\python.exe
set PASSED=0
set FAILED=0

echo Verifying Python syntax...
echo.

for %%f in (
    "src/agents/exp_executor.py"
    "src/agents/__init__.py"
    "src/graph/nodes.py"
    "src/graph/orchestrator.py"
    "src/common/llm_client.py"
    "tests/test_executor_agent.py"
    "tests/test_orchestrator_agent.py"
) do (
    !PYTHON! -m py_compile %%f 2>nul
    if !errorlevel! equ 0 (
        echo [PASS] %%f
        set /a PASSED+=1
    ) else (
        echo [FAIL] %%f
        set /a FAILED+=1
    )
)

echo.
echo Results: %PASSED% passed, %FAILED% failed
if %FAILED% gtr 0 exit /b 1
exit /b 0
