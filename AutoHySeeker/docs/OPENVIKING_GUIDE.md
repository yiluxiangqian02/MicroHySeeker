# OpenViking 使用指南 (AutoHySeeker)

> 适用版本: OpenViking v5.0 embedded mode
> 更新日期: 2026-03-21

---

## 1. 概述

OpenViking 是 AutoHySeeker 的知识库引擎，负责：
- 存储和检索实验记录、运维日志、文献、分析结果
- 自动生成多层级摘要 (L0 摘要 / L1 概览)
- 基于 embedding 的语义搜索

### 架构位置

```
AutoHySeeker
  └── OpenVikingClient (src/knowledge/viking_client.py)
        └── SyncOpenViking (OpenViking SDK, embedded mode)
              ├── VikingFS (AGFS 文件系统)
              ├── VectorDB (本地向量数据库, LevelDB + 持久化索引)
              └── 后台处理管线 (Semantic + Embedding 异步队列)
```

---

## 2. 资源处理管线

**写入一个资源后，OpenViking 会自动完成以下全部流程：**

```
add_resource(path)
  │
  ├─ [同步] 解析文件 (PDF/Markdown/代码/…) → 写入 VikingFS
  │                     ↓ 自动入队 SemanticQueue
  ├─ [异步] 为每个文件调 LLM 生成摘要
  ├─ [异步] 为每个目录生成 .overview.md (L1) 和 .abstract.md (L0)
  │                     ↓ 自动入队 EmbeddingQueue
  ├─ [异步] 调 embedding API 计算向量
  └─ [异步] 写入向量数据库 → 资源变为可搜索
```

**关键特性：**
- `add_resource()` 返回后，文件已存储但尚未可搜索
- 必须调用 `wait_processed()` 或传 `wait=True` 才能保证搜索到
- L0/L1 生成需要 VLM (LLM) 可用；不可用时降级为简单标题摘要
- 向量化需要 embedding API 可用
- 向量索引**持久化到磁盘**，重启不丢失

---

## 3. 配置

### 配置文件位置

查找顺序：
1. 环境变量 `OPENVIKING_CONFIG_FILE`
2. `OpenViking/.local_dev/ov.conf` (AutoHySeeker 自动设置)
3. `~/.openviking/ov.conf`

### 最小必需配置

```json
{
  "storage": {
    "workspace": "/path/to/workspace"
  },
  "embedding": {
    "dense": {
      "provider": "openai",
      "model": "baai/bge-m3",
      "api_key": "your-key",
      "api_base": "https://your-endpoint/api/v1",
      "dimension": 1024
    }
  }
}
```

### 可选：启用 L0/L1 自动生成

需要配置 VLM (大语言模型)：

```json
{
  "vlm": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "your-key",
    "api_base": "https://api.openai.com/v1",
    "max_concurrent": 10
  }
}
```

### 完整配置项参考

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `storage.workspace` | string | 必需 | VikingFS 数据存储目录 |
| `storage.vectordb.backend` | string | `"local"` | `"local"` (嵌入式) 或云端 VikingDB |
| `storage.vectordb.dimension` | int | `1536` | 必须与 embedding 模型维度一致 |
| `storage.agfs.mode` | string | `"http"` | `"binding-client"` 用于本地高性能模式 |
| `embedding.dense.provider` | string | 必需 | `"openai"`, `"volcengine"`, `"jina"` |
| `embedding.dense.model` | string | 必需 | embedding 模型名 |
| `embedding.dense.dimension` | int | 必需 | 向量维度 |
| `embedding.max_concurrent` | int | `10` | 最大并发 embedding 请求数 |
| `vlm.provider` | string | 可选 | L0/L1 生成用的 LLM |
| `vlm.model` | string | 可选 | LLM 模型名 |
| `default_search_limit` | int | `3` | search/find 默认返回数量 |
| `default_search_mode` | string | `"fast"` | `"fast"` 或 `"thinking"` |
| `log.level` | string | `"INFO"` | 日志级别 |

