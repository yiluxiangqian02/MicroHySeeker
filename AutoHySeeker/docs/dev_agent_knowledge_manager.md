# Agent E — KnowledgeManager 开发指南

> 代号：KM | 优先级：P3 (Week 7) | 域：RAG 知识管理
> 总体架构参考：[`langgraph_architecture.md`](langgraph_architecture.md) | Tool/Skill定义参考：[`skills_architecture.md`](skills_architecture.md)

---

## 一、Agent 概览

### 1.1 职责定位

KnowledgeManager 是**知识库管理员** — 支撑其他所有 Agent 的知识底座：

- 文档入库：PDF/手册/论文 → 分块+Embedding → ChromaDB（E1）
- 知识问答：自然语言问题 → RAG 检索+LLM 生成回答（E2）
- 实验归档：完成的实验 → 结构化知识条目 → 入库供后续参考（E3）

### 1.2 拥有的 Skills

| Skill | 名称 | LLM 角色 | 必须 LLM? |
|-------|------|----------|-----------|
| **E1** | `build_knowledge_base` | 文档摘要生成 | ✅ 不需要（可选摘要） |
| **E2** | `knowledge_qa` | RAG 问答 | ❌ 必须 |
| **E3** | `auto_archive_experiment` | 归档摘要 | ✅ 不需要（可选摘要） |

### 1.3 被调用关系

```
ExperimentDesigner (B) ──→ KM.E2  "CV 扫速一般用多少？"
DiagnosticsExpert (D)  ──→ KM.E2  搜索错误解决方案
Orchestrator           ──→ KM.E1  "帮我把这篇论文入库"
Orchestrator           ──→ KM.E2  直接知识问答
ExperimentSupervisor   ──→ KM.E3  实验完成后自动归档（Phase 3+）
```

KM 是**服务型 Agent**，通常不直接面向用户，而是被其他 Agent 调用。

---

## 二、LangGraph Subgraph 设计

### 2.1 State 定义

```python
class KnowledgeState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 任务类型
    task: Literal["ingest", "query", "archive"]
    
    # E1: 入库
    source_type: str | None        # "pdf" | "text" | "manual"
    source_path: str | None
    collection: str | None         # 目标集合
    metadata: dict | None
    
    # E2: 问答
    query: str | None
    collections: list[str] | None  # 搜索范围
    
    # E3: 归档
    run_dir: str | None
    
    # 结果
    ingest_result: dict | None     # {doc_id, chunks_count, summary}
    search_results: list[dict]     # [{chunk, score, metadata, source}]
    answer: str | None             # LLM 生成的回答
    confidence: float | None
    results: dict | None           # 通用结果
```

### 2.2 Graph 结构

```python
def build_knowledge_graph():
    graph = StateGraph(KnowledgeState)
    
    graph.add_node("route_task", route_task_node)
    graph.add_node("ingest_document", ingest_document_node)
    graph.add_node("search_and_answer", search_and_answer_node)
    graph.add_node("archive_experiment", archive_experiment_node)
    
    graph.add_edge(START, "route_task")
    graph.add_conditional_edges("route_task", route_km_task, {
        "ingest": "ingest_document",
        "query": "search_and_answer",
        "archive": "archive_experiment",
    })
    graph.add_edge("ingest_document", END)
    graph.add_edge("search_and_answer", END)
    graph.add_edge("archive_experiment", END)
    
    return graph.compile()
```

---

## 三、节点函数设计

### 3.1 `ingest_document_node` — 文档入库 (E1)

```python
async def ingest_document_node(state: KnowledgeState) -> dict:
    """
    E1: 文档 → 分块 → Embedding → ChromaDB
    
    LLM: 可选（生成文档摘要作为 metadata）
    """
    source_type = state["source_type"]
    source_path = state["source_path"]
    collection = state.get("collection", "domain_knowledge")
    
    if source_type == "pdf":
        result = rag_tools.ingest_pdf(source_path, collection=collection)
    elif source_type == "text":
        text = Path(source_path).read_text(encoding="utf-8")
        result = rag_tools.ingest_text(
            text=text,
            metadata=state.get("metadata", {}),
            collection=collection,
        )
    
    # 可选：LLM 生成摘要
    summary = None
    if llm_available:
        # 取前几个 chunk 生成摘要
        summary = await llm_client.chat(
            system="生成以下文档的简短摘要（3-5句话）。",
            user=result.get("first_chunks_text", "")[:2000],
        )
    
    return {
        "ingest_result": {
            "doc_id": result["doc_id"],
            "chunks_count": result["chunks_count"],
            "collection": collection,
            "summary": summary,
        },
        "results": result,
    }
```

