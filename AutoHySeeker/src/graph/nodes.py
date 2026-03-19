"""Node functions for the supervisor graph.

After agent consolidation (7→4), DataAnalyst / KnowledgeManager /
ExperimentSupervisor are skills of the Orchestrator.  The graph routes
their former keywords to the orchestrator agent.
"""

from __future__ import annotations

from typing import Any

from src.agents.diagnostics import DiagnosticsExpertAgent
from src.agents.exp_designer import ExperimentDesignerAgent
from src.agents.exp_executor import ExperimentExecutorAgent
from src.agents.orchestrator import OrchestratorAgent
from src.graph.state import AutoHySeekerState

AGENT_MAP = {
    "orchestrator": OrchestratorAgent(),
    "exp_designer": ExperimentDesignerAgent(),
    "exp_executor": ExperimentExecutorAgent(),
    "diagnostics": DiagnosticsExpertAgent(),
}

# Backward-compatible aliases: old agent names → orchestrator
_AGENT_ALIASES = {
    "data_analyst": "orchestrator",
    "knowledge_mgr": "orchestrator",
    "exp_supervisor": "orchestrator",
}


def _task_text(task: dict[str, Any]) -> str:
    values = [
        str(task.get("intent", "")),
        str(task.get("goal", "")),
        str(task.get("prompt", "")),
        str(task.get("query", "")),
        str(task.get("type", "")),
    ]
    return " ".join(values).lower()


def _infer_agent(task: dict[str, Any], requested: str | None = None) -> str:
    if requested:
        resolved = _AGENT_ALIASES.get(requested, requested)
        if resolved in AGENT_MAP:
            return resolved

    text = _task_text(task)

    # Orchestrator keywords (closed-loop optimization as a whole)
    if any(keyword in text for keyword in ("闭环", "优化循环", "配比优化", "optimization loop", "closed-loop")):
        return "orchestrator"
    # Data analysis keywords → orchestrator (DataAnalysisSkill)
    if any(keyword in text for keyword in ("cv", "eis", "analy", "signal", "data")):
        return "orchestrator"
    if any(keyword in text for keyword in ("design", "next experiment", "optimize", "optuna")):
        return "exp_designer"
    if any(keyword in text for keyword in ("diagnos", "error", "failure", "anomaly", "troubleshoot")):
        return "diagnostics"
    if any(keyword in text for keyword in ("execute", "run experiment", "启动实验", "执行实验", "start experiment")):
        return "exp_executor"
    # Knowledge keywords → orchestrator (KnowledgeArchiveSkill)
    if any(keyword in text for keyword in ("knowledge", "paper", "literature", "summary")):
        return "orchestrator"
    return "orchestrator"


def route_intent(state: AutoHySeekerState) -> dict[str, Any]:
    task = state.get("task", {})
    selected_agent = _infer_agent(task, state.get("current_agent"))
    context = dict(state.get("context", {}))
    context["routed_by"] = "route_intent"
    context["route_reason"] = selected_agent
    return {"current_agent": selected_agent, "context": context}


def select_agent_node(state: AutoHySeekerState) -> str:
    agent = state.get("current_agent") or "orchestrator"
    resolved = _AGENT_ALIASES.get(agent, agent)
    if resolved not in AGENT_MAP:
        return "orchestrator"
    return resolved


async def _invoke_agent(state: AutoHySeekerState, agent_name: str) -> dict[str, Any]:
    resolved = _AGENT_ALIASES.get(agent_name, agent_name)
    agent = AGENT_MAP[resolved]
    try:
        result = await agent.invoke(
            task=state.get("task", {}),
            context=state.get("context", {}),
            messages=state.get("messages", []),
        )
        return {"result": result, "error": None}
    except Exception as exc:
        return {
            "error": str(exc),
            "result": {
                "agent": resolved,
                "content": "",
            },
        }


async def run_orchestrator(state: AutoHySeekerState) -> dict[str, Any]:
    return await _invoke_agent(state, "orchestrator")


async def run_exp_designer(state: AutoHySeekerState) -> dict[str, Any]:
    return await _invoke_agent(state, "exp_designer")


async def run_exp_executor(state: AutoHySeekerState) -> dict[str, Any]:
    return await _invoke_agent(state, "exp_executor")


async def run_diagnostics(state: AutoHySeekerState) -> dict[str, Any]:
    return await _invoke_agent(state, "diagnostics")


# Backward-compatible aliases for old node names
async def run_data_analyst(state: AutoHySeekerState) -> dict[str, Any]:
    return await _invoke_agent(state, "orchestrator")


async def run_knowledge_mgr(state: AutoHySeekerState) -> dict[str, Any]:
    return await _invoke_agent(state, "orchestrator")


async def run_exp_supervisor(state: AutoHySeekerState) -> dict[str, Any]:
    return await _invoke_agent(state, "orchestrator")


def format_response(state: AutoHySeekerState) -> dict[str, Any]:
    payload = dict(state.get("result") or {})
    payload.setdefault("agent", state.get("current_agent", "unknown"))
    if state.get("error"):
        payload["ok"] = False
        payload["error"] = state["error"]
    else:
        payload["ok"] = True
    return {"result": payload}
