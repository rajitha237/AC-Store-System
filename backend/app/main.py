import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.init_db import initialize_database
from app.db.session import engine


settings = get_settings()

logger = logging.getLogger(
    "uvicorn.error"
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    logger.info(
        "Starting %s [%s]",
        settings.app_name,
        settings.environment,
    )

    await initialize_database()

    try:
        yield
    finally:
        await engine.dispose()

        logger.info(
            "Stopping %s",
            settings.app_name,
        )


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Internal sales, service, installment, inventory, "
        "returns and accounting management system."
    ),
    debug=settings.debug,
    docs_url=(
        None
        if settings.is_production
        else "/docs"
    ),
    redoc_url=(
        None
        if settings.is_production
        else "/redoc"
    ),
    openapi_url=(
        None
        if settings.is_production
        else "/openapi.json"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)


@app.get(
    "/",
    tags=["Root"],
)
async def root() -> dict[str, str]:
    return {
        "message":
            settings.app_name,
        "status":
            "running",
        "version":
            settings.app_version,
    }
