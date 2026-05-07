from pathlib import Path
from typing import AsyncIterator

import pytest

from sundarr.app.cloud import LocalCloudProvider
from sundarr.app.cloud.base import CloudFile
from sundarr.app.models import Resource, ResourceLink, Setting, TransferFile, TransferLog, TransferTask
from sundarr.app.storage import LocalWriter
from sundarr.app.storage.base import StorageWriter
from sundarr.app.worker import (
    WorkerSettings,
    claim_pending_tasks,
    cleanup_cloud_staging,
    load_local_runtime_config,
    load_worker_settings,
    process_transfer_task,
)


def test_load_worker_settings_uses_defaults(db_session) -> None:
    settings = load_worker_settings(db_session)

    assert settings.enabled is True
    assert settings.concurrency == 2


def test_load_worker_settings_reads_database_values(db_session) -> None:
    db_session.add(Setting(key="worker.enabled", value_json={"enabled": False}, is_sensitive=False))
    db_session.add(Setting(key="worker.concurrency", value_json={"value": 4}, is_sensitive=False))
    db_session.commit()

    settings = load_worker_settings(db_session)

    assert settings.enabled is False
    assert settings.concurrency == 4


def test_load_worker_settings_clamps_concurrency(db_session) -> None:
    db_session.add(Setting(key="worker.concurrency", value_json={"value": 0}, is_sensitive=False))
    db_session.commit()

    settings = load_worker_settings(db_session)

    assert settings.concurrency == 1


def test_claim_pending_tasks_respects_concurrency(db_session) -> None:
    _seed_transfer_tasks(db_session, ["pending", "pending", "pending"])

    claimed = claim_pending_tasks(db_session, WorkerSettings(enabled=True, concurrency=2))

    assert [task.id for task in claimed] == ["task_0", "task_1"]
    assert db_session.get(TransferTask, "task_0").status == "staging_to_cloud"
    assert db_session.get(TransferTask, "task_1").status == "staging_to_cloud"
    assert db_session.get(TransferTask, "task_2").status == "pending"
    assert db_session.query(TransferLog).count() == 2


def test_claim_pending_tasks_accounts_for_running_tasks(db_session) -> None:
    _seed_transfer_tasks(db_session, ["downloading", "pending", "pending"])

    claimed = claim_pending_tasks(db_session, WorkerSettings(enabled=True, concurrency=2))

    assert [task.id for task in claimed] == ["task_1"]
    assert db_session.get(TransferTask, "task_1").status == "staging_to_cloud"
    assert db_session.get(TransferTask, "task_2").status == "pending"


def test_claim_pending_tasks_ignores_non_pending_tasks(db_session) -> None:
    _seed_transfer_tasks(db_session, ["completed", "failed", "cancelled"])

    claimed = claim_pending_tasks(db_session, WorkerSettings(enabled=True, concurrency=2))

    assert claimed == []
    assert db_session.query(TransferLog).count() == 0


def test_claim_pending_tasks_respects_disabled_worker(db_session) -> None:
    _seed_transfer_tasks(db_session, ["pending"])

    claimed = claim_pending_tasks(db_session, WorkerSettings(enabled=False, concurrency=2))

    assert claimed == []
    assert db_session.get(TransferTask, "task_0").status == "pending"


def test_claim_pending_tasks_ignores_unsupported_target(db_session) -> None:
    _seed_transfer_tasks(db_session, ["pending"], target_type="smb")

    claimed = claim_pending_tasks(db_session, WorkerSettings(enabled=True, concurrency=2))

    assert claimed == []
    assert db_session.get(TransferTask, "task_0").status == "pending"


def test_load_local_runtime_config_returns_none_without_full_config(db_session) -> None:
    assert load_local_runtime_config(db_session) is None


def test_load_local_runtime_config_reads_database_values(db_session, tmp_path: Path) -> None:
    db_session.add(
        Setting(
            key="cloud.local",
            value_json={"staging_root": str(tmp_path / "staging"), "share_root": str(tmp_path / "shares")},
            is_sensitive=False,
        )
    )
    db_session.add(Setting(key="storage.local", value_json={"root": str(tmp_path / "storage")}, is_sensitive=False))
    db_session.commit()

    config = load_local_runtime_config(db_session)

    assert config is not None


