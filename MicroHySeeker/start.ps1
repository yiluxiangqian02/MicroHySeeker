# MicroHySeeker 一键启动脚本 (PowerShell)
# 直接使用项目内 .venv 环境，无需 conda

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[!] 未找到 .venv 环境，正在自动创建..." -ForegroundColor Yellow
    
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        $uvPath = "$env:USERPROFILE\.local\bin\uv.exe"
        if (Test-Path $uvPath) { $uv = $uvPath }
        else {
            Write-Host "[错误] 未安装 uv，请先运行:" -ForegroundColor Red
            Write-Host '  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
            exit 1
        }
    }
    
    & $uv venv .venv
    $env:UV_INDEX_URL = 'https://mirrors.zju.edu.cn/pypi/web/simple'
    & $uv pip install -r requirements.txt --python .venv\Scripts\python.exe
}

& .\.venv\Scripts\python.exe .\run_ui.py @args
