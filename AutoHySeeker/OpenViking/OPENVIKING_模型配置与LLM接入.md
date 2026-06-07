# OpenViking 模型配置与 LLM 接入情况

> 2026-04-20 调研报告

---

## 一、总体实现状态

✅ **已完整实现**：OpenViking 具备完整的模型配置管理系统和多个 LLM 提供商的接入实现。

---

## 二、配置管理体系

### 2.1 核心配置类

**位置**：`openviking_cli/utils/config/`

| 配置类 | 用途 | 关键字段 |
|--------|------|---------|
| `OpenVikingConfig` | 主配置器（汇总层） | `embedding`, `vlm`, `storage`, `log` 等 |
| `EmbeddingConfig` | Embedding 模型配置 | `dense`, `sparse`, `hybrid` |
| `EmbeddingModelConfig` | 单个 Embedding 模型配置 | `model`, `api_key`, `provider`, `dimension` |
| `VLMConfig` | LLM / 视觉大模型配置 | `model`, `api_key`, `api_base`, `provider` |
| `ConfigLoader` | 配置文件加载器 | 从 JSON / 环境变量加载 |

### 2.2 配置文件加载流程

```
环境变量 OPENVIKING_CONFIG_FILE
    ↓
JSON 配置文件 (~/.openviking/ov.conf)
    ↓
ConfigLoader.load() → 解析 JSON
    ↓
OpenVikingConfig.from_dict() → 生成配置对象
    ↓
各模块使用相应配置
```

---

## 三、LLM 接入实现

### 3.1 VLM（视觉语言模型）后端

**位置**：`openviking/models/vlm/`

#### 已实现的后端

| 后端 | 位置 | 支持功能 | 状态 |
|------|------|---------|------|
| **OpenAI** | `backends/openai_vlm.py` | 文本补全、图像理解 | ✅ 完整实现 |
| **VolcEngine** | `backends/volcengine_vlm.py` | 文本补全、多模态、思维链 | ✅ 完整实现 |
| **LiteLLM** | `backends/litellm_vlm.py` | 统一代理（支持 100+ 模型） | ✅ 完整实现 |

#### VLM 核心接口（`base.py`）

```python
class VLMBase(ABC):
    # 文本补全
    def get_completion(self, prompt: str, thinking: bool = False) -> str
    async def get_completion_async(self, prompt: str, thinking: bool = False) -> str
    
    # 视觉补全（支持图像输入）
    def get_vision_completion(self, prompt: str, images: List[Union[str, Path, bytes]]) -> str
    async def get_vision_completion_async(self, prompt: str, images: [...]]) -> str
    
    # 配置检查
    def is_available(self) -> bool
    
    # Token 使用追踪
    def update_token_usage(self, model_name: str, provider: str, ...) -> None
```

---

### 3.2 嵌入模型（Embedding）后端

**位置**：`openviking/models/embedder/`

#### 已实现的后端

| 后端 | 位置 | 支持向量类型 | 状态 |
|------|------|-----------|------|
| **OpenAI** | `openai_embedders.py` | 密集向量 | ✅ |
| **VolcEngine** | `volcengine_embedders.py` | 密集向量 + 稀疏向量混合 | ✅ |
| **Jina** | `jina_embedders.py` | 密集向量 | ✅ |
| **VikingDB** | `vikingdb_embedders.py` | 密集 + 稀疏混合 | ✅ |

#### Embedding 核心接口（`base.py`）

```python
class EmbedderBase(ABC):
    def embed(self, text: str) -> EmbedResult
    async def embed_async(self, text: str) -> EmbedResult
    def embed_batch(self, texts: List[str]) -> List[EmbedResult]
    async def embed_batch_async(self, texts: List[str]) -> List[EmbedResult]

class EmbedResult:
    dense_vector: Optional[List[float]]      # 密集向量
    sparse_vector: Optional[Dict[str, float]] # 稀疏向量
    is_dense, is_sparse, is_hybrid: bool
```

---

## 四、Provider 支持与配置

### 4.1 支持的 Provider

| Provider | VLM 支持 | Embedding 支持 | 推荐用途 |
|----------|----------|---------------|---------|
| **OpenAI** | ✅ | ✅ | 国际模型，稳定可靠 |
| **VolcEngine**（豆包）| ✅ | ✅ | 国内首选，成本低 |
| **Jina** | ❌ | ✅ | 开源向量化方案 |
| **VikingDB** | ❌ | ✅ | 混合向量检索 |
| **LiteLLM** | ✅ | ❌ | 模型统一适配 |

### 4.2 多 Provider 配置示例

