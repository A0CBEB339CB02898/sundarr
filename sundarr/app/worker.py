import signal
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.cloud import CloudProvider, LocalCloudProvider
from sundarr.app.core.database import get_session_factory
from sundarr.app.models import (
    DownloadToLocalBinding,
    DownloadToLocalSeenFile,
    ResourceLink,
    Setting,
    TransferFile,
    TransferLog,
    TransferTask,
)
from sundarr.app.storage import LocalWriter, SmbConfig, SmbWriter, StorageWriter


WORKER_ENABLED_KEY = "worker.enabled"
WORKER_CONCURRENCY_KEY = "worker.concurrency"
LOCAL_CLOUD_KEY = "cloud.local"
LOCAL_STORAGE_KEY = "storage.local"
DTL_CONFIG_KEY = "download_to_local.config"
DEFAULT_WORKER_ENABLED = True
DEFAULT_WORKER_CONCURRENCY = 2
WORKER_RECOVERY_ERROR_CODE = "WORKER_RECOVERY_REQUIRED"
DEFAULT_DTL_DELETE_SOURCE = True
DEFAULT_DTL_DELETE_EMPTY_DIRS = True
DTL_CHUNK_SIZE = 1024 * 1024
RUNNING_TASK_STATUSES = {
    "staging_to_cloud",
    "cloud_ready",
    "downloading",
    "verifying",
    "renaming",
    "cleaning_cloud",
    "cleaning_source",
}


class TaskCancelled(Exception):
    pass


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
        with session_factory() as session:
            recovered_count = recover_running_tasks(session)
        if recovered_count:
            print(f"Sundarr Worker 已保守恢复 {recovered_count} 个运行态任务。", flush=True)
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

    running_count = session.query(TransferTask).filter(TransferTask.status.in_(RUNNING_TASK_STATUSES)).count()
    capacity = max(0, settings.concurrency - running_count)
    if capacity <= 0:
        return []

    pending_tasks = (
        session.query(TransferTask)
        .filter(TransferTask.status == "pending")
        .order_by(TransferTask.created_at, TransferTask.id)
        .all()
    )
    tasks: list[TransferTask] = []
    for task in pending_tasks:
        if len(tasks) >= capacity:
            break
        if _is_supported_claim_task(session, task):
            tasks.append(task)

    now = datetime.now(UTC)
    for task in tasks:
        if task.mode in ("ingest", "download_to_local"):
            task.status = "downloading"
        else:
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


def _is_supported_claim_task(session: Session, task: TransferTask) -> bool:
    if task.mode == "download_to_local":
        return task.source_type == "smb" and task.target_type == "smb"
    if task.target_type != "local" or not task.link_id:
        return False
    link = session.get(ResourceLink, task.link_id)
    return bool(link and link.provider == "local")


def recover_running_tasks(session: Session) -> int:
    tasks = session.query(TransferTask).filter(TransferTask.status.in_(RUNNING_TASK_STATUSES)).all()
    if not tasks:
        return 0

    for task in tasks:
        previous_status = task.status
        task.status = "failed"
        task.error_code = WORKER_RECOVERY_ERROR_CODE
        task.error_message = "Worker 启动时发现任务停留在运行态，已标记为可重试失败。"
        task.retryable = True
        files = (
            session.query(TransferFile)
            .filter(TransferFile.task_id == task.id, TransferFile.status.in_(["pending", "downloading", "verified"]))
            .all()
        )
        for transfer_file in files:
            transfer_file.status = "failed"
            transfer_file.error_code = WORKER_RECOVERY_ERROR_CODE
            transfer_file.error_message = task.error_message
        session.add(
            TransferLog(
                id=uuid4().hex,
                task_id=task.id,
                level="warning",
                event="worker_startup_recovered",
                message="Worker 启动时保守恢复运行态任务，保留 .downloading 文件和 cloud staging。",
                data_json={"previous_status": previous_status},
            )
        )
    session.commit()
    return len(tasks)


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


