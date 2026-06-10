"""Regenerate all paper/section abstracts and overviews per 10_Abstract+overview Prompt.md.

Usage:
    python regenerate_summaries.py                     # regenerate ALL (422 files)
    python regenerate_summaries.py --paper-id 2025_sha_...  # single paper
    python regenerate_summaries.py --dry-run           # preview without calling LLM

Prompt specification: LiteratureClean/10_Abstract+overview Prompt.md
LLM config: configs/agent_models.toml [chat] section
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent.resolve()
AUTOHYSEEKER = HERE.parent.resolve()
AGENT_MODELS_PATH = AUTOHYSEEKER / "configs" / "agent_models.toml"

# ── L0 Paper Abstract Prompt ──────────────────────────────────────────
PAPER_L0_SYSTEM = (
    "你是一个科研文献摘要撰写助手。输出必须严格遵循指定格式，不要添加任何额外说明文字。"
)

PAPER_L0_USER = """请为论文全文生成一个约200字的中文摘要，用于后续向量检索判断相关性。

要求：
1. 一句话说明研究对象（什么材料体系、什么反应类型）
2. 一句话说明核心发现（方向性的，不需要具体数值）
3. 一句话说明研究方法路线
4. 一句话说明主要结论/贡献
5. 列出3-5个关键词

不要写：具体的数值、文献引用、作者信息、背景铺垫

输出格式（纯文本）：
研究对象：...
核心发现：...
方法路线：...
主要结论：...
关键词：xxx, xxx, xxx

以下为论文全文内容：
{content}"""

# ── L0 Section Abstract Prompt ────────────────────────────────────────
SECTION_L0_SYSTEM = (
    "你是一个科研文献摘要撰写助手。输出必须严格遵循指定格式，不要添加任何额外说明文字。"
)

SECTION_L0_USER = """请为论文章节生成一个约200字的中文摘要，用于后续向量检索判断该章节与查询的相关性。

要求：
1. 一句话说明本章节的定位（Introduction/Methods/Results/Discussion中的哪个）
2. 一句话概括本章节的核心内容
3. 列出本章节涉及的关键实体（材料名、方法名、指标名、条件等）

不要写具体数值。

输出格式（纯文本）：
章节定位：...
核心内容：...
关键实体：xxx, xxx, xxx

以下为章节内容：
标题：{section_title}
段落内容：
{paragraphs_text}"""

# ── L1 Paper Overview Prompt ──────────────────────────────────────────
PAPER_L1_SYSTEM = (
    "你是一个科研文献导览撰写助手。输出必须严格遵循指定格式，不要添加任何额外说明文字。"
)

PAPER_L1_USER = """请为以下论文生成一个约800字的结构化导览，用于Agent检索时从论文导航到具体章节。

要求：
1. 论文定位（1句话，这篇论文整体做什么）
2. 各章节简要索引（每章1句话），按实际章节名列出
3. 全文关键实体汇总（材料、方法、指标、条件）

输出格式（纯文本）：
论文定位：...

章节索引：
{section_list}

关键实体：xxx, xxx, xxx

以下为论文全文内容：
{content}"""

# ── L1 Section Overview Prompt ────────────────────────────────────────
SECTION_L1_SYSTEM = (
    "你是一个科研文献导览撰写助手。输出必须严格遵循指定格式，不要添加任何额外说明文字。"
)

SECTION_L1_USER = """请为以下论文章节生成一个约800字的结构化导览，用于Agent检索时从章节定位到具体段落。

要求：
1. 本章节定位（1句话）
2. 逐段索引（每段1句话说明信息类型），格式：P001: ...
3. 本章节关键实体列表

输出格式（纯文本）：
章节定位：...

逐段索引：
{paragraph_index}

关键实体：xxx, xxx, xxx

