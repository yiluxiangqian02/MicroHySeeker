# AutoHySeeker LLM 使用场景与配置方案

> 最后更新：2026-03-07  
> 基于代码分析和价格表

---

## 📊 LLM 使用场景分析

### 1. Agent 层（src/agents/）

**调用位置：** `src/agents/base.py` → `chat_completion()`

**使用的 Agent：**
- `DataAnalystAgent` - CV/EIS 信号解读
- `DiagnosticsExpertAgent` - 故障诊断
- `ExperimentDesignerAgent` - 实验设计
- `ExperimentSupervisorAgent` - 实验监控协调
- `KnowledgeManagerAgent` - 知识管理

**特点：**
- 每个 Agent 有独立的系统提示（system prompt）
- 通过 `BaseAgent.invoke()` 统一调用
- 支持自定义模型（默认使用 `DEFAULT_MODEL`）

**Token 消耗估算：**
- 输入：系统提示（500-1000 tokens）+ 用户任务（200-500 tokens）
- 输出：分析结果（500-2000 tokens）
- 单次调用：约 1000-3500 tokens

### 2. C1 Skill - ContextualizeExperiment（已实现但未启用）

**调用位置：** `src/skills/contextualize_experiment.py`

**功能：** 从 OpenViking 知识库检索文献和实验记录，LLM 合成上下文摘要

**当前状态：** 
- ⚠️ 代码中未直接调用 `chat_completion`
- 使用 `knowledge_retriever` 工具（不需要 LLM）
- 如果需要智能分析，需要配置 LLM API

**Token 消耗估算：**
- 输入：实验数据 + 检索到的文献（2000-5000 tokens）
- 输出：上下文摘要（500-1000 tokens）
- 单次调用：约 2500-6000 tokens

### 3. 其他 Skills（无 LLM 调用）

以下 Skills 均为 **LLM-free**，不消耗 API：
- A1 SingleExperimentAnalysis - 纯数据分析
- B1 GenerateExperimentPlan - 模板 + 规则引擎
- C2 SuggestNextExperiment - 规则推荐
- D1/D2/D3 Diagnostics - 规则引擎
- E1/E2 Execution - 监控和调度

---

## 🎯 推荐配置方案

### 方案 1：极致省钱（推荐用于开发/测试）

```bash
# .env 配置
OPENAI_BASE_URL=https://router.shengsuanyun.com/api/v1
OPENAI_API_KEY=<你的胜算云 API Key>
DEFAULT_MODEL=deepseek/deepseek-v3.2
FALLBACK_MODEL=alibaba/qwen-plus
OPENAI_TIMEOUT_SECONDS=60
```

**模型选择：**
- **主模型**: DeepSeek V3.2（¥2/¥3）- 性能优秀，价格低
- **降级模型**: Ali / Qwen-Plus（¥0.8/¥2）- 更便宜的备选

**月成本估算**（假设 Agent 调用 1000 次/月）：
- 输入：1000 次 × 1K tokens × ¥2/M = ¥2
- 输出：1000 次 × 1.5K tokens × ¥3/M = ¥4.5
- **总计：约 ¥6.5/月**

### 方案 2：性价比平衡（推荐用于生产）

```bash
# .env 配置
OPENAI_BASE_URL=https://router.shengsuanyun.com/api/v1
OPENAI_API_KEY=<你的胜算云 API Key>
DEFAULT_MODEL=zhipu/glm-4.6
FALLBACK_MODEL=alibaba/qwen3.5-plus
OPENAI_TIMEOUT_SECONDS=60
```

**模型选择：**
- **主模型**: bigmodel / GLM-4.6（¥2/¥8）- 智谱 AI，质量好
- **降级模型**: Ali / Qwen3.5-Plus（¥0.8/¥4.8）- 超长上下文

**月成本估算**（假设 Agent 调用 1000 次/月）：
- 输入：1000 次 × 1K tokens × ¥2/M = ¥2
- 输出：1000 次 × 1.5K tokens × ¥8/M = ¥12
- **总计：约 ¥14/月**

### 方案 3：质量优先（输出 ≤ ¥10/M）

```bash
# .env 配置
OPENAI_BASE_URL=https://router.shengsuanyun.com/api/v1
OPENAI_API_KEY=<你的胜算云 API Key>
DEFAULT_MODEL=moonshot/kimi-latest
FALLBACK_MODEL=alibaba/qwen3-max-2026-01-23
OPENAI_TIMEOUT_SECONDS=60
```

**模型选择：**
- **主模型**: Moonshot / Kimi-latest（¥2/¥10）- 长上下文专家
- **降级模型**: Ali / Qwen3-Max（¥2.5/¥10）- 千问旗舰

**月成本估算**（假设 Agent 调用 1000 次/月）：
- 输入：1000 次 × 1K tokens × ¥2/M = ¥2
- 输出：1000 次 × 1.5K tokens × ¥10/M = ¥15
- **总计：约 ¥17/月**

---

## 🔧 配置步骤

### 1. 创建 .env 文件

```bash
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
cp .env.example .env
```

### 2. 编辑 .env 文件

根据上述方案选择一个，填入配置：

```bash
# LLM API 配置
OPENAI_BASE_URL=https://router.shengsuanyun.com/api/v1
OPENAI_API_KEY=<你的 API Key>
DEFAULT_MODEL=deepseek/deepseek-v3.2
FALLBACK_MODEL=alibaba/qwen-plus
OPENAI_TIMEOUT_SECONDS=60

# 数据路径（已有默认值）
DATA_ROOT=../data
LOG_ROOT=./logs

# API 服务（已有默认值）
API_HOST=0.0.0.0
API_PORT=8100
```

### 3. 验证配置

```bash
# 启动 FastAPI 后端
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8100

# 测试 Agent 调用
curl -X POST http://localhost:8100/api/v1/agents/invoke \
  -H "Content-Type: application/json" \
  -d '{"agent": "data_analyst", "task": {"action": "analyze", "data": "test"}}'
```

---

## 📈 不同场景的模型选择建议

| 场景 | 推荐模型 | 输入价格 | 输出价格 | 理由 |
|------|---------|---------|---------|------|
| **数据分析** | DeepSeek V3.2 | ¥2/M | ¥3/M | 推理能力强，价格低 |
| **实验设计** | GLM-4.6 | ¥2/M | ¥8/M | 中文理解好，质量稳定 |
| **故障诊断** | Qwen-Plus | ¥0.8/M | ¥2/M | 快速响应，成本低 |
| **知识管理** | Kimi-latest | ¥2/M | ¥10/M | 长上下文，适合文献检索 |
| **通用对话** | Qwen-Turbo | ¥0.3/M | ¥0.6/M | 极低成本，日常交互 |

---

## 🔄 动态切换模型（高级）

如果需要针对不同任务使用不同模型，可以修改 `src/agents/base.py`：

```python
# 在 BaseAgent.__init__ 中根据 agent 类型选择模型
MODEL_MAP = {
    "data_analyst": "deepseek/deepseek-v3.2",
    "exp_designer": "zhipu/glm-4.6",
    "diagnostics": "alibaba/qwen-plus",
    "knowledge_mgr": "moonshot/kimi-latest",
}

self.model = MODEL_MAP.get(self.__class__.__name__.lower(), DEFAULT_MODEL)
```

---

## 📝 更新日志

| 日期 | 变更内容 | 操作人 |
|------|---------|--------|
| 2026-03-07 | 初始创建 LLM 配置方案 | Pi |

---

*如需调整模型或价格变动，请同步更新 `LLM_PRICING.md` 和本文件。*
