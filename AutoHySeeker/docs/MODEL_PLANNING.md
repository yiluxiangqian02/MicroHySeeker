# AutoHySeeker 模型配置方案

> 最后更新：2026-03-07  
> 支持 UI 动态切换

---

## 📊 LLM 使用场景分析

### 场景 1：数据分析（DataAnalystAgent）
**用途：** CV/EIS 信号解读、不确定性分析、数据趋势发现

**特点：**
- 需要理解电化学专业术语
- 输入：实验数据（JSON/CSV）+ 历史对比
- 输出：分析报告（500-1500 tokens）
- 调用频率：每次实验后 1 次

**推荐模型：**
1. **DeepSeek V3.2**（¥2/¥3）- 推理能力强，适合数据分析
2. **GLM-4.6**（¥2/¥8）- 中文理解好，质量稳定
3. **Qwen3-Max**（¥2.5/¥10）- 旗舰模型，复杂分析

---

### 场景 2：故障诊断（DiagnosticsExpertAgent）
**用途：** 识别失败模式、仪器异常、故障排查步骤

**特点：**
- 需要快速响应
- 输入：错误日志 + 系统状态
- 输出：诊断结果 + 解决方案（300-800 tokens）
- 调用频率：实验失败时 1 次

**推荐模型：**
1. **Qwen-Plus**（¥0.8/¥2）- 快速响应，成本低
2. **DeepSeek V3.2**（¥2/¥3）- 推理能力强
3. **GLM-4.5-Air**（¥0.8/¥2）- 轻量快速

---

### 场景 3：实验设计（ExperimentDesignerAgent）
**用途：** 提出下一步实验方案、参数优化建议

**特点：**
- 需要创造性思维
- 输入：当前实验结果 + 研究目标
- 输出：实验方案（800-2000 tokens）
- 调用频率：每个实验周期 1-3 次

**推荐模型：**
1. **GLM-4.6**（¥2/¥8）- 创造性好，方案质量高
2. **Qwen3.5-Plus**（¥0.8/¥4.8）- 长上下文，综合考虑
3. **Kimi-latest**（¥2/¥10）- 长上下文专家

---

### 场景 4：实验监控（ExperimentSupervisorAgent）
**用途：** 协调实验生命周期、操作决策、安全执行

**特点：**
- 需要实时决策
- 输入：实时状态 + 任务队列
- 输出：操作指令（200-500 tokens）
- 调用频率：实验运行中多次

**推荐模型：**
1. **Qwen-Turbo**（¥0.3/¥0.6）- 极低成本，快速响应
2. **Qwen-Plus**（¥0.8/¥2）- 性价比高
3. **GLM-4.5-Air**（¥0.8/¥2）- 轻量快速

---

### 场景 5：知识管理（KnowledgeManagerAgent）
**用途：** 组织实验洞察、提取可复用知识、提供上下文

**特点：**
- 需要长上下文理解
- 输入：历史实验记录 + 文献
- 输出：知识总结（1000-3000 tokens）
- 调用频率：定期整理（每周 1-2 次）

**推荐模型：**
1. **Kimi-latest**（¥2/¥10）- 长上下文专家（128K）
2. **Qwen3.5-Plus**（¥0.8/¥4.8）- 超长上下文（1000K）
3. **GLM-4.6**（¥2/¥8）- 知识整理能力强

---

## 🎯 预设配置方案

### 方案 A：极致省钱（月成本 ~¥10）

适合开发测试，优先使用最便宜的模型

| Agent | 主模型 | 降级模型 | Temperature | Max Tokens |
|-------|--------|----------|-------------|------------|
| 数据分析 | DeepSeek V3.2 (¥2/¥3) | Qwen-Plus (¥0.8/¥2) | 0.1 | 2000 |
| 故障诊断 | Qwen-Plus (¥0.8/¥2) | Qwen-Turbo (¥0.3/¥0.6) | 0.1 | 1000 |
| 实验设计 | DeepSeek V3.2 (¥2/¥3) | Qwen-Plus (¥0.8/¥2) | 0.3 | 2500 |
| 实验监控 | Qwen-Turbo (¥0.3/¥0.6) | Qwen-Plus (¥0.8/¥2) | 0.1 | 800 |
| 知识管理 | Qwen3.5-Plus (¥0.8/¥4.8) | DeepSeek V3.2 (¥2/¥3) | 0.2 | 3000 |

### 方案 B：性价比平衡（月成本 ~¥30）

适合生产环境，平衡质量和成本

| Agent | 主模型 | 降级模型 | Temperature | Max Tokens |
|-------|--------|----------|-------------|------------|
| 数据分析 | GLM-4.6 (¥2/¥8) | DeepSeek V3.2 (¥2/¥3) | 0.1 | 2000 |
| 故障诊断 | Qwen-Plus (¥0.8/¥2) | Qwen-Turbo (¥0.3/¥0.6) | 0.1 | 1000 |
| 实验设计 | GLM-4.6 (¥2/¥8) | Qwen3.5-Plus (¥0.8/¥4.8) | 0.3 | 2500 |
| 实验监控 | Qwen-Plus (¥0.8/¥2) | Qwen-Turbo (¥0.3/¥0.6) | 0.1 | 800 |
| 知识管理 | Qwen3.5-Plus (¥0.8/¥4.8) | GLM-4.6 (¥2/¥8) | 0.2 | 3000 |

### 方案 C：质量优先（月成本 ~¥50）

适合重要实验，追求最佳质量

