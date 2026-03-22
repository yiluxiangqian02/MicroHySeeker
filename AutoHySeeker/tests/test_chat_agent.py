from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


class TestChatAgent:
    def test_optimization_status_intent_returns_summary(self) -> None:
        from src.agents.chat_agent import ChatAgent

        agent = ChatAgent()
        with patch(
            "src.api.routes.optimization.get_optimization_status",
            new=AsyncMock(
                return_value={
                    "running": True,
                    "status": "running",
                    "current_round": 3,
                    "max_rounds": 10,
                    "best_result": {"round": 2, "params": {"Fe": 0.3}, "metrics": {"overpotential_mV": 182.5}},
                }
            ),
        ), patch(
            "src.api.routes.optimization.get_optimization_history",
            new=AsyncMock(return_value={"history": [], "best_result": None, "total_rounds": 3}),
        ):
            result = asyncio.run(agent.chat("现在优化到第几轮了？"))

        assert result["status"] == "success"
        assert result["data"]["intent"] == "optimization_status"
        assert "第 3/10 轮" in result["data"]["reply"]

    def test_stop_intent_calls_optimization_stop(self) -> None:
        from src.agents.chat_agent import ChatAgent

        agent = ChatAgent()
        with patch(
            "src.api.routes.optimization.stop_optimization",
            new=AsyncMock(return_value={"status": "stop_requested"}),
        ) as stop_mock:
            result = asyncio.run(agent.chat("帮我停一下优化"))

        stop_mock.assert_awaited_once()
        assert result["data"]["intent"] == "control_stop"
        assert "停止指令" in result["data"]["reply"]

    def test_follow_up_query_uses_previous_user_message(self) -> None:
        from src.agents.chat_agent import ChatAgent

        knowledge_skill = AsyncMock()
        knowledge_skill.search = AsyncMock(return_value=[])
        agent = ChatAgent(knowledge_skill=knowledge_skill)

        result = asyncio.run(
            agent.chat(
                "再详细一点",
                history=[{"role": "user", "content": "Fe-Co-Ni 催化剂的 Tafel 斜率一般是多少？"}],
            )
        )

        knowledge_skill.search.assert_awaited_once()
        called_query = knowledge_skill.search.await_args.kwargs["query"]
        assert "Tafel" in called_query or "tafel" in called_query.lower()
        assert result["data"]["effective_message"] != "再详细一点"


class TestChatRoutes:
    def test_post_api_chat_returns_message_and_stores_history(self) -> None:
        from src.api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        payload = {
            "status": "success",
            "agent": "chat",
            "timestamp": "2026-03-19T00:00:00Z",
            "data": {"reply": "当前第 2 轮。", "intent": "optimization_status"},
        }
        with patch("src.api.routes.chat.ChatAgent.chat", new=AsyncMock(return_value=payload)):
            response = client.post("/api/chat", json={"message": "现在优化到哪了？", "session_id": "sess_1"})
            history = client.get("/api/chat/history", params={"session_id": "sess_1"})

        assert response.status_code == 200
        body = response.json()
        assert body["intent"] == "optimization_status"
        assert body["message"]["content"] == "当前第 2 轮。"
        assert history.status_code == 200
        assert history.json()["total"] == 2

    def test_legacy_chat_ask_endpoint_is_compatible(self) -> None:
        from src.api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        payload = {
            "status": "success",
            "agent": "chat",
            "timestamp": "2026-03-19T00:00:00Z",
            "data": {"reply": "已发送停止指令。", "intent": "control_stop"},
        }
        with patch("src.api.routes.chat.ChatAgent.chat", new=AsyncMock(return_value=payload)):
            response = client.post("/api/v1/chat/ask", json={"question": "帮我停一下优化"})

        assert response.status_code == 200
        body = response.json()
        assert body["agent_type"] == "control_stop"
        assert body["message"]["content"] == "已发送停止指令。"

    def test_delete_chat_history_clears_session(self) -> None:
        from src.api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        payload = {
            "status": "success",
            "agent": "chat",
            "timestamp": "2026-03-19T00:00:00Z",
            "data": {"reply": "ok", "intent": "knowledge_query"},
        }
        with patch("src.api.routes.chat.ChatAgent.chat", new=AsyncMock(return_value=payload)):
            client.post("/api/chat", json={"message": "test", "session_id": "sess_2"})

        clear_response = client.delete("/api/chat/history", params={"session_id": "sess_2"})
        history_response = client.get("/api/chat/history", params={"session_id": "sess_2"})

        assert clear_response.status_code == 200
        assert history_response.json()["total"] == 0


class TestChatGraphRouting:
    def test_chat_keywords_route_to_chat_agent(self) -> None:
        from src.graph.nodes import route_intent

        state = {
            "messages": [],
            "current_agent": "",
            "task": {"intent": "现在优化到第几轮了？"},
            "context": {},
            "error": None,
            "result": None,
        }
        result = route_intent(state)
        assert result["current_agent"] == "chat"

    def test_chat_registered_in_agent_map(self) -> None:
        from src.graph.nodes import AGENT_MAP, select_agent_node

        assert "chat" in AGENT_MAP
        state = {
            "messages": [],
            "current_agent": "chat",
            "task": {},
            "context": {},
            "error": None,
            "result": None,
        }
        assert select_agent_node(state) == "chat"

    def test_supervisor_graph_routes_chat_node(self) -> None:
        from src.graph.orchestrator import build_supervisor_graph

        graph = build_supervisor_graph()
        state = {
            "messages": [],
            "current_agent": "",
            "task": {"type": "chat", "intent": "帮我停一下优化"},
            "context": {},
            "error": None,
            "result": None,
        }
        with patch("src.graph.nodes.ChatAgent.invoke", new=AsyncMock(return_value={"agent": "chat", "content": "ok"})):
            result = asyncio.run(graph.ainvoke(state))

        assert result["result"]["agent"] == "chat"
        assert result["result"]["ok"] is True
