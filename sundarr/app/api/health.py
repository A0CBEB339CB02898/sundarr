from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from sundarr.app.cli import WORKER_SERVICE, _is_process_running, _read_pid
from sundarr.app.config import get_settings
from sundarr.app.core.database import get_db, get_engine
from sundarr.app.models import Setting

router = APIRouter(tags=["health"])


def _utc_now_iso() -> str:
    # ISO-8601 UTC with trailing Z (`datetime.isoformat()` yields `+00:00`,
    # which is correct but less ergonomic for JS `new Date(...)`).
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _check_database() -> str:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("select 1"))
    except SQLAlchemyError:
        return "error"
    return "ok"


def _check_redis() -> str:
    try:
        Redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        ).ping()
    except RedisError:
        return "error"
    return "ok"


@router.get("/health")
async def health() -> dict:
    # Each probe records its own `checked_at` timestamp so the web console
    # can show per-component freshness instead of a single wall-clock stamp.
    # Scalar fields (`status`, `database`, `redis`, `worker`) are retained
    # for backward compatibility with docs/07-接口契约.md §2 and any
    # external monitors.
    api_checked_at = _utc_now_iso()

    database_status = _check_database()
    database_checked_at = _utc_now_iso()

    redis_status = _check_redis()
    redis_checked_at = _utc_now_iso()

    worker_status_value = _worker_status()
    worker_checked_at = _utc_now_iso()

    return {
        "status": "ok",
        "database": database_status,
        "redis": redis_status,
        "worker": worker_status_value,
        "checked_at": worker_checked_at,
        "components": {
            "api": {"status": "ok", "checked_at": api_checked_at},
            "database": {"status": database_status, "checked_at": database_checked_at},
            "redis": {"status": redis_status, "checked_at": redis_checked_at},
            "worker": {"status": worker_status_value, "checked_at": worker_checked_at},
        },
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