@pytest.mark.anyio
async def test_process_transfer_task_keeps_cancelled_task(db_session, tmp_path: Path) -> None:
    task, link = _seed_single_local_task(db_session)
    task.status = "cancelled"
    db_session.commit()

    await process_transfer_task(db_session, task, link, SingleFileCloudProvider(), LocalWriter(tmp_path / "storage"))

    db_session.refresh(task)
    assert task.status == "cancelled"
    assert db_session.query(TransferFile).count() == 0
    assert db_session.query(TransferLog).count() == 0


@pytest.mark.anyio
async def test_process_transfer_task_local_happy_path(db_session, tmp_path: Path) -> None:
    share_root = tmp_path / "shares"
    staging_root = tmp_path / "staging"
    storage_root = tmp_path / "storage"
    source_dir = share_root / "movie_share"
    source_dir.mkdir(parents=True)
    payload = b"0123456789"
    (source_dir / "Movie.mkv").write_bytes(payload)

    resource = Resource(id="res_local", title="本地电影", score=1)
    link = ResourceLink(id="link_local", resource_id=resource.id, provider="local", url="local://movie_share")
    task = TransferTask(
        id="task_local",
        resource_id=resource.id,
        link_id=link.id,
        status="staging_to_cloud",
        mode="copy",
        target_type="local",
        target_path="Movies/Movie.mkv",
    )
    db_session.add_all([resource, link, task])
    db_session.commit()

    await process_transfer_task(
        db_session,
        task,
        link,
        LocalCloudProvider(staging_root=staging_root, share_root=share_root, chunk_size=4),
        LocalWriter(storage_root),
    )

    db_session.refresh(task)
    assert task.status == "completed"
    assert task.total_bytes == len(payload)
    assert task.done_bytes == len(payload)
    assert (storage_root / "Movies" / "Movie.mkv").read_bytes() == payload
    assert not (storage_root / "Movies" / "Movie.mkv.downloading").exists()
    assert not (staging_root / "task_local").exists()

    transfer_file = db_session.query(TransferFile).one()
    assert transfer_file.status == "completed"
    assert transfer_file.done_bytes == len(payload)
    assert {log.event for log in db_session.query(TransferLog).all()} >= {
        "cloud_staging_started",
        "cloud_staging_completed",
        "transfer_completed",
        "cleanup_completed",
    }


@pytest.mark.anyio
async def test_cleanup_cloud_staging_requires_completed_files_and_matching_targets(db_session, tmp_path: Path) -> None:
    task, writer, storage_root = _seed_cleanup_task(db_session, tmp_path)
    (storage_root / "Movies" / "Movie.mkv").write_bytes(b"1234")
    cloud_provider = DeleteTrackingCloudProvider()

    cleaned = await cleanup_cloud_staging(db_session, task, cloud_provider, writer)

    db_session.refresh(task)
    assert cleaned is True
    assert task.status == "completed"
    assert cloud_provider.deleted_paths == ["/Sundarr/_staging/task_cleanup"]
    assert "cleanup_completed" in {log.event for log in db_session.query(TransferLog).all()}


@pytest.mark.anyio
async def test_cleanup_cloud_staging_refuses_failed_task(db_session, tmp_path: Path) -> None:
    task, writer, storage_root = _seed_cleanup_task(db_session, tmp_path, task_status="failed")
    (storage_root / "Movies" / "Movie.mkv").write_bytes(b"1234")
    cloud_provider = DeleteTrackingCloudProvider()

    cleaned = await cleanup_cloud_staging(db_session, task, cloud_provider, writer)

    assert cleaned is False
    assert cloud_provider.deleted_paths == []


@pytest.mark.anyio
async def test_cleanup_cloud_staging_refuses_uncompleted_file(db_session, tmp_path: Path) -> None:
    task, writer, storage_root = _seed_cleanup_task(db_session, tmp_path, file_status="verified")
    (storage_root / "Movies" / "Movie.mkv").write_bytes(b"1234")
    cloud_provider = DeleteTrackingCloudProvider()

    cleaned = await cleanup_cloud_staging(db_session, task, cloud_provider, writer)

    assert cleaned is False
    assert cloud_provider.deleted_paths == []


