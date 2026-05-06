import signal
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.cloud import CloudProvider, LocalCloudProvider
from sundarr.app.core.database import get_session_factory
from sundarr.app.models import ResourceLink, Setting, TransferFile, TransferLog, TransferTask
from sundarr.app.storage import LocalWriter, StorageWriter


WORKER_ENABLED_KEY = "worker.enabled"
WORKER_CONCURRENCY_KEY = "worker.concurrency"
LOCAL_CLOUD_KEY = "cloud.local"
LOCAL_STORAGE_KEY = "storage.local"
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


@dataclass(frozen=True)
class LocalRuntimeConfig:
    cloud_provider: LocalCloudProvider
    storage_writer: LocalWriter


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
            claimed_ids: list[str] = []
            local_runtime: LocalRuntimeConfig | None = None
            with session_factory() as session:
                settings = load_worker_settings(session)
                claimed = claim_pending_tasks(session, settings)
                claimed_ids = [task.id for task in claimed]
                local_runtime = load_local_runtime_config(session)
            if not settings.enabled:
                print("Sundarr Worker 已禁用，保持空转。", flush=True)
            elif claimed:
                print(f"Sundarr Worker 已领取 {len(claimed)} 个任务。", flush=True)
                if local_runtime is not None:
                    import asyncio

                    asyncio.run(process_claimed_tasks(session_factory, claimed_ids, local_runtime))
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
        .join(ResourceLink, TransferTask.link_id == ResourceLink.id)
        .filter(TransferTask.status.in_(RUNNING_TASK_STATUSES))
        .filter(TransferTask.target_type == "local", ResourceLink.provider == "local")
        .count()
    )
    capacity = max(0, settings.concurrency - running_count)
    if capacity <= 0:
        return []

    tasks = (
        session.query(TransferTask)
        .join(ResourceLink, TransferTask.link_id == ResourceLink.id)
        .filter(TransferTask.status == "pending")
        .filter(TransferTask.target_type == "local", ResourceLink.provider == "local")
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


async def process_claimed_tasks(session_factory, task_ids: list[str], local_runtime: LocalRuntimeConfig) -> None:
    for task_id in task_ids:
        with session_factory() as session:
            task = session.get(TransferTask, task_id)
            if task is None:
                continue
            link = session.get(ResourceLink, task.link_id)
            if link is None or link.provider != "local" or task.target_type != "local":
                continue
            await process_transfer_task(session, task, link, local_runtime.cloud_provider, local_runtime.storage_writer)


async def process_transfer_task(
    session: Session,
    task: TransferTask,
    link: ResourceLink,
    cloud_provider: CloudProvider,
    storage_writer: StorageWriter,
) -> TransferTask:
    _add_log(session, task.id, "info", "cloud_staging_started", "开始转存到 cloud staging。")
    task.status = "staging_to_cloud"
    task.cloud_staging_path = await cloud_provider.save_share(link.url, link.code, task.id)
    _add_log(session, task.id, "info", "cloud_staging_completed", "cloud staging 已准备完成。")

    files = await cloud_provider.list_files(task.cloud_staging_path)
    task.total_bytes = sum(file.size for file in files)
    task.done_bytes = 0
    task.status = "downloading"
    session.commit()

    for file in files:
        target_path = task.target_path if len(files) == 1 else f"{task.target_path.rstrip('/')}/{file.name}"
        temp_path = f"{target_path}.downloading"
        transfer_file = TransferFile(
            id=uuid4().hex,
            task_id=task.id,
            cloud_file_id=file.id,
            cloud_path=file.path,
            target_path=target_path,
            temp_path=temp_path,
            filename=file.name,
            size_bytes=file.size,
            done_bytes=0,
            status="downloading",
        )
        session.add(transfer_file)
        session.commit()

        handle = await storage_writer.open_append(temp_path)
        with handle:
            async for chunk in cloud_provider.open_file_stream(file.id):
                handle.write(chunk)
                transfer_file.done_bytes += len(chunk)
                task.done_bytes += len(chunk)
                session.commit()

        task.status = "verifying"
        transfer_file.status = "verified"
        session.commit()
        if await storage_writer.size(temp_path) != file.size:
            raise ValueError("SIZE_MISMATCH")

        task.status = "renaming"
        session.commit()
        await storage_writer.rename(temp_path, target_path)
        transfer_file.status = "completed"
        session.commit()

    task.status = "completed"
    task.completed_at = datetime.now(UTC)
    _add_log(session, task.id, "info", "transfer_completed", "任务已完成。")
    session.commit()
    return task


def _add_log(session: Session, task_id: str, level: str, event: str, message: str) -> None:
    session.add(
        TransferLog(
            id=uuid4().hex,
            task_id=task_id,
            level=level,
            event=event,
            message=message,
            data_json=None,
        )
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


def main() -> None:
    WorkerRuntime().run()


if __name__ == "__main__":
    main()
