# AutoHySeeker 后端开发指南

> 2026-02-27 | 状态：规划阶段
> 定位：AutoHySeeker 的 **服务端架构** — FastAPI + LangGraph + OpenViking
> 关联：[architecture_overview.md](architecture_overview.md) | [project_plan.md](project_plan.md) | [open_source_integration.md](open_source_integration.md)

---

## 一、系统定位

AutoHySeeker 后端是一个 **独立的 Python 服务进程**，通过 REST/WebSocket 对外暴露 AI 多 Agent 能力，同时通过 IPC 桥接与 MicroHySeeker 桌面端（PySide6）交互。

```
┌──────────────────────────────────────────────────────────────────────┐
│                       AutoHySeeker 后端                              │
│                                                                      │
│  ┌────────────┐   ┌────────────────┐   ┌──────────────────────────┐ │
│  │  FastAPI    │   │  LangGraph     │   │  OpenViking              │ │
│  │  HTTP/WS    │──▶│  Agent 编排    │──▶│  上下文数据库            │ │
│  │  Server     │   │  Orchestrator  │   │  (AGFS + VectorDB)       │ │
│  └────────────┘   └────────────────┘   └──────────────────────────┘ │
│        │                   │                       │                 │
│        │           ┌───────┴────────┐              │                 │
│        │           │  5 Expert      │              │                 │
│        │           │  Agents (A-E)  │              │                 │
│        │           └───────┬────────┘              │                 │
│        │                   │                       │                 │
│  ┌─────┴───────────────────┴───────────────────────┴──────────────┐ │
│  │                  Shared Tool Layer                              │ │
│  │  data_reader | echem_analysis | visualization | log_analysis   │ │
│  │  experiment_builder | experiment_control (Phase 4)             │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
         │                                             │
    HTTP/WS API                                   IPC Bridge
         │                                             │
    ┌────┴─────┐                              ┌────────┴────────┐
    │ Web 前端  │                              │ MicroHySeeker   │
    │ (React)  │                              │ (PySide6)       │
    └──────────┘                              └─────────────────┘
```

---

## 二、技术栈

| 层 | 技术 | 版本要求 | 说明 |
|---|---|---|---|
| HTTP 框架 | FastAPI | ≥0.110 | async 原生、OpenAPI 自动文档、WebSocket 内置 |
| Agent 编排 | LangGraph | ≥0.2 | StateGraph、条件边、Checkpoint、Human-in-the-loop |
| 上下文数据库 | OpenViking | 本地 fork | AGFS + 向量索引 + Session + 记忆 |
| LLM 客户端 | litellm | ≥1.0 | 统一 OpenAI/Claude/Doubao/本地模型 |
| 数据校验 | Pydantic | ≥2.0 | Request/Response 模型、Settings |
| 任务队列 | 内建 asyncio | — | 短期够用；规模化可引入 Celery |
| 数据库 | SQLite | — | LangGraph checkpoint + 结构化元数据 |
| 测试 | pytest + pytest-asyncio | — | 异步测试 |

---

## 三、项目目录结构

