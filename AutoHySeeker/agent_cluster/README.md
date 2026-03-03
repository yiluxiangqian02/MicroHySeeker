# AutoHySeeker Agent 集群 — 使用指南

## 快速开始

### 1. 创建新任务

```powershell
# 方式一：使用 cluster.ps1
.\AutoHySeeker\agent_cluster\cluster.ps1 create copilot "实现贝叶斯优化模块" feat/bayes-opt

# 方式二：直接调用 dispatch.py
python AutoHySeeker\agent_cluster\dispatch.py create --agent codex --desc "修复 CV 数据读取 bug"
```

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

### 5. 启动后台监控

```powershell
.\AutoHySeeker\agent_cluster\cluster.ps1 monitor
```

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
2. 生成 worktree + prompt 文件
   ↓
3. Agent 在 worktree 中工作
   ↓
4. 完成后提交到分支
   ↓
5. Pi 标记完成 (dispatch.py done)
   ↓
6. 自动清理 worktree
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

*最后更新：Pi @ 2026-03-03*
