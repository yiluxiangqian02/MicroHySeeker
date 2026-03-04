# Agent 集群快速操作脚本 (PowerShell)
# 用法: .\cluster.ps1 [命令] [参数]
# 示例:
#   .\cluster.ps1 status
#   .\cluster.ps1 create copilot "实现贝叶斯优化" feat/bayes-opt
#   .\cluster.ps1 done TASK_001
#   .\cluster.ps1 steer TASK_001 "先做API层"
#   .\cluster.ps1 monitor
#   .\cluster.ps1 review TASK_001
#   .\cluster.ps1 retry TASK_001
#   .\cluster.ps1 logs
#   .\cluster.ps1 kill TASK_001

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
    Write-Host "  monitor                         — 启动后台监控 (循环)"
    Write-Host "  monitor-once                    — 运行一次监控检查"
    Write-Host "  review <task-id>                — 对 PR 做自动 Code Review"
    Write-Host "  retry <task-id>                 — 智能重试失败的任务"
    Write-Host "  logs [task-id]                  — 查看监控日志"
    Write-Host "  kill <task-id>                  — 杀死 Agent 进程"
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
    "monitor-once" {
        & $Python "$ClusterDir\monitor.py" --once
    }
    "review" {
        if (-not $Arg1) { Write-Host "用法: cluster.ps1 review <task-id>" -ForegroundColor Red; exit 1 }
        & $Python "$ClusterDir\reviewer.py" --task-id $Arg1
    }
    "retry" {
        if (-not $Arg1) { Write-Host "用法: cluster.ps1 retry <task-id>" -ForegroundColor Red; exit 1 }
        & $Python "$ClusterDir\retry.py" --task-id $Arg1
    }
    "logs" {
        $LogsDir = "$ClusterDir\logs"
        if ($Arg1) {
            # 搜索包含 task-id 的日志行
            $logFiles = Get-ChildItem "$LogsDir\monitor_*.log" -ErrorAction SilentlyContinue | Sort-Object Name -Descending
            if ($logFiles) {
                Write-Host "=== Logs for $Arg1 ===" -ForegroundColor Cyan
                foreach ($f in $logFiles) {
                    $matches = Select-String -Path $f.FullName -Pattern $Arg1 -SimpleMatch
                    if ($matches) {
                        Write-Host "`n--- $($f.Name) ---" -ForegroundColor Yellow
                        $matches | ForEach-Object { Write-Host $_.Line }
                    }
                }
            } else {
                Write-Host "No log files found." -ForegroundColor Yellow
            }
        } else {
            # 显示最新日志文件内容
            $latest = Get-ChildItem "$LogsDir\monitor_*.log" -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
            if ($latest) {
                Write-Host "=== Latest log: $($latest.Name) ===" -ForegroundColor Cyan
                Get-Content $latest.FullName
            } else {
                Write-Host "No monitor logs found in $LogsDir" -ForegroundColor Yellow
            }
        }
    }
    "kill" {
        if (-not $Arg1) { Write-Host "用法: cluster.ps1 kill <task-id>" -ForegroundColor Red; exit 1 }
        # 从 tasks.json 读取 PID
        $tasksFile = "$ClusterDir\tasks\tasks.json"
        if (Test-Path $tasksFile) {
            $tasksData = Get-Content $tasksFile | ConvertFrom-Json
            $task = $tasksData.tasks | Where-Object { $_.id -eq $Arg1 }
            if ($task -and $task.pid) {
                $pid = $task.pid
                Write-Host "Killing PID $pid for task $Arg1..." -ForegroundColor Yellow
                try {
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    Write-Host "✅ Process $pid killed." -ForegroundColor Green
                    # 更新状态
                    & $Python "$ClusterDir\dispatch.py" fail --task-id $Arg1 --reason "Killed by user via cluster.ps1 kill"
                } catch {
                    Write-Host "❌ Failed to kill PID $pid`: $_" -ForegroundColor Red
                }
            } else {
                Write-Host "No PID found for task $Arg1 (maybe agent was started manually)." -ForegroundColor Yellow
            }
        } else {
            Write-Host "tasks.json not found." -ForegroundColor Red
        }
    }
    "open" {
        if (-not $Arg1) { Write-Host "用法: cluster.ps1 open <task-id>" -ForegroundColor Red; exit 1 }
        $prompt_file = "$ClusterDir\prompts\${Arg1}_prompt.md"
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