以下为章节内容：
标题：{section_title}
段落内容：
{paragraphs_text}"""

# ── English L0 Paper Abstract Prompt ──────────────────────────────────
EN_PAPER_L0_SYSTEM = (
    "You are a scientific abstract writer. Output must strictly follow the "
    "specified format. Do not add any extra commentary."
)

EN_PAPER_L0_USER = """Write a concise abstract (~200 words) for the following paper,
to be used for vector-based relevance retrieval.

Requirements:
1. One sentence identifying the research object (material system, reaction type)
2. One sentence stating the core finding (directional, no specific values)
3. One sentence describing the methodological approach
4. One sentence summarizing the main conclusion/contribution
5. List 3-5 keywords

Do NOT include: specific numerical values, literature references, author info, background.

Output format (plain text):
Research Object: ...
Core Finding: ...
Method: ...
Conclusion: ...
Keywords: xxx, xxx, xxx

Paper content:
{content}"""

# ── English L0 Section Abstract Prompt ────────────────────────────────
EN_SECTION_L0_SYSTEM = (
    "You are a scientific abstract writer. Output must strictly follow the "
    "specified format. Do not add any extra commentary."
)

EN_SECTION_L0_USER = """Write a concise abstract (~200 words) for the following paper section,
to be used for vector-based relevance retrieval.

Requirements:
1. One sentence positioning this section (Introduction / Methods / Results / Discussion)
2. One sentence summarizing the core content of this section
3. List key entities involved (materials, methods, metrics, conditions, etc.)

Do NOT include specific numerical values.

Output format (plain text):
Section Role: ...
Core Content: ...
Key Entities: xxx, xxx, xxx

Section content:
Title: {section_title}
Paragraphs:
{paragraphs_text}"""

# ── English L1 Paper Overview Prompt ──────────────────────────────────
EN_PAPER_L1_SYSTEM = (
    "You are a scientific overview writer. Output must strictly follow the "
    "specified format. Do not add any extra commentary."
)

EN_PAPER_L1_USER = """Write a structured overview (~800 words) for the following paper,
to help agents navigate from paper-level to specific sections.

Requirements:
1. Paper positioning (1 sentence: what this paper does overall)
2. Section index (1 sentence per chapter), using actual section names
3. Summary of key entities (materials, methods, metrics, conditions)

Output format (plain text):
Paper Positioning: ...

Section Index:
{section_list}

Key Entities: xxx, xxx, xxx

Paper content:
{content}"""

# ── English L1 Section Overview Prompt ────────────────────────────────
EN_SECTION_L1_SYSTEM = (
    "You are a scientific overview writer. Output must strictly follow the "
    "specified format. Do not add any extra commentary."
)

EN_SECTION_L1_USER = """Write a structured overview (~800 words) for the following paper section,
to help agents navigate from section-level to specific paragraphs.

Requirements:
1. Section positioning (1 sentence)
2. Paragraph index (1 sentence per paragraph describing information type), format: P001: ...
3. Key entities in this section

Output format (plain text):
Section Positioning: ...

Paragraph Index:
{paragraph_index}

Key Entities: xxx, xxx, xxx

Section content:
Title: {section_title}
Paragraphs:
{paragraphs_text}"""

# ── LLM Judge Prompt ──────────────────────────────────────────────────
LLM_JUDGE_SYSTEM = "你是一个科研文献段落筛选助手。输出严格JSON数组，不要任何其他文字。"

LLM_JUDGE_USER = """用户查询：
{query}

以下是一个学术论文章节的段落原文，每段有编号。

{section_content}

请阅读所有段落，选出与用户查询直接相关的段落。

判断标准：
- 段落内容是否包含查询所需的信息类型（因果关系、参数范围、方法描述、实验条件、性能比较等）
- 不要求段落的主题和查询完全一致，只要包含有用信息即可保留
- 如果全部段落都不相关，输出 []

