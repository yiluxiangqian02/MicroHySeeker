"""Async API client for AutoHySeeker integration tests.

Wraps every REST endpoint in a typed async method with timeout control
and raises :class:`APIError` on non-2xx responses so tests can assert
cleanly without inspecting raw ``httpx.Response`` objects.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx


class APIError(RuntimeError):
    """Raised when the API returns a 4xx or 5xx status code."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class AutoHySeekerAPIClient:
    """Typed async wrapper for the AutoHySeeker REST API.

    Args:
        client: An ``httpx.AsyncClient`` already configured with the correct
            base URL (typically via ``ASGITransport`` in tests).
        timeout: Default per-request timeout in seconds.
    """

    def __init__(self, client: httpx.AsyncClient, timeout: float = 30.0) -> None:
        self.client = client
        self.timeout = timeout

    # ── internal helpers ───────────────────────────────────────────────────────

    def _raise_for_status(self, resp: httpx.Response) -> dict[str, Any]:
        """Decode response JSON and raise APIError on non-2xx."""
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise APIError(resp.status_code, str(detail))
        return resp.json()  # type: ignore[return-value]

    # ── health ─────────────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        """GET /health → ``{"status": "ok", "service": "..."}``."""
        resp = await self.client.get("/health", timeout=self.timeout)
        return self._raise_for_status(resp)

    # ── tasks ──────────────────────────────────────────────────────────────────

    async def create_task(
        self,
        task_type: str = "general",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /tasks/create → task record with ``task_id`` and ``status``."""
        resp = await self.client.post(
            "/tasks/create",
            json={"task_type": task_type, "payload": payload or {}},
            timeout=self.timeout,
        )
        return self._raise_for_status(resp)

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """GET /tasks/{task_id}/status → task record."""
        resp = await self.client.get(
            f"/tasks/{task_id}/status", timeout=self.timeout
        )
        return self._raise_for_status(resp)

    async def wait_for_task(
        self,
        task_id: str,
        *,
        target_status: str = "completed",
        timeout_s: float = 30.0,
        poll_interval_s: float = 0.5,
    ) -> dict[str, Any]:
        """Poll task status until it reaches *target_status* or times out.

        Raises:
            TimeoutError: if the task does not reach ``target_status``
                within ``timeout_s`` seconds.
            APIError: if the task status becomes ``"failed"`` or ``"error"``.
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_s
        while loop.time() < deadline:
            record = await self.get_task_status(task_id)
            if record["status"] == target_status:
                return record
            if record["status"] in ("failed", "error"):
                raise APIError(0, f"Task {task_id} entered error state: {record}")
            await asyncio.sleep(poll_interval_s)
        raise TimeoutError(
            f"Task {task_id!r} did not reach {target_status!r} within {timeout_s}s"
        )

    # ── agents ─────────────────────────────────────────────────────────────────

    async def invoke_agent(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
        messages: list[dict[str, Any]] | None = None,
        current_agent: str | None = None,
    ) -> dict[str, Any]:
        """POST /agents/invoke → ``{"ok": bool, "result": ..., "state": ...}``."""
        body: dict[str, Any] = {
            "task": task,
            "context": context or {},
        }
        if messages is not None:
            body["messages"] = messages
        if current_agent is not None:
            body["current_agent"] = current_agent
        resp = await self.client.post(
            "/agents/invoke", json=body, timeout=self.timeout
        )
        return self._raise_for_status(resp)

    # ── diagnostics ────────────────────────────────────────────────────────────

    async def invoke_diagnostics(
        self,
        action: str = "check_health",
        *,
        run_dir: str = "",
        data_dir: str = "",
        recent_n: int = 10,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /diagnostics/invoke → ``{"ok": bool, "action": ..., "result": ...}``."""
        body = {
            "action": action,
            "run_dir": run_dir,
            "data_dir": data_dir,
            "recent_n": recent_n,
            "context": context or {},
        }
        resp = await self.client.post(
            "/diagnostics/invoke", json=body, timeout=self.timeout
        )
        return self._raise_for_status(resp)

    # ── context (C1 / C2) ──────────────────────────────────────────────────────

    async def invoke_context(
        self,
        action: str = "contextualize",
        *,
        run_dir: str = "",
        history_dir: str = "",
        context_data: dict[str, Any] | None = None,
        goal: str = "",
        name: str = "",
        threshold_sigma: float = 2.0,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /context/invoke → ``{"ok": bool, "action": ..., "result": ...}``."""
        body: dict[str, Any] = {
            "action": action,
            "run_dir": run_dir,
            "history_dir": history_dir,
            "goal": goal,
            "name": name,
            "threshold_sigma": threshold_sigma,
        }
        if context_data is not None:
            body["context_data"] = context_data
        if extra_context:
            body["extra_context"] = extra_context
        resp = await self.client.post(
            "/context/invoke", json=body, timeout=self.timeout
        )
        return self._raise_for_status(resp)

    async def contextualize(
        self,
        run_dir: str,
        history_dir: str = "",
        threshold_sigma: float = 2.0,
    ) -> dict[str, Any]:
        """Shortcut: C1 contextualize via POST /context/contextualize."""
        resp = await self.client.post(
            "/context/contextualize",
            params={
                "run_dir": run_dir,
                "history_dir": history_dir,
                "threshold_sigma": threshold_sigma,
            },
            timeout=self.timeout,
        )
        return self._raise_for_status(resp)

    async def suggest_next(
        self, goal: str = "", name: str = ""
    ) -> dict[str, Any]:
        """Shortcut: C2 suggest-next via POST /context/suggest-next."""
        resp = await self.client.post(
            "/context/suggest-next",
            params={"goal": goal, "name": name},
            timeout=self.timeout,
        )
        return self._raise_for_status(resp)

    # ── data ───────────────────────────────────────────────────────────────────

    async def get_experiments(self, limit: int = 10) -> dict[str, Any]:
        """GET /data/experiments?limit={limit} → ``{"count": ..., "items": [...]}``."""
        resp = await self.client.get(
            "/data/experiments", params={"limit": limit}, timeout=self.timeout
        )
        return self._raise_for_status(resp)
