from sundarr.app.models import Resource, ResourceLink, Setting, TransferLog, TransferTask
from sundarr.app.worker import WorkerSettings, claim_pending_tasks, load_worker_settings


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


def _seed_transfer_tasks(db_session, statuses: list[str]) -> None:
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
                target_type="smb",
                target_path=f"Movies/Movie{index}.mkv",
            )
        )
    db_session.commit()
