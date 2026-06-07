"""Inspect LiteratureClean structure and vectordb stored metadata for one paper."""
import os, sys, json
sys.path.insert(0, "OpenViking")
os.environ["OPENVIKING_CONFIG_FILE"] = "OpenViking/.local_dev/ov.conf"
from pathlib import Path

# 1. LiteratureClean directory structure for one paper
CLEAN_ROOT = Path("LiteratureClean")
paper = "2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e"
paper_dir = CLEAN_ROOT / paper

print("=== LiteratureClean paper structure ===")
for root, dirs, files in os.walk(paper_dir):
    rel = Path(root).relative_to(paper_dir)
    depth = len(rel.parts)
    if depth > 4:
        continue
    indent = "  " * depth
    folder = rel.parts[-1] if rel.parts else paper
    print(f"{indent}{folder}/")
    for f in sorted(files):
        print(f"{indent}  {f}")

# 2. Check metadata.json content
meta_files = list(paper_dir.rglob("metadata.json"))
if meta_files:
    print("\n=== metadata.json sample ===")
    print(json.dumps(json.loads(meta_files[0].read_text()), indent=2, ensure_ascii=False)[:600])

# 3. Check .abstract.md content
abs_files = list(paper_dir.rglob(".abstract.md"))[:3]
for f in abs_files:
    print(f"\n=== {f.relative_to(CLEAN_ROOT)} ===")
    print(f.read_text(encoding="utf-8")[:400])

# 4. Check structured.json (if exists)
struct_files = list(paper_dir.rglob("structured.json"))[:1]
for f in struct_files:
    print(f"\n=== {f.relative_to(CLEAN_ROOT)} (first 400 chars) ===")
    print(f.read_text(encoding="utf-8")[:400])