@pytest.mark.anyio
async def test_cleanup_cloud_staging_refuses_unsafe_path(db_session, tmp_path: Path) -> None:
    task, writer, storage_root = _seed_cleanup_task(db_session, tmp_path, cloud_staging_path="/Sundarr/_staging")
    (storage_root / "Movies" / "Movie.mkv").write_bytes(b"1234")
    cloud_provider = DeleteTrackingCloudProvider()

    cleaned = await cleanup_cloud_staging(db_session, task, cloud_provider, writer)

    assert cleaned is False
    assert cloud_provider.deleted_paths == []


@pytest.mark.anyio
async def test_cleanup_cloud_staging_refuses_missing_target(db_session, tmp_path: Path) -> None:
    task, writer, _storage_root = _seed_cleanup_task(db_session, tmp_path)
    cloud_provider = DeleteTrackingCloudProvider()

    cleaned = await cleanup_cloud_staging(db_session, task, cloud_provider, writer)

    assert cleaned is False
    assert cloud_provider.deleted_paths == []


@pytest.mark.anyio
async def test_cleanup_cloud_staging_failure_keeps_completed_task(db_session, tmp_path: Path) -> None:
    task, writer, storage_root = _seed_cleanup_task(db_session, tmp_path)
    (storage_root / "Movies" / "Movie.mkv").write_bytes(b"1234")

    cleaned = await cleanup_cloud_staging(db_session, task, FailingDeleteCloudProvider(), writer)

    db_session.refresh(task)
    assert cleaned is False
    assert task.status == "completed"
    assert task.error_code == "CLOUD_CLEANUP_FAILED"
    assert task.retryable is True
    assert "cleanup_failed" in {log.event for log in db_session.query(TransferLog).all()}


@pytest.mark.anyio
async def test_process_transfer_task_marks_cloud_stream_failure(db_session, tmp_path: Path) -> None:
    task, link = _seed_single_local_task(db_session)

    await process_transfer_task(db_session, task, link, FailingStreamCloudProvider(), LocalWriter(tmp_path / "storage"))

    db_session.refresh(task)
    assert task.status == "failed"
    assert task.error_code == "CLOUD_STREAM_FAILED"
    assert task.retryable is True
    assert db_session.query(TransferFile).one().status == "failed"
    assert "transfer_failed" in {log.event for log in db_session.query(TransferLog).all()}


@pytest.mark.anyio
async def test_process_transfer_task_marks_size_mismatch(db_session, tmp_path: Path) -> None:
    task, link = _seed_single_local_task(db_session)

    await process_transfer_task(db_session, task, link, SingleFileCloudProvider(), WrongSizeWriter(tmp_path / "storage"))

    db_session.refresh(task)
    assert task.status == "failed"
    assert task.error_code == "SIZE_MISMATCH"
    assert task.retryable is False
    assert db_session.query(TransferFile).one().status == "failed"


@pytest.mark.anyio
async def test_process_transfer_task_marks_write_failure(db_session) -> None:
    task, link = _seed_single_local_task(db_session)

    await process_transfer_task(db_session, task, link, SingleFileCloudProvider(), FailingWriteWriter())

    db_session.refresh(task)
    assert task.status == "failed"
    assert task.error_code == "STORAGE_WRITE_FAILED"
    assert task.retryable is True
    assert db_session.query(TransferFile).one().status == "failed"


@pytest.mark.anyio
async def test_process_transfer_task_marks_target_exists_and_keeps_temp(db_session, tmp_path: Path) -> None:
    task, link = _seed_single_local_task(db_session)
    storage_root = tmp_path / "storage"
    target = storage_root / "Movies" / "Movie.mkv"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing")

    await process_transfer_task(db_session, task, link, SingleFileCloudProvider(), LocalWriter(storage_root))

    db_session.refresh(task)
    assert task.status == "failed"
    assert task.error_code == "TARGET_EXISTS"
    assert task.retryable is False
    assert (storage_root / "Movies" / "Movie.mkv.downloading").exists()
    assert target.read_bytes() == b"existing"


