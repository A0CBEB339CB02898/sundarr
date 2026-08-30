import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import Redis
from sqlalchemy import text


from sundarr.app.api.health import router as health_router
from sundarr.app.api.discover import router as discover_router
from sundarr.app.api.media_libraries import router as media_libraries_router
from sundarr.app.api.plugins import router as plugins_router
from sundarr.app.api.remote_media_libraries import router as remote_media_libraries_router
from sundarr.app.api.resources import router as resources_router
from sundarr.app.api.search import router as search_router
from sundarr.app.api.smb_connections import router as smb_connections_router
from sundarr.app.api.sources import router as sources_router
from sundarr.app.api.sync import router as sync_router
from sundarr.app.api.transfers import router as transfers_router
from sundarr.app.config import get_settings, redact_url_password
from sundarr.app.core.database import get_engine, get_session_factory
from sundarr.app.db_admin import ensure_runtime_schema_for_engine
from sundarr.app.plugins.manager import plugin_manager
from sundarr.app.services.catalog_cache import catalog_cache

logger = logging.getLogger("sundarr.startup")


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Sundarr API 启动中，版本：%s", settings.app_version)
        logger.info("数据库配置：%s", redact_url_password(settings.database_url))
        logger.info("Redis 配置：%s", redact_url_password(settings.redis_url))
        database_ready = False
        try:
            with get_engine().connect() as connection:
                connection.execute(text("select 1"))
            logger.info("数据库连接状态：ok")
            ensure_runtime_schema_for_engine(get_engine())
            database_ready = True
        except Exception as exc:
            logger.error("数据库连接状态：error，原因：%s", exc)
        try:
            Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
            logger.info("Redis 连接状态：ok")
        except Exception as exc:
            logger.error("Redis 连接状态：error，原因：%s", exc)
        if database_ready:
            try:
                with get_session_factory()() as session:
                    stats = await plugin_manager.load_all_repositories(session)
                logger.info(
                    "API 插件恢复完成：成功 %s，失败 %s",
                    stats["loaded"],
                    stats["error"],
                )
            except Exception as exc:
                logger.error("API 插件恢复失败，主服务继续启动：%s", exc)
        try:
            yield
        finally:
            await plugin_manager.dispose_all()
            await catalog_cache.close()

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(discover_router)
    app.include_router(search_router)
    app.include_router(resources_router)
    app.include_router(sources_router)
    app.include_router(smb_connections_router)
    app.include_router(media_libraries_router)
    app.include_router(remote_media_libraries_router)
    app.include_router(sync_router)
    app.include_router(transfers_router)
    app.include_router(plugins_router)
    return app


app = create_app()