输出格式（严格JSON数组，不要任何其他文字）：
["P003", "P005"]"""


# ── Language Detection ──────────────────────────────────────────────────

def detect_paper_language(paper_dir: Path) -> str:
    """Return 'zh' or 'en' based on the paper's dominant language."""
    full_clean = paper_dir / "full_clean.md"
    if not full_clean.exists():
        return "en"  # default to English
    text = full_clean.read_text(encoding="utf-8", errors="replace")[:5000]
    # Count Chinese characters
    zh_chars = sum(1 for c in text if "一" <= c <= "鿿" or "㐀" <= c <= "䶿")
    # If >15% Chinese characters, treat as Chinese paper
    return "zh" if zh_chars > len(text) * 0.15 else "en"


def select_prompts(lang: str):
    """Return (paper_L0_sys, paper_L0_usr, paper_L1_sys, paper_L1_usr,
                section_L0_sys, section_L0_usr, section_L1_sys, section_L1_usr)."""
    if lang == "zh":
        return (PAPER_L0_SYSTEM, PAPER_L0_USER, PAPER_L1_SYSTEM, PAPER_L1_USER,
                SECTION_L0_SYSTEM, SECTION_L0_USER, SECTION_L1_SYSTEM, SECTION_L1_USER)
    else:
        return (EN_PAPER_L0_SYSTEM, EN_PAPER_L0_USER, EN_PAPER_L1_SYSTEM, EN_PAPER_L1_USER,
                EN_SECTION_L0_SYSTEM, EN_SECTION_L0_USER, EN_SECTION_L1_SYSTEM, EN_SECTION_L1_USER)


# ── Helpers ────────────────────────────────────────────────────────────

def load_chat_llm_config() -> dict[str, Any]:
    if not AGENT_MODELS_PATH.exists():
        raise RuntimeError(f"Config not found: {AGENT_MODELS_PATH}")
    with AGENT_MODELS_PATH.open("rb") as fh:
        raw = tomllib.load(fh)
    chat = raw.get("chat", {})
    if not isinstance(chat, dict):
        raise RuntimeError("agent_models.toml [chat] section is missing or invalid")
    required = ["model", "base_url", "api_key"]
    for key in required:
        if key not in chat or not chat[key]:
            raise RuntimeError(f"agent_models.toml [chat].{key} is required")
    return {
        "model": chat["model"],
        "base_url": chat["base_url"],
        "api_key": os.path.expandvars(chat["api_key"]),
        "temperature": chat.get("temperature", 0.3),
        "max_tokens": chat.get("max_tokens", 2000),
    }


def call_llm(system: str, user: str, cfg: dict[str, Any]) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    completion = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
        stream=False,
    )
    if not completion.choices:
        return ""
    return (completion.choices[0].message.content or "").strip()


def _read_metadata_title(paper_dir: Path) -> str:
    meta = paper_dir / "metadata.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            return data.get("title", paper_dir.name)
        except Exception:
            pass
    return paper_dir.name