```
AutoHySeeker/
├── openviking/                    # OpenViking 本地 fork（魔改版）
├── docs/                          # 规划文档
└── src/
    └── autohyseeker/
        ├── __init__.py
        ├── __main__.py            # python -m autohyseeker
        │
        ├── server/                # ★ FastAPI 服务层
        │   ├── __init__.py
        │   ├── app.py             # FastAPI app 工厂、lifespan、CORS
        │   ├── routes/
        │   │   ├── __init__.py
        │   │   ├── chat.py        # POST /api/chat — 对话入口（走 Orchestrator）
        │   │   ├── agents.py      # POST /api/agents/{name}/invoke — 直接调用 Agent
        │   │   ├── experiments.py  # GET/POST /api/experiments — 实验管理
        │   │   ├── knowledge.py   # POST /api/knowledge — 知识入库/检索
        │   │   ├── sessions.py    # CRUD /api/sessions — Session 管理
        │   │   └── health.py      # GET /api/health — 健康检查
        │   ├── ws/
        │   │   ├── __init__.py
        │   │   └── stream.py      # WebSocket /ws/chat — 流式对话
        │   └── middleware/
        │       ├── __init__.py
        │       └── error_handler.py
        │
        ├── graph/                 # ★ LangGraph 编排层
        │   ├── __init__.py
        │   ├── state.py           # 所有 State TypedDict（唯一定义处）
        │   ├── orchestrator.py    # Orchestrator Graph
        │   ├── analyst_graph.py   # DataAnalyst Subgraph
        │   ├── designer_graph.py  # ExperimentDesigner Subgraph
        │   ├── supervisor_graph.py# ExperimentSupervisor Subgraph
        │   ├── diagnostics_graph.py # DiagnosticsExpert Subgraph
        │   └── knowledge_graph.py   # KnowledgeManager Subgraph
        │
        ├── agents/                # Agent 节点函数 + Prompt
        │   ├── __init__.py
        │   ├── router.py          # Orchestrator 路由节点
        │   ├── analyst_nodes.py   # DA 节点函数
        │   ├── designer_nodes.py  # ED 节点函数
        │   ├── supervisor_nodes.py# ES 节点函数
        │   ├── diagnostics_nodes.py # DX 节点函数
        │   ├── knowledge_nodes.py   # KM 节点函数
        │   └── prompts/
        │       ├── __init__.py
        │       ├── analyst.py
        │       ├── designer.py
        │       ├── supervisor.py
        │       ├── diagnostics.py
        │       └── knowledge.py
        │
        ├── tools/                 # ★ Tool 函数层（被 Agent 调用）
        │   ├── __init__.py
        │   ├── registry.py        # ToolRegistry — 统一注册 + Function Calling
        │   ├── data_reader.py     # 实验数据读取（8 函数）
        │   ├── echem_analysis.py  # 电化学分析（8 函数）
        │   ├── visualization.py   # 图表生成（6 函数）
        │   ├── log_analysis.py    # 日志分析（8 函数）
        │   ├── experiment_builder.py # 实验构建（11 函数）
        │   ├── report_generator.py   # 报告生成
        │   └── experiment_control.py # IPC 控制 MicroHySeeker（Phase 4）
        │
        ├── skills/                # Skill 层（组合 Tool + LLM）
        │   ├── __init__.py
        │   ├── diagnostics/       # D1, D2, D3
        │   ├── data_analysis/     # A1, A2, A3, A4
        │   ├── experiment_design/ # B1, B2, B3, B4
        │   ├── experiment_execution/ # C1, C2, C3
        │   └── knowledge_management/ # E1, E2, E3
        │
        ├── openviking_adapter/    # ★ OpenViking 适配层
        │   ├── __init__.py
        │   ├── client.py          # VikingKnowledgeBase 封装类
        │   ├── echem_parser.py    # 电化学 CSV Parser（提案1）
        │   ├── memory_config.py   # 记忆分类扩展配置（提案2）
        │   └── uri_conventions.py # Viking URI 命名约定
        │
        ├── bridge/                # ★ MicroHySeeker IPC 桥接层
        │   ├── __init__.py
        │   ├── protocol.py        # IPC 消息协议定义
        │   ├── ipc_client.py      # 连接 MicroHySeeker 的客户端
        │   └── event_bridge.py    # 事件桥接（MicroHySeeker 信号 → Agent 事件）
        │
        ├── config/                # 配置
        │   ├── __init__.py
        │   ├── settings.py        # Pydantic Settings（环境变量 + .toml）
        │   └── openviking.toml    # OpenViking 配置
        │
        └── cli/                   # CLI 入口
            ├── __init__.py
            └── main.py            # click CLI
```

---

## 四、FastAPI 服务层设计

### 4.1 App 工厂

```python
# server/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期：启动时初始化 OpenViking + LangGraph"""
    # Startup
    app.state.viking = await initialize_openviking()
    app.state.graphs = build_all_graphs()
    yield
    # Shutdown
    app.state.viking.close()

def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoHySeeker API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # React dev server
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    from .routes import chat, agents, experiments, knowledge, sessions, health
    app.include_router(chat.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")
    app.include_router(experiments.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    
    # WebSocket
    from .ws import stream
    app.include_router(stream.router)
    
    return app
```

### 4.2 核心 API 端点

#### 对话入口