| Agent | 主模型 | 降级模型 | Temperature | Max Tokens |
|-------|--------|----------|-------------|------------|
| 数据分析 | Qwen3-Max (¥2.5/¥10) | GLM-4.6 (¥2/¥8) | 0.1 | 2000 |
| 故障诊断 | DeepSeek V3.2 (¥2/¥3) | Qwen-Plus (¥0.8/¥2) | 0.1 | 1000 |
| 实验设计 | Kimi-latest (¥2/¥10) | Qwen3-Max (¥2.5/¥10) | 0.3 | 2500 |
| 实验监控 | Qwen-Plus (¥0.8/¥2) | Qwen-Turbo (¥0.3/¥0.6) | 0.1 | 800 |
| 知识管理 | Kimi-latest (¥2/¥10) | Qwen3.5-Plus (¥0.8/¥4.8) | 0.2 | 3000 |

---

## 🔧 配置文件结构

### 1. 主配置文件：`configs/llm_models.json`

```json
{
  "version": "1.0.0",
  "active_preset": "性价比平衡",
  "api": {
    "base_url": "https://router.shengsuanyun.com/api/v1",
    "api_key": "${SHENGSUANYUN_API_KEY}",
    "timeout": 60
  },
  "presets": {
    "极致省钱": {
      "name": "极致省钱",
      "description": "适合开发测试，优先使用最便宜的模型",
      "monthly_cost_estimate": "¥10",
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
          "model": "deepseek/deepseek-v3.2",
          "fallback": "alibaba/qwen-plus",
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
          "fallback": "deepseek/deepseek-v3.2",
          "temperature": 0.2,
          "max_tokens": 3000
        }
      }
    }
  },
  "custom": {
    "enabled": false,
    "agents": {}
  }
}
```

### 2. 模型元数据：`configs/model_metadata.json`

包含所有可用模型的详细信息（价格、能力、上下文长度等）

---

## 🖥️ UI 设计方案

### 页面：设置 → 模型配置

**功能模块：**

1. **预设方案选择**
   - 单选按钮：极致省钱 / 性价比平衡 / 质量优先 / 自定义
   - 显示预估月成本
   - 一键切换

2. **Agent 模型配置**
   - 每个 Agent 独立配置卡片
   - 下拉菜单选择模型（显示价格）
   - 调整 Temperature 和 Max Tokens

3. **API 配置**
   - Base URL 输入框
   - API Key 输入框（密码类型）
   - 测试连接按钮

4. **成本监控**
   - 本月已用成本 / 预算
   - 进度条可视化
   - 按 Agent 分类统计

---

## 📝 实现步骤

### Step 1：创建配置文件（后端）

```bash
# 创建配置文件
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\configs
# 创建 llm_models.json
# 创建 model_metadata.json
```

### Step 2：修改 LLM 客户端

```python
# src/common/llm_client.py
def load_model_config(agent_name: str) -> dict:
    """根据 agent 名称加载模型配置"""
    config_path = Path("configs/llm_models.json")
    config = json.loads(config_path.read_text())
    preset_name = config["active_preset"]
    preset = config["presets"][preset_name]
    return preset["agents"].get(agent_name, {})
```

### Step 3：修改 BaseAgent

```python
# src/agents/base.py
class BaseAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        
        # 从配置加载模型
        config = load_model_config(name)
        self.model = config.get("model", DEFAULT_MODEL)
        self.fallback_model = config.get("fallback", FALLBACK_MODEL)
        self.temperature = config.get("temperature", 0.1)
        self.max_tokens = config.get("max_tokens", 2000)
```

### Step 4：添加 API 端点

```python
# src/api/routes/settings.py
from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/models/config")
async def get_model_config():
    """获取当前模型配置"""
    return load_config()

@router.post("/models/config")
async def update_model_config(config: dict):
    """更新模型配置"""
    save_config(config)
    return {"success": True}

@router.get("/models/metadata")
async def get_model_metadata():
    """获取模型元数据（价格、能力等）"""
    return load_metadata()

@router.get("/models/usage")
async def get_usage_stats():
    """获取本月使用统计"""
    return calculate_usage()
```

### Step 5：前端实现（React + TypeScript）

```typescript
// src/api/settings.ts
export async function getModelConfig() {
  return fetch('/api/v1/settings/models/config').then(r => r.json())
}

export async function updateModelConfig(config: ModelConfig) {
  return fetch('/api/v1/settings/models/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  }).then(r => r.json())
}

export async function getUsageStats() {
  return fetch('/api/v1/settings/models/usage').then(r => r.json())
}
```

---

## 📊 使用统计追踪

### 数据库表结构（SQLite）

```sql
CREATE TABLE llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_name TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_cny REAL,
    success BOOLEAN,
    error_message TEXT
);

CREATE INDEX idx_timestamp ON llm_usage(timestamp);
CREATE INDEX idx_agent ON llm_usage(agent_name);
```

### 统计查询

```python
def get_monthly_usage():
    """获取本月使用统计"""
    query = """
        SELECT 
            agent_name,
            COUNT(*) as call_count,
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output,
            SUM(cost_cny) as total_cost
        FROM llm_usage
        WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
        GROUP BY agent_name
    """
    return db.execute(query).fetchall()
```

---

## 🎯 下一步行动

1. ✅ **规划完成** - 场景分析 + 配置方案设计
2. ⏳ **创建配置文件** - llm_models.json + model_metadata.json
3. ⏳ **修改后端代码** - llm_client.py + base.py 支持动态配置
4. ⏳ **添加 API 端点** - settings.py 路由
5. ⏳ **实现前端 UI** - 设置页面
6. ⏳ **添加使用统计** - 数据库 + 成本监控

---

## 📝 更新日志

| 日期 | 变更内容 | 操作人 |
|------|---------|--------|
| 2026-03-07 | 初始创建模型配置规划文档 | Pi |

---

*需要开始实现时，按照上述步骤逐步进行。*
