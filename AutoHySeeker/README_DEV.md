# AutoHySeeker — 开发者快速上手

## 项目结构

```
AutoHySeeker/
  src/
    common/       # 配置、日志、LLM 客户端
    tools/        # 原子操作（读 CSV、控制实验等）
    agents/       # Agent 定义（DataAnalyst、ExperimentDesigner 等）
    graph/        # LangGraph 编排层
    api/          # FastAPI HTTP 服务
    skills/       # 复合技能（调用 tools + LLM）
  pyproject.toml  # uv 依赖管理
  .env            # 环境变量（从 .env.example 复制）
```

## 快速开始

### 1. 安装依赖

```bash
cd AutoHySeeker
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写 OPENAI_API_KEY
```

### 3. 启动 API 服务

```bash
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8100
```

访问 http://localhost:8100/docs 查看 API 文档。

### 4. 测试基础功能

```bash
# 列出最近实验
curl http://localhost:8100/data/experiments?n=5

# 调用 Agent
curl -X POST http://localhost:8100/agents/invoke \
  -H "Content-Type: application/json" \
  -d '{"task": {"intent": "analyze CV data"}, "context": {}}'
```

## 开发指南

### 添加新 Tool

1. 在 `src/tools/` 下创建新文件
2. 实现函数，遵循 `def tool_name(args) -> result` 签名
3. 在 `src/tools/registry.py` 的 `build_default_registry()` 中注册

### 添加新 Agent

1. 在 `src/agents/` 下创建新文件
2. 继承 `BaseAgent`，定义 `system_prompt`
3. 在 `src/graph/nodes.py` 的 `AGENT_MAP` 中注册
4. 在 `src/graph/orchestrator.py` 中添加路由节点

### 添加新 Skill

1. 在 `src/skills/` 下创建新文件
2. 实现 `async def skill_name(...) -> dict`，内部调用 tools + agent
3. 在 `src/skills/__init__.py` 中导出

## 测试

```bash
uv run pytest
```

## 日志

日志输出到 `../../logs/autohyseeker.log`（相对于 AutoHySeeker/ 目录）。

---

*最后更新：2026-03-03 | Codex @ TASK_001*