```python
# server/routes/chat.py
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None     # 复用已有对话
    thread_id: str | None = None      # LangGraph checkpoint thread

class ChatResponse(BaseModel):
    response: str
    agent_used: str                    # 实际路由到的 Agent
    session_id: str
    figures: list[str] = []            # 生成的图表路径
    metadata: dict = {}

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    """对话入口 — 走 Orchestrator 路由到对应 Agent"""
    graphs = request.app.state.graphs
    viking = request.app.state.viking
    
    config = {"configurable": {"thread_id": req.thread_id or req.session_id}}
    result = await graphs["orchestrator"].ainvoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config,
    )
    
    return ChatResponse(
        response=result["final_response"],
        agent_used=result.get("current_agent", "direct"),
        session_id=req.session_id or "new",
        figures=result.get("figures", []),
    )
```

#### WebSocket 流式对话

```python
# server/ws/stream.py
from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """WebSocket 流式对话 — Agent 思考过程实时推送"""
    await ws.accept()
    
    try:
        while True:
            data = await ws.receive_json()
            message = data["message"]
            thread_id = data.get("thread_id", "ws_default")
            
            config = {"configurable": {"thread_id": thread_id}}
            
            # 流式执行：每个节点完成后推送中间状态
            async for event in graphs["orchestrator"].astream_events(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                version="v2",
            ):
                await ws.send_json({
                    "type": event["event"],           # "on_chain_start", "on_chain_end"
                    "node": event.get("name", ""),     # "router", "analyst", ...
                    "data": event.get("data", {}),
                })
    except Exception:
        await ws.close()
```

#### 直接调用 Agent

```python
# server/routes/agents.py
router = APIRouter(tags=["agents"])

@router.post("/agents/{agent_name}/invoke")
async def invoke_agent(agent_name: str, req: dict, request: Request):
    """直接调用特定 Agent（跳过 Orchestrator）"""
    graphs = request.app.state.graphs
    if agent_name not in graphs:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    
    result = await graphs[agent_name].ainvoke(req)
    return result
```

#### 实验数据 API

```python
# server/routes/experiments.py
router = APIRouter(tags=["experiments"])

@router.get("/experiments")
async def list_experiments(
    date: str | None = None,
    limit: int = 20,
):
    """列出实验记录"""
    runs = data_reader.list_experiment_runs(
        data_dir=settings.microhyseeker_data_dir,
        date_range=(date, date) if date else None,
        limit=limit,
    )
    return runs

@router.get("/experiments/{run_id}")
async def get_experiment(run_id: str):
    """获取实验详情"""
    return data_reader.read_run_summary(run_id)

@router.post("/experiments/{run_id}/diagnose")
async def diagnose_experiment(run_id: str, request: Request):
    """诊断失败实验"""
    result = await request.app.state.graphs["diagnostics"].ainvoke({
        "task": "diagnose",
        "run_dir": run_id,
        "messages": [],
    })
    return result
```

#### 知识管理 API

```python
# server/routes/knowledge.py
router = APIRouter(tags=["knowledge"])

@router.post("/knowledge/ingest")
async def ingest_resource(path: str, target_dir: str = "resources"):
    """入库文档/数据到 OpenViking"""
    result = viking.add_resource(path, target=f"viking://{target_dir}/")
    viking.wait_processed()
    return result

@router.post("/knowledge/search")
async def search_knowledge(query: str, top_k: int = 5):
    """知识检索"""
    return viking.search(query, limit=top_k)

@router.get("/knowledge/tree")
async def knowledge_tree(uri: str = "viking://"):
    """浏览知识库目录结构"""
    return viking.tree(uri)
```

### 4.3 启动方式

```python
# __main__.py
import uvicorn
from autohyseeker.server.app import create_app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8100)
```

```bash
# 开发模式
python -m autohyseeker                    # 默认 :8100
uvicorn autohyseeker.server.app:create_app --reload --port 8100

# CLI 模式（不启动 HTTP 服务）
python -m autohyseeker.cli diagnose data/2026-02-13/153000_test/
python -m autohyseeker.cli chat
```

---

## 五、LangGraph 编排层

### 5.1 Graph 构建

Graph 定义参考 [langgraph_architecture.md](langgraph_architecture.md) §三/§四，此处补充服务集成方式：

