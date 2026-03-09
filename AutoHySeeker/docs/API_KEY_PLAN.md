# 模型使用场景与 API Key 申请清单

> 最后更新：2026-03-07  
> 用途：为每个独立场景申请专用 API Key

---

## 📊 所有模型使用场景

### 场景 1：OpenClaw 主 Agent（Pi 日常对话）

**当前状态：** ✅ 已配置

**用途：**
- Pi 的日常对话
- 任务理解和规划
- 文件操作建议
- 代码审查建议

**当前配置：**
- 提供商：中转站
- Base URL: `https://www.zhongzhuan.win/v1`
- 模型: `claude-opus-4-6`
- API Key: 已配置

**推荐：保持不变**

---

### 场景 2：OpenClaw Memory Search（记忆向量化）

**当前状态：** ✅ 已配置

**用途：**
- 记忆搜索的文本向量化
- MEMORY.md 和 memory/*.md 的语义检索

**当前配置：**
- 提供商：胜算云
- Base URL: `https://router.shengsuanyun.com/api/v1`
- 模型: `baai/bge-m3`（Embedding 模型）
- API Key: 已配置

**推荐：保持不变**

---

### 场景 3：AutoHySeeker - 数据分析 Agent

**当前状态：** ❌ 未配置

**用途：**
- CV/EIS 信号解读
- 数据趋势分析
- 不确定性分析

**特点：**
- 调用频率：每次实验后 1 次
- Token 消耗：输入 ~1K, 输出 ~1.5K
- 需要推理能力

**推荐配置：**
- 提供商：胜算云
- 模型: `deepseek/deepseek-v3.2`（¥2/¥3）
- 降级模型: `alibaba/qwen-plus`（¥0.8/¥2）
- 理由：推理能力强，成本低

**建议：申请独立 API Key（命名：AutoHySeeker-DataAnalyst）**

---

### 场景 4：AutoHySeeker - 故障诊断 Agent

**当前状态：** ❌ 未配置

**用途：**
- 识别失败模式
- 仪器异常检测
- 故障排查步骤

**特点：**
- 调用频率：实验失败时 1 次
- Token 消耗：输入 ~0.8K, 输出 ~0.5K
- 需要快速响应

**推荐配置：**
- 提供商：胜算云
- 模型: `alibaba/qwen-plus`（¥0.8/¥2）
- 降级模型: `alibaba/qwen-turbo`（¥0.3/¥0.6）
- 理由：快速响应，成本低

**建议：与数据分析共用 API Key 或申请独立**

---

### 场景 5：AutoHySeeker - 实验设计 Agent

**当前状态：** ❌ 未配置

**用途：**
- 提出下一步实验方案
- 参数优化建议
- 创造性思维

**特点：**
- 调用频率：每个实验周期 1-3 次
- Token 消耗：输入 ~1.2K, 输出 ~1.5K
- 需要创造性

**推荐配置：**
- 提供商：胜算云
- 模型: `zhipu/glm-4.6`（¥2/¥8）
- 降级模型: `alibaba/qwen3.5-plus`（¥0.8/¥4.8）
- 理由：创造性好，方案质量高

**建议：与数据分析共用 API Key 或申请独立**

---

### 场景 6：AutoHySeeker - 实验监控 Agent

**当前状态：** ❌ 未配置

**用途：**
- 协调实验生命周期
- 操作决策
- 安全执行

**特点：**
- 调用频率：实验运行中多次
- Token 消耗：输入 ~0.5K, 输出 ~0.3K
- 需要实时决策

**推荐配置：**
- 提供商：胜算云
- 模型: `alibaba/qwen-turbo`（¥0.3/¥0.6）
- 降级模型: `alibaba/qwen-plus`（¥0.8/¥2）
- 理由：极低成本，快速响应

**建议：与数据分析共用 API Key**

---

### 场景 7：AutoHySeeker - 知识管理 Agent

**当前状态：** ❌ 未配置

**用途：**
- 组织实验洞察
- 提取可复用知识
- 提供上下文

**特点：**
- 调用频率：每周 1-2 次
- Token 消耗：输入 ~2K, 输出 ~2K
- 需要长上下文

**推荐配置：**
- 提供商：胜算云
- 模型: `alibaba/qwen3.5-plus`（¥0.8/¥4.8）
- 降级模型: `zhipu/glm-4.6`（¥2/¥8）
- 理由：超长上下文（1000K），性价比高

**建议：与数据分析共用 API Key**

---

### 场景 8：Coding Agent（代码开发）

**当前状态：** ✅ 已配置

**用途：**
- Copilot/Codex/Claude Code 进行代码开发
- 自动化代码生成和修复

**当前配置：**
- Copilot: auth 登录（不按 token 计费）
- Codex: auth 登录（每 5 小时有 token 上限）
- Claude Code: 按 token 计费

**推荐：保持不变**

---

## 🎯 API Key 申请方案

### 方案 A：最小化（1 个 API Key）

**适合：** 开发测试阶段

| API Key 名称 | 用途 | 提供商 | 模型 |
|-------------|------|--------|------|
| AutoHySeeker-Production | 所有 5 个 Agent 共用 | 胜算云 | 多模型混用 |

**优点：**
- 管理简单
- 成本统一
- 配置简单

**缺点：**
- 无法按 Agent 分别统计成本
- 无法独立限流

**月成本：** ¥5-15

---

### 方案 B：按功能分离（2 个 API Key）

**适合：** 生产环境

| API Key 名称 | 用途 | 提供商 | 模型 |
|-------------|------|--------|------|
| AutoHySeeker-Analysis | 数据分析 + 实验设计 | 胜算云 | DeepSeek V3.2 + GLM-4.6 |
| AutoHySeeker-Operations | 故障诊断 + 实验监控 + 知识管理 | 胜算云 | Qwen 系列 |

**优点：**
- 核心功能（分析/设计）独立
- 运维功能（诊断/监控）独立
- 可分别限流和监控

**缺点：**
- 需要管理 2 个 Key
- 配置稍复杂

**月成本：** ¥5-15

---

### 方案 C：完全隔离（5 个 API Key）

**适合：** 大规模生产 + 精细化成本控制

| API Key 名称 | 用途 | 提供商 | 模型 |
|-------------|------|--------|------|
| AutoHySeeker-DataAnalyst | 数据分析 | 胜算云 | DeepSeek V3.2 |
| AutoHySeeker-Diagnostics | 故障诊断 | 胜算云 | Qwen-Plus |
| AutoHySeeker-Designer | 实验设计 | 胜算云 | GLM-4.6 |
| AutoHySeeker-Supervisor | 实验监控 | 胜算云 | Qwen-Turbo |
| AutoHySeeker-Knowledge | 知识管理 | 胜算云 | Qwen3.5-Plus |

**优点：**
- 每个 Agent 独立计费
- 精细化成本控制
- 可独立限流
- 便于故障隔离

**缺点：**
- 管理复杂
- 配置繁琐

**月成本：** ¥5-15

---

## 💡 推荐方案

### 推荐：方案 A（1 个 API Key）

**理由：**
1. 开发测试阶段，调用量不大
2. 管理简单，配置方便
3. 成本可控（月 ¥5-15）
4. 后续可随时升级到方案 B 或 C

**申请步骤：**

1. 访问 https://router.shengsuanyun.com
2. 注册/登录账号
3. 创建 API Key（命名：`AutoHySeeker-Production`）
4. 复制 API Key
5. 配置到 `AutoHySeeker/.env`

---

## 📝 配置文件示例

### AutoHySeeker/.env

```bash
# LLM API 配置（胜算云 - 所有 Agent 共用）
OPENAI_BASE_URL=https://router.shengsuanyun.com/api/v1
OPENAI_API_KEY=<你申请的 AutoHySeeker-Production API Key>
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

### AutoHySeeker/configs/llm_models.json

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

## 📊 成本对比

| 方案 | API Key 数量 | 管理复杂度 | 月成本 | 推荐场景 |
|------|-------------|-----------|--------|---------|
| 方案 A | 1 | 低 | ¥5-15 | ✅ 开发测试 |
| 方案 B | 2 | 中 | ¥5-15 | 生产环境 |
| 方案 C | 5 | 高 | ¥5-15 | 大规模生产 |

**注意：** 成本相同，主要区别在于管理粒度和监控能力。

---

## ✅ 最终建议

**立即申请：1 个胜算云 API Key**

**命名：** `AutoHySeeker-Production`

**用途：** AutoHySeeker 所有 5 个 Agent 共用

**后续：** 根据实际使用情况，可随时升级到方案 B 或 C

---

## 📝 更新日志

| 日期 | 变更内容 | 操作人 |
|------|---------|--------|
| 2026-03-07 | 初始创建 API Key 申请清单 | Pi |