def _seed_transfer_tasks(db_session, statuses: list[str], target_type: str = "local") -> None:
    resource = Resource(id="res_worker", title="测试资源", score=1)
    link = ResourceLink(id="link_worker", resource_id=resource.id, provider="local", url="local://share")
    db_session.add_all([resource, link])
    for index, status in enumerate(statuses):
        db_session.add(
            TransferTask(
                id=f"task_{index}",
                resource_id=resource.id,
                link_id=link.id,
                status=status,
                mode="copy",
                target_type=target_type,
                target_path=f"Movies/Movie{index}.mkv",
            )
        )
    db_session.commit()


def _seed_single_local_task(db_session) -> tuple[TransferTask, ResourceLink]:
    resource = Resource(id=uuid_text("res"), title="本地电影", score=1)
    link = ResourceLink(id=uuid_text("link"), resource_id=resource.id, provider="local", url="local://movie_share")
    task = TransferTask(
        id=uuid_text("task"),
        resource_id=resource.id,
        link_id=link.id,
        status="staging_to_cloud",
        mode="copy",
        target_type="local",
        target_path="Movies/Movie.mkv",
    )
    db_session.add_all([resource, link, task])
    db_session.commit()
    return task, link


def _seed_cleanup_task(
    db_session,
    tmp_path: Path,
    task_status: str = "completed",
    file_status: str = "completed",
    cloud_staging_path: str = "/Sundarr/_staging/task_cleanup",
) -> tuple[TransferTask, LocalWriter, Path]:
    resource = Resource(id="res_cleanup", title="清理测试", score=1)
    link = ResourceLink(id="link_cleanup", resource_id=resource.id, provider="local", url="local://movie_share")
    task = TransferTask(
        id="task_cleanup",
        resource_id=resource.id,
        link_id=link.id,
        status=task_status,
        mode="copy",
        target_type="local",
        target_path="Movies/Movie.mkv",
        cloud_staging_path=cloud_staging_path,
    )
    transfer_file = TransferFile(
        id="file_cleanup",
        task_id=task.id,
        cloud_path="/Sundarr/_staging/task_cleanup/Movie.mkv",
        target_path="Movies/Movie.mkv",
        temp_path="Movies/Movie.mkv.downloading",
        filename="Movie.mkv",
        size_bytes=4,
        done_bytes=4,
        status=file_status,
    )
    storage_root = tmp_path / "storage"
    (storage_root / "Movies").mkdir(parents=True)
    db_session.add_all([resource, link, task, transfer_file])
    db_session.commit()
    return task, LocalWriter(storage_root), storage_root


def uuid_text(prefix: str) -> str:
    return f"{prefix}_failure"


class SingleFileCloudProvider:
    name = "single"

    async def save_share(self, url: str, code: str | None, target_dir: str) -> str:
        return f"/Sundarr/_staging/{target_dir}"

    async def list_files(self, path: str) -> list[CloudFile]:
        return [CloudFile(id="file_1", path=f"{path}/Movie.mkv", name="Movie.mkv", size=4)]

    async def open_file_stream(self, file_id: str, offset: int = 0) -> AsyncIterator[bytes]:
        yield b"1234"

    async def delete(self, path: str) -> None:
        return None


class DeleteTrackingCloudProvider(SingleFileCloudProvider):
    def __init__(self) -> None:
        self.deleted_paths: list[str] = []

    async def delete(self, path: str) -> None:
        self.deleted_paths.append(path)


class FailingDeleteCloudProvider(SingleFileCloudProvider):
    async def delete(self, path: str) -> None:
        raise ValueError("CLOUD_DELETE_FAILED")


class FailingStreamCloudProvider(SingleFileCloudProvider):
    async def open_file_stream(self, file_id: str, offset: int = 0) -> AsyncIterator[bytes]:
        yield b"12"
        raise ValueError("CLOUD_STREAM_FAILED")


class WrongSizeWriter(LocalWriter):
    async def size(self, path: str) -> int:
        return 999


class FailingWriteWriter(StorageWriter):
    name = "failing"

    async def exists(self, path: str) -> bool:
        return False

    async def size(self, path: str) -> int:
        return 0

    async def mkdirs(self, path: str) -> None:
        return None

    async def open_append(self, path: str):
        raise ValueError("STORAGE_WRITE_FAILED")

    async def rename(self, src: str, dst: str) -> None:
        return None

    async def remove(self, path: str) -> None:
        return None