```python
# graph/__init__.py
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def build_all_graphs() -> dict:
    """构建所有 Agent Graph，共享 checkpointer"""
    checkpointer = AsyncSqliteSaver.from_conn_string("data/checkpoints.db")
    
    return {
        "orchestrator": build_orchestrator_graph(checkpointer),
        "diagnostics": build_diagnostics_graph(),
        "analyst": build_analyst_graph(),
        "supervisor": build_supervisor_graph(),
        "designer": build_designer_graph(),
        "knowledge": build_knowledge_graph(),
    }
```

### 5.2 Graph ↔ FastAPI 集成模式

```python
# Orchestrator 是唯一带 checkpointer 的 Graph（多轮对话）
# 其他 Agent 是无状态 Subgraph（单次调用）

# 在 Orchestrator 中引用 Subgraph：
orchestrator_graph.add_node("analyst", analyst_subgraph)
# FastAPI 调 Orchestrator → Orchestrator 调 Subgraph → 结果逐层返回
```

---

## 六、OpenViking 适配层

### 6.1 VikingKnowledgeBase 封装

```python
# openviking_adapter/client.py
from openviking import SyncOpenViking

class VikingKnowledgeBase:
    """AutoHySeeker 对 OpenViking 的封装 — 统一入口"""
    
    def __init__(self, config_path: str = "config/openviking.toml"):
        self.client = SyncOpenViking(config_path=config_path)
    
    def initialize(self):
        """初始化 + 创建目录结构"""
        self.client.initialize()
        self._ensure_directory_structure()
    
    def _ensure_directory_structure(self):
        """确保 viking:// 目录结构已创建"""
        dirs = [
            "viking://resources/experiments/",
            "viking://resources/literature/",
            "viking://resources/manuals/",
            "viking://agent/shared/experiment_context/",
            "viking://agent/shared/analysis_results/",
            "viking://agent/memories/cases/",
            "viking://agent/memories/patterns/",
            "viking://agent/memories/materials/",
            "viking://agent/memories/calibrations/",
            "viking://agent/memories/failures/",
            "viking://agent/memories/methodology/",
        ]
        for d in dirs:
            try:
                self.client.mkdir(d)
            except Exception:
                pass  # 已存在
    
    def ingest_document(self, path: str, target_dir: str = "resources"):
        """入库文档"""
        self.client.add_resource(path, target=f"viking://{target_dir}/", wait=True)
    
    def search(self, query: str, top_k: int = 5, **kwargs):
        """统一检索"""
        return self.client.search(query, limit=top_k, **kwargs)
    
    def find(self, query: str, top_k: int = 5):
        """简单语义搜索（不走 IntentAnalyzer）"""
        return self.client.find(query, limit=top_k)
```

### 6.2 注册电化学 Parser

```python
# openviking_adapter/echem_parser.py
# 详见 innovation_proposals.md 提案1
# 在 VikingKnowledgeBase.initialize() 中注册：
#   self.client._async_client.parser_registry.register_custom(ECDataParser())
```

---

## 七、IPC 桥接层（Phase 4）

### 7.1 通信协议

AutoHySeeker 与 MicroHySeeker 之间通过 **本地 TCP Socket** 通信（两个进程在同一台 Windows 机器上）。

```python
# bridge/protocol.py
from pydantic import BaseModel
from enum import Enum

class IPCCommand(str, Enum):
    LOAD_EXPERIMENT = "load_experiment"
    START_EXPERIMENT = "start_experiment"
    STOP_EXPERIMENT = "stop_experiment"
    GET_STATUS = "get_status"
    GET_ENGINE_STATE = "get_engine_state"
    SUBSCRIBE_EVENTS = "subscribe_events"

class IPCMessage(BaseModel):
    command: IPCCommand
    payload: dict = {}
    request_id: str

class IPCEvent(BaseModel):
    event_type: str              # "step_started", "step_completed", "error", ...
    data: dict
    timestamp: str
```

### 7.2 Phase 1-3 的替代方案

Phase 1-3 不需要 IPC——Agent 直接读取 MicroHySeeker 的数据目录：

```python
# config/settings.py
class Settings(BaseSettings):
    # MicroHySeeker 数据目录（两个进程共享文件系统）
    microhyseeker_data_dir: str = "../../data"
    microhyseeker_log_dir: str = "../../logs"
    
    # Phase 4: IPC 配置
    ipc_host: str = "127.0.0.1"
    ipc_port: int = 8101
```