async def process_claimed_tasks(
    session_factory,
    task_ids: list[str],
    local_runtime: LocalRuntimeConfig | None,
) -> None:
    for task_id in task_ids:
        with session_factory() as session:
            task = session.get(TransferTask, task_id)
            if task is None:
                continue
            if task.status == "cancelled":
                continue
            if task.mode == "download_to_local":
                await process_dtl_task(session, task)
                continue
            if local_runtime is None or not task.link_id:
                continue
            link = session.get(ResourceLink, task.link_id)
            if link is None or link.provider != "local" or task.target_type != "local":
                continue
            await process_transfer_task(
                session,
                task,
                link,
                local_runtime.cloud_provider,
                local_runtime.storage_writer,
            )


async def process_transfer_task(
    session: Session,
    task: TransferTask,
    link: ResourceLink,
    cloud_provider: CloudProvider,
    storage_writer: StorageWriter,
) -> TransferTask:
    if task.status == "cancelled":
        return task
    try:
        return await _process_transfer_task(session, task, link, cloud_provider, storage_writer)
    except TaskCancelled:
        return task
    except Exception as exc:
        _mark_task_failed(session, task, exc)
        return task


async def _process_transfer_task(
    session: Session,
    task: TransferTask,
    link: ResourceLink,
    cloud_provider: CloudProvider,
    storage_writer: StorageWriter,
) -> TransferTask:
    _raise_if_cancelled(session, task)
    _add_log(session, task.id, "info", "cloud_staging_started", "开始转存到 cloud staging。")
    task.status = "staging_to_cloud"
    task.cloud_staging_path = await cloud_provider.save_share(link.url, link.code, task.id)
    _add_log(session, task.id, "info", "cloud_staging_completed", "cloud staging 已准备完成。")
    session.commit()
    _raise_if_cancelled(session, task)

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
        _raise_if_cancelled(session, task)

        handle = await storage_writer.open_append(temp_path)
        with handle:
            async for chunk in cloud_provider.open_file_stream(file.id):
                _raise_if_cancelled(session, task)
                handle.write(chunk)
                transfer_file.done_bytes += len(chunk)
                task.done_bytes += len(chunk)
                session.commit()

        _raise_if_cancelled(session, task)
        task.status = "verifying"
        transfer_file.status = "verified"
        session.commit()
        if await storage_writer.size(temp_path) != file.size:
            raise ValueError("SIZE_MISMATCH")

        _raise_if_cancelled(session, task)
        task.status = "renaming"
        session.commit()
        await storage_writer.rename(temp_path, target_path)
        transfer_file.status = "completed"
        session.commit()

    task.status = "completed"
    task.completed_at = datetime.now(UTC)
    _add_log(session, task.id, "info", "transfer_completed", "任务已完成。")
    session.commit()
    await cleanup_cloud_staging(session, task, cloud_provider, storage_writer)
    return task


async def process_dtl_task(
    session: Session,
    task: TransferTask,
    source_writer: StorageWriter | None = None,
    target_writer: StorageWriter | None = None,
) -> TransferTask:
    if task.status == "cancelled":
        return task
    try:
        return await _process_dtl_task(session, task, source_writer, target_writer)
    except TaskCancelled:
        return task
    except Exception as exc:
        _mark_task_failed(session, task, exc)
        return task


