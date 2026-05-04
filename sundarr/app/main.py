from fastapi import FastAPI

from sundarr.app.api.health import router as health_router
from sundarr.app.api.resources import router as resources_router
from sundarr.app.api.search import router as search_router
from sundarr.app.api.sources import router as sources_router
from sundarr.app.api.storage import router as storage_router
from sundarr.app.api.transfers import router as transfers_router
from sundarr.app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(resources_router)
    app.include_router(sources_router)
    app.include_router(storage_router)
    app.include_router(transfers_router)
    return app


app = create_app()
