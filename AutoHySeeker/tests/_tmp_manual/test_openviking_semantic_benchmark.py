"""OpenViking 语义搜索精度验证脚本 v2

由于 OpenViking 原生 engine.pyd (C++ DLL) 在当前环境无法加载，
本脚本采用两层验证策略：

1. 直接验证 embedding API (baai/bge-m3) 的语义相似度计算能力
2. 验证 OpenVikingClient fallback 模式的关键词搜索能力

用法:
    cd AutoHySeeker
    python -m tests._tmp_manual.test_openviking_semantic_benchmark
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

# ── 确保 AutoHySeeker 根目录在 sys.path ──
AUTOHYSEEKER_ROOT = Path(__file__).resolve().parents[2]
if str(AUTOHYSEEKER_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOHYSEEKER_ROOT))


# ── 配置 ──

LITERATURE_DIR = Path(
    r"D:\minerU\Analysis\10,000-h-stable intermittent alkaline seawater electrolysis"
    r".pdf-115d9b9d-c45f-4f91-95c2-c8aee82be06c"
)

EMBEDDING_API = {
    "api_base": "https://router.shengsuanyun.com/api/v1",
    "api_key": "nz0GMlymJVmKJUrS4uCwfNjFnjYzvK7-Le5iV0Ka7Vfmw9shyIG-iTyFnpBy2CnzG9k9amXJom7mcmQp_KYYY2lw",
    "model": "baai/bge-m3",
}

PAPER_META = {
    "title": "10,000-h-stable intermittent alkaline seawater electrolysis",
    "doi": "10.1038/s41586-025-08610-1",
    "catalyst": "NiCoP-Cr2O3",
}


# ── Step 1: 文献分段 ──

def chunk_markdown(md_path: Path) -> list[dict[str, Any]]:
    """按 # 标题拆分 markdown，返回 chunk 列表。"""
    text = md_path.read_text(encoding="utf-8")

    sections: list[dict[str, str]] = []
    current_title = "Abstract"
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("# "):
            if current_lines:
                sections.append({"title": current_title, "text": "\n".join(current_lines)})
            current_title = line.lstrip("# ").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({"title": current_title, "text": "\n".join(current_lines)})

    chunks: list[dict[str, Any]] = []
    for i, sec in enumerate(sections):
        clean = re.sub(r"!\[.*?\]\(.*?\)", "", sec["text"])
        clean = re.sub(r"\n{2,}", "\n", clean).strip()

        if len(clean) < 100:
            continue

        chunks.append({
            "chunk_id": f"chunk_{i:03d}",
            "section_title": sec["title"],
            "text": clean[:2000],  # 限制长度避免 token 超限
            "char_count": len(clean),
        })

    return chunks


# ── Step 2: Embedding API 调用 ──

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """调用 baai/bge-m3 embedding API 获取向量（通过 openai SDK）。"""
    client = OpenAI(
        api_key=EMBEDDING_API["api_key"],
        base_url=EMBEDDING_API["api_base"],
    )

    all_embeddings: list[list[float]] = []
    # 分批请求，每批 5 条
    batch_size = 5
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for attempt in range(3):
            try:
                resp = client.embeddings.create(
                    model=EMBEDDING_API["model"],
                    input=batch,
                )
                for item in resp.data:
                    all_embeddings.append(item.embedding)
                break
            except Exception as exc:
                if attempt < 2:
                    print(f"    重试 ({attempt + 1}/3): {exc}")
                    time.sleep(2)
                else:
                    raise

    return all_embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度。"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Step 3: Benchmark 查询 ──

