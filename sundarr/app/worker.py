import os
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
    MediaLibrary,
    RemoteMediaLibrary,
    ResourceLink,
    Setting,
    SyncBinding,
    SyncSeenFile,
    TransferFile,
    TransferLog,
    TransferTask,
)
from sundarr.app.storage import LocalWriter, SmbConfig, SmbWriter, StorageWriter
from sundarr.app.plugins.coordinator import RepositoryActivationCoordinator
from sundarr.app.plugins.manager import PluginManager, PluginProcessRole
from sundarr.app.plugins.runtime_registry import watchlist_provider_registry


WORKER_ENABLED_KEY = "worker.enabled"
WORKER_CONCURRENCY_KEY = "worker.concurrency"
LOCAL_CLOUD_KEY = "cloud.local"
LOCAL_STORAGE_KEY = "storage.local"
DTL_CONFIG_KEY = "download_to_local.config"
WATCHLIST_SYNC_INTERVAL_KEY = "discovery.watchlist_sync_interval_seconds"
DEFAULT_WORKER_ENABLED = True
DEFAULT_WORKER_CONCURRENCY = 2
DEFAULT_WATCHLIST_SYNC_INTERVAL_SECONDS = 900
WORKER_RECOVERY_ERROR_CODE = "WORKER_RECOVERY_REQUIRED"
DEFAULT_SYNC_DELETE_SOURCE = True
DEFAULT_SYNC_DELETE_EMPTY_DIRS = True
SYNC_CHUNK_SIZE = 1024 * 1024
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


class TaskPaused(Exception):
    pass


class _SpeedTracker:
    """1-second sliding window byte-rate tracker."""

    def __init__(self, window_seconds: float = 1.0) -> None:
        self._window = window_seconds
        self._bytes = 0
        self._started = time.monotonic()

    def add(self, nbytes: int) -> None:
        self._bytes += max(0, int(nbytes))

    def sample(self) -> int | None:
        elapsed = time.monotonic() - self._started
        if elapsed < self._window:
            return None
        rate = int(self._bytes / elapsed) if elapsed > 0 else 0
        self._bytes = 0
        self._started = time.monotonic()
        return rate


@dataclass(frozen=True)
class WorkerSettings:
    enabled: bool = DEFAULT_WORKER_ENABLED
    concurrency: int = DEFAULT_WORKER_CONCURRENCY


@dataclass(frozen=True)
class LocalRuntimeConfig:
    cloud_provider: LocalCloudProvider
    storage_writer: LocalWriter