### 3.2 `search_and_answer_node` — 知识问答 (E2)

```python
async def search_and_answer_node(state: KnowledgeState) -> dict:
    """
    E2: 语义搜索 → LLM 生成回答
    
    ★ LLM 必须：RAG 的核心是检索+生成。
    """
    query = state["query"]
    collections = state.get("collections", None)  # None = 搜索所有集合
    
    # 语义搜索
    if collections:
        all_results = []
        for col in collections:
            results = rag_tools.semantic_search(query=query, collection=col, top_k=3)
            all_results.extend(results)
        # 按 score 排序，取 top-k
        all_results.sort(key=lambda x: x["score"], reverse=True)
        search_results = all_results[:5]
    else:
        search_results = rag_tools.semantic_search(query=query, top_k=5)
    
    # LLM 生成回答
    context = "\n\n".join(
        f"[来源: {r.get('metadata', {}).get('source', '未知')}]\n{r['chunk']}"
        for r in search_results
    )
    
    answer = await llm_client.chat(
        system=KM_SYSTEM_PROMPT,
        user=f"问题: {query}\n\n相关知识:\n{context}\n\n请基于以上知识回答问题。如果知识不足以回答，请说明。",
    )
    
    return {
        "search_results": search_results,
        "answer": answer,
        "confidence": _calculate_confidence(search_results),
    }


def _calculate_confidence(results: list[dict]) -> float:
    """根据搜索结果的相似度评估回答置信度"""
    if not results:
        return 0.0
    avg_score = sum(r["score"] for r in results) / len(results)
    top_score = results[0]["score"]
    return min(1.0, top_score * 0.7 + avg_score * 0.3)
```

### 3.3 `archive_experiment_node` — 实验归档 (E3)

```python
async def archive_experiment_node(state: KnowledgeState) -> dict:
    """
    E3: 实验结果 → 结构化知识条目 → 入库
    
    LLM: 可选（生成实验总结作为知识条目）
    """
    run_dir = state["run_dir"]
    
    # 读取实验数据
    summary = data_reader.read_run_summary(run_dir)
    plan = data_reader.read_experiment_plan(run_dir)
    
    # 构建知识条目
    knowledge_entry = {
        "experiment_name": summary.get("name", ""),
        "date": summary.get("date", ""),
        "technique": _extract_techniques(plan),
        "parameters": _extract_key_params(plan),
        "status": summary.get("status", ""),
        "results_summary": summary.get("details", {}),
    }
    
    # 可选：LLM 生成实验总结
    if llm_available:
        text_summary = await llm_client.chat(
            system="将以下实验数据总结为一段知识条目，重点描述实验条件和结果。",
            user=json.dumps(knowledge_entry, ensure_ascii=False, indent=2),
        )
        knowledge_entry["llm_summary"] = text_summary
    
    # 入库
    result = rag_tools.ingest_experiment_knowledge(
        run_dir=run_dir,
        metadata=knowledge_entry,
    )
    
    return {
        "ingest_result": result,
        "results": {"archived": True, "doc_id": result["doc_id"]},
    }
```

---

## 四、RAG 基础设施

### 4.1 Embedding 模型

```python
# src/rag/embeddings.py
class EmbeddingManager:
    """Embedding 模型统一管理"""
    
    def __init__(self, config):
        if config.provider == "local":
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(config.model)  # e.g. "BAAI/bge-m3"
        elif config.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI()
            self.model_name = config.model  # e.g. "text-embedding-3-small"
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        if hasattr(self, 'model'):
            return self.model.encode(texts).tolist()
        else:
            resp = self.client.embeddings.create(input=texts, model=self.model_name)
            return [d.embedding for d in resp.data]
```

