from pathlib import Path
from PyPDF2 import PdfReader

candidates = [
    Path(r"D:/AI4S/MicroHySeeker/MicroHySeeker/MicroHySeeker/docs/MKS SERVO42&57D_RS485 闭环步进电机 使用说明 V1.0.6.pdf"),
    Path(r"D:/AI4S/MicroHySeeker/MicroHySeeker/docs/MKS SERVO42&57D_RS485 闭环步进电机 使用说明 V1.0.6.pdf"),
]
pdf = next((p for p in candidates if p.exists()), None)
print(f"PDF={pdf}")
if not pdf:
    raise SystemExit(1)

reader = PdfReader(str(pdf))
texts = [(pg.extract_text() or "") for pg in reader.pages]
full = "\n".join(texts)
print(f"PAGES={len(reader.pages)} CHARS={len(full)}")

keywords = ["短路帽", "短路", "跳帽", "端子", "终端", "120", "EN", "使能", "地址", "拨码", "RS485", "自动", "DIR"]
for key in keywords:
    idx = full.find(key)
    if idx >= 0:
        s = max(0, idx - 120)
        e = min(len(full), idx + 260)
        snippet = full[s:e].replace("\n", " ")
        print(f"\n=== {key} ===")
        print(snippet)

print("\n=== PER-PAGE KEY HITS ===")
for i, t in enumerate(texts, start=1):
    hits = [k for k in keywords if k in t]
    if hits:
        print(f"page {i}: {hits}")
