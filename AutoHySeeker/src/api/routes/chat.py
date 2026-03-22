"""Chat API routes backed by ChatAgent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.agents.chat_agent import ChatAgent

router = APIRouter(tags=["chat"])

_chat_sessions: dict[str, list[dict[str, Any]]] = {}


class ChatMessage(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    agent_type: str | None = None


class ChatRequest(BaseModel):
    message: str | None = None
    question: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[ChatMessage] = Field(default_factory=list)
    session_id: str = "default"
    experiment_id: str | None = None


class ChatResponse(BaseModel):
    message: ChatMessage
    agent_type: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_message(
    *,
    index: int,
    role: str,
    content: str,
    agent_type: str | None = None,
) -> dict[str, Any]:
    timestamp = _now()
    return {
        "id": f"msg_{index}",
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "agent_type": agent_type,
    }


def _get_session_history(session_id: str) -> list[dict[str, Any]]:
    return _chat_sessions.setdefault(session_id, [])


def _resolve_user_message(request: ChatRequest) -> str:
    content = (request.message or request.question or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="message or question is required")
    return content


def _serialise_history(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    return list(items[-limit:])


@router.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    try:
        user_message = _resolve_user_message(request)
        session_history = _get_session_history(request.session_id)
        agent_history: list[dict[str, Any]] = [item.model_dump() for item in request.history] or list(session_history)

        chat_agent = ChatAgent()
        context = dict(request.context)
        if request.experiment_id:
            context["experiment_id"] = request.experiment_id

        result = await chat_agent.chat(
            message=user_message,
            context=context,
            history=agent_history,
        )

        data = result.get("data", {})
        reply = str(data.get("reply", "")).strip() or "暂时没有可返回的内容。"
        intent = str(data.get("intent", "chat"))

        user_record = _make_message(index=len(session_history), role="user", content=user_message)
        assistant_record = _make_message(
            index=len(session_history) + 1,
            role="assistant",
            content=reply,
            agent_type=intent,
        )

        session_history.extend([user_record, assistant_record])

        return {
            "status": result.get("status", "success"),
            "agent": result.get("agent", "chat"),
            "timestamp": result.get("timestamp", _now()),
            "session_id": request.session_id,
            "intent": intent,
            "message": assistant_record,
            "history_length": len(session_history),
            "data": data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {exc}") from exc


@router.post("/api/v1/chat/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest) -> ChatResponse:
    response = await chat(request)
    message = ChatMessage(**response["message"])
    return ChatResponse(message=message, agent_type=str(response.get("intent", "chat")))


@router.get("/api/chat/history")
async def get_chat_history(
    session_id: str = Query(default="default"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    messages = _serialise_history(_get_session_history(session_id), limit)
    return {"messages": messages, "total": len(_get_session_history(session_id)), "session_id": session_id}


@router.get("/api/v1/chat/history")
async def get_chat_history_v1(
    session_id: str = Query(default="default"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    return await get_chat_history(session_id=session_id, limit=limit)


@router.delete("/api/chat/history")
async def clear_chat_history(session_id: str = Query(default="default")) -> dict[str, Any]:
    messages = _get_session_history(session_id)
    messages.clear()
    return {"message": "Chat history cleared", "success": True, "session_id": session_id}


@router.delete("/api/v1/chat/history")
async def clear_chat_history_v1(session_id: str = Query(default="default")) -> dict[str, Any]:
    return await clear_chat_history(session_id=session_id)
