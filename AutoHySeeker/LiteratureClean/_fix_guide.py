"""Fix GUIDE: truncate garbled lines and append sections 16+17."""
import re
from pathlib import Path

guide = Path(__file__).parent / "LITERATURE_CLEANING_GUIDE.md"
text = guide.read_text(encoding="utf-8")
lines = text.split("\n")

# Find first line that looks garbled (high ratio of CJK unified ideographs from GBK mojibake range)
def is_garbled(line):
    if not line.strip():
        return False
    cjk = sum(1 for c in line if "\u4e00" <= c <= "\u9fff")
    non_ascii = sum(1 for c in line if ord(c) > 127)
    if non_ascii > 5 and cjk / max(non_ascii, 1) > 0.9 and len(line) > 10:
        # Likely mojibake: nearly all non-ascii are CJK
        return True
    return False

corrupt_start = None
for i, l in enumerate(lines):
    if is_garbled(l):
        corrupt_start = i
        break

if corrupt_start is None:
    print("No garbled lines found - GUIDE looks clean already.")
else:
    print(f"Garbled content starts at line {corrupt_start}: {repr(lines[corrupt_start][:60])}")
    # Truncate from corrupt_start
    clean_lines = lines[:corrupt_start]
    # Find last meaningful heading before corrupt
    for j in range(len(clean_lines)-1, -1, -1):
        if clean_lines[j].startswith("##"):
            print(f"Last section heading at line {j}: {clean_lines[j]}")
            break
    # Write back clean lines
    guide.write_text("\n".join(clean_lines).rstrip() + "\n", encoding="utf-8")
    print(f"Truncated to {len(clean_lines)} lines.")

# Now check what sections exist at end
text2 = guide.read_text(encoding="utf-8")
sections = [l for l in text2.split("\n") if l.startswith("## ")]
print("Current sections:", sections[-5:])
