# Task TASK_006 — Phase 4: 实现 C1 ContextualizeExperiment + C2 SuggestNextExperiment Skills，完善 Supervisor Graph，API 路由整合

> **分配 Agent**: copilot
> **工作分支**: `feat/phase4-context-supervisor`
> **Worktree**: `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_phase4-context-supervisor`
> **创建时间**: 2026-03-05T15:37:39.480141+00:00

## Agent 规则

- 按次数计费，请尽量在一次会话中完成更多工作
- 默认使用 claude-sonnet-4.6，连续2次失败切 claude-opus-4.6
- 适合复杂算法、大重构、跨文件任务

## 安全规则（必须遵守）

以下路径**禁止删除或破坏性修改**：
- `MicroHySeeker/src/` — 核心源码
- `MicroHySeeker/config/system.json` — 系统配置
- `data/` — 实验数据（只读）
- `logs/` — 日志（只读）
- `AutoHySeeker/OpenViking/` — 知识库
- `.git/` — git 历史

操作原则：优先在 `feat/phase4-context-supervisor` 分支上操作，不直接修改 main/autohyseeker。

## 协作文件

完成任务后，请更新 `AutoHySeeker/agent_cluster/AGENT_COORD.md`：
- 将任务状态改为 `done`
- 在"经验库"中记录有效做法

## 任务描述

Phase 4: 实现 C1 ContextualizeExperiment + C2 SuggestNextExperiment Skills，完善 Supervisor Graph，API 路由整合



## 完成标准

- [ ] 代码已在 `feat/phase4-context-supervisor` 分支提交
- [ ] 相关测试通过（如有）
- [ ] 已更新 AGENT_COORD.md
- [ ] 如有 UI 变化，附截图描述

---
*此文件由 dispatch.py 自动生成 | 如需指令更新，查看同目录 TASK_006_steer.md*