BENCHMARK_QUERIES: list[dict[str, Any]] = [
    {
        "query": "NiCoP催化剂的过电位是多少",
        "expected_sections": ["Abstract", "Activity and stability"],
        "description": "查找催化剂过电位数据",
    },
    {
        "query": "seawater electrolysis cathode degradation mechanism",
        "expected_sections": ["Abstract", "Cathode oxidation"],
        "description": "查找阴极降解机制",
    },
    {
        "query": "phosphate passivation layer protection",
        "expected_sections": ["Catalysts design strategy", "Reaction mechanism", "Article"],
        "description": "查找磷酸盐钝化层保护作用",
    },
    {
        "query": "intermittent electrolysis stability test 10000 hours",
        "expected_sections": ["Abstract", "Activity and stability"],
        "description": "查找间歇稳定性测试结果",
    },
    {
        "query": "TOF-SIMS characterization element distribution",
        "expected_sections": ["Reaction mechanism", "Article"],
        "description": "查找 TOF-SIMS 表征结果",
    },
    {
        "query": "DFT calculation oxygen migration energy barrier",
        "expected_sections": ["Theoretical insight", "Computational methods"],
        "description": "查找理论计算结果",
    },
    {
        "query": "NiCo-LDH hydrothermal synthesis method",
        "expected_sections": ["Synthesis of NiCo", "Synthesis of NiCoP"],
        "description": "查找合成方法",
    },
    {
        "query": "AEM electrolyser performance voltage current density",
        "expected_sections": ["Activity and stability", "AEM electrolyser measurement"],
        "description": "查找 AEM 电解槽性能",
    },
    {
        "query": "chloride ion corrosion resistance",
        "expected_sections": ["Abstract", "Reaction mechanism", "Discussion"],
        "description": "查找氯离子腐蚀抵抗",
    },
    {
        "query": "operando Raman spectroscopy P-O vibration",
        "expected_sections": ["Reaction mechanism", "Operando Raman"],
        "description": "查找原位拉曼表征",
    },
    {
        "query": "HAADF-STEM atomic structure passivation layer",
        "expected_sections": ["Structural evolution", "HAADF-STEM characterization"],
        "description": "查找 STEM 原子结构",
    },
    {
        "query": "renewable energy hydrogen production seawater",
        "expected_sections": ["Abstract", "Discussion"],
        "description": "查找可再生能源制氢概述",
    },
]


def section_matches(hit_section: str, expected_sections: list[str]) -> bool:
    """检查一个命中的 section 是否匹配期望 section 列表中的任一项。"""
    hit_lower = hit_section.lower()
    for exp in expected_sections:
        if exp.lower() in hit_lower or hit_lower in exp.lower():
            return True
    return False


# ── Part A: 直接 Embedding 语义搜索验证 ──

def run_embedding_benchmark(chunks: list[dict[str, Any]], top_k: int = 3) -> dict[str, Any]:
    """直接用 embedding API 计算语义相似度，评估搜索精度。"""
    print("\n" + "=" * 60)
    print("Part A: 直接 Embedding API 语义搜索验证")
    print("=" * 60)

    # 构造 chunk 的 embedding 输入文本（限制在 500 字以内避免 API 超时）
    chunk_texts = []
    for c in chunks:
        text = f"{c['section_title']}: {c['text'][:400]}"
        chunk_texts.append(text)

    # 获取所有 chunk 的 embeddings
    print(f"\n获取 {len(chunk_texts)} 个 chunk 的 embeddings（逐条请求）...")
    all_chunk_embeddings = get_embeddings(chunk_texts)

    print(f"  完成! embedding 维度: {len(all_chunk_embeddings[0])}")

    # 获取所有 query 的 embeddings
    query_texts = [bq["query"] for bq in BENCHMARK_QUERIES]
    print(f"\n获取 {len(query_texts)} 个查询的 embeddings...")
    query_embeddings = get_embeddings(query_texts)

    # 计算每个 query 与所有 chunk 的相似度，取 top_k
    results: list[dict[str, Any]] = []

    for i, bq in enumerate(BENCHMARK_QUERIES):
        q_emb = query_embeddings[i]

        similarities = []
        for j, c_emb in enumerate(all_chunk_embeddings):
            sim = cosine_similarity(q_emb, c_emb)
            similarities.append((sim, j))

        similarities.sort(reverse=True)
        top_hits = similarities[:top_k]

        hit_sections = [chunks[idx]["section_title"] for _, idx in top_hits]
        hit_scores = [round(score, 4) for score, _ in top_hits]

        hits_in_expected = sum(
            1 for s in hit_sections
            if section_matches(s, bq["expected_sections"])
        )
        precision = hits_in_expected / top_k

        result = {
            "query_id": i + 1,
            "query": bq["query"],
            "description": bq["description"],
            "expected_sections": bq["expected_sections"],
            "hit_sections": hit_sections,
            "hit_scores": hit_scores,
            "precision_at_k": precision,
            "any_hit": hits_in_expected > 0,
        }
        results.append(result)

        status = "HIT" if result["any_hit"] else "MISS"
        print(f"\n  [{status}] Q{i + 1}: {bq['description']}")
        print(f"    query:    {bq['query']}")
        print(f"    expected: {bq['expected_sections']}")
        print(f"    got:      {list(zip(hit_sections, hit_scores))}")
        print(f"    P@{top_k}: {precision:.2f}")

    total = len(results)
    avg_precision = sum(r["precision_at_k"] for r in results) / total
    hit_rate = sum(1 for r in results if r["any_hit"]) / total

    return {
        "mode": "embedding_api_direct",
        "total_queries": total,
        "top_k": top_k,
        "avg_precision_at_k": round(avg_precision, 3),
        "hit_rate": round(hit_rate, 3),
        "hit_count": sum(1 for r in results if r["any_hit"]),
        "miss_count": sum(1 for r in results if not r["any_hit"]),
        "per_query": results,
    }


