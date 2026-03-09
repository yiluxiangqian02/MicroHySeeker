# AutoHySeeker 模型需求与推荐配置

> 最后更新：2026-03-07  
> 用途：为每个使用场景申请独立 API Key

---

## 🎯 模型调用需求清单

### 需求 1：OpenClaw 主 Agent（通用对话）

**使用场景：** 你（Pi）的日常对话、任务理解、文件操作建议

**当前配置：**
- Base URL: `https://www.zhongzhuan.win/v1`
- 模型: `custom-www-zhongzhuan-win/claude-opus-4-6`
- 用途: OpenClaw 主会话

**推荐保持不变** - 已有配置，无需额外申请

---

### 需求 2：AutoHySeeker Agent 层（5 个专业 Agent）

**使用场景：** AutoHySeeker 后端的 5 个专业 Agent

#### 2.1 数据分析 Agent（DataAnalystAgent）
- **用途**: CV/EIS 信号解读、数据趋势分析
- **调用频率**: 每次实验后 1 次
- **Token 消耗**: 输入 ~1K, 输出 ~1.5K
- **推荐模型**: `deepseek/deepseek-v3.2`（¥2/¥3）
- **降级模型**: `alibaba/qwen-plus`（¥0.8/¥2）

#### 2.2 故障诊断 Agent（DiagnosticsExpertAgent）
- **用途**: 识别失败模式、仪器异常
- **调用频率**: 实验失败时 1 次
- **Token 消耗**: 输入 ~0.8K, 输出 ~0.5K
- **推荐模型**: `alibaba/qwen-plus`（¥0.8/¥2）
- **降级模型**: `alibaba/qwen-turbo`（¥0.3/¥0.6）

#### 2.3 实验设计 Agent（ExperimentDesignerAgent）
- **用途**: 提出下一步实验方案
- **调用频率**: 每个实验周期 1-3 次
- **Token 消耗**: 输入 ~1.2K, 输出 ~1.5K
- **推荐模型**: `zhipu/glm-4.6`（¥2/¥8）
- **降级模型**: `alibaba/qwen3.5-plus`（¥0.8/¥4.8）

#### 2.4 实验监控 Agent（ExperimentSupervisorAgent）
- **用途**: 协调实验生命周期、操作决策
- **调用频率**: 实验运行中多次
- **Token 消耗**: 输入 ~0.5K, 输出 ~0.3K
- **推荐模型**: `alibaba/qwen-turbo`（¥0.3/¥0.6）
- **降级模型**: `alibaba/qwen-plus`（¥0.8/¥2）

#### 2.5 知识管理 Agent（KnowledgeManagerAgent）
- **用途**: 组织实验洞察、提取知识
- **调用频率**: 每周 1-2 次
- **Token 消耗**: 输入 ~2K, 输出 ~2K
- **推荐模型**: `alibaba/qwen3.5-plus`（¥0.8/¥4.8）
- **降级模型**: `zhipu/glm-4.6`（¥2/¥8）

**统一配置：**
- Base URL: `https://router.shengsuanyun.com/api/v1`
- API Key: 需要申请 1 个胜算云 API Key（所有 Agent 共用）

---

### 需求 3：Coding Agent（代码开发）

**使用场景：** Copilot/Codex/Claude Code 进行代码开发

**当前配置：**
- Copilot: 已配置（auth 登录，不按 token 计费）
- Codex: 已配置（auth 登录，每 5 小时有 token 上限）
- Claude Code: 已配置（按 token 计费）

**推荐保持不变** - 已有配置，无需额外申请

---

### 需求 4：OpenClaw Memory Search（记忆检索）

**使用场景：** 记忆搜索的向量化

**当前配置：**
- Base URL: `https://router.shengsuanyun.com/api/v1`
- API Key: 已配置（`nz0GMlymJVmKJUrS4uCwfNjFnjYzvK7-Le5iV0Ka7Vfmw9shyIG-iTyFnpBy2CnzG9k9amXJom7mcmQp_KYYY2lw`）
- 模型: `baai/bge-m3`

**推荐保持不变** - 已有配置，无需额外申请

---

## 📋 需要申请的 API Key 清单

| # | 用途 | 提供商 | Base URL | 需要申请 |
|---|------|--------|----------|---------|
| 1 | OpenClaw 主 Agent | 中转站 | `https://www.zhongzhuan.win/v1` | ❌ 已有 |
| 2 | AutoHySeeker 5 个 Agent | 胜算云 | `https://router.shengsuanyun.com/api/v1` | ✅ **需要申请** |
| 3 | Coding Agent | Copilot/Codex/Claude Code | 各自服务 | ❌ 已有 |
| 4 | Memory Search | 胜算云 | `https://router.shengsuanyun.com/api/v1` | ❌ 已有 |

