"""ChatAgent for natural-language status, knowledge, and control queries."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Iterable

from src.agents.base import BaseAgent
from src.skills.knowledge_query_skill import KnowledgeQuerySkill
from src.tools import echem_reader

CHAT_SYSTEM_PROMPT = """\
你是 AutoHySeeker 的 ChatAgent，负责作为统一自然语言入口回答用户问题。

你的优先职责：
1. 回答实验进度、优化状态、最优结果等系统状态问题。
2. 处理知识库查询，包括实验记录、故障历史和文献信息。
3. 处理用户控制指令，例如停止优化。
4. 结合多轮对话上下文理解追问。

回答要求：
- 优先准确、简洁、可执行。
- 如果没有足够数据，明确说明缺少什么。
- 不要编造实验结果或系统状态。
"""

_FOLLOW_UP_HINTS = (
    "再详细",
    "详细一点",
    "展开",
    "继续",
    "还有",
    "那之前",
    "为什么",
    "怎么说",
    "具体点",
)

_STATUS_KEYWORDS = ("状态", "进度", "跑到哪", "第几轮", "best", "最优", "最好结果")
_OPTIMIZATION_KEYWORDS = ("优化", "optimization", "loop", "闭环")
_EXPERIMENT_KEYWORDS = ("实验", "experiment", "run", "轮次")
_STOP_KEYWORDS = ("停", "停止", "stop", "终止", "暂停")
_KNOWLEDGE_KEYWORDS = (
    "文献",
    "知识库",
    "有没有",
    "之前",
    "历史",
    "tafel",
    "过电位",
    "催化剂",
    "故障",
    "报错",
    "配比",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _history_content(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("content", ""))
    return str(getattr(item, "content", ""))


def _history_role(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("role", "user"))
    return str(getattr(item, "role", getattr(item, "type", "user")))


class ChatAgent(BaseAgent):
    """Unified conversational interface for AutoHySeeker."""

    def __init__(self, knowledge_skill: KnowledgeQuerySkill | None = None) -> None:
        super().__init__(
            name="chat",
            system_prompt=CHAT_SYSTEM_PROMPT,
        )
        self._knowledge_skill = knowledge_skill or KnowledgeQuerySkill()

    async def chat(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        history: Iterable[Any] | None = None,
    ) -> dict[str, Any]:
        history_items = list(history or [])
        safe_context = dict(context or {})
        try:
            effective_message = self._expand_follow_up(message, history_items)
            intent = self.classify_intent(effective_message, safe_context)

            if intent == "optimization_status":
                data = await self._handle_optimization_status()
            elif intent == "experiment_status":
                data = await self._handle_experiment_status(safe_context)
            elif intent == "control_stop":
                data = await self._handle_stop_optimization()
            elif intent == "knowledge_query":
                data = await self._handle_knowledge_query(effective_message)
            else:
                data = self._handle_general_help()

            data["intent"] = intent
            data["effective_message"] = effective_message
            return self._success(data)
        except Exception as exc:
            return self._error(f"chat handling failed: {exc}")

    def classify_intent(self, message: str, context: dict[str, Any] | None = None) -> str:
        text = message.lower()
        context = context or {}
        if any(keyword in text for keyword in _STOP_KEYWORDS) and any(
            keyword in text for keyword in _OPTIMIZATION_KEYWORDS + _EXPERIMENT_KEYWORDS
        ):
            return "control_stop"
        if any(keyword in text for keyword in _OPTIMIZATION_KEYWORDS) and any(
            keyword in text for keyword in _STATUS_KEYWORDS
        ):
            return "optimization_status"
        if any(keyword in text for keyword in _STATUS_KEYWORDS) and (
            any(keyword in text for keyword in _EXPERIMENT_KEYWORDS)
            or context.get("experiment_id")
        ):
            return "experiment_status"
        if any(keyword in text for keyword in _KNOWLEDGE_KEYWORDS):
            return "knowledge_query"
        if "help" in text or "能做什么" in text or "你可以做什么" in text:
            return "general_help"
        return "knowledge_query"

    def _expand_follow_up(self, message: str, history: list[Any]) -> str:
        text = message.strip()
        if not text:
            return text

        if not any(hint in text for hint in _FOLLOW_UP_HINTS):
            return text

        for item in reversed(history):
            if _history_role(item) != "user":
                continue
            previous = _history_content(item).strip()
            if previous and previous != text:
                return f"{previous}；补充追问：{text}"
        return text

    async def _handle_optimization_status(self) -> dict[str, Any]:
        from src.api.routes import optimization as optimization_routes

        status = await optimization_routes.get_optimization_status()
        history = await optimization_routes.get_optimization_history()
        best = status.get("best_result") or history.get("best_result")
        current_round = status.get("current_round", 0)
        max_rounds = status.get("max_rounds", 0)
        running = bool(status.get("running"))

        if running:
            reply = f"当前优化正在运行，第 {current_round}/{max_rounds} 轮，状态为 {status.get('status', 'running')}。"
        else:
            reply = f"当前没有正在运行的优化任务，最近状态为 {status.get('status', 'idle')}。"

        if best:
            params = best.get("params", {})
            metrics = best.get("metrics", {})
            reply += f" 当前最优结果来自第 {best.get('round', '?')} 轮，参数 {params}，指标 {metrics}。"

        total_rounds = history.get("total_rounds", 0)
        if total_rounds:
            reply += f" 历史累计记录 {total_rounds} 轮。"

        return {
            "reply": reply,
            "snapshot": {
                "running": running,
                "status": status.get("status", "idle"),
                "current_round": current_round,
                "max_rounds": max_rounds,
                "best_result": best,
                "history_count": total_rounds,
            },
        }

    async def _handle_experiment_status(self, context: dict[str, Any]) -> dict[str, Any]:
        experiment_id = str(context.get("experiment_id") or "").strip()
        recent = echem_reader.list_recent_experiments(10)

        if experiment_id:
            match = next(
                (
                    item for item in recent
                    if experiment_id in str(item.get("name", "")) or experiment_id in str(item.get("run_dir", ""))
                ),
                None,
            )
        else:
            match = recent[0] if recent else None

        if not match:
            reply = "当前没有可用的实验目录记录。"
            if experiment_id:
                reply = f"没有找到实验 `{experiment_id}` 的本地记录。"
            return {"reply": reply, "experiment": None}

        details = echem_reader.read_experiment_dir(str(match.get("run_dir", "")))
        counts = details.get("counts", {})
        reply = (
            f"最近实验 `{match.get('name', '')}` 位于 {match.get('run_dir', '')}。"
            f" 当前检测到 CSV {counts.get('csv', 0)} 个、CV {counts.get('cv', 0)} 个、EIS {counts.get('eis', 0)} 个。"
        )
        return {"reply": reply, "experiment": {"summary": match, "details": details}}

    async def _handle_stop_optimization(self) -> dict[str, Any]:
        from src.api.routes import optimization as optimization_routes

        result = await optimization_routes.stop_optimization()
        status = str(result.get("status", "unknown"))
        if status == "stop_requested":
            reply = "已发送停止指令，优化会在当前轮次安全结束后退出。"
        elif status == "not_running":
            reply = "当前没有正在运行的优化任务，无需停止。"
        else:
            reply = f"已处理停止请求，返回状态：{status}。"
        return {"reply": reply, "control_result": result}

    async def _handle_knowledge_query(self, message: str) -> dict[str, Any]:
        text = message.strip()
        if not text:
            return {"reply": "请提供更具体的问题，例如实验记录、文献主题或故障类型。", "items": []}

        threshold_filter = self._extract_threshold_filter(text)
        if threshold_filter is not None:
            items = await self._query_experiments_by_threshold(*threshold_filter)
            return {
                "reply": self._format_threshold_reply(*threshold_filter, items),
                "items": items,
            }

        if "故障" in text or "报错" in text or "timeout" in text.lower():
            fault_type = self._extract_fault_type(text)
            items = await self._knowledge_skill.get_fault_history(fault_type=fault_type, top_k=5)
            return {
                "reply": self._format_fault_reply(fault_type, items),
                "items": items,
            }

        partitions = ["literature"] if any(keyword in text for keyword in ("文献", "tafel", "催化剂")) else None
        items = await self._knowledge_skill.search(query=text, partitions=partitions, top_k=5)

        # ── RAG: if we have retrieved docs, call LLM to generate a grounded answer ──
        if items:
            rag_reply = await self._generate_rag_answer(text, items)
            if rag_reply:
                return {"reply": rag_reply, "items": items}

        return {
            "reply": self._format_search_reply(text, items),
            "items": items,
        }

    async def _generate_rag_answer(self, question: str, items: list[dict[str, Any]]) -> str:
        """Use LLM to answer the question grounded in retrieved knowledge items."""
        context_parts: list[str] = []
        for i, item in enumerate(items[:5], 1):
            partition = item.get("partition", "unknown")
            payload = item.get("payload", {})
            score = item.get("score", 0.0)

            if partition == "literature":
                title = payload.get("title", "未知标题")
                content = (payload.get("content") or payload.get("abstract") or "")[:800]
                context_parts.append(f"[文献 {i}] 《{title}》（相关度 {score:.2f}）\n{content}")
            elif partition == "experiments":
                run_id = payload.get("run_id", "unknown")
                params = payload.get("params", {})
                metrics = payload.get("metrics", {})
                interp = payload.get("interpretation", "")[:400]
                context_parts.append(
                    f"[实验 {i}] {run_id}（相关度 {score:.2f}）\n参数: {params}\n指标: {metrics}"
                    + (f"\n解释: {interp}" if interp else "")
                )
            elif partition == "operations":
                event_type = payload.get("event_type", "")
                message = payload.get("message", "")[:400]
                context_parts.append(f"[运维 {i}] {event_type}（相关度 {score:.2f}）\n{message}")
            else:
                content = json.dumps(payload, ensure_ascii=False)[:400]
                context_parts.append(f"[知识 {i}] partition={partition}（相关度 {score:.2f}）\n{content}")

        context_text = "\n\n".join(context_parts)
        rag_system_prompt = (
            "你是 AutoHySeeker 知识库助手。请基于以下检索到的知识库文档，"
            "准确、简洁地回答用户问题。如果文档中没有足够信息，请明确说明。"
            "不要编造信息，直接引用文档中的数据和结论。用中文回答。\n\n"
            f"=== 检索到的知识文档 ===\n{context_text}\n=== 文档结束 ==="
        )

        try:
            result = await self.invoke(
                task={"question": question},
                context={"rag_context": context_text},
                messages=[{"role": "system", "content": rag_system_prompt}],
            )
            answer = str(result.get("content", "")).strip()
            if answer:
                return answer
        except Exception:
            pass

        return ""

    def _extract_threshold_filter(self, message: str) -> tuple[str, float] | None:
        pattern = re.compile(
            r"([A-Za-z]{1,2})[^0-9]{0,8}(?:超过|大于|高于|不少于|>=?)\s*(\d+(?:\.\d+)?)\s*%?",
            re.IGNORECASE,
        )
        match = pattern.search(message)
        if not match:
            return None
        return match.group(1).capitalize(), float(match.group(2)) / 100.0

    async def _query_experiments_by_threshold(self, element: str, threshold: float) -> list[dict[str, Any]]:
        hits = await self._knowledge_skill.search(query="", partitions=["experiments"], top_k=20)
        items: list[dict[str, Any]] = []
        for hit in hits:
            payload = hit.get("payload", {})
            params = payload.get("params", {})
            try:
                value = float(params.get(element, 0.0))
            except (TypeError, ValueError):
                value = 0.0
            if value >= threshold:
                items.append(
                    {
                        "run_id": payload.get("run_id"),
                        "project_id": payload.get("project_id"),
                        "params": params,
                        "metrics": payload.get("metrics", {}),
                        "score": hit.get("score", 0.0),
                    }
                )
        return items[:5]

    def _extract_fault_type(self, message: str) -> str:
        lowered = message.lower()
        if "timeout" in lowered:
            return "timeout"
        if "pump" in lowered or "泵" in message:
            return "pump"
        if "通信" in message:
            return "communication"
        return message.strip()

    def _format_threshold_reply(self, element: str, threshold: float, items: list[dict[str, Any]]) -> str:
        if not items:
            return f"没有查到 `{element}` 占比高于 {threshold:.0%} 的历史实验记录。"
        head = f"查到 {len(items)} 条 `{element}` 占比高于 {threshold:.0%} 的实验记录："
        lines = [head]
        for item in items[:3]:
            lines.append(
                f"- {item.get('run_id', 'unknown')}: params={item.get('params', {})}, metrics={item.get('metrics', {})}"
            )
        return "\n".join(lines)

    def _format_fault_reply(self, fault_type: str, items: list[dict[str, Any]]) -> str:
        if not items:
            return f"知识库中没有找到与 `{fault_type}` 相关的故障历史。"
        lines = [f"找到 {len(items)} 条与 `{fault_type}` 相关的故障记录："]
        for item in items[:3]:
            lines.append(
                f"- {item.get('event_type', 'unknown')} | severity={item.get('severity', '')} | "
                f"action={item.get('action_taken', '')} | resolved={item.get('resolved')}"
            )
        return "\n".join(lines)

    def _format_search_reply(self, query: str, items: list[dict[str, Any]]) -> str:
        if not items:
            return f"知识库中暂未检索到与“{query}”相关的记录。"

        lines = [f"知识库中找到 {len(items)} 条与“{query}”相关的记录："]
        for item in items[:3]:
            partition = item.get("partition", "unknown")
            payload = item.get("payload", {})
            if partition == "experiments":
                lines.append(
                    f"- 实验 {payload.get('run_id', 'unknown')}: params={payload.get('params', {})}, "
                    f"metrics={payload.get('metrics', {})}"
                )
            elif partition == "literature":
                lines.append(
                    f"- 文献 {payload.get('title', 'unknown')} ({payload.get('year', 'n/a')}): "
                    f"{(payload.get('abstract') or payload.get('content', ''))[:80]}"
                )
            elif partition == "operations":
                lines.append(
                    f"- 运维记录 {payload.get('event_type', 'unknown')}: {payload.get('message', '')[:80]}"
                )
            else:
                lines.append(f"- {partition}: {(json.dumps(payload, ensure_ascii=False))[:100]}")
        return "\n".join(lines)

    def _handle_general_help(self) -> dict[str, Any]:
        return {
            "reply": (
                "我可以查询优化状态、实验状态、知识库记录，也可以帮你发送停止优化指令。"
                " 你可以直接问“现在优化到第几轮了？”、“之前有没有类似实验？”或“帮我停一下优化”。"
            ),
            "items": [],
        }

    def _success(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "success",
            "data": data,
            "agent": self.name,
            "timestamp": _utc_now(),
        }

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "status": "error",
            "error": message,
            "agent": self.name,
            "timestamp": _utc_now(),
            "data": {
                "reply": "当前无法完成该聊天请求，请稍后重试。",
                "intent": "error",
            },
        }
