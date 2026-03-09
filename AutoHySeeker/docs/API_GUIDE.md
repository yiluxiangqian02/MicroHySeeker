# 胜算云 API 使用指南

> 最后更新：2026-03-07  
> 官方文档：https://docs.router.shengsuanyun.com/

---

## 📋 目录

1. [基础配置](#基础配置)
2. [OpenAI 兼容 API](#openai-兼容-api)
3. [Web Search 功能](#web-search-功能)
4. [模型列表](#模型列表)
5. [错误处理](#错误处理)
6. [最佳实践](#最佳实践)

---

## 基础配置

### API 端点

```
Base URL: https://router.shengsuanyun.com/api/v1
```

### 认证方式

所有请求需要在 Header 中携带 API Key：

```bash
Authorization: Bearer <your-api-key>
```

### 获取 API Key

1. 访问 https://router.shengsuanyun.com
2. 注册/登录账号
3. 在控制台获取 API Key

---

## OpenAI 兼容 API

胜算云完全兼容 OpenAI API 格式，可以直接替换 OpenAI 的 Base URL。

### 1. Chat Completions（对话补全）

#### 基础用法

```bash
curl https://router.shengsuanyun.com/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{
    "model": "deepseek/deepseek-v3.2",
    "messages": [
      {
        "role": "system",
        "content": "你是一个有帮助的助手。"
      },
      {
        "role": "user",
        "content": "什么是量子计算？"
      }
    ]
  }'
```

#### Python 示例（OpenAI SDK）

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://router.shengsuanyun.com/api/v1",
    api_key="<your-api-key>"
)

response = client.chat.completions.create(
    model="deepseek/deepseek-v3.2",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "什么是量子计算？"}
    ]
)

print(response.choices[0].message.content)
```

#### 支持的参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model` | string | ✅ | 模型名称（如 `deepseek/deepseek-v3.2`） |
| `messages` | array | ✅ | 对话消息列表 |
| `temperature` | float | ❌ | 采样温度（0-2，默认 1） |
| `top_p` | float | ❌ | 核采样参数（0-1，默认 1） |
| `max_tokens` | integer | ❌ | 最大生成 tokens 数 |
| `stream` | boolean | ❌ | 是否流式输出（默认 false） |
| `stop` | string/array | ❌ | 停止词 |
| `presence_penalty` | float | ❌ | 存在惩罚（-2 到 2） |
| `frequency_penalty` | float | ❌ | 频率惩罚（-2 到 2） |
| `user` | string | ❌ | 用户标识符 |

#### 流式输出

```python
response = client.chat.completions.create(
    model="deepseek/deepseek-v3.2",
    messages=[{"role": "user", "content": "写一首诗"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### 2. Embeddings（文本嵌入）

#### 基础用法

```bash
curl https://router.shengsuanyun.com/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{
    "model": "baai/bge-m3",
    "input": "你好，世界！"
  }'
```

#### Python 示例

```python
response = client.embeddings.create(
    model="baai/bge-m3",
    input="你好，世界！"
)

embedding = response.data[0].embedding
print(f"向量维度: {len(embedding)}")
```

#### 批量嵌入

```python
response = client.embeddings.create(
    model="baai/bge-m3",
    input=[
        "第一段文本",
        "第二段文本",
        "第三段文本"
    ]
)

for i, data in enumerate(response.data):
    print(f"文本 {i+1} 的向量: {data.embedding[:5]}...")
```

### 3. Models（模型列表）

#### 获取可用模型

```bash
curl https://router.shengsuanyun.com/api/v1/models \
  -H "Authorization: Bearer <your-api-key>"
```

#### Python 示例

```python
models = client.models.list()

for model in models.data:
    print(f"模型ID: {model.id}")
    print(f"所有者: {model.owned_by}")
    print("---")
```

### 4. Completions（文本补全，旧版）

**注意：** 推荐使用 Chat Completions API，Completions API 已逐步废弃。

```bash
curl https://router.shengsuanyun.com/api/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{
    "model": "deepseek/deepseek-v3.2",
    "prompt": "从前有座山，",
    "max_tokens": 50
  }'
```

---

## Web Search 功能

胜算云提供增强的 Web Search 功能，可以让 LLM 实时搜索互联网信息。

### 启用方式

在 Chat Completions 请求中添加 `tools` 参数：

```python
response = client.chat.completions.create(
    model="deepseek/deepseek-v3.2",
    messages=[
        {"role": "user", "content": "2026年3月7日的新闻有哪些？"}
    ],
    tools=[
        {
            "type": "web_search",
            "web_search": {
                "search_engine": "bing",  # 可选：bing, google, duckduckgo
                "max_results": 5
            }
        }
    ]
)
```

### 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `type` | string | 固定为 `"web_search"` |
| `web_search.search_engine` | string | 搜索引擎（`bing`/`google`/`duckduckgo`，默认 `bing`） |
| `web_search.max_results` | integer | 最大搜索结果数（1-10，默认 5） |

### 完整示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://router.shengsuanyun.com/api/v1",
    api_key="<your-api-key>"
)

response = client.chat.completions.create(
    model="deepseek/deepseek-v3.2",
    messages=[
        {
            "role": "system",
            "content": "你是一个能够搜索互联网的助手。"
        },
        {
            "role": "user",
            "content": "DeepSeek V3 模型有什么特点？"
        }
    ],
    tools=[
        {
            "type": "web_search",
            "web_search": {
                "search_engine": "bing",
                "max_results": 5
            }
        }
    ]
)

print(response.choices[0].message.content)
```

### 工作流程

1. LLM 接收用户问题
2. 判断是否需要搜索
3. 如果需要，自动调用搜索引擎
4. 将搜索结果整合到回答中
5. 返回包含最新信息的回答

### 注意事项

- Web Search 会增加响应时间（通常 2-5 秒）
- 搜索结果会计入 token 消耗（输入 tokens）
- 不是所有模型都支持 Web Search（推荐使用 DeepSeek/Qwen/GLM 系列）

---

## 模型列表

### 推荐模型（输出 ≤ ¥10/M）

#### 超低成本

```
deepseek/deepseek-v3.2          # ¥2/¥3 - 推理能力强
alibaba/qwen-turbo              # ¥0.3/¥0.6 - 超长上下文
alibaba/qwen-plus               # ¥0.8/¥2 - 通义千问
```

#### 性价比平衡

```
zhipu/glm-4.6                   # ¥2/¥8 - 智谱 AI
alibaba/qwen3.5-plus            # ¥0.8/¥4.8 - 超长上下文
bytedance/doubao-seed-1.6       # ¥0.8/¥8 - 字节豆包
```

#### 质量优先

```
moonshot/kimi-latest            # ¥2/¥10 - 长上下文专家
alibaba/qwen3-max-2026-01-23    # ¥2.5/¥10 - 千问旗舰
```

### 模型命名规则

```
<provider>/<model-name>

示例：
- deepseek/deepseek-v3.2
- alibaba/qwen-plus
- zhipu/glm-4.6
- moonshot/kimi-latest
```

---

## 错误处理

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 401 | 未授权 | 检查 API Key 是否正确 |
| 429 | 请求过多 | 降低请求频率或升级套餐 |
| 500 | 服务器错误 | 稍后重试 |
| 503 | 服务不可用 | 模型暂时不可用，切换其他模型 |

### Python 错误处理示例

```python
from openai import OpenAI, APIError, RateLimitError, APIConnectionError

client = OpenAI(
    base_url="https://router.shengsuanyun.com/api/v1",
    api_key="<your-api-key>"
)

try:
    response = client.chat.completions.create(
        model="deepseek/deepseek-v3.2",
        messages=[{"role": "user", "content": "你好"}]
    )
    print(response.choices[0].message.content)
    
except RateLimitError:
    print("请求频率过高，请稍后重试")
    
except APIConnectionError:
    print("网络连接失败")
    
except APIError as e:
    print(f"API 错误: {e}")
```

---

## 最佳实践

### 1. 重试机制

```python
import time
from openai import OpenAI, APIError

def chat_with_retry(client, messages, model, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            return response.choices[0].message.content
        except APIError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"请求失败，{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                raise
```

### 2. 成本优化

```python
# 使用便宜的模型处理简单任务
def smart_model_selection(task_complexity):
    if task_complexity == "simple":
        return "alibaba/qwen-turbo"  # ¥0.3/¥0.6
    elif task_complexity == "medium":
        return "deepseek/deepseek-v3.2"  # ¥2/¥3
    else:
        return "zhipu/glm-4.6"  # ¥2/¥8

model = smart_model_selection("simple")
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "你好"}]
)
```

### 3. 流式输出（提升用户体验）

```python
def stream_chat(client, messages, model):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True
    )
    
    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    print()  # 换行
    return full_response
```

### 4. Token 计数（成本控制）

```python
import tiktoken

def count_tokens(text, model="gpt-3.5-turbo"):
    """估算 token 数量"""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# 使用示例
user_input = "这是一段很长的文本..."
token_count = count_tokens(user_input)
print(f"预计消耗 {token_count} tokens")

# 根据 token 数选择模型
if token_count > 10000:
    model = "moonshot/kimi-latest"  # 长上下文模型
else:
    model = "deepseek/deepseek-v3.2"  # 标准模型
```

### 5. 批量处理

```python
import asyncio
from openai import AsyncOpenAI

async def batch_chat(client, tasks):
    """并发处理多个任务"""
    async def process_one(task):
        response = await client.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[{"role": "user", "content": task}]
        )
        return response.choices[0].message.content
    
    results = await asyncio.gather(*[process_one(task) for task in tasks])
    return results

# 使用示例
client = AsyncOpenAI(
    base_url="https://router.shengsuanyun.com/api/v1",
    api_key="<your-api-key>"
)

tasks = ["任务1", "任务2", "任务3"]
results = asyncio.run(batch_chat(client, tasks))
```

---

## 快速开始模板

### AutoHySeeker 集成示例

```python
# src/common/llm_client.py
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://router.shengsuanyun.com/api/v1",
    api_key="<your-api-key>",
    timeout=60.0
)

async def chat_completion(messages, model="deepseek/deepseek-v3.2", **kwargs):
    """胜算云 LLM 调用封装"""
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    except Exception as e:
        # 降级到备用模型
        if model != "alibaba/qwen-plus":
            return await chat_completion(
                messages, 
                model="alibaba/qwen-plus", 
                **kwargs
            )
        raise
```

---

## 📝 更新日志

| 日期 | 变更内容 | 操作人 |
|------|---------|--------|
| 2026-03-07 | 初始创建胜算云 API 使用指南 | Pi |

---

*如有 API 变更，请及时更新本文档。*