---

## 八、开发分阶段计划

### Phase 1（Week 1-4）— 基础骨架 + D/C Agent

```
Week 1: 项目骨架
  ☐ pyproject.toml + 依赖安装
  ☐ server/app.py — FastAPI 最小可运行版本
  ☐ openviking_adapter/client.py — VikingKnowledgeBase 封装
  ☐ tools/data_reader.py — 8 个数据读取函数
  ☐ tools/log_analysis.py — 8 个日志分析函数
  ☐ GET /api/health 健康检查

Week 2-3: DiagnosticsExpert (D)
  ☐ graph/state.py — DiagnosticsState
  ☐ graph/diagnostics_graph.py
  ☐ agents/diagnostics_nodes.py
  ☐ POST /api/agents/diagnostics/invoke
  ☐ 端到端测试

Week 3-4: ExperimentSupervisor (C) — 后分析模式
  ☐ graph/state.py — SupervisorState
  ☐ graph/supervisor_graph.py
  ☐ agents/supervisor_nodes.py
  ☐ C→D 联动测试

Week 4: Orchestrator 基础版
  ☐ graph/orchestrator.py — 路由 D + C
  ☐ POST /api/chat
  ☐ WebSocket /ws/chat（基础版）
  ☐ cli/main.py — diagnose, health-check, review 命令
```

### Phase 2（Week 5-6）— DataAnalyst (A)

```
Week 5: 分析工具 + Graph
  ☐ tools/echem_analysis.py — 8 个分析函数
  ☐ tools/visualization.py — 6 个图表函数
  ☐ graph/analyst_graph.py + agents/analyst_nodes.py
  ☐ openviking_adapter/echem_parser.py（创新提案1）

Week 6: 集成 + API
  ☐ Orchestrator 路由增加 analyst
  ☐ GET /api/experiments — 实验列表
  ☐ POST /api/experiments/{id}/analyze
  ☐ cli: analyze, compare, ask
```

### Phase 3（Week 7-9）— B/E Agent + OpenViking 深度集成

```
Week 7: OpenViking 完整集成
  ☐ 注册 ECDataParser
  ☐ 记忆分类扩展（创新提案2）
  ☐ 目录结构初始化（创新提案5）
  ☐ POST /api/knowledge/* API

Week 8: ExperimentDesigner (B)
  ☐ tools/experiment_builder.py — 11 个函数
  ☐ graph/designer_graph.py + agents/designer_nodes.py
  ☐ POST /api/chat — 路由增加 designer

Week 9: KnowledgeManager (E) + Orchestrator 完整版
  ☐ graph/knowledge_graph.py + agents/knowledge_nodes.py
  ☐ 实验因果图谱（创新提案4）
  ☐ Orchestrator 完整路由
  ☐ cli: design, ask-kb, ingest, archive, chat
```

### Phase 4（Week 10-12）— 实时控制 + 自适应

```
Week 10-11: IPC 桥接
  ☐ bridge/ 模块完整实现
  ☐ MicroHySeeker 侧 IPC 服务端
  ☐ 实验上下文总线（创新提案3）

Week 12: 自适应闭环
  ☐ C3 adaptive_experiment_loop
  ☐ B2 参数优化（Optuna 集成）
  ☐ 端到端自适应实验测试
```

---

## 九、数据流架构

### 9.1 一次典型对话的数据流

```
用户: "帮我分析今天的CV实验"
  │
  ▼
POST /api/chat { message: "帮我分析今天的CV实验" }
  │
  ▼
Orchestrator.router_node
  → LLM 分类 → agent="analyst"
  │
  ▼
DataAnalyst Subgraph
  ├── classify_task → "single_analysis"
  ├── gather_data → data_reader.list_experiment_runs() → read_echem_csv()
  ├── analyze → echem_analysis.detect_cv_peaks()
  ├── visualize → visualization.plot_cv() → 保存图表到 /tmp/figures/
  └── interpret → LLM 生成自然语言解读
  │
  ▼
Orchestrator.synthesize_node
  → 组合 report + figures
  │
  ▼
ChatResponse {
  response: "## CV 分析报告\n峰电流 12.3μA...",
  agent_used: "analyst",
  figures: ["/tmp/figures/cv_001.png"],
}
```