class WorkerRuntime:
    def __init__(
        self,
        poll_interval_seconds: float = 5.0,
        plugin_manager: PluginManager | None = None,
    ) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._running = True
        self._last_scan_times: dict[str, float] = {}
        self._last_watchlist_sync_times: dict[str, float] = {}
        self.plugin_manager = plugin_manager or PluginManager(
            process_role=PluginProcessRole.WORKER,
            coordinator=RepositoryActivationCoordinator(),
        )

    def stop(self, signum: int | None = None, frame: object | None = None) -> None:
        self._running = False

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        session_factory = get_session_factory()
        print("Sundarr Worker 已启动。", flush=True)
        import asyncio

        with session_factory() as session:
            plugin_stats = asyncio.run(
                self.plugin_manager.load_all_repositories(
                    session,
                    process_role=PluginProcessRole.WORKER,
                )
            )
        print(
            f"Worker 插件恢复完成：成功 {plugin_stats['loaded']}，失败 {plugin_stats['error']}。",
            flush=True,
        )
        with session_factory() as session:
            recovered_count = recover_running_tasks(session)
        if recovered_count:
            print(f"Sundarr Worker 已保守恢复 {recovered_count} 个运行态任务。", flush=True)
        while self._running:
            claimed_ids: list[str] = []
            local_runtime: LocalRuntimeConfig | None = None
            with session_factory() as session:
                asyncio.run(
                    self.plugin_manager.reconcile_repositories(
                        session,
                        process_role=PluginProcessRole.WORKER,
                    )
                )
                settings = load_worker_settings(session)
                self._auto_scan_and_create_tasks(session)
                if settings.enabled:
                    self._auto_sync_watchlists(session)
                claimed = claim_pending_tasks(session, settings)
                claimed_ids = [task.id for task in claimed]
                local_runtime = load_local_runtime_config(session)
            if not settings.enabled:
                print("Sundarr Worker 已禁用，保持空转。", flush=True)
            elif claimed:
                print(f"Sundarr Worker 已领取 {len(claimed)} 个任务。", flush=True)
                asyncio.run(process_claimed_tasks(session_factory, claimed_ids, local_runtime))
            time.sleep(self.poll_interval_seconds)
        asyncio.run(self.plugin_manager.dispose_all())
        print("Sundarr Worker 已停止。", flush=True)

    def _auto_scan_and_create_tasks(self, session: Session) -> None:
        import asyncio

        bindings = session.query(SyncBinding).filter(SyncBinding.enabled.is_(True)).all()
        now = time.time()
        for binding in bindings:
            remote_lib = session.get(RemoteMediaLibrary, binding.remote_library_id)
            if remote_lib is None or not remote_lib.enabled:
                continue
            interval = remote_lib.scan_interval_seconds or 60
            last = self._last_scan_times.get(binding.id, 0)
            if now - last < interval:
                continue
            self._last_scan_times[binding.id] = now
            try:
                from sundarr.app.services.sync_service import sync_service
                from sundarr.app.schemas.sync import SyncScanRequest, SyncTaskCreateRequest

                asyncio.run(sync_service.scan(session, SyncScanRequest(binding_id=binding.id)))
                asyncio.run(sync_service.create_tasks(session, SyncTaskCreateRequest(binding_id=binding.id)))
                pending_count = session.query(TransferTask).filter(TransferTask.status == "pending").count()
                print(f"Worker 自动扫描 [{binding.name}] 完成，待处理任务: {pending_count}", flush=True)
            except Exception as exc:
                print(f"Worker 自动扫描 [{binding.name}] 失败: {exc}", flush=True)

    def _auto_sync_watchlists(self, session: Session) -> None:
        import asyncio

        interval = load_watchlist_sync_interval(session)
        now = time.time()
        for provider_id in watchlist_provider_registry.snapshot():
            last = self._last_watchlist_sync_times.get(provider_id, 0)
            if now - last < interval:
                continue
            self._last_watchlist_sync_times[provider_id] = now
            try:
                from sundarr.app.services.watchlist_service import watchlist_service

                result = asyncio.run(watchlist_service.sync(session, provider_id))
                print(
                    f"Worker 想看同步 [{provider_id}] 完成，新增或刷新 {result.pulled_count} 项。",
                    flush=True,
                )
            except Exception as exc:
                print(f"Worker 想看同步 [{provider_id}] 失败: {exc}", flush=True)


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
        if task.mode == "download_to_local":
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
                await process_sync_task(session, task)
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
    except TaskPaused:
        task.speed_bytes_per_sec = 0
        _add_log(session, task.id, "info", "task_paused_by_worker", "Worker 检测到暂停状态，已停止写入并保留临时文件。")
        session.commit()
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
    _check_task_state(session, task)
    # Only run cloud staging once; resume skips it if staging is already prepared.
    if not task.cloud_staging_path:
        _add_log(session, task.id, "info", "cloud_staging_started", "开始转存到 cloud staging。")
        task.status = "staging_to_cloud"
        task.cloud_staging_path = await cloud_provider.save_share(link.url, link.code, task.id)
        _add_log(session, task.id, "info", "cloud_staging_completed", "cloud staging 已准备完成。")
        session.commit()
    _check_task_state(session, task)

    files = await cloud_provider.list_files(task.cloud_staging_path)
    task.total_bytes = sum(file.size for file in files)
    existing_files = {
        file.cloud_file_id: file
        for file in session.query(TransferFile).filter(TransferFile.task_id == task.id).all()
        if file.cloud_file_id
    }
    # Recompute done_bytes from existing per-file progress so resume reflects actual temp sizes.
    task.done_bytes = sum(f.done_bytes for f in existing_files.values())
    task.speed_bytes_per_sec = 0
    task.status = "downloading"
    session.commit()

    for file in files:
        target_path = task.target_path if len(files) == 1 else f"{task.target_path.rstrip('/')}/{file.name}"
        temp_path = f"{target_path}.sundarr.downloading"
        transfer_file = existing_files.get(file.id)
        if transfer_file is None:
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

        if transfer_file.status == "completed":
            continue
        transfer_file.status = "downloading"
        session.commit()
        _check_task_state(session, task)

        # Resume: align temp file and cloud offset based on current temp size.
        existing_temp_size = 0
        if await storage_writer.exists(temp_path):
            try:
                existing_temp_size = int(await storage_writer.size(temp_path))
            except Exception:
                existing_temp_size = 0
        if existing_temp_size > file.size:
            # Corrupt / leftover temp — reset to zero and restart this file.
            await storage_writer.truncate(temp_path, 0)
            existing_temp_size = 0
        if existing_temp_size != transfer_file.done_bytes:
            # Keep DB counters consistent with reality on disk.
            delta = existing_temp_size - transfer_file.done_bytes
            transfer_file.done_bytes = existing_temp_size
            task.done_bytes = max(0, task.done_bytes + delta)
            session.commit()

        if existing_temp_size >= file.size and file.size > 0:
            transfer_file.status = "verified"
            session.commit()
        else:
            handle = await storage_writer.open_append(temp_path)
            speed_tracker = _SpeedTracker()
            with handle:
                async for chunk in cloud_provider.open_file_stream(file.id, offset=existing_temp_size):
                    _check_task_state(session, task)
                    handle.write(chunk)
                    transfer_file.done_bytes += len(chunk)
                    task.done_bytes += len(chunk)
                    speed_tracker.add(len(chunk))
                    new_speed = speed_tracker.sample()
                    if new_speed is not None:
                        task.speed_bytes_per_sec = new_speed
                    session.commit()
            task.speed_bytes_per_sec = 0
            session.commit()

        _check_task_state(session, task)
        task.status = "verifying"
        transfer_file.status = "verified"
        session.commit()
        if await storage_writer.size(temp_path) != file.size:
            raise ValueError("SIZE_MISMATCH")

        _check_task_state(session, task)
        task.status = "renaming"
        session.commit()
        await storage_writer.rename(temp_path, target_path)
        transfer_file.status = "completed"
        session.commit()

    task.status = "completed"
    task.speed_bytes_per_sec = 0
    task.completed_at = datetime.now(UTC)
    _add_log(session, task.id, "info", "transfer_completed", "任务已完成。")
    session.commit()
    await cleanup_cloud_staging(session, task, cloud_provider, storage_writer)
    return task