### 4.2 向量库

```python
# src/rag/vector_store.py
import chromadb

class VectorStore:
    def __init__(self, persist_dir: str):
        self.client = chromadb.PersistentClient(path=persist_dir)
    
    def get_or_create_collection(self, name: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(name=name)
    
    def add_documents(self, collection: str, texts: list[str], 
                      embeddings: list, metadatas: list[dict], ids: list[str]):
        col = self.get_or_create_collection(collection)
        col.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
    
    def query(self, collection: str, query_embedding: list, top_k: int = 5):
        col = self.get_or_create_collection(collection)
        return col.query(query_embeddings=[query_embedding], n_results=top_k)
```

### 4.3 知识库集合设计

| 集合 | 内容 | 来源 | 初始化时机 |
|------|------|------|-----------|
| `instrument_manual` | CHI 660F 手册、泵手册 | PDF 入库 | Phase 3 Week 7 |
| `domain_knowledge` | 电化学基础知识 | 教材/文档 | Phase 3 Week 7 |
| `error_solutions` | 错误→解决方案 | 手工+D1积累 | Phase 3 Week 7 |
| `experiment_archive` | 历史实验结果 | E3 自动归档 | Phase 3+ 持续增长 |
| `literature` | 学术文献 | PDF 入库 | 用户按需 |

---

## 五、System Prompt

```python
KM_SYSTEM_PROMPT = """你是 AutoHySeeker 系统的知识库助手（KnowledgeManager）。

你的专业领域：
- 电化学实验方法和理论
- MicroHySeeker 微流控实验平台
- CHI 660F 电化学工作站操作

回答原则：
1. 严格基于检索到的知识回答，不要编造
2. 如果检索结果不足以回答，明确说明
3. 引用来源文档
4. 区分"确定的事实"和"推测的建议"
5. 如涉及安全问题，优先强调注意事项
"""
```

---

## 六、开发清单（Week 7）

```
Week 7:
  ☐ rag/embeddings.py — Embedding 模型封装（本地 BGE-M3 + OpenAI）
  ☐ rag/vector_store.py — ChromaDB 封装
  ☐ rag/chunker.py — 文本分块（RecursiveCharacterTextSplitter）
  ☐ rag/pdf_parser.py — PDF 解析（pymupdf）
  ☐ rag/collections.py — 集合管理
  ☐ tools/rag_tools.py — 全部 7 函数
  ☐ graph/state.py — KnowledgeState
  ☐ graph/knowledge_graph.py — 图定义
  ☐ agents/knowledge_nodes.py — 全部节点
  ☐ skills/knowledge/build_knowledge_base.py (E1)
  ☐ skills/knowledge/knowledge_qa.py (E2)
  ☐ skills/knowledge/auto_archive.py (E3)
  ☐ 初始化知识库：CHI 660F 手册 + 错误知识库
  ☐ CLI: python -m autohyseeker.cli ask-kb "..."
  ☐ CLI: python -m autohyseeker.cli ingest <pdf_path>
  ☐ CLI: python -m autohyseeker.cli archive <run_dir>
```

---

## 七、注意事项

### 7.1 本地 vs 远程 Embedding

- **开发/测试**：用本地 BGE-M3（sentence-transformers），无需 API
- **生产**：可切换 OpenAI text-embedding-3-small（更快、更准）
- 切换通过 `configs/rag_config.toml` 配置

### 7.2 中文支持

BGE-M3 原生支持中英文混合。实验数据既有中文标签也有英文指标名，需要确保分块策略不会切断中英文混合句子。

### 7.3 Phase 1 的过渡方案

Phase 1 没有 RAG，需要在代码中做好接口预留：

```python
# Phase 1: 硬编码降级
if rag_available:
    results = rag_tools.semantic_search(...)
else:
    results = []  # 或查硬编码知识库
```

D Agent 的 `search_solutions` 节点在 Phase 1 使用 `ERROR_KNOWLEDGE_BASE` dict，Phase 3 升级为 RAG。

---

*此文档可直接作为 KnowledgeManager Agent 的开发执行依据。*
