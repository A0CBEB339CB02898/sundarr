from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import Setting, TransferLog, TransferTask
from sundarr.app.services.storage_config_service import STORAGE_CONFIG_KEY


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_save_storage_config_redacts_password(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/storage/config/save",
        json={
            "host": "fnos.local",
            "share": "media",
            "username": "sundarr",
            "password": "secret",
            "base_path": "/",
            "libraries": {"movies": "Movies"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "password" not in body
    assert body["password_set"] is True

    setting = db_session.get(Setting, STORAGE_CONFIG_KEY)
    assert setting is not None
    assert setting.is_sensitive is True
    assert setting.value_json["password"] == "secret"


def test_save_storage_config_empty_password_keeps_old_value(db_session: Session) -> None:
    client = make_client(db_session)
    client.post(
        "/storage/config/save",
        json={"host": "old.local", "share": "media", "username": "user", "password": "secret"},
    )

    response = client.post(
        "/storage/config/save",
        json={"host": "new.local", "share": "media", "username": "user", "password": ""},
    )

    assert response.status_code == 200
    assert response.json()["host"] == "new.local"
    setting = db_session.get(Setting, STORAGE_CONFIG_KEY)
    assert setting is not None
    assert setting.value_json["password"] == "secret"


def test_get_storage_config_returns_empty_default(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/storage/config")

    assert response.status_code == 200
    assert response.json()["password_set"] is False


def test_storage_config_test_rejects_bad_path(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/storage/config/test",
        json={"host": "fnos.local", "share": "media", "username": "user", "base_path": "../bad"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error_code"] == "SMB_PATH_INVALID"


def test_save_storage_config_interrupts_running_smb_tasks(db_session: Session) -> None:
    client = make_client(db_session)
    client.post(
        "/storage/config/save",
        json={"host": "old.local", "share": "media", "username": "user", "password": "secret"},
    )
    db_session.add(
        TransferTask(
            id="task_running",
            link_id="link_1",
            status="downloading",
            mode="copy",
            target_type="smb",
            target_path="Movies/Movie.mkv",
            storage_config_snapshot={"host": "old.local"},
        )
    )
    db_session.add(
        TransferTask(
            id="task_completed",
            link_id="link_2",
            status="completed",
            mode="copy",
            target_type="smb",
            target_path="Movies/Done.mkv",
            storage_config_snapshot={"host": "old.local"},
        )
    )
    db_session.commit()

    response = client.post(
        "/storage/config/save",
        json={"host": "new.local", "share": "media", "username": "user", "password": "secret"},
    )

    assert response.status_code == 200
    running_task = db_session.get(TransferTask, "task_running")
    assert running_task is not None
    assert running_task.status == "failed"
    assert running_task.error_code == "STORAGE_CONFIG_CHANGED"
    assert running_task.retryable is True

    completed_task = db_session.get(TransferTask, "task_completed")
    assert completed_task is not None
    assert completed_task.status == "completed"

    logs = db_session.query(TransferLog).filter(TransferLog.task_id == "task_running").all()
    assert len(logs) == 1
    assert logs[0].event == "storage_config_changed"
