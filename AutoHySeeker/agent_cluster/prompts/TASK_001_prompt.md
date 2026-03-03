# TASK_001 — 搭建 AutoHySeeker src/ 完整骨架

> **Agent**: GitHub Copilot (claude-sonnet-4.6)
> **Branch**: `feat/autohyseeker-core-scaffold`
> **Worktree**: `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_autohyseeker-core-scaffold`
> **计费方式**: 按次数 — 请尽量在本次会话中完成全部内容

---

## 背景

这是一个电化学自动实验平台 AutoHySeeker 的 AI Agent 后端。
前端（MicroHySeeker）是 PySide6 GUI，通过文件读写 + HTTP API 与 AutoHySeeker 通信。

### 技术栈

- Python 3.11（虚拟环境在 `MicroHySeeker\.venv\`）
- LangGraph（多 Agent 编排）
- OpenAI SDK（兼容 Yuan API：base_url=https://api.mcxhm.cn，api_key 从环境变量读）
- FastAPI + uvicorn（HTTP 后端，端口 8100）
- Optuna（贝叶斯优化，后续）
- uv（包管理，已有 `AutoHySeeker/OpenViking/pyproject.toml` 参考）

---

## 任务：搭建完整 src/ 骨架

在 `AutoHySeeker/` 目录下（worktree 根目录下的 `AutoHySeeker/`）创建以下结构：

```
AutoHySeeker/
  src/
    __init__.py
    common/
      __init__.py
      config.py          # 从环境变量 / .env 读取配置（API key, model, base_url 等）
      llm_client.py      # OpenAI SDK 封装（支持 Yuan API），暴露 get_client() / get_chat_completion()
      logger.py          # 统一日志（logging，输出到 logs/ 目录）
    tools/
      __init__.py
      registry.py        # ToolRegistry：注册/列出/调用 tool
      echem_reader.py    # Tool: read_cv_csv, read_eis_csv, read_experiment_dir
      experiment_ctrl.py # Tool: start_experiment(stub), stop_experiment(stub) — Phase 4 实现
      file_watcher.py    # Tool: watch_data_dir (监听新实验数据)
    agents/
      __init__.py
      base.py            # BaseAgent: system_prompt + invoke() 接口
      data_analyst.py    # DataAnalyst Agent (Subgraph A)
      exp_designer.py    # ExperimentDesigner Agent (Subgraph B)
      exp_supervisor.py  # ExperimentSupervisor Agent (Subgraph C)
      diagnostics.py     # DiagnosticsExpert Agent (Subgraph D)
      knowledge_mgr.py   # KnowledgeManager Agent (Subgraph E)
    graph/
      __init__.py
      state.py           # AutoHySeekerState (TypedDict): messages, current_agent, task, context, error
      orchestrator.py    # build_supervisor_graph() -> LangGraph StateGraph
      nodes.py           # 各路由节点函数
    api/
      __init__.py
      main.py            # FastAPI app, 端口 8100
      routes/
        __init__.py
        tasks.py         # POST /tasks/create, GET /tasks/{id}/status
        agents.py        # POST /agents/invoke
        data.py          # GET /data/experiments, GET /data/latest
    skills/
      __init__.py
      analyze_cv.py      # Skill: 完整 CV 分析流程（调 tools + LLM）
      diagnose_exp.py    # Skill: 失败实验诊断
  pyproject.toml         # uv 管理，依赖：langgraph, openai, fastapi, uvicorn, pandas, numpy
  .env.example           # 环境变量示例
  README_DEV.md          # 开发者快速上手
```

---

## 具体要求

### 1. `common/config.py`
```python
# 从环境变量读取，提供默认值
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.mcxhm.cn")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "anthropic/claude-sonnet-4-6")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "anthropic/claude-opus-4-6")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "../../data"))  # 相对于 AutoHySeeker/
LOG_ROOT = Path(os.getenv("LOG_ROOT", "../../logs"))
```

### 2. `common/llm_client.py`
- 使用 `openai.AsyncOpenAI(base_url=..., api_key=...)`
- 封装 `async chat_completion(messages, model=DEFAULT_MODEL, **kwargs) -> str`
- 支持 retry（重试 2 次，延迟 2s）

### 3. `tools/echem_reader.py`
MicroHySeeker 的实验数据格式：
- 数据目录：`data/YYYY-MM-DD/YYYY-MM-DD_HH-MM-SS_单次实验/`
- 每个实验目录包含 CSV 文件（CV、EIS、CA 等）
- CSV 格式：首行为表头，数据列为 Potential(V), Current(A) 等

实现以下 tools：
```python
def read_experiment_dir(run_dir: str) -> dict  # 返回实验元数据 + 文件列表
def read_cv_csv(path: str) -> pd.DataFrame     # 读取 CV 数据
def list_recent_experiments(n: int = 10) -> list  # 列出最近 N 个实验
```

### 4. `graph/state.py`
```python
class AutoHySeekerState(TypedDict):
    messages: list[BaseMessage]
    current_agent: str       # 当前处理的 Agent 名称
    task: dict               # 当前任务描述
    context: dict            # 从文件/数据库读取的上下文
    error: Optional[str]     # 错误信息
    result: Optional[dict]   # 最终结果
```

### 5. `graph/orchestrator.py`
实现基础 Supervisor 图：
- 入口节点：`route_intent` — 根据用户输入决定调哪个 Agent
- Agent 节点：data_analyst, exp_designer, exp_supervisor, diagnostics, knowledge_mgr
- 出口节点：`format_response`
- 使用条件边路由

### 6. `api/main.py`
```python
app = FastAPI(title="AutoHySeeker API", version="0.1.0")
# 路由：/health, /tasks/*, /agents/*, /data/*
# 启动：uvicorn src.api.main:app --host 0.0.0.0 --port 8100
```

### 7. `pyproject.toml`
```toml
[project]
name = "autohyseeker"
version = "0.1.0"
dependencies = [
    "langgraph>=0.2",
    "openai>=1.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pandas>=2.0",
    "numpy>=1.26",
    "python-dotenv>=1.0",
    "pydantic>=2.0",
    "httpx>=0.27",
]
```

---

## 安全规则（必须遵守）

以下路径禁止删除或破坏性修改：
- `MicroHySeeker/src/` — 核心 GUI 源码，不要动
- `MicroHySeeker/config/system.json`
- `data/` 目录 — 实验数据，只读
- `logs/` 目录 — 只读
- `.git/` — git 历史

---

## 完成标准

- [ ] 所有文件已创建，`__init__.py` 无语法错误
- [ ] `python -m src.api.main` 可启动（或 `uvicorn src.api.main:app`）
- [ ] `python -m pytest` 至少通过基础 import 测试
- [ ] 在 `feat/autohyseeker-core-scaffold` 分支提交，commit message 格式：`feat: [TASK_001] ...`
- [ ] 更新 `AutoHySeeker/agent_cluster/AGENT_COORD.md`（任务状态改为 done）

---

## 工作目录

在 worktree 中工作：
```
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\agent_cluster\worktrees\feat_autohyseeker-core-scaffold\
```

在这个目录下，项目结构与主仓库相同，你在 `AutoHySeeker/` 子目录下创建 `src/` 等内容。

---

*此 prompt 由 Pi (OpenClaw) @ 2026-03-03 生成 | Task ID: TASK_001*
