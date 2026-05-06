import signal
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.core.database import get_session_factory
from sundarr.app.models import Setting, TransferLog, TransferTask


WORKER_ENABLED_KEY = "worker.enabled"
WORKER_CONCURRENCY_KEY = "worker.concurrency"
DEFAULT_WORKER_ENABLED = True
DEFAULT_WORKER_CONCURRENCY = 2
RUNNING_TASK_STATUSES = {
    "staging_to_cloud",
    "cloud_ready",
    "downloading",
    "verifying",
    "renaming",
    "cleaning_cloud",
}


@dataclass(frozen=True)
class WorkerSettings:
    enabled: bool = DEFAULT_WORKER_ENABLED
    concurrency: int = DEFAULT_WORKER_CONCURRENCY


class WorkerRuntime:
    def __init__(self, poll_interval_seconds: float = 5.0) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._running = True

    def stop(self, signum: int | None = None, frame: object | None = None) -> None:
        self._running = False

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        session_factory = get_session_factory()
        print("Sundarr Worker 已启动。", flush=True)
        while self._running:
            with session_factory() as session:
                settings = load_worker_settings(session)
                claimed = claim_pending_tasks(session, settings)
            if not settings.enabled:
                print("Sundarr Worker 已禁用，保持空转。", flush=True)
            elif claimed:
                print(f"Sundarr Worker 已领取 {len(claimed)} 个任务。", flush=True)
            time.sleep(self.poll_interval_seconds)
        print("Sundarr Worker 已停止。", flush=True)


def load_worker_settings(session: Session) -> WorkerSettings:
    enabled = _read_bool_setting(session, WORKER_ENABLED_KEY, DEFAULT_WORKER_ENABLED, "enabled")
    concurrency = _read_int_setting(session, WORKER_CONCURRENCY_KEY, DEFAULT_WORKER_CONCURRENCY, "value")
    return WorkerSettings(enabled=enabled, concurrency=max(1, concurrency))


def claim_pending_tasks(session: Session, settings: WorkerSettings) -> list[TransferTask]:
    if not settings.enabled:
        return []

    running_count = (
        session.query(TransferTask)
        .filter(TransferTask.status.in_(RUNNING_TASK_STATUSES))
        .count()
    )
    capacity = max(0, settings.concurrency - running_count)
    if capacity <= 0:
        return []

    tasks = (
        session.query(TransferTask)
        .filter(TransferTask.status == "pending")
        .order_by(TransferTask.created_at, TransferTask.id)
        .limit(capacity)
        .all()
    )
    now = datetime.now(UTC)
    for task in tasks:
        task.status = "staging_to_cloud"
        task.started_at = task.started_at or now
        session.add(
            TransferLog(
                id=uuid4().hex,
                task_id=task.id,
                level="info",
                event="worker_task_claimed",
                message="Worker 已领取任务。",
                data_json={"worker_concurrency": settings.concurrency},
            )
        )
    session.commit()
    return tasks


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


def main() -> None:
    WorkerRuntime().run()


if __name__ == "__main__":
    main()
