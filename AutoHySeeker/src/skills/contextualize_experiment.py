"""C1 — ContextualizeExperimentSkill: retrieve context from OpenViking knowledge base.

Queries the OpenViking knowledge base for relevant:
* **Literature** — academic papers, instrument manuals, domain knowledge
* **Experiment records** — archived past experiments with similar goals/techniques

Then optionally uses the LLM (claude-opus-4.6) to synthesise a concise context
summary from the retrieved chunks.

Falls back gracefully in two stages:
1. If the LLM is unavailable — returns raw retrieved chunks without synthesis.
2. If OpenViking is unavailable — returns an empty-context result with a clear message.
"""

from __future__ import annotations

import json
from typing import Any

from src.skills.base import BaseSkill, SkillResult

# LLM model for Phase 4 C-series skills
_OPUS_MODEL = "anthropic/claude-opus-4-6"


def _build_synthesis_prompt(
    query: str,
    goal: str,
    literature: list[dict[str, Any]],
    experiments: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build LLM messages to synthesise context from retrieved chunks."""
    lit_text = "\n\n".join(
        "[文献 {n} | score={s}]\n{c}".format(
            n=i + 1,
            s=f"{r['score']:.3f}" if isinstance(r.get("score"), (int, float)) else "?",
            c=r.get("content", ""),
        )
        for i, r in enumerate(literature)
    ) or "(无相关文献)"

    exp_text = "\n\n".join(
        f"[实验记录 {i + 1} | {r.get('uri', '?')}]\n{r.get('content', '')}"
        for i, r in enumerate(experiments)
    ) or "(无历史实验记录)"

    system = (
        "You are an expert electrochemist and scientific context synthesiser for "
        "the AutoHySeeker autonomous experimentation platform. "
        "Given retrieved literature and past experiment records, produce a concise "
        "scientific context summary that will help design or interpret the current "
        "experiment. "
        "Respond in JSON."
    )

    user = f"""Synthesise scientific context for the following experiment task.

**Query:** {query}
**Experiment Goal:** {goal or "Not specified"}

**Retrieved Literature:**
{lit_text}

**Relevant Past Experiments:**
{exp_text}

Return a JSON object:
{{
  "context_summary": "<2-4 sentence synthesis of the most relevant information>",
  "key_references": ["<brief citation 1>", "<brief citation 2>"],
  "relevant_parameters": {{"<param>": "<value/range from literature>"}},
  "experimental_precedents": ["<relevant past result 1>"],
  "confidence": "high|medium|low"
}}"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _raw_context_summary(
    query: str,
    literature: list[dict[str, Any]],
    experiments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fallback context dict when LLM synthesis is unavailable."""
    refs = [
        r.get("uri") or r.get("metadata", {}).get("source", f"lit_{i + 1}")
        for i, r in enumerate(literature)
    ]
    exp_refs = [
        r.get("uri") or r.get("metadata", {}).get("run_id", f"exp_{i + 1}")
        for i, r in enumerate(experiments)
    ]

    parts = []
    if literature:
        parts.append(f"Retrieved {len(literature)} literature chunk(s) relevant to: {query!r}.")
    if experiments:
        parts.append(f"Found {len(experiments)} similar past experiment(s).")
    if not parts:
        parts.append(f"No knowledge-base results found for: {query!r}.")

    return {
        "context_summary": " ".join(parts),
        "key_references": refs,
        "relevant_parameters": {},
        "experimental_precedents": exp_refs,
        "confidence": "low",
        "source": "raw_chunks",
    }


class ContextualizeExperimentSkill(BaseSkill):
    """C1 — Retrieve relevant literature and experiment records from OpenViking.

    Workflow:

    1. Query ``VikingKnowledgeBase.search_literature(query)``
    2. Query ``VikingKnowledgeBase.search_experiments(query)``
    3. Use LLM (claude-opus-4.6) to synthesise a context summary.
    4. Return :class:`~src.skills.base.SkillResult` with retrieved chunks
       and synthesised context.

    Degradation:
    * No LLM → returns raw chunks without synthesis (``source="raw_chunks"``).
    * No OpenViking → returns empty context with informative message.
    """

    name = "contextualize_experiment"
    description = "从 OpenViking 知识库检索相关文献与实验记录，使用 LLM 合成上下文摘要"
    required_tools: list[str] = []

    #: LLM model for context synthesis
    model: str = _OPUS_MODEL

    async def execute(
        self,
        query: str = "",
        goal: str = "",
        techniques: list[str] | None = None,
        top_k: int = 5,
        **kwargs: Any,
    ) -> SkillResult:
        """Retrieve context from the OpenViking knowledge base.

        Args:
            query: Natural-language search query describing the experiment topic
                (e.g. ``"HER activity NiFe catalyst acidic electrolyte"``).
            goal: Free-text experiment goal used to supplement the query and
                LLM synthesis prompt (e.g. ``"screen OER catalysts"``).
            techniques: Optional list of electrochemical techniques to append
                to the query (e.g. ``["CV", "EIS"]``).
            top_k: Maximum number of chunks to retrieve per source (literature /
                experiments).  Defaults to 5.
            **kwargs: Ignored.

        Returns:
            :class:`~src.skills.base.SkillResult` where ``data`` is a dict with:

            * ``literature`` — list of retrieved literature chunks.
            * ``experiments`` — list of retrieved experiment records.
            * ``context_summary`` — synthesised summary string.
            * ``key_references`` — brief citation list.
            * ``relevant_parameters`` — parameter hints from literature.
            * ``experimental_precedents`` — relevant past experiment URIs.
            * ``confidence`` — ``"high"|"medium"|"low"``.
            * ``source`` — ``"llm"|"raw_chunks"|"unavailable"``.
        """
        if not query and not goal:
            return SkillResult(
                success=False,
                data={},
                message="At least one of 'query' or 'goal' is required",
                artifacts=[],
            )

        # Build effective query
        effective_query = query or goal
        if techniques:
            effective_query = f"{effective_query} {' '.join(techniques)}"

        # ── Step 1: retrieve from OpenViking ─────────────────────────────────
        try:
            from src.rag import get_viking_kb  # noqa: PLC0415
            kb = get_viking_kb()
        except Exception as import_exc:
            return SkillResult(
                success=False,
                data={"source": "unavailable"},
                message=f"OpenViking client unavailable: {import_exc}",
                artifacts=[],
            )

        literature = kb.search_literature(effective_query, top_k=top_k)
        experiments = kb.search_experiments(effective_query, top_k=top_k)

        n_lit = len(literature)
        n_exp = len(experiments)

        if not kb.is_available:
            return SkillResult(
                success=True,
                data={
                    "literature": [],
                    "experiments": [],
                    "context_summary": (
                        "OpenViking knowledge base is not initialised. "
                        "No context could be retrieved. "
                        "Ingest documents using VikingKnowledgeBase.ingest_document() first."
                    ),
                    "key_references": [],
                    "relevant_parameters": {},
                    "experimental_precedents": [],
                    "confidence": "low",
                    "source": "unavailable",
                },
                message="OpenViking unavailable — empty context returned",
                artifacts=[],
            )

        # ── Step 2: LLM synthesis ─────────────────────────────────────────────
        try:
            from src.common.llm_client import chat_completion  # noqa: PLC0415

            messages = _build_synthesis_prompt(effective_query, goal, literature, experiments)
            raw = await chat_completion(messages=messages, model=self.model, temperature=0.2)

            # Strip markdown fences if present
            text = raw.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            context_data: dict[str, Any] = json.loads(text)
            context_data["source"] = "llm"
            context_data["model"] = self.model

        except Exception as llm_exc:
            # Fallback: return raw chunks without LLM synthesis
            context_data = _raw_context_summary(effective_query, literature, experiments)
            context_data["llm_error"] = type(llm_exc).__name__

        # Merge retrieved chunks into final result
        context_data["literature"] = literature
        context_data["experiments"] = experiments

        return SkillResult(
            success=True,
            data=context_data,
            message=(
                f"Retrieved {n_lit} literature chunk(s) and {n_exp} experiment record(s) "
                f"[source={context_data.get('source', '?')}]"
            ),
            artifacts=[],
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Natural-language search query for the knowledge base, "
                        "e.g. 'HER NiFe catalyst acidic electrolyte Tafel slope'"
                    ),
                },
                "goal": {
                    "type": "string",
                    "description": "Free-text experiment goal used to supplement the query",
                },
                "techniques": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Electrochemical techniques to include in the search query",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of chunks per source (default 5)",
                    "default": 5,
                },
            },
            "required": [],
        }


# Convenience singleton
contextualize_experiment_skill = ContextualizeExperimentSkill()
