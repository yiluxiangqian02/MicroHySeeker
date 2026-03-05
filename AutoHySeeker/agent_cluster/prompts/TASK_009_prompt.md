# Task TASK_009 — Phase 4: 实现 C1 ContextualizeExperiment Skill（从知识库检索相关文献和实验记录），更新 PROGRESS.md

> **分配 Agent**: codex
> **工作分支**: `feat/phase4-c1`
> **Worktree**: `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_phase4-c1`
> **创建时间**: 2026-03-05T16:25:07.063929+00:00

## Agent 规则

- 按 token 计费，保持 prompt 简洁
- 适合小型修复、单文件改动、快速 debug

## 安全规则（必须遵守）

以下路径**禁止删除或破坏性修改**：
- `MicroHySeeker/src/` — 核心源码
- `MicroHySeeker/config/system.json` — 系统配置
- `data/` — 实验数据（只读）
- `logs/` — 日志（只读）
- `AutoHySeeker/OpenViking/` — 知识库
- `.git/` — git 历史

操作原则：优先在 `feat/phase4-c1` 分支上操作，不直接修改 main/autohyseeker。

## 协作文件

完成任务后，请更新 `AutoHySeeker/agent_cluster/AGENT_COORD.md`：
- 将任务状态改为 `done`
- 在"经验库"中记录有效做法

## 任务描述

Phase 4: 实现 C1 ContextualizeExperiment Skill（从知识库检索相关文献和实验记录），更新 PROGRESS.md



## 完成标准

- [ ] 代码已在 `feat/phase4-c1` 分支提交
- [ ] 相关测试通过（如有）
- [ ] 已更新 AGENT_COORD.md
- [ ] 如有 UI 变化，附截图描述

---
*此文件由 dispatch.py 自动生成 | 如需指令更新，查看同目录 TASK_009_steer.md*
