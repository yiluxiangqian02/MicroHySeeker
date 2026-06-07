# OpenViking 功能说明

> 本文档作为 OpenViking 在 AutoHySeeker 项目中的功能速查手册。

---

## 一、定位

OpenViking 是一个开源的、专为 **AI Agent** 设计的**上下文数据库**（Context Database）。

它解决的核心问题是：AI Agent 在执行长程任务时，记忆、资源、技能碎片化，传统 RAG 检索效果差、链路不透明的问题。

---

## 二、核心功能

### 1. 文件系统式上下文管理

OpenViking 用 **虚拟文件系统（`viking://` 协议）** 统一组织 Agent 所需的三类上下文：

```
viking://
├── resources/        # 资源：项目文档、代码库、网页、PDF 等
│   └── my_project/
│       ├── docs/
│       └── src/
├── user/             # 用户：个人偏好、习惯记忆
│   └── memories/
│       └── preferences/
└── agent/            # Agent：技能、指令、任务经验记忆
    ├── skills/
    ├── memories/
    └── instructions/
```

- 每条上下文有唯一 URI，可用 `ls`、`find`、`glob`、`read` 等类文件操作精确访问，告别黑箱式语义匹配。

---

### 2. 三层分级上下文加载（L0 / L1 / L2）

写入时自动生成三个层级，按需加载，大幅节省 Token：

| 层级 | 内容 | 用途 | Token 量级 |
|------|------|------|-----------|
| L0 `.abstract` | 一句话摘要 | 快速判断相关性 | ~100 tokens |
| L1 `.overview` | 核心信息 + 使用场景 | Agent 规划阶段决策 | ~2k tokens |
| L2 原始文件 | 完整原始数据 | 确有必要时深入读取 | 按实际大小 |

---

### 3. 目录递归检索（Hierarchical Retrieval）

比普通向量检索更精准的五步策略：

1. **意图分析** — 解析查询，生成多个检索条件
2. **初始定位** — 向量检索找到高分目录
3. **精细探索** — 在该目录内做二次检索
4. **递归下探** — 逐层递归子目录
5. **结果汇总** — 返回最相关上下文

核心实现：`openviking/retrieve/hierarchical_retriever.py`

---

### 4. 可视化检索轨迹（可观测性）

每次检索的目录浏览路径、文件定位过程完整留存，可追溯问题根源，指导优化检索逻辑。不再是黑箱。

---

### 5. 会话自动管理与记忆自迭代

会话结束后，系统自动：
- 压缩对话内容、资源引用、工具调用记录
- 提取长期记忆写回 `user/memories/` 和 `agent/memories/`
- Agent 越用越聪明，用户偏好自动积累

核心实现：`openviking/session/`（`session.py`、`memory_extractor.py`、`compressor.py`、`memory_deduplicator.py`）

---

## 三、主要 API（Python 客户端）

```python
import openviking as ov

client = ov.SyncOpenViking(path="./data")
client.initialize()

# 添加资源（支持 URL、本地文件、目录）
result = client.add_resource(path="./my_doc.pdf")
root_uri = result['root_uri']

# 浏览目录结构
client.ls(root_uri)

# 通配符查找文件
client.glob(pattern="**/*.md", uri=root_uri)

# 读取文件内容
client.read("viking://resources/my_project/docs/api.md")

# 等待语义处理完成（L0/L1 生成）
client.wait_processed()

# 获取摘要 / 概览
client.abstract(root_uri)
client.overview(root_uri)

# 语义检索
results = client.find("what is openviking", target_uri=root_uri)
for r in results.resources:
    print(r.uri, r.score)

client.close()
```

---

## 四、项目结构速览

```
OpenViking/
├── openviking/
│   ├── core/         # 核心引擎、文件系统抽象
│   ├── models/       # VLM / Embedding 模型封装
│   ├── parse/        # 资源解析（PDF、网页、代码库等）
│   ├── retrieve/     # 检索模块（分层递归检索、意图分析）
│   ├── storage/      # 向量数据库、文件系统队列
│   ├── session/      # 会话管理、记忆提取与去重
│   ├── message/      # 消息格式化
│   └── prompts/      # 各类任务提示词模板
├── src/              # C++ 扩展（高性能索引 + 存储）
├── crates/           # Rust CLI 扩展
├── vectordb/         # 向量数据库实现
├── examples/         # 使用示例
└── tests/            # 测试用例
```

---

## 五、依赖模型

需配置以下两类模型服务（支持火山引擎豆包、OpenAI 等兼容 OpenAI 格式的服务）：

| 类型 | 作用 | 推荐模型 |
|------|------|---------|
| **VLM（多模态大模型）** | 图像理解、内容摘要生成 | `doubao-seed-1-8-251228` / `gpt-4-vision-preview` |
| **Embedding 模型** | 向量化 + 语义检索 | `doubao-embedding-vision-250615` / `text-embedding-3-large` |

配置文件路径：`~/.openviking/ov.conf`，通过环境变量 `OPENVIKING_CONFIG_FILE` 指向。

---

## 六、在 AutoHySeeker 中的潜在用途

| 场景 | 说明 |
|------|------|
| 文献知识库管理 | 将 MinerU 解析出的论文 Markdown/图片作为资源导入，支持语义检索 |
| 实验记忆积累 | 将实验执行过程、参数调优经验写入 `agent/memories/`，后续实验自动参考 |
| 多轮对话上下文压缩 | 长实验会话结束后提取关键记忆，避免上下文超限 |
| 技能管理 | 将常用分析流程封装为 `agent/skills/`，复用于后续任务 |

---

> 官方文档：https://www.openviking.ai/docs  
> GitHub：https://github.com/volcengine/OpenViking
