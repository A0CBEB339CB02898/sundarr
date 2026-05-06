from fastapi import APIRouter
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from sundarr.app.config import get_settings
from sundarr.app.core.database import get_engine
from sundarr.app.cli import WORKER_SERVICE, _is_process_running, _read_pid

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    database_status = "ok"
    try:
        with get_engine().connect() as connection:
            connection.execute(text("select 1"))
    except SQLAlchemyError:
        database_status = "error"

    redis_status = "ok"
    try:
        Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
    except RedisError:
        redis_status = "error"

    return {
        "status": "ok",
        "database": database_status,
        "redis": redis_status,
        "worker": _worker_status(),
    }


def _worker_status() -> str:
    pid = _read_pid(WORKER_SERVICE)
    if pid is None:
        return "unknown"
    return "ok" if _is_process_running(pid) else "error"
