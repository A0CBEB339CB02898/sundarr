from pathlib import Path

import pytest

from sundarr.app.cloud import LocalCloudProvider
from sundarr.app.models import Resource, ResourceLink, Setting, TransferFile, TransferLog, TransferTask
from sundarr.app.storage import LocalWriter
from sundarr.app.worker import WorkerSettings, claim_pending_tasks, load_local_runtime_config, load_worker_settings, process_transfer_task


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

    transfer_file = db_session.query(TransferFile).one()
    assert transfer_file.status == "completed"
    assert transfer_file.done_bytes == len(payload)
    assert {log.event for log in db_session.query(TransferLog).all()} >= {
        "cloud_staging_started",
        "cloud_staging_completed",
        "transfer_completed",
    }


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
