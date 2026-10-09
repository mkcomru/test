from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from config.logger_setup import setup_logging
from config.settings import get_settings
from src.common.database import engine
from src.transfer.routers import router as transfer_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.environment, settings.debug)
    async with engine.connect():
        log.info("database connected")
    yield
    await engine.dispose()
    log.info("shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(title="transfers", lifespan=lifespan)
    app.include_router(transfer_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