async def process_sync_task(
    session: Session,
    task: TransferTask,
    source_writer: StorageWriter | None = None,
    target_writer: StorageWriter | None = None,
) -> TransferTask:
    if task.status == "cancelled":
        return task
    try:
        return await _process_sync_task(session, task, source_writer, target_writer)
    except TaskCancelled:
        tw = target_writer or SmbWriter(SmbConfig.from_dict(task.storage_config_snapshot or {}))
        await _cleanup_downloading_files(session, task, tw)
        return task
    except TaskPaused:
        task.speed_bytes_per_sec = 0
        _add_log(session, task.id, "info", "task_paused_by_worker", "Worker 检测到暂停状态，已停止写入并保留临时文件。")
        session.commit()
        return task
    except Exception as exc:
        _mark_task_failed(session, task, exc)
        return task


async def _process_sync_task(
    session: Session,
    task: TransferTask,
    source_writer: StorageWriter | None,
    target_writer: StorageWriter | None,
) -> TransferTask:
    if task.mode != "download_to_local" or task.source_type != "smb" or task.target_type != "smb":
        raise ValueError("WORKER_UNSUPPORTED_TASK")
    if not task.source_path:
        raise ValueError("SYNC_SOURCE_PATH_INVALID")

    source_writer = source_writer or SmbWriter(SmbConfig.from_dict(task.source_config_snapshot or {}))
    target_writer = target_writer or SmbWriter(SmbConfig.from_dict(task.storage_config_snapshot or {}))
    transfer_file = _get_or_create_sync_file(session, task)
    _check_task_state(session, task)

    # Resume: reconcile temp file size with DB counters.
    expected_size = transfer_file.size_bytes
    existing_temp_size = 0
    if await target_writer.exists(transfer_file.temp_path):
        try:
            existing_temp_size = int(await target_writer.size(transfer_file.temp_path))
        except Exception:
            existing_temp_size = 0
    if expected_size and existing_temp_size > expected_size:
        await target_writer.truncate(transfer_file.temp_path, 0)
        existing_temp_size = 0
    if existing_temp_size != transfer_file.done_bytes:
        transfer_file.done_bytes = existing_temp_size
        task.done_bytes = existing_temp_size

    task.status = "downloading"
    task.speed_bytes_per_sec = 0
    transfer_file.status = "downloading"
    resume_log_event = "sync_copy_resumed" if existing_temp_size > 0 else "sync_copy_started"
    resume_log_message = (
        f"从断点 {existing_temp_size} 字节继续下载。" if existing_temp_size > 0 else "开始从 SMB 来源下载到本地媒体库。"
    )
    _add_log(session, task.id, "info", resume_log_event, resume_log_message)
    session.commit()

    speed_tracker = _SpeedTracker()

    with await source_writer.open_read(task.source_path, offset=existing_temp_size) as input_file:
        with await target_writer.open_append(transfer_file.temp_path) as output_file:
            while True:
                _check_task_state(session, task)
                chunk = input_file.read(SYNC_CHUNK_SIZE)
                if not chunk:
                    break
                output_file.write(chunk)
                transfer_file.done_bytes += len(chunk)
                task.done_bytes += len(chunk)
                speed_tracker.add(len(chunk))
                new_speed = speed_tracker.sample()
                if new_speed is not None:
                    task.speed_bytes_per_sec = new_speed
                session.commit()

    task.speed_bytes_per_sec = 0
    session.commit()
    _check_task_state(session, task)
    task.status = "verifying"
    transfer_file.status = "verified"
    session.commit()
    if await target_writer.size(transfer_file.temp_path) != expected_size:
        raise ValueError("SIZE_MISMATCH")

    _check_task_state(session, task)
    task.status = "renaming"
    session.commit()
    await target_writer.rename(transfer_file.temp_path, transfer_file.target_path)
    transfer_file.status = "completed"
    task.status = "completed"
    task.completed_at = datetime.now(UTC)
    _mark_sync_seen_file_completed(session, task)
    _add_log(session, task.id, "info", "sync_transfer_completed", "下载到本地已完成。")
    session.commit()

    await cleanup_sync_source(session, task, source_writer)
    return task


