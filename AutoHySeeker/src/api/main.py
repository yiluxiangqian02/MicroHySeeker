"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn

from src.api.routes.agent_control import router as agent_control_router
from src.api.routes.agents import router as agents_router
from src.api.routes.approval import router as approval_router
from src.api.routes.chat import router as chat_router
from src.api.routes.context import router as context_router
from src.api.routes.control import router as control_router
from src.api.routes.data import router as data_router
from src.api.routes.diagnostics import router as diagnostics_router
from src.api.routes.monitor import router as monitor_router
from src.api.routes.experiments import router as experiments_router
from src.api.routes.knowledge import router as knowledge_router
from src.api.routes.optimization import router as optimization_router
from src.api.routes.projects import router as projects_router
from src.api.routes.system import router as system_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.templates import router as templates_router
from src.common.config import API_HOST, API_PORT
from src.common.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="AutoHySeeker API", version="0.1.0")

# Allow the Vite dev server (and any other origin) to call the API.
# In production this list should be tightened to the actual frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(experiments_router)
app.include_router(optimization_router)
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(approval_router)
app.include_router(data_router)
app.include_router(diagnostics_router)
app.include_router(monitor_router)
app.include_router(context_router)
app.include_router(templates_router)
app.include_router(control_router)
app.include_router(agent_control_router)
app.include_router(chat_router)
app.include_router(projects_router)
app.include_router(knowledge_router)


@app.on_event("startup")
async def _startup_filter() -> None:
    _install_access_log_filter()
    await _ensure_mhs_running()


# ── Auto-launch MHS headless server if not running ─────────────────────────

_MHS_BASE = "http://127.0.0.1:8100"
_MHS_PROCESS: subprocess.Popen | None = None


def _locate_mhs_server() -> Path | None:
    """Locate the MHS run_server.py relative to the AHS project root."""
    from src.common.config import PROJECT_ROOT
    candidate = PROJECT_ROOT.parent / "MicroHySeeker" / "run_server.py"
    if candidate.exists():
        return candidate
    return None


def _locate_mhs_python() -> str:
    """Locate the MHS .venv python executable."""
    from src.common.config import PROJECT_ROOT
    venv_python = PROJECT_ROOT.parent / "MicroHySeeker" / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    # fallback: same python as AHS
    return sys.executable


async def _ensure_mhs_running() -> None:
    """Check if MHS is reachable; if not, auto-launch headless server."""
    global _MHS_PROCESS

    # 1) Check if already running
    try:
        async with httpx.AsyncClient(
            timeout=2.0,
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
        ) as client:
            resp = await client.get(f"{_MHS_BASE}/api/system/health")
            if resp.status_code == 200:
                logger.info("MHS already running at %s", _MHS_BASE)
                return
    except Exception:
        pass

    # 2) Locate and launch
    server_script = _locate_mhs_server()
    if server_script is None:
        logger.warning("MHS run_server.py not found; cannot auto-launch")
        return

    mhs_python = _locate_mhs_python()
    mhs_dir = server_script.parent  # MicroHySeeker/
    logger.info("MHS not running — launching headless server: %s %s", mhs_python, server_script)

    # Build a clean env: isolate from conda to ensure .venv packages are used
    child_env = os.environ.copy()
    venv_dir = Path(mhs_python).resolve().parents[1]  # .venv
    venv_scripts = str(venv_dir / "Scripts") if os.name == "nt" else str(venv_dir / "bin")
    child_env["VIRTUAL_ENV"] = str(venv_dir)
    child_env.pop("CONDA_PREFIX", None)
    child_env.pop("CONDA_DEFAULT_ENV", None)
    child_env.pop("CONDA_PYTHON_EXE", None)
    # Prepend .venv Scripts to PATH so `python` inside subprocesses also resolves to .venv
    child_env["PATH"] = venv_scripts + os.pathsep + child_env.get("PATH", "")

    try:
        _MHS_PROCESS = subprocess.Popen(
            [mhs_python, str(server_script), "--port", "8100"],
            cwd=str(mhs_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=child_env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception:
        logger.exception("Failed to launch MHS server")
        return

    # 3) Wait for it to come up (up to 15 seconds)
    for attempt in range(30):
        await asyncio.sleep(0.5)
        try:
            async with httpx.AsyncClient(
                timeout=1.0,
                transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
            ) as client:
                resp = await client.get(f"{_MHS_BASE}/api/system/health")
                if resp.status_code == 200:
                    logger.info("MHS headless server launched successfully (attempt %d)", attempt + 1)
                    return
        except Exception:
            pass

    logger.warning("MHS headless server launched but health check still failing after 15s")


@app.on_event("shutdown")
async def _shutdown_mhs() -> None:
    """Terminate the MHS subprocess if we launched it."""
    global _MHS_PROCESS
    if _MHS_PROCESS is not None and _MHS_PROCESS.poll() is None:
        logger.info("Shutting down MHS headless server (pid=%d)", _MHS_PROCESS.pid)
        _MHS_PROCESS.terminate()
        try:
            _MHS_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _MHS_PROCESS.kill()
        _MHS_PROCESS = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "autohyseeker-api"}


# ── Suppress noisy polling endpoints from uvicorn access logs ──────────────

_QUIET_PATHS = frozenset({
    "/health",
    "/api/optimization/status",
    "/api/optimization/history",
    "/api/system/status",
    "/api/system/health",
    "/api/experiments/active-progress",
})


class _QuietAccessFilter(logging.Filter):
    """Drop uvicorn access-log lines for high-frequency polling endpoints."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(p in msg for p in _QUIET_PATHS)


def _install_access_log_filter() -> None:
    for name in ("uvicorn.access",):
        uv_logger = logging.getLogger(name)
        uv_logger.addFilter(_QuietAccessFilter())


def main() -> None:
    _install_access_log_filter()
    logger.info("starting API service on %s:%s", API_HOST, API_PORT)
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=False)


if __name__ == "__main__":
    main()