### 9.2 MicroHySeeker 数据读取路径

```
MicroHySeeker 数据目录:
  data/
  ├── 2026-02-13/
  │   ├── 153000_CV_Fe_gradient/
  │   │   ├── run_summary.json          ← data_reader.read_run_summary()
  │   │   ├── run_log.log               ← data_reader.read_run_log()
  │   │   ├── echem/
  │   │   │   ├── step_2_CV.csv         ← data_reader.read_echem_csv()
  │   │   │   └── step_5_EIS.csv
  │   │   └── pump/
  │   │       └── pump_operations.csv   ← data_reader.read_pump_operations()
  │   └── ...
  └── ...

AutoHySeeker 通过 settings.microhyseeker_data_dir 定位数据目录。
数据是只读的——AutoHySeeker 不修改 MicroHySeeker 的数据文件。
AutoHySeeker 自己的数据（checkpoints、图表、报告）存在 AutoHySeeker/data/ 下。
```

---

## 十、配置管理

### 10.1 配置文件

```toml
# config/autohyseeker.toml

[server]
host = "0.0.0.0"
port = 8100
cors_origins = ["http://localhost:3000"]

[microhyseeker]
data_dir = "../../data"              # MicroHySeeker 实验数据目录
log_dir = "../../logs"               # MicroHySeeker 日志目录

[llm]
provider = "openai"                  # openai | anthropic | doubao | local
model = "gpt-4o"                     # 主模型（分析/诊断/设计）
model_mini = "gpt-4o-mini"           # 轻量模型（路由/分类）
api_key_env = "OPENAI_API_KEY"       # 环境变量名
base_url = ""                        # 自定义 API 地址（可选）

[openviking]
config_path = "config/openviking.toml"

[ipc]
enabled = false                      # Phase 4 启用
host = "127.0.0.1"
port = 8101
```

### 10.2 Settings 类

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8100
    
    # MicroHySeeker 数据路径
    microhyseeker_data_dir: str = "../../data"
    microhyseeker_log_dir: str = "../../logs"
    
    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_model_mini: str = "gpt-4o-mini"
    
    # OpenViking
    openviking_config: str = "config/openviking.toml"
    
    # IPC
    ipc_enabled: bool = False
    ipc_host: str = "127.0.0.1"
    ipc_port: int = 8101
    
    class Config:
        env_prefix = "AUTOHYSEEKER_"
        toml_file = "config/autohyseeker.toml"
```

---

## 十一、测试策略

| 层 | 测试方式 | 工具 |
|---|---|---|
| Tool 函数 | 单元测试（用真实数据文件） | pytest |
| Agent 节点 | 单元测试（mock LLM） | pytest + unittest.mock |
| Graph 流转 | 集成测试（验证条件边逻辑） | pytest-asyncio |
| API 端点 | HTTP 测试 | httpx + TestClient |
| WebSocket | 流式测试 | httpx.AsyncClient |
| C→D 联动 | 端到端测试 | Graph 直接调用 |

```python
# tests/test_api/test_chat.py
async def test_chat_routes_to_diagnostics():
    async with AsyncClient(app=create_app(), base_url="http://test") as client:
        resp = await client.post("/api/chat", json={
            "message": "为什么今天的实验失败了？"
        })
        assert resp.status_code == 200
        assert resp.json()["agent_used"] == "diagnostics"
```

---

## 十二、部署

### 开发环境

```bash
cd AutoHySeeker
pip install -e ".[dev]"              # 安装开发依赖
pip install -e third_party/agfs/agfs-sdk/python  # pyagfs
python -m autohyseeker               # 启动服务 :8100
```

### 生产环境（同一台 Windows 机器）

```
MicroHySeeker.exe  ← PySide6 桌面端（已有）
     │
     └── 自动启动 AutoHySeeker 后端服务：
         python -m autohyseeker --config config/autohyseeker.toml
```

两个进程共享同一台机器的文件系统（data/ 目录），通过 HTTP API（:8100）+ IPC（:8101）通信。

---

*此文档是 AutoHySeeker 后端的完整开发参考。关联文档：[architecture_overview.md](architecture_overview.md)、[project_plan.md](project_plan.md)。完整文档导航见 [README.md](README.md)。*
