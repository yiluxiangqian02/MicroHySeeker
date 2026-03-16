# 06 知识管理 Agent (Knowledge Manager)

## 1. 定位

**知识管理 Agent 是系统的"图书馆员"和"档案管理员"。**

它负责两件事：
1. **检索**：为其他 Agent 提供文献和历史实验知识（RAG）
2. **沉淀**：将实验结果自动归档为可检索的知识条目

类比：它是实验室的 **文献管理员**，帮助团队快速找到相关参考。

---

## 2. 职责范围

| 职责 | 描述 | 优先级 |
|------|------|--------|
| **文献检索** | 根据查询检索相关论文/知识 (RAG) | P0 |
| **历史查询** | 检索过去的实验结果和配比信息 | P0 |
| **知识沉淀** | 将新实验结果索引到知识库 | P1 |
| **上下文构建** | 为 Designer 提供参考配比/性能范围 | P1 |
| **文献导入** | 批量导入文献 PDF 到 ChromaDB | P2 |

### 不负责的工作
- ❌ 不做数据分析（Analyst 的工作）
- ❌ 不设计实验（Designer 的工作）
- ❌ 不做优化决策（Orchestrator 的工作）

---

## 3. 输入 / 输出

### 输入（来自其他 Agent 的查询）
```python
# 来自 Designer 的查询
{
    "action": "retrieve_knowledge",
    "query": "Fe-Co-Ni 三元合金催化剂 HER 最优配比范围",
    "context": {
        "elements": ["Fe", "Co", "Ni"],
        "target": "overpotential",
        "search_type": "literature"   # "literature" | "experiment_history" | "both"
    },
    "top_k": 5
}

# 来自 Orchestrator 的归档任务
{
    "action": "archive_experiment",
    "run_id": "20260315_154200_HER_Fe6Co25Ni15",
    "params": {"Fe": 0.6, "Co": 0.25, "Ni": 0.15},
    "metrics": {"overpotential_mV": 182.5, "current_density_mA_cm2": 15.3},
    "interpretation": "...",
}
```

### 输出
```python
# 检索结果
{
    "status": "retrieved",
    "results": [
        {
            "source": "literature",
            "title": "Ternary Fe-Co-Ni alloys for HER",
            "content": "研究表明 Fe:Co:Ni = 2:5:3 配比在酸性条件下展现最低过电位...",
            "relevance": 0.92,
            "reference": "DOI: 10.1021/xxx"
        },
        {
            "source": "experiment_history",
            "run_id": "20260310_xxx",
            "params": {"Fe": 0.3, "Co": 0.5, "Ni": 0.2},
            "result": {"overpotential_mV": 195.0},
            "relevance": 0.85
        }
    ],
    "summary": "根据文献和历史实验，Co 含量 > 40% 倾向于给出较低过电位。"
}

# 归档确认
{
    "status": "archived",
    "doc_id": "exp_20260315_xxx",
    "collection": "experiment_results"
}
```

---

## 4. 工具权限

| 工具 | 权限 | 用途 |
|------|------|------|
| `retrieve_knowledge()` | ✅ | RAG 检索 |
| `retrieve_literature()` | ✅ | 文献检索 |
| `parse_literature_from_chunk()` | ✅ | 解析文献引用 |
| `read_run_metadata()` | ✅ | 读取实验元数据 |
| `list_recent_experiments()` | ✅ | 历史实验列表 |
| `get_run_detail()` | ✅ | 实验详情 |

---

## 5. 当前实现状态

### 已有代码

| 文件 | 行数 | 状态 | 说明 |
|------|------|------|------|
| `agents/knowledge_mgr.py` | ~18 | ⚠️ Stub | 仅有类定义 + system prompt |
| `tools/knowledge_retriever.py` | ~100 | ✅ 基础 | RAG 检索函数 |
| `rag.py` | ~200 | ✅ 基础 | ChromaDB 集成 |

### 关键问题