# ── Part B: Fallback 关键词搜索验证 ──

def run_fallback_benchmark(chunks: list[dict[str, Any]], top_k: int = 3) -> dict[str, Any]:
    """用 OpenVikingClient fallback store 验证关键词搜索。"""
    print("\n" + "=" * 60)
    print("Part B: OpenVikingClient Fallback 关键词搜索验证")
    print("=" * 60)

    from src.knowledge.viking_client import OpenVikingClient

    client = OpenVikingClient()
    print(f"  OpenViking SDK available: {client.is_available}")
    print(f"  (预期 False — 使用 fallback store 做关键词匹配)")

    # 写入所有 chunk
    for chunk in chunks:
        embedding_text = (
            f"Paper: {PAPER_META['title']}\n"
            f"Section: {chunk['section_title']}\n"
            f"Catalyst: {PAPER_META['catalyst']}\n\n"
            f"{chunk['text'][:2000]}"
        )
        payload = {
            "chunk_id": chunk["chunk_id"],
            "section_title": chunk["section_title"],
            "content": embedding_text,
        }
        client.write_json(
            partition="literature",
            payload=payload,
            resource_name=f"lit_{chunk['chunk_id']}.json",
        )

    print(f"  已写入 {len(chunks)} 个 chunk 到 fallback store")

    # 搜索
    results: list[dict[str, Any]] = []
    for i, bq in enumerate(BENCHMARK_QUERIES):
        hits = client.search(bq["query"], partition="literature", top_k=top_k)

        hit_sections: list[str] = []
        for hit in hits:
            section = _extract_section_from_hit(hit)
            hit_sections.append(section)

        hits_in_expected = sum(
            1 for s in hit_sections
            if section_matches(s, bq["expected_sections"])
        )
        precision = hits_in_expected / top_k if top_k > 0 else 0.0

        result = {
            "query_id": i + 1,
            "query": bq["query"],
            "description": bq["description"],
            "expected_sections": bq["expected_sections"],
            "hit_sections": hit_sections,
            "precision_at_k": precision,
            "any_hit": hits_in_expected > 0,
        }
        results.append(result)

        status = "HIT" if result["any_hit"] else "MISS"
        print(f"  [{status}] Q{i + 1}: {bq['description']} → got {hit_sections}")

    total = len(results)
    avg_precision = sum(r["precision_at_k"] for r in results) / total if total else 0
    hit_rate = sum(1 for r in results if r["any_hit"]) / total if total else 0

    client.close()

    return {
        "mode": "fallback_keyword",
        "total_queries": total,
        "top_k": top_k,
        "avg_precision_at_k": round(avg_precision, 3),
        "hit_rate": round(hit_rate, 3),
        "hit_count": sum(1 for r in results if r["any_hit"]),
        "miss_count": sum(1 for r in results if not r["any_hit"]),
        "per_query": results,
    }