---

## 4. API 参考

### 4.1 初始化与关闭

```python
import openviking as ov

# 创建客户端 (单例模式)
client = ov.SyncOpenViking(path="./ov_workspace")
client.initialize()

# 使用完毕
client.close()
```

### 4.2 资源写入

```python
# 写入文件 (PDF, Markdown, 代码, 图片等)
result = client.add_resource(
    path="/data/papers/seawater_electrolysis.pdf",
    target="viking://resources/literature/",  # 可选：指定目标分区
    reason="海水电解文献",                     # 可选：写入原因
    wait=True,                                 # True = 等待处理完成
    timeout=120,                               # 超时秒数
)
root_uri = result["root_uri"]
# → "viking://resources/literature/seawater_electrolysis/"

# 也支持: 目录, URL, GitHub 仓库地址
client.add_resource(path="https://github.com/user/repo", wait=True)

# 异步写入 + 手动等待
client.add_resource(path="file.md")
client.wait_processed(timeout=60)  # 等待所有后台队列清空
```

### 4.3 搜索

```python
# 快速语义搜索 (纯向量检索, 速度快)
results = client.find(
    query="NiCoP 催化剂过电位",
    target_uri="viking://resources/literature/",  # 限定搜索范围
    limit=5,
    score_threshold=0.3,                          # 最低相似度阈值
)

# 完整检索 (含 LLM 意图分析, 质量更高但更慢)
results = client.search(
    query="间歇电解稳定性测试方法",
    limit=10,
)

# 遍历结果
for ctx in results.resources:
    print(f"URI:   {ctx.uri}")
    print(f"Score: {ctx.score}")
    print(f"摘要:  {ctx.abstract[:200]}")
    print(f"层级:  L{ctx.level}")  # 0=摘要, 1=概览, 2=详情
```

### 4.4 读取 L0/L1 摘要

```python
# L0 摘要 (简短)
abstract = client.abstract("viking://resources/literature/seawater_electrolysis/")

# L1 概览 (结构化详情)
overview = client.overview("viking://resources/literature/seawater_electrolysis/")
```

### 4.5 读取原始文件

```python
# 读取文件内容
content = client.read("viking://resources/experiments/run_001.json/run_001.json")

# 列目录
items = client.ls("viking://resources/experiments/", simple=True)

# 目录树
tree = client.tree("viking://resources/")
```

### 4.6 删除与移动

```python
# 删除 (目录需要 recursive=True)
client.rm("viking://resources/old_paper/", recursive=True)

# 移动/重命名
client.mv("viking://resources/draft/", "viking://resources/final/")
```

### 4.7 关联管理

```python
# 建立资源关联
client.link(
    from_uri="viking://resources/experiments/run_005/",
    uris="viking://resources/literature/seawater_electrolysis/",
    reason="该实验参考了这篇文献的方法",
)

# 查看关联
relations = client.relations("viking://resources/experiments/run_005/")

# 删除关联
client.unlink(
    from_uri="viking://resources/experiments/run_005/",
    uri="viking://resources/literature/seawater_electrolysis/",
)
```

### 4.8 会话管理 (可选)

```python
# 创建对话会话
session = client.create_session()
session_id = session["id"]

# 添加消息
client.add_message(session_id, role="user", content="分析最近的实验结果")
client.add_message(session_id, role="assistant", content="根据数据...")

# 归档会话 (提取长期记忆)
client.commit_session(session_id)

# 带会话上下文的搜索 (搜索结果会考虑对话历史)
results = client.search("过电位趋势", session_id=session_id)
```

---

## 5. 支持的文件类型

