"""check_rebuild_stability.py

Validate Plan-B stability for B4/B5:
- B4: heading order stability (doc_heading_order + heading_uid sequence)
- B5: paragraph_uid stability across rebuild

Workflow:
1) snapshot current outputs
2) optional rebuild via batch_clean_mineru.py --overwrite
3) snapshot again and compare
4) write JSON/Markdown report

Usage:
    python check_rebuild_stability.py --run-rebuild
    python check_rebuild_stability.py --paper 2025_sha_xxx --run-rebuild
    python check_rebuild_stability.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_CLEAN_ROOT = HERE
DEFAULT_JSON_REPORT = HERE / "rebuild_stability_report.json"
DEFAULT_MD_REPORT = HERE / "rebuild_stability_report.md"


@dataclass
class Snapshot:
    heading_order_rows: list[tuple[str, int]]
    paragraph_uid_rows: list[tuple[str, str, int, int]]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def candidate_papers(clean_root: Path) -> list[Path]:
    return sorted(
        [d for d in clean_root.iterdir() if d.is_dir() and (d / "metadata.json").exists()],
        key=lambda item: item.name,
    )


def make_snapshot(paper_dir: Path) -> Snapshot:
    original_structure = load_json(paper_dir / "original_structure_index.json")
    paragraph_index = load_json(paper_dir / "paragraph_index.json")

    heading_rows: list[tuple[str, int]] = []
    for h in (original_structure.get("headings") or []):
        heading_rows.append((str(h.get("heading_uid") or ""), int(h.get("doc_heading_order") or 0)))

    paragraph_rows: list[tuple[str, str, int, int]] = []
    for item in paragraph_index if isinstance(paragraph_index, list) else []:
        paragraph_rows.append(
            (
                str(item.get("paragraph_uid") or ""),
                str(item.get("heading_uid") or ""),
                int(item.get("doc_heading_order") or 0),
                int(item.get("block_order") or 0),
            )
        )

    paragraph_rows.sort(key=lambda x: (x[2], x[3], x[0]))
    return Snapshot(heading_order_rows=heading_rows, paragraph_uid_rows=paragraph_rows)


def compare_snapshot(before: Snapshot, after: Snapshot) -> dict[str, Any]:
    heading_stable = before.heading_order_rows == after.heading_order_rows
    paragraph_uid_stable = before.paragraph_uid_rows == after.paragraph_uid_rows

    result: dict[str, Any] = {
        "heading_order_stable": heading_stable,
        "paragraph_uid_stable": paragraph_uid_stable,
        "heading_count_before": len(before.heading_order_rows),
        "heading_count_after": len(after.heading_order_rows),
        "paragraph_count_before": len(before.paragraph_uid_rows),
        "paragraph_count_after": len(after.paragraph_uid_rows),
    }

    if not heading_stable:
        result["heading_first_diff"] = _first_diff(before.heading_order_rows, after.heading_order_rows)
    if not paragraph_uid_stable:
        result["paragraph_first_diff"] = _first_diff(before.paragraph_uid_rows, after.paragraph_uid_rows)

    return result


def _first_diff(before: list[Any], after: list[Any]) -> dict[str, Any]:
    max_len = max(len(before), len(after))
    for i in range(max_len):
        b = before[i] if i < len(before) else None
        a = after[i] if i < len(after) else None
        if b != a:
            return {"index": i, "before": b, "after": a}
    return {"index": -1, "before": None, "after": None}


def run_rebuild(paper_filter: str | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(HERE / "batch_clean_mineru.py"), "--overwrite"]
    if paper_filter:
        cmd.extend(["--paper", paper_filter])
    completed = subprocess.run(
        cmd,
        cwd=str(HERE),
        text=True,
        capture_output=True,
    )
    combined = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return completed.returncode, combined


def make_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Rebuild Stability Report")
    lines.append("")
    lines.append(f"Generated at: {summary['generated_at']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- paper_count: {summary['paper_count']}")
    lines.append(f"- pass_count: {summary['pass_count']}")
    lines.append(f"- fail_count: {summary['fail_count']}")
    lines.append(f"- pass_rate: {summary['pass_rate']}")
    lines.append("")
    lines.append("## Per Paper")
    lines.append("")
    lines.append("| paper_id | status | heading_order_stable | paragraph_uid_stable |")
    lines.append("|---|---|---|---|")
    for item in summary["papers"]:
        lines.append(
            f"| {item['paper_id']} | {item['status']} | "
            f"{item['heading_order_stable']} | {item['paragraph_uid_stable']} |"
        )

    failed = [x for x in summary["papers"] if x["status"] == "fail"]
    if failed:
        lines.append("")
        lines.append("## Failure Details")
        lines.append("")
        for item in failed:
            lines.append(f"- {item['paper_id']}")
            if "heading_first_diff" in item:
                lines.append(f"  - heading_first_diff: {item['heading_first_diff']}")
            if "paragraph_first_diff" in item:
                lines.append(f"  - paragraph_first_diff: {item['paragraph_first_diff']}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check heading order and paragraph_uid stability across rebuild.")
    parser.add_argument("--clean-root", type=Path, default=DEFAULT_CLEAN_ROOT)
    parser.add_argument("--paper", type=str, default="")
    parser.add_argument("--run-rebuild", action="store_true", help="Run batch_clean_mineru.py --overwrite before comparing snapshots.")
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean_root = args.clean_root.resolve()

    papers = candidate_papers(clean_root)
    if args.paper:
        papers = [p for p in papers if p.name == args.paper]

    if not papers:
        print(f"[stability] no paper directories found in {clean_root}")
        raise SystemExit(1)

    before = {p.name: make_snapshot(p) for p in papers}

    rebuild_status = {"ran": False, "exit_code": 0, "output_tail": ""}
    if args.run_rebuild:
        code, output = run_rebuild(args.paper or None)
        rebuild_status = {
            "ran": True,
            "exit_code": code,
            "output_tail": "\n".join(output.splitlines()[-80:]),
        }
        if code != 0:
            summary = {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "clean_root": str(clean_root),
                "paper_count": len(papers),
                "pass_count": 0,
                "fail_count": len(papers),
                "pass_rate": "0.00%",
                "rebuild_status": rebuild_status,
                "papers": [
                    {
                        "paper_id": p.name,
                        "status": "fail",
                        "heading_order_stable": False,
                        "paragraph_uid_stable": False,
                        "error": "rebuild command failed",
                    }
                    for p in papers
                ],
            }
            write_json(args.json_report, summary)
            args.md_report.write_text(make_markdown(summary), encoding="utf-8")
            print(f"[stability] rebuild failed, see {args.json_report}")
            raise SystemExit(1)

    after = {p.name: make_snapshot(p) for p in papers}

    items: list[dict[str, Any]] = []
    for p in papers:
        result = compare_snapshot(before[p.name], after[p.name])
        status = "pass" if result["heading_order_stable"] and result["paragraph_uid_stable"] else "fail"
        items.append({"paper_id": p.name, "status": status, **result})

    pass_count = sum(1 for x in items if x["status"] == "pass")
    fail_count = len(items) - pass_count
    pass_rate = f"{(pass_count / len(items) * 100):.2f}%"

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "clean_root": str(clean_root),
        "paper_count": len(items),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": pass_rate,
        "rebuild_status": rebuild_status,
        "papers": items,
    }

    write_json(args.json_report, summary)
    args.md_report.write_text(make_markdown(summary), encoding="utf-8")

    print(f"[stability] papers={len(items)} pass={pass_count} fail={fail_count} pass_rate={pass_rate}")
    print(f"[stability] json={args.json_report}")
    print(f"[stability] md={args.md_report}")

    raise SystemExit(1 if fail_count else 0)


if __name__ == "__main__":
    main()