def _extract_section_from_hit(hit: dict[str, Any]) -> str:
    """从搜索结果中提取 section_title。"""
    content = hit.get("content", "")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed.get("section_title", "unknown")
        except (json.JSONDecodeError, TypeError):
            pass
        match = re.search(r"Section:\s*(.+?)(?:\n|$)", content)
        if match:
            return match.group(1).strip()
    meta = hit.get("metadata", {})
    if isinstance(meta, dict):
        return meta.get("section_title", "unknown")
    return "unknown"


# ── Main ──

def main() -> None:
    print("=" * 70)
    print("OpenViking 语义搜索精度验证 v2")
    print("=" * 70)

    md_path = LITERATURE_DIR / "full.md"
    if not md_path.exists():
        print(f"ERROR: 找不到文献文件: {md_path}")
        sys.exit(1)

    # Step 1: 分段
    print(f"\n[Step 1] 文献分段: {md_path.name}")
    chunks = chunk_markdown(md_path)
    print(f"  共生成 {len(chunks)} 个 chunk:")
    for c in chunks:
        print(f"    {c['chunk_id']}: {c['section_title'][:50]} ({c['char_count']} chars)")

    # Part A: 直接 Embedding API 语义搜索
    try:
        embedding_summary = run_embedding_benchmark(chunks, top_k=3)
    except Exception as exc:
        print(f"\n  Part A 失败: {exc}")
        embedding_summary = None

    # Part B: Fallback 关键词搜索
    fallback_summary = run_fallback_benchmark(chunks, top_k=3)

    # 输出结果
    print("\n" + "=" * 70)
    print("验证结果汇总")
    print("=" * 70)

    if embedding_summary:
        print(f"\n  [Part A] Embedding API 语义搜索 (baai/bge-m3)")
        print(f"    命中率 (Hit Rate):  {embedding_summary['hit_rate']:.1%}  ({embedding_summary['hit_count']}/{embedding_summary['total_queries']})")
        print(f"    平均 P@3:          {embedding_summary['avg_precision_at_k']:.3f}")

    print(f"\n  [Part B] Fallback 关键词搜索")
    print(f"    命中率 (Hit Rate):  {fallback_summary['hit_rate']:.1%}  ({fallback_summary['hit_count']}/{fallback_summary['total_queries']})")
    print(f"    平均 P@3:          {fallback_summary['avg_precision_at_k']:.3f}")

    # 保存结果
    output_path = AUTOHYSEEKER_ROOT / "tests" / "_tmp_manual" / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "paper": PAPER_META,
        "chunk_count": len(chunks),
        "embedding_benchmark": embedding_summary,
        "fallback_benchmark": fallback_summary,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\n  详细结果已保存到: {output_path}")

    # 评级 (基于 embedding 结果)
    print("\n" + "-" * 40)
    if embedding_summary:
        hr = embedding_summary["hit_rate"]
        ap = embedding_summary["avg_precision_at_k"]
        if hr >= 0.9 and ap >= 0.5:
            grade = "A"
            msg = "语义搜索精度优秀，可直接用于 Phase 1 知识库"
        elif hr >= 0.7 and ap >= 0.3:
            grade = "B"
            msg = "语义搜索基本可用，建议优化 embedding 输入格式"
        elif hr >= 0.5:
            grade = "C"
            msg = "语义搜索需要改进，建议增加自然语言描述或换用更好的 embedding 模型"
        else:
            grade = "D"
            msg = "语义搜索精度不足，需要重大改进"
        print(f"  Embedding 搜索评级: {grade} — {msg}")
    else:
        print("  Embedding 搜索: 跳过（API 不可用）")

    hr2 = fallback_summary["hit_rate"]
    print(f"  Fallback 搜索评级:   {'可用' if hr2 >= 0.5 else '需改进'} (Hit Rate: {hr2:.1%})")
    print("-" * 40)


if __name__ == "__main__":
    main()