def _read_limited(path: Path, limit: int = 16000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def find_papers() -> list[Path]:
    papers = []
    for d in sorted(HERE.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "metadata.json").exists():
            continue
        if not (d / "ov_index").exists():
            continue
        papers.append(d)
    return papers


def build_section_list(paper_dir: Path) -> str:
    """Build a section list string from sections_by_heading directory names."""
    sbh = paper_dir / "sections_by_heading"
    if not sbh.exists():
        return "(no sections found)"

    lines = []
    for sec_dir in sorted(sbh.iterdir()):
        if not sec_dir.is_dir() or sec_dir.name == "_debug":
            continue
        heading_file = sec_dir / "heading.json"
        if heading_file.exists():
            try:
                h = json.loads(heading_file.read_text(encoding="utf-8"))
                title = h.get("heading_text", sec_dir.name)
            except Exception:
                title = sec_dir.name
        else:
            title = sec_dir.name
        lines.append(f"  {sec_dir.name}: {title}")
    return "\n".join(lines) if lines else "(no sections found)"


def build_paragraph_index_for_section(paper_dir: Path, section_slug: str) -> str:
    """Build P001, P002, ... index from paragraph files."""
    para_dir = paper_dir / "sections_by_heading" / section_slug / "paragraphs"
    if not para_dir.exists():
        return "(no paragraphs)"

    lines = []
    for i, pf in enumerate(sorted(para_dir.glob("*.md")), 1):
        text = _read_limited(pf, 800)
        # Extract first sentence as summary
        m = re.search(r"## Text\s*\n\s*\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
        if m:
            preview = m.group(1).strip()[:120].replace("\n", " ")
        else:
            preview = text[:120].replace("\n", " ")
        lines.append(f"P{i:03d}: {preview}")
    return "\n".join(lines) if lines else "(no paragraphs)"


def read_section_paragraphs_text(paper_dir: Path, section_slug: str) -> str:
    """Read all paragraph texts for a section, labeled P001, P002, ..."""
    para_dir = paper_dir / "sections_by_heading" / section_slug / "paragraphs"
    if not para_dir.exists():
        return "(no paragraphs)"

    parts = []
    for i, pf in enumerate(sorted(para_dir.glob("*.md")), 1):
        text = pf.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"## Text\s*\n\s*\n(.+?)(?=\n## |\Z)", text, re.DOTALL)
        if m:
            body = m.group(1).strip()
        else:
            body = text.strip()
        if body:
            parts.append(f"=== P{i:03d} ===\n{body}")
    return "\n\n".join(parts) if parts else "(no paragraphs)"


# ── Generators ─────────────────────────────────────────────────────────

def generate_paper_l0(paper_dir: Path, cfg: dict[str, Any], lang: str = "en") -> str:
    content = _read_limited(paper_dir / "full_clean.md", 16000)
    sys_p, usr_p, _, _, _, _, _, _ = select_prompts(lang)
    user = usr_p.format(content=content)
    return call_llm(sys_p, user, cfg)


def generate_paper_l1(paper_dir: Path, cfg: dict[str, Any], lang: str = "en") -> str:
    content = _read_limited(paper_dir / "full_clean.md", 16000)
    section_list = build_section_list(paper_dir)
    _, _, sys_p, usr_p, _, _, _, _ = select_prompts(lang)
    user = usr_p.format(section_list=section_list, content=content)
    return call_llm(sys_p, user, cfg)


def generate_section_l0(
    paper_dir: Path, section_slug: str, cfg: dict[str, Any], lang: str = "en"
) -> str:
    heading_file = paper_dir / "sections_by_heading" / section_slug / "heading.json"
    if heading_file.exists():
        try:
            h = json.loads(heading_file.read_text(encoding="utf-8"))
            section_title = h.get("heading_text", section_slug)
        except Exception:
            section_title = section_slug
    else:
        section_title = section_slug

    paragraphs_text = read_section_paragraphs_text(paper_dir, section_slug)
    _, _, _, _, sys_p, usr_p, _, _ = select_prompts(lang)
    user = usr_p.format(
        section_title=section_title, paragraphs_text=paragraphs_text
    )
    return call_llm(sys_p, user, cfg)


def generate_section_l1(
    paper_dir: Path, section_slug: str, cfg: dict[str, Any], lang: str = "en"
) -> str:
    heading_file = paper_dir / "sections_by_heading" / section_slug / "heading.json"
    if heading_file.exists():
        try:
            h = json.loads(heading_file.read_text(encoding="utf-8"))
            section_title = h.get("heading_text", section_slug)
        except Exception:
            section_title = section_slug
    else:
        section_title = section_slug

    para_index = build_paragraph_index_for_section(paper_dir, section_slug)
    paragraphs_text = read_section_paragraphs_text(paper_dir, section_slug)
    _, _, _, _, _, _, sys_p, usr_p = select_prompts(lang)
    user = usr_p.format(
        section_title=section_title,
        paragraph_index=para_index,
        paragraphs_text=paragraphs_text,
    )
    return call_llm(sys_p, user, cfg)


# ── Main ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate abstract/overview per 10_Abstract+overview Prompt.md"
    )
    parser.add_argument(
        "--paper-id", type=str, default=None, help="Only regenerate a single paper"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be regenerated without calling LLM",
    )
    args = parser.parse_args()

    cfg = load_chat_llm_config()
    print(f"LLM: {cfg['model']} @ {cfg['base_url']}")

    papers = find_papers()
    if args.paper_id:
        papers = [p for p in papers if p.name == args.paper_id]
        if not papers:
            print(f"Paper not found: {args.paper_id}")
            return

    print(f"Papers: {len(papers)}")

    total_files = 0
    total_ok = 0
    total_err = 0

    for paper_dir in papers:
        paper_id = paper_dir.name
        ov = paper_dir / "ov_index"
        sections_root = ov / "sections"

        lang = detect_paper_language(paper_dir)
        lang_label = "ZH" if lang == "zh" else "EN"
        print(f"\n[{paper_id}] [{lang_label}]")

        # ── Paper L0 ──
        pa = ov / "paper.abstract.md"
        if args.dry_run:
            print(f"  [dry-run] would regenerate paper.abstract.md")
        else:
            try:
                result = generate_paper_l0(paper_dir, cfg, lang)
                pa.write_text(result + "\n", encoding="utf-8")
                print(f"  paper.abstract.md: OK ({len(result)} chars)")
                total_ok += 1
            except Exception as e:
                print(f"  paper.abstract.md: ERR {e}")
                total_err += 1
            time.sleep(0.5)  # rate limit
        total_files += 1

        # ── Paper L1 ──
        po = ov / "paper.overview.md"
        if args.dry_run:
            print(f"  [dry-run] would regenerate paper.overview.md")
        else:
            try:
                result = generate_paper_l1(paper_dir, cfg, lang)
                po.write_text(result + "\n", encoding="utf-8")
                print(f"  paper.overview.md: OK ({len(result)} chars)")
                total_ok += 1
            except Exception as e:
                print(f"  paper.overview.md: ERR {e}")
                total_err += 1
            time.sleep(0.5)
        total_files += 1

        # ── Section L0 + L1 ──
        if not sections_root.exists():
            continue

        section_dirs = sorted(
            [d for d in sections_root.iterdir() if d.is_dir()]
        )
        for sec_dir in section_dirs:
            section_slug = sec_dir.name
            short = section_slug[:50]

            # Section L0
            sa = sec_dir / "abstract.md"
            if args.dry_run:
                print(f"  [dry-run] would regenerate {short}/abstract.md")
            else:
                try:
                    result = generate_section_l0(paper_dir, section_slug, cfg, lang)
                    sa.write_text(result + "\n", encoding="utf-8")
                    print(f"  {short}/abstract.md: OK ({len(result)} chars)")
                    total_ok += 1
                except Exception as e:
                    print(f"  {short}/abstract.md: ERR {e}")
                    total_err += 1
                time.sleep(0.3)
            total_files += 1

            # Section L1
            so = sec_dir / "overview.md"
            if args.dry_run:
                print(f"  [dry-run] would regenerate {short}/overview.md")
            else:
                try:
                    result = generate_section_l1(paper_dir, section_slug, cfg, lang)
                    so.write_text(result + "\n", encoding="utf-8")
                    print(f"  {short}/overview.md: OK ({len(result)} chars)")
                    total_ok += 1
                except Exception as e:
                    print(f"  {short}/overview.md: ERR {e}")
                    total_err += 1
                time.sleep(0.3)
            total_files += 1

    print(f"\n{'='*60}")
    print(f"Total files: {total_files}")
    print(f"OK: {total_ok}, ERR: {total_err}")
    if args.dry_run:
        print("(dry-run, no files written)")


if __name__ == "__main__":
    main()