**结论：只需要申请 1 个胜算云 API Key（用于 AutoHySeeker Agent 层）**

---

## 🔧 推荐配置方案

### 方案：性价比平衡（推荐）

**月成本估算：** 约 ¥30（假设每月 1000 次 Agent 调用）

**配置文件：** `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\.env`

```bash
# LLM API 配置（胜算云）
OPENAI_BASE_URL=https://router.shengsuanyun.com/api/v1
OPENAI_API_KEY=<申请的胜算云 API Key>
DEFAULT_MODEL=deepseek/deepseek-v3.2
FALLBACK_MODEL=alibaba/qwen-plus
OPENAI_TIMEOUT_SECONDS=60

# 数据路径
DATA_ROOT=../data
LOG_ROOT=./logs

# API 服务
API_HOST=0.0.0.0
API_PORT=8100
```

**模型配置文件：** `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\configs\llm_models.json`

```json
{
  "version": "1.0.0",
  "active_preset": "性价比平衡",
  "api": {
    "base_url": "https://router.shengsuanyun.com/api/v1",
    "api_key": "${OPENAI_API_KEY}",
    "timeout": 60
  },
  "presets": {
    "性价比平衡": {
      "name": "性价比平衡",
      "description": "适合生产环境，平衡质量和成本",
      "monthly_cost_estimate": "¥30",
      "agents": {
        "data_analyst": {
          "model": "deepseek/deepseek-v3.2",
          "fallback": "alibaba/qwen-plus",
          "temperature": 0.1,
          "max_tokens": 2000
        },
        "diagnostics": {
          "model": "alibaba/qwen-plus",
          "fallback": "alibaba/qwen-turbo",
          "temperature": 0.1,
          "max_tokens": 1000
        },
        "exp_designer": {
          "model": "zhipu/glm-4.6",
          "fallback": "alibaba/qwen3.5-plus",
          "temperature": 0.3,
          "max_tokens": 2500
        },
        "exp_supervisor": {
          "model": "alibaba/qwen-turbo",
          "fallback": "alibaba/qwen-plus",
          "temperature": 0.1,
          "max_tokens": 800
        },
        "knowledge_mgr": {
          "model": "alibaba/qwen3.5-plus",
          "fallback": "zhipu/glm-4.6",
          "temperature": 0.2,
          "max_tokens": 3000
        }
      }
    }
  }
}
```

---

## 📝 申请步骤

### 胜算云 API Key 申请

1. 访问 https://router.shengsuanyun.com
2. 注册/登录账号
3. 进入控制台 → API 密钥
4. 创建新密钥（命名：AutoHySeeker-Production）
5. 复制 API Key
6. 填入 `AutoHySeeker/.env` 文件的 `OPENAI_API_KEY`

---

## 💰 成本估算

### 月度使用预估（开发测试阶段）

| Agent | 调用次数/月 | 输入 tokens | 输出 tokens | 单次成本 | 月成本 |
|-------|------------|------------|------------|---------|--------|
| 数据分析 | 100 | 1K | 1.5K | ¥0.0065 | ¥0.65 |
| 故障诊断 | 50 | 0.8K | 0.5K | ¥0.0026 | ¥0.13 |
| 实验设计 | 30 | 1.2K | 1.5K | ¥0.0144 | ¥0.43 |
| 实验监控 | 200 | 0.5K | 0.3K | ¥0.0003 | ¥0.06 |
| 知识管理 | 10 | 2K | 2K | ¥0.0112 | ¥0.11 |
| **总计** | **390** | - | - | - | **¥1.38** |

**实际月成本：约 ¥1-5**（开发测试阶段）

### 月度使用预估（生产阶段）

假设每天 10 个实验：

| Agent | 调用次数/月 | 月成本 |
|-------|------------|--------|
| 数据分析 | 300 | ¥1.95 |
| 故障诊断 | 100 | ¥0.26 |
| 实验设计 | 100 | ¥1.44 |
| 实验监控 | 600 | ¥0.18 |
| 知识管理 | 30 | ¥0.34 |
| **总计** | **1130** | **¥4.17** |

**实际月成本：约 ¥5-15**（生产阶段）

---

## 🎯 总结

**需要申请：1 个胜算云 API Key**

**推荐模型组合：**
- 数据分析：DeepSeek V3.2（¥2/¥3）
- 故障诊断：Qwen-Plus（¥0.8/¥2）
- 实验设计：GLM-4.6（¥2/¥8）
- 实验监控：Qwen-Turbo（¥0.3/¥0.6）
- 知识管理：Qwen3.5-Plus（¥0.8/¥4.8）

**预估月成本：¥5-15**（生产阶段）

---

## 📝 更新日志

| 日期 | 变更内容 | 操作人 |
|------|---------|--------|
| 2026-03-07 | 初始创建模型需求与推荐配置 | Pi |
