"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "autohyseeker-api"}


def main() -> None:
    logger.info("starting API service on %s:%s", API_HOST, API_PORT)
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=False)


if __name__ == "__main__":
    main()

