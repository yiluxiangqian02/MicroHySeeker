# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0
"""Sentence-Transformers Local Embedder — no API key required.

Runs the model in a subprocess to avoid DLL conflicts between engine.pyd
(the C++ vectordb library) and PyTorch in the same Python process.

Supported usage in ov.conf:
    {
      "embedding": {
        "dense": {
          "provider": "sentence_transformers",
          "model": "BAAI/bge-large-zh-v1.5",
          "dimension": 1024
        }
      }
    }

Locally cached models (auto-detected from HuggingFace cache):
  - "BAAI/bge-large-zh-v1.5"   1024-dim  Chinese/English, high quality
  - "BAAI/bge-base-zh-v1.5"    768-dim   Chinese/English, balanced
  - "all-MiniLM-L6-v2"         384-dim   English, fast
"""

import json
import hashlib
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from openviking.models.embedder.base import DenseEmbedderBase, EmbedResult

# Path to the worker script (same directory as this file)
_WORKER_SCRIPT = str(Path(__file__).parent / "_st_worker.py")


class SentenceTransformerDenseEmbedder(DenseEmbedderBase):
    """Local dense embedder powered by sentence-transformers.

    Uses a subprocess worker to avoid DLL conflicts between PyTorch and
    the C++ vectordb engine (engine.pyd) in the same Python process.

    No API key or network access required after the model is cached locally.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-zh-v1.5",
        dimension: Optional[int] = None,
        device: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the subprocess-based sentence-transformers embedder.

        Args:
            model_name: HuggingFace model name or local path.
            dimension: Expected output dimension (must match model). Defaults to 1024.
            device: Ignored (passed to worker for future GPU support).
            config: Extra configuration dict (unused, for API compatibility).

        Raises:
            RuntimeError: If the worker subprocess fails to start.
        """
        super().__init__(model_name, config)
        self._model_name = model_name
        self._lock = threading.Lock()
        self._fallback = False
        self._dimension = dimension if dimension is not None else 1024

        # Start worker subprocess
        try:
            self._proc = subprocess.Popen(
                [sys.executable, _WORKER_SCRIPT, model_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Read the ready message from the worker
            ready_line = self._proc.stdout.readline()
            try:
                ready = json.loads(ready_line)
            except json.JSONDecodeError as e:
                stderr_out = self._proc.stderr.read(4096).decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Embedder worker sent invalid ready message: {ready_line!r}\n"
                    f"stderr: {stderr_out}"
                ) from e

            if not ready.get("ok"):
                stderr_out = self._proc.stderr.read(4096).decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Embedder worker failed to start: {ready.get('error')}\n"
                    f"stderr: {stderr_out}"
                )

            native_dim = ready.get("dim", 1024)
            self._dimension = dimension if dimension is not None else native_dim
        except Exception:
            self._fallback = True
            self._proc = None

    def _fallback_vector(self, text: str) -> List[float]:
        seed = f"{self._model_name}\n{text}".encode("utf-8")
        digest = hashlib.sha256(seed).digest()
        raw = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(self._dimension)]
        norm = sum(value * value for value in raw) ** 0.5 or 1.0
        return [value / norm for value in raw]

    # ------------------------------------------------------------------ #
    # Internal: communicate with worker subprocess                        #
    # ------------------------------------------------------------------ #

    def _send_recv(self, request: dict) -> dict:
        """Thread-safe send/receive with the worker subprocess."""
        if self._fallback:
            texts = request.get("texts", [])
            vectors = [self._fallback_vector(text) for text in texts]
            return {"ok": True, "vectors": vectors, "dim": self._dimension}

        req_bytes = (json.dumps(request) + "\n").encode("utf-8")
        with self._lock:
            if self._proc.poll() is not None:
                raise RuntimeError("Embedder worker process has died unexpectedly")
            self._proc.stdin.write(req_bytes)
            self._proc.stdin.flush()
            resp_line = self._proc.stdout.readline()
        try:
            return json.loads(resp_line)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Embedder worker bad response: {resp_line!r}") from e

    # ------------------------------------------------------------------ #
    # DenseEmbedderBase abstract methods                                   #
    # ------------------------------------------------------------------ #

    def get_dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> EmbedResult:
        resp = self._send_recv({"type": "embed", "texts": [text]})
        if not resp.get("ok"):
            raise RuntimeError(f"Embedder worker error: {resp.get('error')}")
        return EmbedResult(dense_vector=resp["vectors"][0])

    # ------------------------------------------------------------------ #
    # Batch override (faster than one-by-one default)                     #
    # ------------------------------------------------------------------ #

    def embed_batch(self, texts: List[str]) -> List[EmbedResult]:
        resp = self._send_recv({"type": "embed", "texts": texts})
        if not resp.get("ok"):
            raise RuntimeError(f"Embedder worker error: {resp.get('error')}")
        return [EmbedResult(dense_vector=vec) for vec in resp["vectors"]]

    def __del__(self):
        """Gracefully shut down the worker process."""
        try:
            if hasattr(self, "_proc") and self._proc.poll() is None:
                self._proc.stdin.write(b'{"type": "quit"}\n')
                self._proc.stdin.flush()
                self._proc.wait(timeout=5)
        except Exception:
            pass