```json
{
  "embedding": {
    "dense": {
      "provider": "volcengine",
      "model": "doubao-embedding-vision-250615",
      "api_key": "xxxx",
      "api_base": "https://ark.cn-beijing.volces.com/api/v3",
      "dimension": 1024
    }
  },
  "vlm": {
    "providers": {
      "volcengine": {
        "model": "doubao-seed-1-8-251228",
        "api_key": "xxxx",
        "api_base": "https://ark.cn-beijing.volces.com/api/v3"
      },
      "openai": {
        "model": "gpt-4-vision-preview",
        "api_key": "sk-xxxx",
        "api_base": "https://api.openai.com/v1"
      }
    },
    "default_provider": "volcengine"
  }
}
```

---

## 五、配置验证与错误处理

### 5.1 配置验证机制

OpenViking 使用 **Pydantic 数据验证** 确保配置的合法性：

```python
# VLMConfig 验证示例
class VLMConfig(BaseModel):
    model: Optional[str]  # 必须填
    api_key: Optional[str]  # 必须填
    provider: Optional[str]  # 必须填
    
    @model_validator(mode="after")
    def validate_config(self):
        if self._has_any_config():
            if not self.model:
                raise ValueError("VLM requires 'model'")
            if not self._get_effective_api_key():
                raise ValueError("VLM requires 'api_key'")
```

### 5.2 错误提示

| 错误场景 | 错误信息 | 解决方案 |
|---------|---------|---------|
| 缺少 model | `VLM configuration requires 'model' to be set` | 配置 `vlm.model` |
| 缺少 api_key | `VLM configuration requires 'api_key' to be set` | 配置 `vlm.api_key` |
| Provider 不支持 | `Invalid embedding provider: 'xxx'` | 选择 openai/volcengine/jina/vikingdb |

---

## 六、使用方式

### 6.1 初始化客户端

```python
import openviking as ov
from openviking_cli.utils.config.open_viking_config import OpenVikingConfig
import json

# 方式 1：从配置文件加载
with open("~/.openviking/ov.conf", "r") as f:
    config_dict = json.load(f)
config = OpenVikingConfig.from_dict(config_dict)
client = ov.SyncOpenViking(path="./data", config=config)

# 方式 2：通过环境变量加载
# 设置 OPENVIKING_CONFIG_FILE=~/.openviking/ov.conf
client = ov.SyncOpenViking(path="./data")

# 初始化
client.initialize()
```

### 6.2 查看配置是否生效

```python
# VLM 可用性检查
if client._async_client._vlm and client._async_client._vlm.is_available():
    print("VLM 已配置并可用")

# Embedding 可用性检查
if client._async_client._embedder:
    print("Embedding 已配置并可用")
```

---

## 七、在 AutoHySeeker 中的使用情况

### 7.1 当前集成

| 组件 | 集成状态 | 说明 |
|------|---------|------|
| OpenViking 核心库 | ✅ | 已导入 AutoHySeeker/OpenViking 目录 |
| 模型配置 | ❓ | **未检查** - 需查看 AutoHySeeker 主程序配置 |
| 文献 Embedding | ❓ | **未使用** - MinerU 解析结果未接入 OpenViking |
| 向量检索 | ❓ | **未使用** - 检索模块未启用 |
| 记忆管理 | ❓ | **未使用** - 会话记忆未启用 |

### 7.2 建议后续接入点

1. **立即可用**：将 MinerU 解析的论文 Markdown 导入 OpenViking resources
2. **需配置**：在 AutoHySeeker 项目中添加 `ov.conf` 配置文件，配置豆包 Embedding 模型
3. **可扩展**：将实验结果、参数调优记录存至 agent/memories，实现经验积累

---

## 八、源码关键路径

```
openviking/
├── models/
│   ├── vlm/
│   │   ├── base.py                 # VLM 抽象基类
│   │   ├── llm.py                  # LLM 统一包装
│   │   └── backends/
│   │       ├── openai_vlm.py       # OpenAI 后端
│   │       ├── volcengine_vlm.py   # VolcEngine 后端
│   │       └── litellm_vlm.py      # LiteLLM 后端
│   └── embedder/
│       ├── base.py                 # Embedder 抽象基类
│       ├── openai_embedders.py
│       ├── volcengine_embedders.py
│       ├── jina_embedders.py
│       └── vikingdb_embedders.py

openviking_cli/utils/config/
├── open_viking_config.py           # 主配置类
├── vlm_config.py                   # VLM 配置类
├── embedding_config.py             # Embedding 配置类
├── config_loader.py                # 配置加载器
└── ...其他配置

examples/chatmem/chatmem.py          # 完整使用示例
```

---

## 总结

OpenViking **已完整实现**：
- ✅ Pydantic 配置管理系统
- ✅ 多 Provider 支持（OpenAI、VolcEngine、Jina、VikingDB 等）
- ✅ VLM 后端（OpenAI、VolcEngine、LiteLLM）
- ✅ Embedding 后端（OpenAI、VolcEngine、Jina、VikingDB）
- ✅ 配置验证和错误提示
- ✅ Token 使用追踪

**在 AutoHySeeker 中的集成**：代码库已导入，但**配置文件、模型接入、实际使用目前状态未知**，需进一步检查 AutoHySeeker 主程序。
