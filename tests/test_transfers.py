from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import Resource, ResourceLink, Setting, TransferFile, TransferLog, TransferTask


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def seed_link(db_session: Session) -> ResourceLink:
    resource = Resource(id="res_1", title="星际穿越", score=1)
    link = ResourceLink(
        id="link_1",
        resource_id=resource.id,
        provider="local",
        url="local://movie_share",
        code=None,
    )
    db_session.add_all([resource, link])
    db_session.commit()
    return link


def test_create_and_get_transfer(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    db_session.commit()

    response = client.post(
        "/transfers",
        json={"link_id": link.id, "target_library": "movies", "target_path": "Movies/Interstellar.mkv"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["resource_id"] == "res_1"
    assert body["target_type"] == "smb"

    task = db_session.get(TransferTask, body["id"])
    assert task is not None
    assert task.storage_config_snapshot is None

    get_response = client.get(f"/transfers/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]
    assert get_response.json()["progress"] == 0
    assert get_response.json()["current_file"] is None


def test_get_transfer_returns_progress_and_current_file(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = TransferTask(
        id="task_progress",
        resource_id="res_1",
        link_id=link.id,
        status="downloading",
        mode="copy",
        target_type="local",
        target_path="Movies/Movie.mkv",
        total_bytes=10,
        done_bytes=4,
    )
    db_session.add(task)
    db_session.add(
        TransferFile(
            id="file_progress",
            task_id=task.id,
            cloud_path="/Sundarr/_staging/task/Movie.mkv",
            target_path="Movies/Movie.mkv",
            temp_path="Movies/Movie.mkv.sundarr.downloading",
            filename="Movie.mkv",
            size_bytes=10,
            done_bytes=4,
            status="downloading",
        )
    )
    db_session.commit()

    response = client.get("/transfers/task_progress")

    assert response.status_code == 200
    body = response.json()
    assert body["progress"] == 40
    assert body["current_file"] == "Movie.mkv"


def test_list_transfers_returns_recent_tasks(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    older = _add_task(db_session, link, "completed")
    newer = TransferTask(
        id="task_newer",
        resource_id=link.resource_id,
        link_id=link.id,
        status="downloading",
        mode="copy",
        target_type="local",
        target_path="Movies/Newer.mkv",
        total_bytes=10,
        done_bytes=5,
    )
    db_session.add(newer)
    db_session.commit()
    db_session.execute(text("update transfer_tasks set updated_at = '2026-05-07 00:00:01' where id = :id"), {"id": older.id})
    db_session.execute(text("update transfer_tasks set updated_at = '2026-05-07 00:00:02' where id = 'task_newer'"))
    db_session.commit()

    response = client.get("/transfers")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body[:2]] == ["task_newer", older.id]
    assert body[0]["progress"] == 50
    assert body[0]["updated_at"] is not None


def test_create_transfer_rejects_missing_link(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/transfers", json={"link_id": "missing", "target_path": "Movies/Movie.mkv"})

    assert response.status_code == 404
    assert response.json()["detail"] == "资源链接不存在。"


def test_cancel_pending_transfer(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "pending")

    response = client.post(f"/transfers/{task.id}/cancel")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["error_code"] == "TASK_CANCELLED"
    db_session.refresh(task)
    assert task.status == "cancelled"
    log = db_session.query(TransferLog).one()
    assert log.event == "task_cancelled"
    assert log.data_json == {"previous_status": "pending"}


def test_cancel_running_transfer_cancels_active_files(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "downloading")
    db_session.add(
        TransferFile(
            id="file_cancel",
            task_id=task.id,
            cloud_path="/Sundarr/_staging/task/Movie.mkv",
            target_path="Movies/Movie.mkv",
            temp_path="Movies/Movie.mkv.sundarr.downloading",
            filename="Movie.mkv",
            size_bytes=10,
            done_bytes=4,
            status="downloading",
        )
    )
    db_session.commit()

    response = client.post(f"/transfers/{task.id}/cancel")

    assert response.status_code == 200
    db_session.refresh(task)
    transfer_file = db_session.get(TransferFile, "file_cancel")
    assert task.status == "cancelled"
    assert transfer_file.status == "cancelled"
    assert transfer_file.temp_path == "Movies/Movie.mkv.sundarr.downloading"


def test_cancel_completed_transfer_is_rejected(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "completed")

    response = client.post(f"/transfers/{task.id}/cancel")

    assert response.status_code == 409
    assert response.json()["detail"] == "当前任务状态不允许取消。"
    db_session.refresh(task)
    assert task.status == "completed"


def test_cancel_failed_transfer_is_rejected(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "failed")

    response = client.post(f"/transfers/{task.id}/cancel")

    assert response.status_code == 409
    assert response.json()["detail"] == "当前任务状态不允许取消。"
    db_session.refresh(task)
    assert task.status == "failed"


def test_cancel_missing_transfer_returns_404(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/transfers/missing/cancel")

    assert response.status_code == 404
    assert response.json()["detail"] == "搬运任务不存在。"


def test_retry_failed_retryable_transfer(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "failed")
    task.error_code = "STORAGE_CONFIG_CHANGED"
    task.error_message = "旧存储配置已变更。"
    task.retryable = True
    task.retry_count = 2
    task.done_bytes = 4
    task.storage_config_snapshot = {"host": "old.example.invalid"}
    db_session.add(
        TransferFile(
            id="file_retry",
            task_id=task.id,
            cloud_path="/Sundarr/_staging/task/Movie.mkv",
            target_path="Movies/Movie.mkv",
            temp_path="Movies/Movie.mkv.sundarr.downloading",
            filename="Movie.mkv",
            size_bytes=10,
            done_bytes=4,
            status="failed",
            error_code="STORAGE_WRITE_FAILED",
            error_message="写入失败。",
        )
    )
    db_session.commit()

    response = client.post(f"/transfers/{task.id}/retry")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["error_code"] is None
    assert body["error_message"] is None
    assert body["retryable"] is None
    assert body["retry_count"] == 3
    db_session.refresh(task)
    transfer_file = db_session.get(TransferFile, "file_retry")
    assert task.done_bytes == 4
    assert task.storage_config_snapshot is None
    assert transfer_file.temp_path == "Movies/Movie.mkv.sundarr.downloading"
    assert transfer_file.status == "failed"
    log = db_session.query(TransferLog).order_by(TransferLog.created_at.desc()).first()
    assert log.event == "task_retried"
    assert log.data_json == {"previous_error_code": "STORAGE_CONFIG_CHANGED", "retry_count": 3}


def test_retry_failed_non_retryable_transfer_is_rejected(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "failed")
    task.retryable = False
    db_session.commit()

    response = client.post(f"/transfers/{task.id}/retry")

    assert response.status_code == 409
    assert response.json()["detail"] == "当前任务状态不允许重试。"
    db_session.refresh(task)
    assert task.status == "failed"


def test_retry_non_failed_transfer_is_rejected(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "pending")
    task.retryable = True
    db_session.commit()

    response = client.post(f"/transfers/{task.id}/retry")

    assert response.status_code == 409
    assert response.json()["detail"] == "当前任务状态不允许重试。"
    db_session.refresh(task)
    assert task.status == "pending"


def test_retry_missing_transfer_returns_404(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/transfers/missing/retry")

    assert response.status_code == 404
    assert response.json()["detail"] == "搬运任务不存在。"


def test_list_transfer_logs_returns_ordered_logs(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "failed")
    db_session.add_all(
        [
            TransferLog(
                id="log_2",
                task_id=task.id,
                level="error",
                event="transfer_failed",
                message="任务失败。",
                data_json={"error_code": "STORAGE_WRITE_FAILED"},
            ),
            TransferLog(
                id="log_1",
                task_id=task.id,
                level="info",
                event="worker_task_claimed",
                message="Worker 已领取任务。",
                data_json={"worker_concurrency": 2},
            ),
        ]
    )
    db_session.commit()
    db_session.execute(text("update transfer_logs set created_at = '2026-05-07 00:00:02' where id = 'log_2'"))
    db_session.execute(text("update transfer_logs set created_at = '2026-05-07 00:00:01' where id = 'log_1'"))
    db_session.commit()

    response = client.get(f"/transfers/{task.id}/logs")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == ["log_1", "log_2"]
    assert body[0]["event"] == "worker_task_claimed"
    assert body[1]["data"] == {"error_code": "STORAGE_WRITE_FAILED"}
    assert "created_at" in body[0]


def test_list_transfer_logs_sanitizes_sensitive_data(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "failed")
    db_session.add(
        TransferLog(
            id="log_sensitive",
            task_id=task.id,
            level="warning",
            event="storage_config_changed",
            message="配置已变更。",
            data_json={
                "host": "nas.example.invalid",
                "password": "secret",
                "nested": {"token": "hidden", "safe": "visible"},
                "items": [{"cookie": "hidden", "name": "visible"}],
            },
        )
    )
    db_session.commit()

    response = client.get(f"/transfers/{task.id}/logs")

    assert response.status_code == 200
    data = response.json()[0]["data"]
    assert data == {"host": "nas.example.invalid", "nested": {"safe": "visible"}, "items": [{"name": "visible"}]}


def test_list_transfer_logs_missing_transfer_returns_404(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/transfers/missing/logs")

    assert response.status_code == 404
    assert response.json()["detail"] == "搬运任务不存在。"


def test_clear_completed_removes_completed_and_cancelled_transfers(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    completed = _add_task(db_session, link, "completed")
    cancelled = _add_task(db_session, link, "cancelled")
    failed = _add_task(db_session, link, "failed")
    running = _add_task(db_session, link, "downloading")
    db_session.add_all(
        [
            TransferFile(
                id="file_completed",
                task_id=completed.id,
                cloud_path="/Sundarr/_staging/completed/Movie.mkv",
                target_path="Movies/Completed.mkv",
                temp_path="Movies/Completed.mkv.sundarr.downloading",
                filename="Completed.mkv",
                size_bytes=1,
                status="completed",
            ),
            TransferLog(id="log_cancelled", task_id=cancelled.id, level="info", event="task_cancelled"),
        ]
    )
    db_session.commit()

    response = client.post("/transfers/clear-completed")

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    assert db_session.get(TransferTask, completed.id) is None
    assert db_session.get(TransferTask, cancelled.id) is None
    assert db_session.get(TransferTask, failed.id) is not None
    assert db_session.get(TransferTask, running.id) is not None
    assert db_session.get(TransferFile, "file_completed") is None
    assert db_session.get(TransferLog, "log_cancelled") is None


def _add_task(db_session: Session, link: ResourceLink, status: str) -> TransferTask:
    task = TransferTask(
        id=f"task_{status}",
        resource_id=link.resource_id,
        link_id=link.id,
        status=status,
        mode="copy",
        target_type="local",
        target_path="Movies/Movie.mkv",
        cloud_staging_path="/Sundarr/_staging/task",
    )
    db_session.add(task)
    db_session.commit()
    return task



def test_pause_running_transfer(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "downloading")
    task.done_bytes = 42
    task.speed_bytes_per_sec = 1024
    db_session.commit()

    response = client.post(f"/transfers/{task.id}/pause")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["speed_bytes_per_sec"] == 0
    db_session.refresh(task)
    assert task.status == "paused"
    assert task.done_bytes == 42
    log = db_session.query(TransferLog).order_by(TransferLog.created_at.desc()).first()
    assert log.event == "task_paused"
    assert log.data_json == {"previous_status": "downloading", "done_bytes": 42}


def test_pause_completed_transfer_rejected(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "completed")

    response = client.post(f"/transfers/{task.id}/pause")

    assert response.status_code == 409
    assert response.json()["detail"] == "当前任务状态不允许暂停。"


def test_resume_paused_transfer(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "paused")
    task.done_bytes = 7
    db_session.commit()

    response = client.post(f"/transfers/{task.id}/resume")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["done_bytes"] == 7
    db_session.refresh(task)
    assert task.status == "pending"
    log = db_session.query(TransferLog).order_by(TransferLog.created_at.desc()).first()
    assert log.event == "task_resumed"
    assert log.data_json == {"done_bytes": 7}


def test_resume_non_paused_transfer_rejected(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "downloading")

    response = client.post(f"/transfers/{task.id}/resume")

    assert response.status_code == 409
    assert response.json()["detail"] == "当前任务未处于暂停状态。"


def test_transfer_response_exposes_speed(db_session: Session) -> None:
    client = make_client(db_session)
    link = seed_link(db_session)
    task = _add_task(db_session, link, "downloading")
    task.speed_bytes_per_sec = 2048
    db_session.commit()

    response = client.get(f"/transfers/{task.id}")

    assert response.status_code == 200
    assert response.json()["speed_bytes_per_sec"] == 2048
