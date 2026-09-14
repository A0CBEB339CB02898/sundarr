"""Worker 数据库配置读取与本地测试运行时组装。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from sundarr.app.cloud import LocalCloudProvider
from sundarr.app.models import Setting
from sundarr.app.storage import LocalWriter

WORKER_ENABLED_KEY = "worker.enabled"
WORKER_CONCURRENCY_KEY = "worker.concurrency"
LOCAL_CLOUD_KEY = "cloud.local"
LOCAL_STORAGE_KEY = "storage.local"
WATCHLIST_SYNC_INTERVAL_KEY = "discovery.watchlist_sync_interval_seconds"
DEFAULT_WORKER_ENABLED = True
DEFAULT_WORKER_CONCURRENCY = 2
DEFAULT_WATCHLIST_SYNC_INTERVAL_SECONDS = 900


@dataclass(frozen=True)
class WorkerSettings:
    enabled: bool = DEFAULT_WORKER_ENABLED
    concurrency: int = DEFAULT_WORKER_CONCURRENCY


@dataclass(frozen=True)
class LocalRuntimeConfig:
    cloud_provider: LocalCloudProvider
    storage_writer: LocalWriter


def load_worker_settings(session: Session) -> WorkerSettings:
    enabled = _read_bool_setting(session, WORKER_ENABLED_KEY, DEFAULT_WORKER_ENABLED, "enabled")
    concurrency = _read_int_setting(session, WORKER_CONCURRENCY_KEY, DEFAULT_WORKER_CONCURRENCY, "value")
    return WorkerSettings(enabled=enabled, concurrency=max(1, concurrency))


def load_watchlist_sync_interval(session: Session) -> int:
    value = _read_int_setting(
        session,
        WATCHLIST_SYNC_INTERVAL_KEY,
        DEFAULT_WATCHLIST_SYNC_INTERVAL_SECONDS,
        "value",
    )
    return max(60, value)


def load_local_runtime_config(session: Session) -> LocalRuntimeConfig | None:
    cloud_setting = session.get(Setting, LOCAL_CLOUD_KEY)
    storage_setting = session.get(Setting, LOCAL_STORAGE_KEY)
    if cloud_setting is None or storage_setting is None:
        return None
    staging_root = cloud_setting.value_json.get("staging_root")
    share_root = cloud_setting.value_json.get("share_root")
    storage_root = storage_setting.value_json.get("root")
    if not all(isinstance(item, str) and item for item in (staging_root, share_root, storage_root)):
        return None
    return LocalRuntimeConfig(
        cloud_provider=LocalCloudProvider(staging_root=Path(staging_root), share_root=Path(share_root)),
        storage_writer=LocalWriter(Path(storage_root)),
    )


def _read_bool_setting(session: Session, key: str, default: bool, field: str) -> bool:
    setting = session.get(Setting, key)
    if setting is None:
        return default
    value = setting.value_json.get(field)
    return value if isinstance(value, bool) else default


def _read_int_setting(session: Session, key: str, default: int, field: str) -> int:
    setting = session.get(Setting, key)
    if setting is None:
        return default
    value = setting.value_json.get(field)
    return value if isinstance(value, int) else default