| 类型 | 扩展名 | 说明 |
|------|--------|------|
| Markdown | `.md`, `.markdown` | 按章节智能切分 |
| 纯文本 | `.txt` | 按段落切分 |
| PDF | `.pdf` | 自动转 Markdown |
| Word | `.doc`, `.docx` | |
| PowerPoint | `.ppt`, `.pptx` | |
| Excel | `.xls`, `.xlsx` | |
| 代码 | `.py`, `.ts`, `.go`, `.rs`, `.java` 等 50+ 种 | 按文件/模块组织 |
| 图片 | `.png`, `.jpg`, `.svg` 等 | 需 VLM 支持 |
| 网页/URL | HTTP/HTTPS 地址 | 自动抓取并解析 |
| GitHub 仓库 | GitHub URL | 克隆并解析代码 |
| 目录 | 本地目录路径 | 递归处理所有文件 |

---

## 6. AutoHySeeker 中的使用方式

### 通过 OpenVikingClient 封装层

AutoHySeeker 不直接使用 `SyncOpenViking`，而是通过 `OpenVikingClient` 封装层，提供：
- 五分区管理 (`experiments`, `operations`, `literature`, `analysis`, `projects`)
- SDK 不可用时的三级回退 (SDK → workspace 文件搜索 → 内存 fallback)
- 标准化的 URI 映射

```python
from src.knowledge.viking_client import OpenVikingClient

client = OpenVikingClient()  # 自动加载 ov.conf

# 写入实验记录到 experiments 分区
result = client.write_json(
    partition="experiments",
    payload={"run_id": "run_001", "params": {"Fe": 0.5}, "metrics": {"ovp": 200}},
    resource_name="run_001.json",
)

# 搜索
hits = client.search("Fe含量高的实验", partition="experiments", top_k=5)

# 读取
content = client.read("viking://resources/experiments/run_001/")
```

### 各模块调用关系

| 调用者 | 操作 | 触发时机 |
|--------|------|---------|
| `run_optimization` | `archive_experiment()` | 每轮实验结束后 |
| `ExperimentExecutorAgent` | `archive_operation()` | 检测到异常时 |
| `ExperimentDesignerAgent` | `search()` (literature) | 设计实验前查文献 |
| `DiagnosticsExpertAgent` | `search()` (operations) | 诊断故障时查历史 |
| `ChatAgent` | `search()` (all) | 用户查询知识库时 |

---

## 7. 语义搜索精度 (Benchmark)

基于 Nature 论文 (NiCoP-Cr2O3 海水电解 10000h) 的实测结果：

| 指标 | 结果 |
|------|------|
| Embedding 模型 | baai/bge-m3 (1024维) |
| 文献分段数 | 27 chunks |
| 测试查询数 | 12 |
| **命中率 (Hit Rate)** | **91.7%** |
| **平均 Precision@3** | **0.444** |
| **评级** | **B (基本可用)** |

详细结果: `tests/_tmp_manual/benchmark_results.json`

### 优化建议

1. 写入时附加中文摘要/关键词，提升跨语言检索
2. 文献按段落而非章节切分，细粒度提高匹配精度
3. 考虑为 `_fallback_search` 增加分词匹配（当前仅支持完整子串匹配）

---

## 8. 常见问题

### Q: engine.pyd DLL 加载失败？
当前 Windows 开发环境下 OpenViking 的 C++ 原生引擎 (`engine.pyd`) 可能因缺少运行时库而无法加载。此时 `OpenVikingClient` 自动降级为 fallback 模式（内存存储 + 关键词搜索）。Linux 部署环境或重新编译后可正常使用。

### Q: embedding API 401 错误？
检查 `OpenViking/.local_dev/ov.conf` 中的 `embedding.dense.api_key` 是否正确。

### Q: 向量索引重启后丢失？
不会。当 `workspace` 路径非空时，OpenViking 使用 `PersistentIndex` + LevelDB，索引持久化到磁盘，重启后自动恢复。

### Q: add_resource 后搜索不到？
必须等待后台处理完成。使用 `add_resource(wait=True)` 或调用 `wait_processed()`。