async def cleanup_sync_source(session: Session, task: TransferTask, source_writer: StorageWriter) -> bool:
    if task.status != "completed" or not task.source_path:
        return False
    delete_source, delete_empty_dirs = _load_sync_cleanup_options(session, task)
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
        task.error_code = "SYNC_SOURCE_DELETE_FAILED"
        task.error_message = str(exc) or "SYNC_SOURCE_DELETE_FAILED"
        task.retryable = True
        _add_log(
            session,
            task.id,
            "error",
            "sync_source_cleanup_failed",
            f"来源文件清理失败：{task.error_message}",
        )
        session.commit()
        return False

    task.status = "completed"
    _add_log(session, task.id, "info", "sync_source_cleanup_completed", "来源文件和空目录已清理。")
    session.commit()
    return True


def _mark_sync_seen_file_completed(session: Session, task: TransferTask) -> None:
    if not task.sync_seen_file_id:
        return
    seen = session.get(SyncSeenFile, task.sync_seen_file_id)
    if seen is not None:
        seen.status = "completed"


def _load_sync_cleanup_options(session: Session, task: TransferTask) -> tuple[bool, bool]:
    delete_source = DEFAULT_SYNC_DELETE_SOURCE
    delete_empty_dirs = DEFAULT_SYNC_DELETE_EMPTY_DIRS

    binding = _get_sync_binding_for_task(session, task)
    if binding is not None:
        if binding.delete_source_after_success is not None:
            delete_source = binding.delete_source_after_success
        if binding.delete_empty_source_dirs is not None:
            delete_empty_dirs = binding.delete_empty_source_dirs
    return delete_source, delete_empty_dirs


def _get_sync_binding_for_task(session: Session, task: TransferTask) -> SyncBinding | None:
    if not task.sync_seen_file_id:
        return None
    seen = session.get(SyncSeenFile, task.sync_seen_file_id)
    if seen is None or not seen.binding_id:
        return None
    return session.get(SyncBinding, seen.binding_id)


def _get_or_create_sync_file(session: Session, task: TransferTask) -> TransferFile:
    transfer_file = session.query(TransferFile).filter(TransferFile.task_id == task.id).one_or_none()
    if transfer_file is not None:
        return transfer_file
    if not task.source_path:
        raise ValueError("SYNC_SOURCE_PATH_INVALID")
    transfer_file = TransferFile(
        id=uuid4().hex,
        task_id=task.id,
        cloud_file_id=None,
        cloud_path=task.source_path,
        target_path=task.target_path,
        temp_path=f"{task.target_path}.sundarr.downloading",
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


def _check_task_state(session: Session, task: TransferTask) -> None:
    """Raise if the task has been cancelled or paused from another thread."""
    session.refresh(task)
    if task.status == "cancelled":
        raise TaskCancelled()
    if task.status == "paused":
        raise TaskPaused()


def _raise_if_cancelled(session: Session, task: TransferTask) -> None:
    _check_task_state(session, task)


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


async def _cleanup_downloading_files(session: Session, task: TransferTask, target_writer: StorageWriter) -> None:
    files = session.query(TransferFile).filter(
        TransferFile.task_id == task.id,
        TransferFile.status.in_(["pending", "downloading", "verified"]),
    ).all()
    for f in files:
        try:
            await target_writer.remove(f.temp_path)
        except Exception:
            pass


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
        "SYNC_SOURCE_DELETE_FAILED",
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
    from sundarr.app.logging_config import configure_file_logging_from_env

    configure_file_logging_from_env()
    pid_file = os.environ.get("SUNDARR_SERVICE_PID_FILE")
    if pid_file:
        Path(pid_file).write_text(str(os.getpid()), encoding="utf-8")
    WorkerRuntime().run()


if __name__ == "__main__":
    main()
