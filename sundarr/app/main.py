import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from sundarr.app.api.health import router as health_router
from sundarr.app.api.resources import router as resources_router
from sundarr.app.api.search import router as search_router
from sundarr.app.api.sources import router as sources_router
from sundarr.app.api.storage import router as storage_router
from sundarr.app.api.transfers import router as transfers_router
from sundarr.app.config import get_settings, redact_url_password
from sundarr.app.core.database import get_engine

logger = logging.getLogger("sundarr.startup")


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Sundarr API 启动中，版本：%s", settings.app_version)
        logger.info("数据库配置：%s", redact_url_password(settings.database_url))
        logger.info("Redis 配置：%s", redact_url_password(settings.redis_url))
        try:
            with get_engine().connect() as connection:
                connection.execute(text("select 1"))
            logger.info("数据库连接状态：ok")
        except Exception as exc:
            logger.error("数据库连接状态：error，原因：%s", exc)
        yield

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(resources_router)
    app.include_router(sources_router)
    app.include_router(storage_router)
    app.include_router(transfers_router)
    return app


app = create_app()
