"""Global Agent state manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from src.common.logger import get_logger

logger = get_logger(__name__)

_AGENT_IDS = [
    "data_analyst",
    "exp_designer",
    "exp_supervisor",
    "diagnostics",
    "knowledge_mgr",
]


class AgentManager:
    """Singleton-style agent status / log / metrics tracker."""

    def __init__(self) -> None:
        self.agents: Dict[str, Dict[str, Any]] = {
            agent_id: {"status": "idle", "tasks": []} for agent_id in _AGENT_IDS
        }
        self.logs: Dict[str, List[Dict[str, str]]] = {
            agent_id: [] for agent_id in _AGENT_IDS
        }
        self.metrics: Dict[str, Dict[str, Any]] = {
            agent_id: {
                "token_usage": 0,
                "response_time": 0.0,
                "success_count": 0,
                "error_count": 0,
            }
            for agent_id in _AGENT_IDS
        }

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def get_status(self, agent_id: str) -> Dict[str, Any]:
        return self.agents.get(agent_id, {})

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        return self.agents

    def start_agent(self, agent_id: str) -> None:
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "running"
            self.add_log(agent_id, "INFO", f"Agent {agent_id} started")

    def stop_agent(self, agent_id: str) -> None:
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "idle"
            self.add_log(agent_id, "INFO", f"Agent {agent_id} stopped")

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def add_log(self, agent_id: str, level: str, message: str) -> None:
        if agent_id not in self.logs:
            self.logs[agent_id] = []
        self.logs[agent_id].append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
            }
        )
        # keep only the 100 most recent entries
        if len(self.logs[agent_id]) > 100:
            self.logs[agent_id] = self.logs[agent_id][-100:]

    def get_logs(self, agent_id: str, limit: int = 50) -> List[Dict[str, str]]:
        return self.logs.get(agent_id, [])[-limit:]

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def get_metrics(self, agent_id: str) -> Dict[str, Any]:
        return self.metrics.get(agent_id, {})

    def update_metrics(self, agent_id: str, **kwargs: Any) -> None:
        if agent_id in self.metrics:
            self.metrics[agent_id].update(kwargs)


# Global singleton
agent_manager = AgentManager()
