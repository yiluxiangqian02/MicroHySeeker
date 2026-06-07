"""Generate and refresh preprocessing regression report for LiteratureClean.

This module is intentionally standalone and lightweight so it can be called
after batch/watch preprocessing without introducing heavy dependencies.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from verify_new_structure import validate_paper_dir


HERE = Path(__file__).resolve().parent
DEFAULT_CLEAN_ROOT = HERE
DEFAULT_RUN_LOG = HERE / "batch_run_log.json"
DEFAULT_REPORT = HERE / "preprocessing_regression_report.md"


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _paper_dirs(clean_root: Path) -> list[Path]:
    return sorted([d for d in clean_root.iterdir() if d.is_dir() and (d / "metadata.json").exists()], key=lambda p: p.name)


def _count_subheadings(paper_dir: Path) -> int:
    sections = paper_dir / "sections"
    if not sections.exists():
        return 0
    total = 0
    for section_dir in sorted([d for d in sections.iterdir() if d.is_dir()], key=lambda p: p.name):
        payload = _load_json(section_dir / "subheading_index.json", {})
        total += len((payload or {}).get("subheadings") or [])
    return total


def _count_figures(paper_dir: Path) -> int:
    figures_dir = paper_dir / "figures"
    if not figures_dir.exists():
        return 0
    return len([d for d in figures_dir.iterdir() if d.is_dir()])


def _count_tables(paper_dir: Path) -> int:
    tables_dir = paper_dir / "tables"
    if not tables_dir.exists():
        return 0
    return len([d for d in tables_dir.iterdir() if d.is_dir()])


def _iter_subheadings(paper_dir: Path) -> list[dict[str, Any]]:
    sections = paper_dir / "sections"
    if not sections.exists():
        return []
    items: list[dict[str, Any]] = []
    for section_dir in sorted([d for d in sections.iterdir() if d.is_dir()], key=lambda p: p.name):
        payload = _load_json(section_dir / "subheading_index.json", {})
        subs = (payload or {}).get("subheadings") or []
        if isinstance(subs, list):
            items.extend([s for s in subs if isinstance(s, dict)])
    return items


def _safe_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _safe_ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return num / den


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _keyword_quality_opinion(uncertain_ratio: float, preview_only_ratio: float, avg_gap: float) -> tuple[str, str]:
    if uncertain_ratio <= 0.10 and preview_only_ratio <= 0.15 and avg_gap >= 2.0:
        return "合格", "关键词覆盖与区分度均在目标范围内，可继续按当前词表迭代。"
    if uncertain_ratio <= 0.20 and preview_only_ratio <= 0.25 and avg_gap >= 1.5:
        return "基本合格", "建议补充少量高区分词，优先降低 preview-only 与低分差条目。"
    if uncertain_ratio > 0.20:
        return "待优化", "is_uncertain 比例偏高，建议补充中英同义词并增强标题关键词覆盖。"
    if preview_only_ratio > 0.25:
        return "待优化", "preview-only 偏高，说明标题关键词不足，建议增加 strong_keywords。"
    return "待优化", "top1-second 分差偏小，关键词区分度不足，建议加入互斥/高区分术语。"


def _tokenize_heading(text: str) -> list[str]:
    # Keep both English words and CJK blocks for mixed-language headings.
    parts = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", text or "")
    return [p.lower() for p in parts]


def _extract_hit_terms(hits: Any) -> list[str]:
    terms: list[str] = []
    if not isinstance(hits, list):
        return terms
    for hit in hits:
        if isinstance(hit, dict):
            term = str(hit.get("term") or "").strip().lower()
            if term:
                terms.append(term)
    return terms


def _score_metrics(paper_dir: Path) -> dict[str, Any]:
    subheadings = _iter_subheadings(paper_dir)
    total = len(subheadings)

    uncertain_count = 0
    preview_only_count = 0
    gap_values: list[float] = []
    low_gap_count = 0
    uncertain_examples: list[dict[str, Any]] = []
    preview_only_examples: list[dict[str, Any]] = []
    low_gap_examples: list[dict[str, Any]] = []
    conflict_term_counts: dict[str, int] = {}
    missing_keyword_counts: dict[str, int] = {}

    for sub in subheadings:
        if sub.get("is_uncertain"):
            uncertain_count += 1

        breakdown = sub.get("score_breakdown") or {}
        gap = _safe_number((breakdown or {}).get("score_gap"))
        if gap is not None:
            gap_values.append(gap)
            if gap < 2:
                low_gap_count += 1
                if len(low_gap_examples) < 5:
                    low_gap_examples.append(
                        {
                            "heading_id": sub.get("heading_id"),
                            "heading": sub.get("original_heading") or "",
                            "top": (breakdown or {}).get("top_section_id") or "",
                            "second": (breakdown or {}).get("second_section_id") or "",
                            "gap": gap,
                        }
                    )

        top_section_id = (breakdown or {}).get("top_section_id")
        top_score = _safe_number((breakdown or {}).get("top_score"))
        second_section_id = (breakdown or {}).get("second_section_id")
        second_score = _safe_number((breakdown or {}).get("second_score"))
        section_scores = (breakdown or {}).get("section_scores") or []
        if not isinstance(section_scores, list):
            continue
        top_row: dict[str, Any] | None = None
        second_row: dict[str, Any] | None = None
        for section in section_scores:
            if isinstance(section, dict) and section.get("section_id") == top_section_id:
                top_row = section
            if isinstance(section, dict) and section.get("section_id") == second_section_id:
                second_row = section
        if not isinstance(top_row, dict):
            continue

        if sub.get("is_uncertain") and len(uncertain_examples) < 5:
            uncertain_examples.append(
                {
                    "heading_id": sub.get("heading_id"),
                    "heading": sub.get("original_heading") or "",
                    "top": top_section_id or "",
                    "top_score": 0.0 if top_score is None else top_score,
                    "second": second_section_id or "",
                    "second_score": 0.0 if second_score is None else second_score,
                    "gap": 0.0 if gap is None else gap,
                    "reasons": sub.get("uncertain_reasons") or [],
                }
            )

        heading_hits = top_row.get("heading_hits") or []
        position_hits = top_row.get("position_hits") or []
        preview_hits = top_row.get("preview_hits") or []

        if isinstance(second_row, dict):
            top_terms = set(_extract_hit_terms(heading_hits))
            second_terms = set(_extract_hit_terms(second_row.get("heading_hits") or []))
            for term in sorted(top_terms.intersection(second_terms)):
                conflict_term_counts[term] = conflict_term_counts.get(term, 0) + 1

        if sub.get("is_uncertain"):
            top_heading_terms = set(_extract_hit_terms(heading_hits))
            second_heading_terms = set(_extract_hit_terms((second_row or {}).get("heading_hits") if isinstance(second_row, dict) else []))
            has_heading_signal = bool(top_heading_terms or second_heading_terms)
            if not has_heading_signal:
                title = str(sub.get("original_heading") or "")
                for token in _tokenize_heading(title):
                    if token in {"figure", "table", "section", "chapter", "part", "study", "results", "method", "discussion"}:
                        continue
                    if token.isdigit():
                        continue
                    missing_keyword_counts[token] = missing_keyword_counts.get(token, 0) + 1

        if heading_hits or position_hits or not preview_hits:
            continue

        preview_weight = 0.0
        for hit in preview_hits:
            if isinstance(hit, dict):
                hit_w = _safe_number(hit.get("weight"))
                if hit_w is not None:
                    preview_weight += hit_w

        if top_score is not None and abs(top_score - preview_weight) < 1e-9 and top_score > 0:
            preview_only_count += 1
            if len(preview_only_examples) < 5:
                preview_only_examples.append(
                    {
                        "heading_id": sub.get("heading_id"),
                        "heading": sub.get("original_heading") or "",
                        "top": top_section_id or "",
                        "top_score": top_score,
                    }
                )

    avg_gap = (sum(gap_values) / len(gap_values)) if gap_values else 0.0
    min_gap = min(gap_values) if gap_values else 0.0
    top_conflicts = sorted(conflict_term_counts.items(), key=lambda x: (-x[1], x[0]))[:10]
    top_missing = sorted(missing_keyword_counts.items(), key=lambda x: (-x[1], x[0]))[:10]

    return {
        "subheading_total": total,
        "is_uncertain_count": uncertain_count,
        "is_uncertain_ratio": _safe_ratio(uncertain_count, total),
        "preview_only_count": preview_only_count,
        "preview_only_ratio": _safe_ratio(preview_only_count, total),
        "avg_score_gap": avg_gap,
        "min_score_gap": min_gap,
        "low_gap_count": low_gap_count,
        "low_gap_ratio": _safe_ratio(low_gap_count, total),
        "uncertain_examples": uncertain_examples,
        "preview_only_examples": preview_only_examples,
        "low_gap_examples": low_gap_examples,
        "top_conflicts": top_conflicts,
        "top_missing_keywords": top_missing,
    }


def _legacy_residuals(paper_dir: Path) -> tuple[list[str], list[str], list[str]]:
    memory_cards_hits: list[str] = []
    empty_legacy_hits: list[str] = []
    legacy_hits: list[str] = []

    memory_cards = paper_dir / "memory_cards"
    if memory_cards.exists():
        memory_cards_hits.append(str(memory_cards))

    for name in [".abstract.md", ".overview.md", "heading_index.md"]:
        p = paper_dir / name
        if p.exists():
            legacy_hits.append(str(p))
            try:
                if p.stat().st_size == 0 and name in {".abstract.md", ".overview.md"}:
                    empty_legacy_hits.append(str(p))
            except Exception:
                pass

    headings_dir = paper_dir / "headings"
    if headings_dir.exists():
        legacy_hits.append(str(headings_dir))

    return memory_cards_hits, empty_legacy_hits, legacy_hits


def generate_preprocessing_regression_report(
    clean_root: Path = DEFAULT_CLEAN_ROOT,
    run_log_path: Path = DEFAULT_RUN_LOG,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    papers = _paper_dirs(clean_root)
    run_log = _load_json(run_log_path, {"entries": {}})
    entries = (run_log or {}).get("entries", {}) if isinstance(run_log, dict) else {}

    per_paper_rows: list[dict[str, Any]] = []
    manual_review_list: list[tuple[str, int]] = []
    structure_failures: list[str] = []
    memory_cards_hits_all: list[str] = []
    empty_legacy_all: list[str] = []
    legacy_all: list[str] = []

    for paper_dir in papers:
        paper_id = paper_dir.name
        document_tree = _load_json(paper_dir / "document_tree.json", {})
        paragraph_index = _load_json(paper_dir / "paragraph_index.json", [])
        evidence_links = _load_json(paper_dir / "evidence_links.json", [])
        quality_report = _load_json(paper_dir / "quality_report.json", {})

        macro_section_count = int((document_tree or {}).get("section_count") or 0)
        paragraph_count = int((document_tree or {}).get("paragraph_count") or (len(paragraph_index) if isinstance(paragraph_index, list) else 0))
        subheading_group_count = _count_subheadings(paper_dir)
        figure_count = _count_figures(paper_dir)
        table_count = _count_tables(paper_dir)
        evidence_count = len(evidence_links) if isinstance(evidence_links, list) else 0

        uncertain_items = (quality_report or {}).get("uncertain_items") or []
        needs_manual_review = len(uncertain_items)
        score_metrics = _score_metrics(paper_dir)
        subheading_total = int(score_metrics["subheading_total"])
        manual_review_ratio = _safe_ratio(needs_manual_review, subheading_total)
        keyword_grade, keyword_advice = _keyword_quality_opinion(
            uncertain_ratio=float(score_metrics["is_uncertain_ratio"]),
            preview_only_ratio=float(score_metrics["preview_only_ratio"]),
            avg_gap=float(score_metrics["avg_score_gap"]),
        )
        if needs_manual_review > 0:
            manual_review_list.append((paper_id, needs_manual_review))

        errors, _warnings = validate_paper_dir(paper_dir, strict=False)
        if errors:
            structure_failures.append(f"- {paper_id}: " + " | ".join(errors[:3]))

        mc_hits, empty_hits, legacy_hits = _legacy_residuals(paper_dir)
        memory_cards_hits_all.extend(mc_hits)
        empty_legacy_all.extend(empty_hits)
        legacy_all.extend(legacy_hits)

        per_paper_rows.append(
            {
                "paper_id": paper_id,
                "macro_sections": macro_section_count,
                "subheading_groups": subheading_group_count,
                "paragraphs": paragraph_count,
                "figures": figure_count,
                "tables": table_count,
                "evidence": evidence_count,
                "needs_manual_review": needs_manual_review,
                "needs_manual_review_ratio": manual_review_ratio,
                "is_uncertain_count": int(score_metrics["is_uncertain_count"]),
                "is_uncertain_ratio": float(score_metrics["is_uncertain_ratio"]),
                "preview_only_count": int(score_metrics["preview_only_count"]),
                "preview_only_ratio": float(score_metrics["preview_only_ratio"]),
                "avg_score_gap": float(score_metrics["avg_score_gap"]),
                "min_score_gap": float(score_metrics["min_score_gap"]),
                "low_gap_count": int(score_metrics["low_gap_count"]),
                "low_gap_ratio": float(score_metrics["low_gap_ratio"]),
                "keyword_grade": keyword_grade,
                "keyword_advice": keyword_advice,
                "uncertain_examples": score_metrics["uncertain_examples"],
                "preview_only_examples": score_metrics["preview_only_examples"],
                "low_gap_examples": score_metrics["low_gap_examples"],
                "top_conflicts": score_metrics["top_conflicts"],
                "top_missing_keywords": score_metrics["top_missing_keywords"],
            }
        )

    runlog_failed = []
    for key, val in entries.items():
        if isinstance(val, dict) and val.get("status") == "failed":
            runlog_failed.append(f"- {key}: {val.get('error') or val.get('reason') or 'unknown'}")

    failure_lines = list(runlog_failed)
    failure_lines.extend(structure_failures)

    total_docs = len(papers)
    failed_count = len(failure_lines)
    success_count = max(0, total_docs - len(structure_failures))

    lines: list[str] = []
    lines.append("# 预处理回归总验证报告")
    lines.append("")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 总体统计")
    lines.append("")
    lines.append(f"- 总文献数: {total_docs}")
    lines.append(f"- 成功处理数: {success_count}")
    lines.append(f"- 失败处理数: {failed_count}")
    lines.append("")
    lines.append("## 每篇文献统计")
    lines.append("")
    lines.append(
        "| paper_id | macro section 数 | subheading group 数 | paragraph 数 | figure 数 | table 数 | evidence 数 | needs_manual_review 数/比例 | is_uncertain=true 数/比例 | preview-only 数/比例 | top1-second 平均分差 | 低分差(<2)数/比例 | 关键词合格意见 |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|---|")
    for row in per_paper_rows:
        manual_review_text = f"{row['needs_manual_review']} ({_pct(float(row['needs_manual_review_ratio']))})"
        uncertain_text = f"{row['is_uncertain_count']} ({_pct(float(row['is_uncertain_ratio']))})"
        preview_only_text = f"{row['preview_only_count']} ({_pct(float(row['preview_only_ratio']))})"
        low_gap_text = f"{row['low_gap_count']} ({_pct(float(row['low_gap_ratio']))})"
        avg_gap_text = f"{float(row['avg_score_gap']):.2f}"
        keyword_text = f"{row['keyword_grade']}：{row['keyword_advice']}"
        lines.append(
            f"| {row['paper_id']} | {row['macro_sections']} | {row['subheading_groups']} | {row['paragraphs']} | {row['figures']} | {row['tables']} | {row['evidence']} | {manual_review_text} | {uncertain_text} | {preview_only_text} | {avg_gap_text} | {low_gap_text} | {keyword_text} |"
        )
    lines.append("")
    lines.append("## 诊断明细（关键词与归并）")
    lines.append("")
    for row in per_paper_rows:
        lines.append(f"### {row['paper_id']}")
        lines.append("")
        lines.append(
            f"- 指标: manual_review={row['needs_manual_review']} ({_pct(float(row['needs_manual_review_ratio']))}), uncertain={row['is_uncertain_count']} ({_pct(float(row['is_uncertain_ratio']))}), preview-only={row['preview_only_count']} ({_pct(float(row['preview_only_ratio']))}), avg_gap={float(row['avg_score_gap']):.2f}"
        )
        if row["top_conflicts"]:
            conflict_text = ", ".join([f"{term}({count})" for term, count in row["top_conflicts"][:5]])
            lines.append(f"- 冲突词 Top5: {conflict_text}")
        else:
            lines.append("- 冲突词 Top5: 无明显重复命中词")

        if row["top_missing_keywords"]:
            missing_text = ", ".join([f"{term}({count})" for term, count in row["top_missing_keywords"][:5]])
            lines.append(f"- 疑似缺失关键词 Top5: {missing_text}")
        else:
            lines.append("- 疑似缺失关键词 Top5: 无")

        if row["uncertain_examples"]:
            lines.append("- is_uncertain 示例:")
            for ex in row["uncertain_examples"][:3]:
                lines.append(
                    "  - "
                    + f"{ex.get('heading_id')}: top={ex.get('top')}({float(ex.get('top_score') or 0):.1f}), "
                    + f"second={ex.get('second')}({float(ex.get('second_score') or 0):.1f}), "
                    + f"gap={float(ex.get('gap') or 0):.1f}, reasons={','.join(ex.get('reasons') or [])}, heading={str(ex.get('heading') or '')[:80]}"
                )

        if row["preview_only_examples"]:
            lines.append("- preview-only 示例:")
            for ex in row["preview_only_examples"][:3]:
                lines.append(
                    "  - "
                    + f"{ex.get('heading_id')}: top={ex.get('top')}({float(ex.get('top_score') or 0):.1f}), heading={str(ex.get('heading') or '')[:80]}"
                )

        if row["low_gap_examples"]:
            lines.append("- 低分差(<2) 示例:")
            for ex in row["low_gap_examples"][:3]:
                lines.append(
                    "  - "
                    + f"{ex.get('heading_id')}: top={ex.get('top')}, second={ex.get('second')}, gap={float(ex.get('gap') or 0):.1f}, heading={str(ex.get('heading') or '')[:80]}"
                )
        lines.append("")

    lines.append("")
    lines.append("## 失败原因")
    lines.append("")
    if failure_lines:
        lines.extend(failure_lines)
    else:
        lines.append("- 本轮无失败")
    lines.append("")
    lines.append("## 需要人工复核的文献列表")
    lines.append("")
    if manual_review_list:
        for paper_id, n in sorted(manual_review_list, key=lambda x: x[0]):
            lines.append(f"- {paper_id} ({n})")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 旧结构残留检查")
    lines.append("")
    lines.append(f"- 是否仍有 memory_cards: {'是' if memory_cards_hits_all else '否'}")
    if memory_cards_hits_all:
        for item in memory_cards_hits_all:
            lines.append(f"  - {item}")
    lines.append(f"- 是否存在空 abstract/overview: {'是' if empty_legacy_all else '否'}")
    if empty_legacy_all:
        for item in empty_legacy_all:
            lines.append(f"  - {item}")
    lines.append(f"- 是否存在旧结构残留 (.abstract/.overview/heading_index/headings): {'是' if legacy_all else '否'}")
    if legacy_all:
        for item in legacy_all:
            lines.append(f"  - {item}")

    report_text = "\n".join(lines) + "\n"
    report_path.write_text(report_text, encoding="utf-8")

    return {
        "total_docs": total_docs,
        "success_count": success_count,
        "failed_count": failed_count,
        "report_path": str(report_path),
    }


if __name__ == "__main__":
    summary = generate_preprocessing_regression_report()
    print(
        "report_updated="
        + summary["report_path"]
        + f" total_docs={summary['total_docs']} success={summary['success_count']} failed={summary['failed_count']}"
    )
