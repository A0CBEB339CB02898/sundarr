from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from sundarr.app.core.database import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    database_status = "ok"
    try:
        with get_engine().connect() as connection:
            connection.execute(text("select 1"))
    except SQLAlchemyError:
        database_status = "error"

    return {
        "status": "ok",
        "database": database_status,
        "redis": "unknown",
        "worker": "unknown",
    }
