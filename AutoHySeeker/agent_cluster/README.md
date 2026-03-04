# AutoHySeeker Agent 集群 — 使用指南

## 快速开始

### 1. 创建新任务（自动启动 Agent）

```powershell
# 方式一：使用 cluster.ps1
.\AutoHySeeker\agent_cluster\cluster.ps1 create copilot "实现贝叶斯优化模块" feat/bayes-opt

# 方式二：直接调用 dispatch.py
python AutoHySeeker\agent_cluster\dispatch.py create --agent codex --desc "修复 CV 数据读取 bug"
```

创建任务后会自动：
1. 创建 git worktree（隔离工作区）
2. 生成专属 prompt 文件（`prompts/TASK_xxx_prompt.md`）
3. 后台启动 Agent 进程（记录 PID）

### 2. 查看任务状态

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 status
```

### 3. 向运行中的 Agent 发送指令

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 steer TASK_001 "先做 API 层，别管 UI"
```

### 4. 标记任务完成

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 done TASK_001
```

### 5. 自动 Code Review

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 review TASK_001
# 或直接指定分支
python AutoHySeeker\agent_cluster\reviewer.py --branch feat/bayes-opt
```

自动流程：找到对应 PR → 获取 diff → 用 codex 做 review → 发布 PR comment

### 6. 智能重试失败任务

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 retry TASK_001
# 或直接调用
python AutoHySeeker\agent_cluster\retry.py --task-id TASK_001
```

自动流程：读取失败原因 → 生成增强 prompt（附加失败分析）→ 重启 Agent（最多 3 次）

### 7. 查看监控日志

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 logs           # 最新日志
.\AutoHySeeker\agent_cluster\cluster.ps1 logs TASK_001  # 过滤特定任务
```

### 8. 杀死 Agent 进程

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 kill TASK_001
```

### 9. 启动后台监控

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 monitor       # 循环监控（每5分钟）
.\AutoHySeeker\agent_cluster\cluster.ps1 monitor-once  # 只运行一次
```

---

## 所有命令速查

| 命令 | 说明 |
|------|------|
| `status` | 查看所有活跃任务 |
| `create <agent> <desc> [branch]` | 创建任务并自动启动 Agent |
| `done <task-id>` | 标记任务完成 |
| `fail <task-id> [reason]` | 标记任务失败 |
| `steer <task-id> <msg>` | 向 Agent 发送临时指令 |
| `monitor` | 启动循环监控（每5分钟） |
| `monitor-once` | 运行一次监控检查 |
| `review <task-id>` | 对 PR 做自动 Code Review |
| `retry <task-id>` | 智能重试失败的任务 |
| `logs [task-id]` | 查看监控日志 |
| `kill <task-id>` | 杀死 Agent 进程 |
| `open <task-id>` | 打开任务 prompt 文件 |

---

## Agent 分工策略

| Agent | 擅长 | 计费 | 典型任务 |
|-------|------|------|----------|
| **Copilot** | 复杂算法、大重构、跨文件分析 | 按次数 | 贝叶斯优化、LangGraph 节点、数据分析算法 |
| **Codex** | 小型修复、局部调试、单文件改动 | 按 token | bug fix、小功能、配置文件修改 |
| **Claude Code** | 后端逻辑、硬件驱动、测试编写 | 按 token | 硬件适配层、API 接口、测试 |

**成本优化原则**：
- Copilot 按次数计费 → 每次任务尽量多做
- Codex/Claude Code 按 token → 保持 prompt 简洁
- 同一问题 Copilot 连续 2 次失败 → 自动建议切 claude-opus-4.6

---

## 工作流

```
1. Pi 创建任务 (dispatch.py create)
   ↓
2. 自动创建 worktree + 生成 prompt + 启动 Agent 进程（记录 PID）
   ↓
3. Agent 在 worktree 中工作
   ↓
4. monitor.py 每5分钟检查：进程存活、PR状态、CI状态、安全违规
   ↓
5a. Agent 完成 → 创建 PR → CI 通过 → 自动标记 review
   ↓
5b. Agent 崩溃 → 自动标记 failed → 用 retry.py 重试（最多3次）
   ↓
6. Pi review PR → cluster.ps1 review TASK_xxx → 自动 code review
   ↓
7. 合并 PR → cluster.ps1 done TASK_xxx → 自动清理 worktree
```

---

## 文件结构

```
agent_cluster/
├── dispatch.py       # 任务创建/状态/完成/失败/转向
├── monitor.py        # 监控：进程/worktree/PR/CI/安全检查
├── reviewer.py       # 自动 Code Review（通过 gh + codex）
├── retry.py          # 智能重试（增强 prompt + 重启 Agent）
├── cluster.ps1       # PowerShell 快捷入口
├── AGENT_COORD.md    # Agent 协调文件（共享状态）
├── tasks/
│   └── tasks.json    # 任务状态存储
├── prompts/
│   ├── TASK_xxx_prompt.md        # 原始 prompt
│   ├── TASK_xxx_steer.md         # 临时指令追加
│   └── TASK_xxx_retry_prompt.md  # 增强重试 prompt
├── logs/
│   └── monitor_YYYYMMDD.log      # 每日监控日志
└── worktrees/        # git worktree 工作区
```

---

## 安全保护

以下路径**禁止删除或破坏性修改**：
- `MicroHySeeker/src/` — 核心源码
- `MicroHySeeker/config/system.json` — 系统配置
- `data/` — 实验数据（只读）
- `logs/` — 日志（只读）
- `AutoHySeeker/OpenViking/` — 知识库
- `.git/` — git 历史

monitor.py 每 5 分钟检查一次，发现违规会记录到 `logs/monitor_YYYYMMDD.log`。

---

## 协作文件

所有 Agent 共享 `AGENT_COORD.md`：
- 当前活跃任务列表
- 已完成任务历史
- 已知问题 / 阻塞项
- 经验库（成功模式）

Agent 完成任务后需更新此文件。

---

*最后更新：Pi @ 2026-03-04*
