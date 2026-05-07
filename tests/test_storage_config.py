from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import Setting, TransferLog, TransferTask
from sundarr.app.services.storage_config_service import STORAGE_CONFIG_KEY
from sundarr.app.storage.smb import SmbStorageError


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
            "host": "nas.example.invalid",
            "share": "share",
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
        json={"host": "old.example.invalid", "share": "share", "username": "user", "password": "secret"},
    )

    response = client.post(
        "/storage/config/save",
        json={"host": "new.example.invalid", "share": "share", "username": "user", "password": ""},
    )

    assert response.status_code == 200
    assert response.json()["host"] == "new.example.invalid"
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
        json={"host": "nas.example.invalid", "share": "share", "username": "user", "base_path": "../bad"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error_code"] == "SMB_PATH_INVALID"


def test_storage_config_test_returns_specific_smb_error(db_session: Session, monkeypatch) -> None:
    client = make_client(db_session)

    async def fail_connection(self):
        raise SmbStorageError("SMB_HOST_UNREACHABLE", "无法连接 SMB 主机或端口。目标：nas.example.invalid:445。")

    monkeypatch.setattr("sundarr.app.services.storage_config_service.SmbWriter.test_connection", fail_connection)

    response = client.post(
        "/storage/config/test",
        json={"host": "nas.example.invalid", "share": "share", "username": "user", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error_code"] == "SMB_HOST_UNREACHABLE"
    assert "nas.example.invalid:445" in response.json()["error_message"]


def test_save_storage_config_interrupts_running_smb_tasks(db_session: Session) -> None:
    client = make_client(db_session)
    client.post(
        "/storage/config/save",
        json={"host": "old.example.invalid", "share": "share", "username": "user", "password": "secret"},
    )
    db_session.add(
        TransferTask(
            id="task_running",
            link_id="link_1",
            status="downloading",
            mode="copy",
            target_type="smb",
            target_path="Movies/Movie.mkv",
            storage_config_snapshot={"host": "old.example.invalid"},
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
            storage_config_snapshot={"host": "old.example.invalid"},
        )
    )
    db_session.commit()

    response = client.post(
        "/storage/config/save",
        json={"host": "new.example.invalid", "share": "share", "username": "user", "password": "secret"},
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


def test_storage_browse_requires_config(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/storage/browse", params={"path": "Movies"})

    assert response.status_code == 404
    assert response.json()["detail"] == "存储配置不存在。"


def test_storage_browse_rejects_path_outside_root(db_session: Session) -> None:
    client = make_client(db_session)
    client.post(
        "/storage/config/save",
        json={"host": "nas.example.invalid", "share": "share", "username": "user", "password": "secret"},
    )

    response = client.get("/storage/browse", params={"path": "../outside"})

    assert response.status_code == 400
    assert response.json()["detail"] == "SMB 路径超出允许范围。"
