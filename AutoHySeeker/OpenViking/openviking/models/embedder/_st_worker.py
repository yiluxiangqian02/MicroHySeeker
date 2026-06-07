"""Sentence-Transformers worker process.

This script is meant to be launched as a subprocess by SentenceTransformerDenseEmbedder
to avoid DLL conflicts between engine.pyd (C++ vectordb) and PyTorch in the same process.

Protocol (line-by-line JSON over stdin/stdout):
  Request:  {"type": "embed", "texts": ["text1", "text2", ...]}
  Response: {"ok": true, "vectors": [[...], ...], "dim": 1024}

  Request:  {"type": "ping"}
  Response: {"ok": true, "dim": <int>}

  Request:  {"type": "quit"}
  (process exits)
"""
import json
import os
import sys


def main():
    # Ensure offline mode (use cached models only)
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

    model_name = sys.argv[1] if len(sys.argv) > 1 else "BAAI/bge-large-zh-v1.5"

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        try:
            dim = model.get_embedding_dimension()
        except AttributeError:
            dim = model.get_sentence_embedding_dimension()
        # Signal ready
        print(json.dumps({"ok": True, "ready": True, "dim": dim}), flush=True)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), flush=True)
        sys.exit(1)

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            req = json.loads(raw_line)
        except json.JSONDecodeError as e:
            print(json.dumps({"ok": False, "error": f"bad JSON: {e}"}), flush=True)
            continue

        if req.get("type") == "quit":
            break
        elif req.get("type") == "ping":
            print(json.dumps({"ok": True, "dim": dim}), flush=True)
        elif req.get("type") == "embed":
            texts = req.get("texts", [])
            try:
                vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                print(json.dumps({"ok": True, "vectors": vecs.tolist(), "dim": dim}), flush=True)
            except Exception as e:
                print(json.dumps({"ok": False, "error": str(e)}), flush=True)
        else:
            print(json.dumps({"ok": False, "error": f"unknown type: {req.get('type')}"}), flush=True)


if __name__ == "__main__":
    main()
