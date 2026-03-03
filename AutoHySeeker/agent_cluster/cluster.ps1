# Agent 集群快速操作脚本 (PowerShell)
# 用法: .\cluster.ps1 [命令] [参数]
# 示例:
#   .\cluster.ps1 status
#   .\cluster.ps1 create copilot "实现贝叶斯优化" feat/bayes-opt
#   .\cluster.ps1 done TASK_001
#   .\cluster.ps1 steer TASK_001 "先做API层"
#   .\cluster.ps1 monitor

param(
    [string]$Command = "status",
    [string]$Arg1 = "",
    [string]$Arg2 = "",
    [string]$Arg3 = ""
)

$ClusterDir = $PSScriptRoot
$RepoRoot = (Resolve-Path "$ClusterDir\..\..").Path
$Python = "$RepoRoot\MicroHySeeker\.venv\Scripts\python.exe"

# 如果 venv 的 python 不存在，回退到系统 python
if (-not (Test-Path $Python)) {
    $Python = "python"
}

function Show-Help {
    Write-Host "AutoHySeeker Agent Cluster" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  status                          — 查看所有活跃任务"
    Write-Host "  create <agent> <desc> [branch]  — 创建新任务 (agent: copilot/codex/claude-code)"
    Write-Host "  done <task-id>                  — 标记任务完成"
    Write-Host "  fail <task-id> [reason]         — 标记任务失败"
    Write-Host "  steer <task-id> <message>       — 向 Agent 发送指令"
    Write-Host "  monitor                         — 启动后台监控"
    Write-Host "  open <task-id>                  — 打开任务 prompt 文件"
    Write-Host ""
}

switch ($Command) {
    "status" {
        & $Python "$ClusterDir\dispatch.py" status
    }
    "create" {
        if (-not $Arg1 -or -not $Arg2) {
            Write-Host "用法: cluster.ps1 create <agent> <description> [branch]" -ForegroundColor Red
            exit 1
        }
        $args_list = @("create", "--agent", $Arg1, "--desc", $Arg2)
        if ($Arg3) { $args_list += @("--branch", $Arg3) }
        & $Python "$ClusterDir\dispatch.py" @args_list
    }
    "done" {
        if (-not $Arg1) { Write-Host "用法: cluster.ps1 done <task-id>" -ForegroundColor Red; exit 1 }
        & $Python "$ClusterDir\dispatch.py" done --task-id $Arg1
    }
    "fail" {
        if (-not $Arg1) { Write-Host "用法: cluster.ps1 fail <task-id> [reason]" -ForegroundColor Red; exit 1 }
        $args_list = @("fail", "--task-id", $Arg1)
        if ($Arg2) { $args_list += @("--reason", $Arg2) }
        & $Python "$ClusterDir\dispatch.py" @args_list
    }
    "steer" {
        if (-not $Arg1 -or -not $Arg2) {
            Write-Host "用法: cluster.ps1 steer <task-id> <message>" -ForegroundColor Red; exit 1
        }
        & $Python "$ClusterDir\dispatch.py" steer --task-id $Arg1 --msg $Arg2
    }
    "monitor" {
        Write-Host "Starting monitor (Ctrl+C to stop)..." -ForegroundColor Yellow
        & $Python "$ClusterDir\monitor.py"
    }
    "open" {
        if (-not $Arg1) { Write-Host "用法: cluster.ps1 open <task-id>" -ForegroundColor Red; exit 1 }
        $prompt_file = "$ClusterDir\prompts\$Arg1_prompt.md"
        if (Test-Path $prompt_file) {
            Start-Process $prompt_file
        } else {
            Write-Host "Prompt file not found: $prompt_file" -ForegroundColor Red
        }
    }
    default {
        Show-Help
    }
}
