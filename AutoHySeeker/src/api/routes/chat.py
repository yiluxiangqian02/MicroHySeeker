"""
Chat API routes for Q&A functionality
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from pathlib import Path

router = APIRouter()

# Simple in-memory chat history (in production, use database)
chat_history: List[Dict[str, Any]] = []


class ChatRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None
    experiment_id: Optional[str] = None


class ChatMessage(BaseModel):
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    agent_type: Optional[str] = None


class ChatResponse(BaseModel):
    message: ChatMessage
    agent_type: str


def classify_question(question: str) -> str:
    """
    Classify question type to route to appropriate agent
    """
    question_lower = question.lower()

    # Data analysis keywords
    analysis_keywords = ["分析", "数据", "对比", "比较", "趋势", "峰值", "电流"]
    if any(keyword in question_lower for keyword in analysis_keywords):
        return "data_analyst"

    # Experiment design keywords
    design_keywords = ["建议", "推荐", "优化", "设计", "参数", "如何", "怎么"]
    if any(keyword in question_lower for keyword in design_keywords):
        return "experiment_designer"

    # Default to knowledge manager
    return "knowledge_manager"


def generate_mock_response(question: str, agent_type: str, context: Optional[Dict] = None) -> str:
    """
    Generate mock response based on agent type
    (In production, this would call actual agents)
    """
    if agent_type == "data_analyst":
        return f"""根据您的问题"{question}"，我分析了相关实验数据：

**数据分析结果：**
- 峰电流：约 45.2 μA
- 峰电位：0.35 V vs Ag/AgCl
- 扫描速率：50 mV/s
- 信噪比：良好

**建议：**
- 数据质量较好，可以继续使用当前参数
- 如需提高灵敏度，可尝试降低扫描速率至 20 mV/s

需要更详细的分析吗？"""

    elif agent_type == "experiment_designer":
        return f"""针对您的问题"{question}"，我提供以下实验建议：

**推荐实验方案：**
1. **循环伏安法 (CV)**
   - 扫描速率：50 mV/s
   - 电位范围：-0.2 V 到 0.8 V
   - 循环次数：3 次

2. **差分脉冲伏安法 (DPV)**
   - 脉冲幅度：50 mV
   - 脉冲宽度：50 ms
   - 扫描速率：20 mV/s

**注意事项：**
- 确保电极表面清洁
- 使用新鲜配制的缓冲液
- 先进行空白对照实验

需要更多细节吗？"""

    else:  # knowledge_manager
        return f"""关于您的问题"{question}"：

**循环伏安法 (CV) 扫描速率选择指南：**

1. **常规分析**：50-100 mV/s
   - 适用于大多数电化学体系
   - 平衡了灵敏度和实验时间

2. **动力学研究**：10-500 mV/s
   - 研究电极反应速率
   - 需要多个扫描速率对比

3. **高灵敏度检测**：10-20 mV/s
   - 提高信噪比
   - 适合低浓度样品

4. **快速筛选**：100-200 mV/s
   - 快速获得初步结果
   - 适合批量样品

**选择建议：**
- 首次实验：从 50 mV/s 开始
- 根据结果调整：信号弱则降低，时间紧则提高

还有其他问题吗？"""


@router.post("/api/v1/chat/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Process user question and route to appropriate agent
    """
    try:
        # Classify question
        agent_type = classify_question(request.question)

        # Generate response (mock for now)
        response_content = generate_mock_response(
            request.question,
            agent_type,
            request.context
        )

        # Create message objects
        timestamp = datetime.now().isoformat()
        user_msg_id = f"msg_{len(chat_history)}"
        assistant_msg_id = f"msg_{len(chat_history) + 1}"

        user_message = {
            "id": user_msg_id,
            "role": "user",
            "content": request.question,
            "timestamp": timestamp,
            "agent_type": None
        }

        assistant_message = {
            "id": assistant_msg_id,
            "role": "assistant",
            "content": response_content,
            "timestamp": timestamp,
            "agent_type": agent_type
        }

        # Store in history
        chat_history.append(user_message)
        chat_history.append(assistant_message)

        return ChatResponse(
            message=ChatMessage(**assistant_message),
            agent_type=agent_type
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")


@router.get("/api/v1/chat/history")
async def get_chat_history(limit: int = 50):
    """
    Get chat history
    """
    try:
        # Return most recent messages
        recent_messages = chat_history[-limit:] if len(chat_history) > limit else chat_history
        return {
            "messages": recent_messages,
            "total": len(chat_history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")


@router.delete("/api/v1/chat/history")
async def clear_chat_history():
    """
    Clear chat history
    """
    try:
        chat_history.clear()
        return {"message": "Chat history cleared", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")