1. **Agent 只有 system prompt**：没有结构化的检索和归档逻辑
2. **ChromaDB 集合定义不清**：需要明确实验历史 vs 文献 的集合分离
3. **缺少实验结果自动归档**：每次实验完成后应自动索引

---

## 6. 需要修改的内容

### 6.1 充实 `agents/knowledge_mgr.py`

```python
class KnowledgeManagerAgent(BaseAgent):
    """知识管理 Agent — RAG 检索 + 实验归档"""
    
    COLLECTIONS = {
        "literature": "学术文献知识",
        "experiment_results": "历史实验结果",
        "troubleshooting": "故障排查经验",
    }
    
    async def retrieve(self, task: dict) -> dict:
        """检索知识。"""
        query = task["query"]
        search_type = task.get("context", {}).get("search_type", "both")
        top_k = task.get("top_k", 5)
        
        results = []
        
        if search_type in ("literature", "both"):
            lit_results = self._search_collection("literature", query, top_k)
            results.extend(lit_results)
        
        if search_type in ("experiment_history", "both"):
            exp_results = self._search_collection("experiment_results", query, top_k)
            results.extend(exp_results)
        
        # LLM 生成摘要
        summary = await self._summarize_results(results, query)
        
        return {
            "status": "retrieved",
            "results": sorted(results, key=lambda x: x["relevance"], reverse=True)[:top_k],
            "summary": summary,
        }
    
    async def archive_experiment(self, task: dict) -> dict:
        """将实验结果归档到知识库。"""
        doc_text = self._format_experiment_doc(task)
        metadata = {
            "run_id": task["run_id"],
            "params": str(task["params"]),
            "metrics": str(task["metrics"]),
            "type": "experiment_result",
        }
        
        doc_id = self._add_to_collection("experiment_results", doc_text, metadata)
        
        return {"status": "archived", "doc_id": doc_id}
```

---

## 7. ChromaDB 集合设计

| 集合名 | 内容 | 索引方式 | 更新频率 |
|--------|------|---------|---------|
| `literature` | 学术论文摘要/关键结论 | 手动导入 | 低 |
| `experiment_results` | 每次实验的参数+结果 | 自动归档 | 每次实验后 |
| `troubleshooting` | 故障诊断经验 | Diagnostics 归档 | 每次故障后 |

### 实验结果文档格式
```text
实验: HER_Fe6Co25Ni15_round_3
日期: 2026-03-15
元素配比: Fe=0.6, Co=0.25, Ni=0.15
总体积: 1000 μL
过电位: 182.5 mV (@ 10 mA/cm²)
电流密度: 15.3 mA/cm²
Tafel 斜率: 68.2 mV/dec
数据质量: 0.92 (可靠)
结论: Fe 含量提升至 60% 显著改善了 HER 性能...
```

---

## 8. 与其他 Agent 的交互

```
Designer → Knowledge:
    "查询 Fe-Co-Ni 催化剂文献，获取推荐配比范围"

Analyst → Knowledge:
    "查询类似配比的历史实验结果作对比参考"

Orchestrator → Knowledge:
    "归档本轮实验结果到知识库"

Diagnostics → Knowledge:  (可选)
    "归档故障排查经验"
```

---

## 9. 执行计划

| 步骤 | 任务 | 涉及文件 | 依赖 |
|------|------|---------|------|
| 1 | 充实 knowledge_mgr.py，添加 retrieve 和 archive 方法 | `agents/knowledge_mgr.py` | 无 |
| 2 | 明确 ChromaDB 集合定义和初始化 | `rag.py` | 步骤 1 |
| 3 | 实现实验结果自动归档 | `agents/knowledge_mgr.py` | 步骤 2 |
| 4 | 接入 tools/knowledge_retriever.py | `agents/knowledge_mgr.py` | 步骤 1 |
| 5 | 更新 System Prompt | `agents/knowledge_mgr.py` | 步骤 1 |
| 6 | 添加单元测试 | `tests/test_knowledge.py` | 步骤 1-3 |
