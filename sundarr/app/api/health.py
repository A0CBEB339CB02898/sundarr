from fastapi import APIRouter, Depends
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from sundarr.app.config import get_settings
from sundarr.app.core.database import get_engine, get_db
from sundarr.app.cli import WORKER_SERVICE, _is_process_running, _read_pid
from sundarr.app.models import Setting

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


@router.get("/worker/status")
async def worker_status(db=Depends(get_db)) -> dict:
    setting = db.get(Setting, "worker.enabled")
    enabled = setting.value_json.get("enabled", True) if setting else True
    pid = _read_pid(WORKER_SERVICE)
    running = _is_process_running(pid) if pid else False
    return {"enabled": enabled, "running": running, "pid": pid}


@router.post("/worker/pause")
async def worker_pause(db=Depends(get_db)) -> dict:
    setting = db.get(Setting, "worker.enabled")
    if setting:
        setting.value_json["enabled"] = False
    else:
        db.add(Setting(key="worker.enabled", value_json={"enabled": False}, is_sensitive=False))
    db.commit()
    return {"ok": True, "enabled": False}


@router.post("/worker/resume")
async def worker_resume(db=Depends(get_db)) -> dict:
    setting = db.get(Setting, "worker.enabled")
    if setting:
        setting.value_json["enabled"] = True
    else:
        db.add(Setting(key="worker.enabled", value_json={"enabled": True}, is_sensitive=False))
    db.commit()
    return {"ok": True, "enabled": True}
