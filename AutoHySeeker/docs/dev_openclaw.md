# OpenClaw 配置与使用指南

> 2026-03-01 | v3.0（通用助手架构 + Skills 领域插件 + 多智能体桥接）
> 核心理念：OpenClaw = 通用 AI 助手（操作系统层），领域能力通过 Skills 插件按需加载
> 关联文档：[open_source_integration.md](open_source_integration.md) · [dev_backend.md](dev_backend.md)

---

## 目录

1. [架构总览](#一架构总览)
2. [OpenClaw 与多智能体系统的关系](#二openclaw-与多智能体系统的关系)
3. [安装与修复](#三安装与修复windows)
4. [配置详解](#四配置详解)
5. [工作区文件说明](#五工作区文件说明)
6. [Skills 系统](#六skills-系统)
7. [启动与操作](#七启动与操作)
8. [心跳主动监控](#八心跳主动监控)
9. [多渠道接入](#九多渠道接入)
10. [常见问题](#十常见问题)

---

## 一、架构总览

OpenClaw 是一个**通用 AI 助手网关**（本地运行），定位为"操作系统层"：

```
┌──────────────────────────────────────────────────┐
│          OpenClaw Gateway (通用 AI 助手)           │
│          ws://127.0.0.1:18789                     │
│                                                   │
│  用户接口:                                         │
│    WebChat  ←── 浏览器 http://127.0.0.1:18789/    │
│    Telegram ←── 手机                               │
│    CLI      ←── 终端                               │
│                                                   │
│  通用能力: 编码 · 文档 · 翻译 · 搜索 · 对话        │
│                                                   │
│  Skills（按需加载的领域插件）:                       │
│    ├── autohyseeker-dev  → 项目代码开发             │
│    ├── echem-data        → 电化学数据分析           │
│    ├── literature        → 学术文献检索             │
│    └── lab-bridge        → 多智能体系统桥接         │
│                                                   │
│  工作区: D:\AI4S\openclaw-workspace\               │
└──────────────────────────────────────────────────┘
          │                          │
          │ 简单任务直接处理           │ 复杂工作流委托
          ▼                          ▼
      用户看到结果              AutoHySeeker 多智能体
                               (LangGraph + FastAPI)
```

**设计原则**：
- **通用性优先** — OpenClaw 不绑定任何特定项目，可用于任何编码、写作、分析任务
- **领域能力插件化** — 电化学分析、文献检索等作为 Skills 按需加载（`always:false`）
- **复杂工作流委托** — 多步实验闭环、贝叶斯优化等通过 lab-bridge Skill 委托给多智能体系统
- **多渠道** — WebChat/Telegram/CLI，实验室手机远程可用
- **24/7 监控** — heartbeat 心跳模式主动监控

---

## 二、OpenClaw 与多智能体系统的关系

> ★ 这是架构设计的核心决策

### 2.1 分层设计

```
┌─────────────────────────────────────────────┐
│       OpenClaw（通用助手 · 操作系统层）        │
│  - 人机接口（WebChat / Telegram / CLI）       │
│  - 通用任务（编码 / 文档 / 搜索 / 翻译）      │
│  - Skills 插件系统                            │
│  - 无状态，每次对话独立                        │
└─────────────┬───────────────────────────────┘
              │ HTTP API（lab-bridge Skill）
              ▼
┌─────────────────────────────────────────────┐
│    AutoHySeeker 多智能体系统（领域引擎层）     │
│  - LangGraph 有状态工作流                     │
│  - C→D→C 实验闭环                             │
│  - 贝叶斯优化 / 强化学习                      │
│  - 多 Agent 协同（Planner / Executor / ...）  │
│  - FastAPI 对外暴露 REST API                  │
│  - OpenViking RAG 知识库                      │
└─────────────────────────────────────────────┘
```

### 2.2 为什么不把一切都包进 OpenClaw Skills？

| 维度 | OpenClaw Skill | 多智能体系统 |
|------|---------------|-------------|
| 状态管理 | ❌ 无状态，每次调用独立 | ✅ LangGraph checkpointer 持久状态 |
| 多 Agent 协同 | ❌ 单 Agent 单轮 | ✅ 多 Agent 协调、投票、辩论 |
| 强化学习 | ❌ 不支持训练循环 | ✅ 课题组要做的方向 |
| 长时间运行 | ❌ 受 timeout 限制 | ✅ 异步任务队列，几小时不是问题 |
| 通用性 | ✅ 可用于任何项目 | ✗ 专为电化学实验设计 |

**结论**：简单任务（看数据、写代码、查文献）→ OpenClaw。复杂工作流（多步实验、优化循环、RL 训练）→ 多智能体系统。通过 lab-bridge Skill 桥接。

### 2.3 典型使用场景

**场景 A：简单数据分析（OpenClaw 直接处理）**
```
你 → WebChat: "分析今天的 CV 数据，和昨天对比"
Agent → 读 CSV → 分析峰值 → 回复 Markdown 报告
```

**场景 B：代码开发（OpenClaw + autohyseeker-dev Skill）**
```
你 → WebChat: "实现 B2 贝叶斯优化 Skill 的单元测试"
Agent → 读文档 → 写测试代码 → 运行 pytest → 回复结果
```

**场景 C：复杂实验（OpenClaw → lab-bridge → 多智能体）**
```
你 → WebChat: "启动一轮 H₂ 浓度优化实验，50-500ppm 范围"
Agent → lab-bridge Skill → HTTP POST localhost:8100/api/v1/experiment/run
    → 多智能体系统接管：Planner→Executor→Optimizer→反馈
Agent → 收到结果 → 翻译为可读报告 → 回复用户
```

---

## 三、安装与修复（Windows）

> **已完成安装**（2026-02-28），版本 v0.1.6。此章节供未来参考。

### 3.1 标准安装步骤

**前提条件**：Node.js ≥22（当前：v22.12.0 ✓）

```powershell
# 1. 设置 npm 全局目录为用户可写路径（避免权限问题）
$env:APPDATA\npm 已在 npm config 中配置

# 2. 安装
npm install -g openclaw-cn@latest

# 3. 修复 Windows 原生模块（已修复）
# clipboard.win32-x64-msvc.node 已手动放置到:
# %APPDATA%\npm\node_modules\openclaw-cn\node_modules\@mariozechner\clipboard\
```

### 3.2 PATH 配置

将 `%APPDATA%\npm` 永久加入 PATH（以便新终端也可用）：

```powershell
# 用户级 PATH（推荐）
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$env:APPDATA\npm*") {
    [Environment]::SetEnvironmentVariable("PATH", "$env:APPDATA\npm;$userPath", "User")
    Write-Host "PATH updated. Restart terminal to take effect."
}
```

当前会话临时可用：
```powershell
$env:PATH = "$env:APPDATA\npm;$env:PATH"
```

### 3.3 已知 Windows 问题

| 问题 | 原因 | 修复 |
|------|------|------|
| EPERM mkdir error | `D:\nodejs\node_global` 没有写权限 | 改用 `%APPDATA%\npm` 目录 |
| `Cannot find module '@mariozechner/clipboard-win32-x64-msvc'` | napi-rs 预编译包缺失 | 手动下载 tgz，复制 `.node` 文件 |
| `openclaw-cn --version` 无输出 | npm bin 不在 PATH | 设置 `$env:PATH` 或永久 PATH |

> 官方建议在 WSL2 下运行 OpenClaw 以获得最佳 Windows 体验，但本地 PowerShell 方式已工作。

---

## 四、配置详解

**配置文件路径**：`C:\Users\25922\.openclaw\openclaw.json`  
**格式**：JSON5（支持注释 `//` 和尾随逗号）

### 4.1 LLM API Key 配置（★ 已完成）

> **实际工作配置**：使用 Yuan API（`api.mcxhm.cn`，国内直连无需代理），通过 `auth-profiles.json` 存储 API Key。

**API Key 存储位置**：`C:\Users\25922\.openclaw\agents\main\agent\auth-profiles.json`
```json
{
  "version": 1,
  "profiles": {
    "anthropic:default": {
      "type": "api_key",
      "provider": "anthropic",
      "key": "sk-Gz1licbjw0xzAVMd2CD0GIC0IvDVPCBSBMnrbto9sdwLwICm"
    }
  }
}
```

**Yuan API Provider 配置**（在 openclaw.json `models.providers.anthropic` 中）：
```json
{
  "baseUrl": "https://api.mcxhm.cn",
  "auth": "api-key",
  "api": "anthropic-messages"
}
```

可用模型（openclaw.json `agents.defaults.model.primary`）：
- `"anthropic/claude-haiku-4-5"` → 最快最便宜（简单问答）
- `"anthropic/claude-sonnet-4-6"` → 平衡（当前默认）✅
- `"anthropic/claude-opus-4-6"` → 最强（复杂编码任务）

API 提供商：Yuan API（`https://api.mcxhm.cn`），国内可直连

### 4.2 完整 openclaw.json（v0.1.6 实际工作配置）

> ⚠️ 以下为 2026-02-28 验证通过的实际配置，使用 Yuan API。

```json5
// C:\Users\25922\.openclaw\openclaw.json
{
  logging: { level: "info" },

  // 网关设置
  gateway: {
    port: 18789,
    mode: "local",
    auth: { token: "mhs-openclaw-a7f3d2e1b9c84056" },
    remote: { token: "mhs-openclaw-a7f3d2e1b9c84056" }
  },

  // 代理设置 (v0.1.6 格式)
  agents: {
    defaults: {
      model: { primary: "anthropic/claude-sonnet-4-6" },
      workspace: "D:/AI4S/openclaw-workspace",
      timeoutSeconds: 1800,
      heartbeat: { every: "0m" },  // "0m" = 禁用心跳
      maxConcurrent: 4,
      subagents: { maxConcurrent: 8 }
    }
  },

  // Yuan API 提供商（国内直连，无需代理）
  models: {
    providers: {
      anthropic: {
        baseUrl: "https://api.mcxhm.cn",
        auth: "api-key",
        api: "anthropic-messages",
        models: [
          { id: "claude-sonnet-4-6", name: "Claude Sonnet 4.6", input: ["text","image"], contextWindow: 200000 },
          { id: "claude-opus-4-6",   name: "Claude Opus 4.6",   input: ["text","image"], contextWindow: 200000 },
          { id: "claude-sonnet-4-5", name: "Claude Sonnet 4.5", input: ["text","image"], contextWindow: 200000 },
          { id: "claude-haiku-4-5",  name: "Claude Haiku 4.5",  input: ["text"],         contextWindow: 200000 }
        ]
      }
    }
  },

  // Auth — 指向 auth-profiles.json 中的配置
  auth: {
    profiles: {
      "anthropic:default": { provider: "anthropic", mode: "api_key" }
    }
  },

  session: {
    scope: "per-sender",
    resetTriggers: ["/new", "/reset"],
    reset: { mode: "daily", atHour: 4, idleMinutes: 1440 }
  },

  skills: {
    load: { watch: true, watchDebounceMs: 500 },
    entries: { "autohyseeker": { enabled: true } }
  }
}
```

### 4.3 Skills 配置

```json5
{
  skills: {
    load: {
      watch: true,       // 监视 SKILL.md 变化自动热重载
      watchDebounceMs: 500
    },
    entries: {
      "autohyseeker": { enabled: true },
      "echem-data":   { enabled: true },
      "literature":   { enabled: true },
      "lab-bridge":   { enabled: true }
    }
  }
}
```

### 4.4 完整配置参考

配置文件位置：`C:\Users\25922\.openclaw\openclaw.json`  
官方文档：https://clawd.org.cn/tools/skills-config.html

---

## 五、工作区文件说明

工作区位置：`D:\AI4S\openclaw-workspace\`

> 设计参考：[xiaomo-starter-kit](https://github.com/xiaomo-starter-kit)

```
openclaw-workspace\
├── SOUL.md          # ★ 核心人格：原则、边界、风格、进化
├── AGENTS.md        # ★ 工作指南：会话流程、记忆管理、能力范围
├── IDENTITY.md      # 身份定义（Pi 🤖，通用助手）
├── USER.md          # 用户信息（称呼、时区、偏好）
├── TOOLS.md         # 系统级环境信息（OS、路径、端口）
├── HEARTBEAT.md     # 心跳监控任务清单
├── MEMORY.md        # 长期记忆（经验蒸馏）
├── memory\          # 每日记忆存档（memory/YYYY-MM-DD.md）
└── skills\
    ├── autohyseeker\  # (name: autohyseeker-dev) 项目代码开发
    │   └── SKILL.md
    ├── echem-data\    # 电化学数据分析
    │   └── SKILL.md
    ├── literature\    # 学术文献检索
    │   └── SKILL.md
    └── lab-bridge\    # 多智能体系统桥接
        └── SKILL.md
```

### 关键设计决策

| 文件 | 以前（v2.0） | 现在（v3.0） |
|------|-------------|-------------|
| SOUL.md | 电化学领域专家人设 | **通用助手**，原则导向 |
| AGENTS.md | AutoHySeeker 定制指令 | **通用工作指南**，领域靠 Skills |
| IDENTITY.md | HySeer ⚗️ | **Pi 🤖**，通用型私人助手 |
| autohyseeker Skill | `always:true`，包含硬件/数据分析 | `always:false`，仅代码开发 |
| echem-data Skill | 不存在（混在 SOUL 里） | **独立 Skill**，专注数据分析 |
| literature Skill | 不存在 | **独立 Skill**，文献检索 |
| lab-bridge Skill | 不存在 | **独立 Skill**，HTTP 桥接多智能体 |

### SKILL.md 格式

```markdown
---
name: skill-name
description: 技能简短描述
metadata: {"openclaw":{"always":false,"os":["win32"]}}
---

# 详细说明
...
```

`always:false` = 按需加载（Agent 判断是否需要）
`always:true` = 每次会话都加载

---

## 六、Skills 系统

### 6.1 Skills 总览

| Skill | 目录名 | SKILL.md name | always | 用途 |
|-------|--------|--------------|--------|------|
| 项目代码开发 | `autohyseeker/` | `autohyseeker-dev` | false | AutoHySeeker 源码开发 |
| 电化学数据分析 | `echem-data/` | `echem-data` | false | CV/EIS/CA 数据分析 |
| 学术文献检索 | `literature/` | `literature` | false | 论文搜索和整理 |
| 多智能体桥接 | `lab-bridge/` | `lab-bridge` | false | HTTP 调用多智能体 API |
| 内置编程代理 | (bundled) | — | — | Codex CLI / Claude Code |

### 6.2 autohyseeker-dev（项目代码开发）

**触发场景**：用户要求开发 AutoHySeeker / MicroHySeeker 代码时加载

包含：
- 项目目录结构和关键文档位置
- 常用命令（pytest/启动后端/查日志）
- 技术栈（Python 3.11 / FastAPI / LangGraph / PySide6）
- 编码规范

### 6.3 echem-data（电化学数据分析）

**触发场景**：用户提到分析实验数据、CV/EIS/CA 数据时加载

包含：
- 数据目录结构（`data/YYYY-MM-DD/`）
- 数据类型说明（CV、EIS、CA、DPV）
- 分析流程和报告模板
- 硬件背景信息

### 6.4 literature（学术文献检索）

**触发场景**：用户要求搜索论文、整理参考文献时加载

包含：
- 五大研究方向
- 搜索工具和数据库
- 输出格式模板
- 文献存储位置

### 6.5 lab-bridge（多智能体系统桥接）

**触发场景**：用户要求启动实验工作流、调用贝叶斯优化时加载

包含：
- API 端点列表（开发中）
- 调用方式（HTTP POST/GET）
- 当前开发状态
- 未来路线图（Phase 1-5）

> ⚠️ lab-bridge 的 API 后端正在开发中，大部分端点尚未实现。

### 6.6 openclaw.json Skills 配置

```json5
{
  skills: {
    load: { watch: true, watchDebounceMs: 500 },
    entries: {
      "autohyseeker": { enabled: true },
      "echem-data":   { enabled: true },
      "literature":   { enabled: true },
      "lab-bridge":   { enabled: true }
    }
  }
}
```

---

## 七、启动与操作

### 7.1 首次配置（★ 必做）

```powershell
# 1. 设置 Anthropic API Key（环境变量方式，v0.1.6 唯一有效方式）
$env:ANTHROPIC_API_KEY = "sk-ant-api03-YOUR_KEY_HERE"

# 或写入启动脚本（推荐，无需每次手动设置）
# 编辑 D:\AI4S\start-openclaw.ps1，替换 YOUR_ANTHROPIC_API_KEY

# 2. 验证配置（应无 Invalid config 报错）
$env:PATH = "$env:APPDATA\npm;$env:PATH"
openclaw-cn doctor
```

### 7.2 启动网关

```powershell
$env:PATH = "$env:APPDATA\npm;$env:PATH"

# 前台运行（开发调试用）
openclaw-cn gateway --port 18789

# 或后台运行（作为守护进程）
openclaw-cn gateway status
```

### 7.3 打开 WebChat UI

```powershell
# 自动打开浏览器
openclaw-cn dashboard

# 或手动访问
Start-Process "http://127.0.0.1:18789/"
```

### 7.4 安装为 Windows 定时任务（开机自启）

```powershell
# 安装守护进程（需管理员权限）
openclaw-cn gateway install

# 启动服务
openclaw-cn gateway start

# 检查状态
openclaw-cn gateway status
```

### 7.5 常用命令

```powershell
openclaw-cn --version              # 查看版本 (当前: 0.1.6)
openclaw-cn status                 # 完整状态报告
openclaw-cn doctor                 # 诊断配置问题
openclaw-cn dashboard              # 打开 WebChat 界面
openclaw-cn gateway status         # 网关状态
openclaw-cn security audit         # 安全审计
```

---

## 八、心跳主动监控

心跳是 OpenClaw 的**主动运行模式** — 按固定间隔触发 Agent 执行 `HEARTBEAT.md` 中的任务。

### 8.1 启用心跳

在 `openclaw.json` 中设置：
```json5
{
  agent: {
    heartbeat: { every: "30m" }  // 每 30 分钟触发一次
  }
}
```

### 8.2 HEARTBEAT.md 示例（AutoHySeeker 监控）

```markdown
# 主动监控任务

## 实验数据监控
检查 `data/` 目录下是否有过去 1 小时内新增的实验数据。
如有，分析 CV/EIS/CA 数据，汇总实验质量（峰值是否正常、基线是否稳定），
通过 WebChat 推送简报。

## 后端健康检查
运行: curl http://localhost:8100/health
如果失败，记录到 MEMORY.md 并发出告警。

## 测试状态
cd AutoHySeeker && python -m pytest tests/ -q --tb=no
如有失败，列出失败的测试文件名。
```

### 8.3 心跳行为

- 如果 `HEARTBEAT.md` 是空的（只有空白）→ **跳过**，不消耗 API
- Agent 回复 `HEARTBEAT_OK` → 抑制对外发送通知
- Agent 有实质内容 → 发送到 WebChat / Telegram

---

## 九、多渠道接入

初始仅推荐使用 **WebChat（本地）**，不需要任何额外配置。

### 9.1 WebChat（默认，立即可用）

- URL: `http://127.0.0.1:18789/`
- 无需额外配置
- 本地浏览器访问

### 9.2 Telegram（推荐作为移动端接入）

便于在实验室用手机远程控制：

```bash
# 1. 创建 Telegram Bot
# 发消息给 @BotFather，运行 /newbot，获取 Bot Token

# 2. 添加配置到 openclaw.json
{
  channels: {
    telegram: {
      token: "你的_TELEGRAM_BOT_TOKEN",
      allowFrom: ["你的_TELEGRAM_USER_ID"]  // 数字 ID，防止他人访问
    }
  }
}

# 3. 重启网关后向 Bot 发消息即可使用
```

**获取你的 Telegram User ID**：发消息给 @userinfobot 或 @getidsbot。

> 安全提示：务必设置 `allowFrom` 白名单，防止 Bot 被他人控制。

---

## 十、常见问题

### Q: 每次打开终端都要手动设置 PATH？

**A**: 将 `%APPDATA%\npm` 永久添加到用户 PATH：
```powershell
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
[Environment]::SetEnvironmentVariable("PATH", "$env:APPDATA\npm;$userPath", "User")
```
之后重开终端即可。

### Q: openclaw-cn 报错 `Cannot find module`？

**A**: 已知 Windows 原生模块问题。修复方法见 §3.3。  
简短步骤：确认 `%APPDATA%\npm\node_modules\openclaw-cn\node_modules\@mariozechner\clipboard\clipboard.win32-x64-msvc.node` 文件存在。

### Q: 网关启动后 WebChat 打不开？

**A**: 检查端口是否被占用：
```powershell
netstat -an | findstr 18789
# 如有冲突改为其他端口
openclaw-cn gateway --port 19789
```

### Q: API Key 怎么配置？

**A**: 当前使用 Yuan API（api.mcxhm.cn），API Key 存储在 `auth-profiles.json` 中：
```
C:\Users\25922\.openclaw\agents\main\agent\auth-profiles.json
```
Provider 配置（baseUrl/auth/api）在 `openclaw.json` 的 `models.providers.anthropic` 中。
两者配合即可工作，无需设置环境变量。

### Q: 如何切换到更强的 Claude 模型？

**A**: 在 `openclaw.json` 中修改：
```json5
agents: { defaults: { model: { primary: "anthropic/claude-opus-4-6" } } }
```
重启网关后生效。可选模型：claude-sonnet-4-6（默认）、claude-opus-4-6（最强）、claude-haiku-4-5（最快）。

### Q: Skills 更新后没生效？

**A**: `skills.load.watch: true` 会自动热重载。如仍未生效，重启新会话（发 `/new`）。

---

## 附：快速启动脚本

保存为 `D:\AI4S\start-openclaw.ps1`（当前已配置好）：

```powershell
# OpenClaw-CN startup script
# Usage: & D:\AI4S\start-openclaw.ps1
# API: Yuan API (api.mcxhm.cn) + Claude model, no proxy needed

$env:PATH = "$env:APPDATA\npm;$env:PATH"
$env:ALL_PROXY = ""
$env:HTTPS_PROXY = ""
$env:HTTP_PROXY = ""

Write-Host "=== OpenClaw-CN Start (Yuan API + Claude) ===" -ForegroundColor Cyan

$version = & openclaw-cn --version 2>&1
Write-Host "OpenClaw version: $version" -ForegroundColor Green

Write-Host "Starting gateway on port 18789..." -ForegroundColor Yellow
Write-Host "WebChat: http://127.0.0.1:18789/?token=mhs-openclaw-a7f3d2e1b9c84056" -ForegroundColor Cyan

Start-Process "http://127.0.0.1:18789/?token=mhs-openclaw-a7f3d2e1b9c84056"
openclaw-cn gateway --port 18789
```

运行：
```powershell
& "D:\AI4S\start-openclaw.ps1"
```

---

*此文档覆盖 OpenClaw v0.1.6 在 Windows 上的完整配置。v3.0 架构：通用助手 + Skills 领域插件 + 多智能体桥接。*
