@echo off
setlocal
cd /d "%~dp0"

if not exist logs mkdir logs

set "_date=%date:~0,4%%date:~5,2%%date:~8,2%"
set "_time=%time:~0,2%%time:~3,2%%time:~6,2%"
set "_time=%_time: =0%"
set "LOG_FILE=logs\run_parse_%_date%_%_time%.log"

echo [MinerU] Starting parse job...
echo [MinerU] Log file: %LOG_FILE%

..\.venv\Scripts\python.exe .\parse_pdfs.py %* > "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo [MinerU] Exit code: %EXIT_CODE%
echo [MinerU] Last 40 lines of log:
powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG_FILE%' -Tail 40"

exit /b %EXIT_CODE%