async def _process_dtl_task(
    session: Session,
    task: TransferTask,
    source_writer: StorageWriter | None,
    target_writer: StorageWriter | None,
) -> TransferTask:
    if task.mode != "download_to_local" or task.source_type != "smb" or task.target_type != "smb":
        raise ValueError("WORKER_UNSUPPORTED_TASK")
    if not task.source_path:
        raise ValueError("DTL_SOURCE_PATH_INVALID")

    source_writer = source_writer or SmbWriter(SmbConfig.from_dict(task.source_config_snapshot or {}))
    target_writer = target_writer or SmbWriter(SmbConfig.from_dict(task.storage_config_snapshot or {}))
    transfer_file = _get_or_create_dtl_file(session, task)
    _raise_if_cancelled(session, task)

    task.status = "downloading"
    transfer_file.status = "downloading"
    _add_log(session, task.id, "info", "dtl_copy_started", "开始从 SMB 来源下载到本地媒体库。")
    session.commit()

    with await source_writer.open_read(task.source_path) as input_file:
        with await target_writer.open_append(transfer_file.temp_path) as output_file:
            while True:
                _raise_if_cancelled(session, task)
                chunk = input_file.read(DTL_CHUNK_SIZE)
                if not chunk:
                    break
                output_file.write(chunk)
                transfer_file.done_bytes += len(chunk)
                task.done_bytes += len(chunk)
                session.commit()

    _raise_if_cancelled(session, task)
    task.status = "verifying"
    transfer_file.status = "verified"
    session.commit()
    expected_size = transfer_file.size_bytes
    if await target_writer.size(transfer_file.temp_path) != expected_size:
        raise ValueError("SIZE_MISMATCH")

    _raise_if_cancelled(session, task)
    task.status = "renaming"
    session.commit()
    await target_writer.rename(transfer_file.temp_path, transfer_file.target_path)
    transfer_file.status = "completed"
    task.status = "completed"
    task.completed_at = datetime.now(UTC)
    _mark_dtl_seen_file_completed(session, task)
    _add_log(session, task.id, "info", "dtl_transfer_completed", "下载到本地已完成。")
    session.commit()

    await cleanup_dtl_source(session, task, source_writer)
    return task


async def cleanup_dtl_source(session: Session, task: TransferTask, source_writer: StorageWriter) -> bool:
    if task.status != "completed" or not task.source_path:
        return False
    delete_source, delete_empty_dirs = _load_dtl_cleanup_options(session, task)
    if not delete_source:
        return False

    task.status = "cleaning_source"
    session.commit()
    try:
        await source_writer.remove(task.source_path)
        if delete_empty_dirs:
            await _remove_empty_source_dirs(source_writer, task.source_path)
    except Exception as exc:
        task.status = "completed"
        task.error_code = "DTL_SOURCE_DELETE_FAILED"
        task.error_message = str(exc) or "DTL_SOURCE_DELETE_FAILED"
        task.retryable = True
        _add_log(
            session,
            task.id,
            "error",
            "dtl_source_cleanup_failed",
            f"来源文件清理失败：{task.error_message}",
        )
        session.commit()
        return False

    task.status = "completed"
    _add_log(session, task.id, "info", "dtl_source_cleanup_completed", "来源文件和空目录已清理。")
    session.commit()
    return True


def _mark_dtl_seen_file_completed(session: Session, task: TransferTask) -> None:
    if not task.ingest_seen_file_id:
        return
    seen = session.get(DownloadToLocalSeenFile, task.ingest_seen_file_id)
    if seen is not None:
        seen.status = "completed"


def _load_dtl_cleanup_options(session: Session, task: TransferTask) -> tuple[bool, bool]:
    delete_source = DEFAULT_DTL_DELETE_SOURCE
    delete_empty_dirs = DEFAULT_DTL_DELETE_EMPTY_DIRS
    setting = session.get(Setting, DTL_CONFIG_KEY)
    if setting is not None:
        value = setting.value_json
        source_value = value.get("delete_source_after_success")
        dirs_value = value.get("delete_empty_source_dirs")
        delete_source = source_value if isinstance(source_value, bool) else delete_source
        delete_empty_dirs = dirs_value if isinstance(dirs_value, bool) else delete_empty_dirs

    binding = _get_dtl_binding_for_task(session, task)
    if binding is not None:
        if binding.delete_source_after_success is not None:
            delete_source = binding.delete_source_after_success
        if binding.delete_empty_source_dirs is not None:
            delete_empty_dirs = binding.delete_empty_source_dirs
    return delete_source, delete_empty_dirs


def _get_dtl_binding_for_task(session: Session, task: TransferTask) -> DownloadToLocalBinding | None:
    if not task.ingest_seen_file_id:
        return None
    seen = session.get(DownloadToLocalSeenFile, task.ingest_seen_file_id)
    if seen is None or not seen.binding_id:
        return None
    return session.get(DownloadToLocalBinding, seen.binding_id)


