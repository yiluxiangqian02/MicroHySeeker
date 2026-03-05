"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
import uvicorn

from src.api.routes.agents import router as agents_router
from src.api.routes.data import router as data_router
from src.api.routes.diagnostics import router as diagnostics_router
from src.api.routes.tasks import router as tasks_router
from src.common.config import API_HOST, API_PORT
from src.common.logger import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

app = FastAPI(title="AutoHySeeker API", version="0.1.0")
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(data_router)
app.include_router(diagnostics_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "autohyseeker-api"}


def main() -> None:
    logger.info("starting API service on %s:%s", API_HOST, API_PORT)
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=False)


if __name__ == "__main__":
    main()