def _get_or_create_dtl_file(session: Session, task: TransferTask) -> TransferFile:
    transfer_file = session.query(TransferFile).filter(TransferFile.task_id == task.id).one_or_none()
    if transfer_file is not None:
        return transfer_file
    if not task.source_path:
        raise ValueError("DTL_SOURCE_PATH_INVALID")
    transfer_file = TransferFile(
        id=uuid4().hex,
        task_id=task.id,
        cloud_file_id=None,
        cloud_path=task.source_path,
        target_path=task.target_path,
        temp_path=f"{task.target_path}.downloading",
        filename=task.target_path.rsplit("/", 1)[-1] or task.target_path,
        size_bytes=task.total_bytes,
        done_bytes=0,
        status="pending",
    )
    session.add(transfer_file)
    session.flush()
    return transfer_file


async def cleanup_cloud_staging(
    session: Session,
    task: TransferTask,
    cloud_provider: CloudProvider,
    storage_writer: StorageWriter,
) -> bool:
    if not await _can_cleanup_cloud_staging(session, task, storage_writer):
        return False

    task.status = "cleaning_cloud"
    session.commit()
    try:
        await cloud_provider.delete(task.cloud_staging_path or "")
    except Exception as exc:
        task.status = "completed"
        task.error_code = "CLOUD_CLEANUP_FAILED"
        task.error_message = str(exc) or "CLOUD_CLEANUP_FAILED"
        task.retryable = True
        _add_log(session, task.id, "error", "cleanup_failed", f"cloud staging 清理失败：{task.error_message}")
        session.commit()
        return False

    task.status = "completed"
    _add_log(session, task.id, "info", "cleanup_completed", "cloud staging 已清理。")
    session.commit()
    return True


async def _can_cleanup_cloud_staging(session: Session, task: TransferTask, storage_writer: StorageWriter) -> bool:
    session.refresh(task)
    if task.status != "completed" or not _is_task_staging_path(task.cloud_staging_path, task.id):
        return False

    files = session.query(TransferFile).filter(TransferFile.task_id == task.id).all()
    if not files or any(file.status != "completed" for file in files):
        return False
    for file in files:
        if not await storage_writer.exists(file.target_path):
            return False
        if await storage_writer.size(file.target_path) != file.size_bytes:
            return False
    return True


def _is_task_staging_path(path: str | None, task_id: str) -> bool:
    if not path:
        return False
    normalized = path.strip("/")
    return normalized == f"Sundarr/_staging/{task_id}"


async def _remove_empty_source_dirs(source_writer: StorageWriter, source_path: str) -> None:
    parts = source_path.strip().replace("\\", "/").strip("/").split("/")[:-1]
    while parts:
        current = "/".join(parts)
        try:
            await source_writer.remove_empty_dir(current)
        except Exception:
            return
        parts.pop()


def _raise_if_cancelled(session: Session, task: TransferTask) -> None:
    session.refresh(task)
    if task.status == "cancelled":
        raise TaskCancelled()


def _mark_task_failed(session: Session, task: TransferTask, exc: Exception) -> None:
    error_code = _error_code_from_exception(exc)
    task.status = "failed"
    task.error_code = error_code
    task.error_message = str(exc) or error_code
    task.retryable = _is_retryable_error(error_code)
    failed_files = (
        session.query(TransferFile)
        .filter(TransferFile.task_id == task.id, TransferFile.status.in_(["pending", "downloading", "verified"]))
        .all()
    )
    for transfer_file in failed_files:
        transfer_file.status = "failed"
        transfer_file.error_code = error_code
        transfer_file.error_message = task.error_message
    _add_log(session, task.id, "error", "transfer_failed", f"任务失败：{task.error_message}")
    session.commit()


def _error_code_from_exception(exc: Exception) -> str:
    if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], str) and exc.args[0].isupper():
        return exc.args[0]
    return "WORKER_TRANSFER_FAILED"


def _is_retryable_error(error_code: str) -> bool:
    return error_code in {
        "CLOUD_STREAM_FAILED",
        "STORAGE_WRITE_FAILED",
        "SMB_HOST_UNREACHABLE",
        "SMB_WRITE_FAILED",
        "WORKER_TRANSFER_FAILED",
        "INGEST_SOURCE_DELETE_FAILED",
        "DTL_SOURCE_DELETE_FAILED",
    }


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
