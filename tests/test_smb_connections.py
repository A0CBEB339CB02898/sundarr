from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import MediaLibrary, SmbConnection
from sundarr.app.storage.smb import SmbStorageError


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _create_smb_connection(client: TestClient, connection_id: str = "conn_1") -> dict:
    return client.post(
        "/storage/smb-connections/create",
        json={
            "id": connection_id,
            "name": "测试连接",
            "host": "nas.example.invalid",
            "port": 445,
            "share": "media",
            "username": "user",
            "password": "secret",
            "base_path": "/",
        },
    ).json()


def test_create_smb_connection(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/storage/smb-connections/create",
        json={
            "id": "conn_1",
            "name": "测试连接",
            "host": "nas.example.invalid",
            "share": "media",
            "username": "user",
            "password": "secret",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "conn_1"
    assert body["name"] == "测试连接"
    assert body["host"] == "nas.example.invalid"
    assert body["password_set"] is True
    assert "password" not in body


def test_create_smb_connection_duplicate(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    response = client.post(
        "/storage/smb-connections/create",
        json={
            "id": "conn_1",
            "name": "重复连接",
            "host": "nas2.example.invalid",
            "share": "media",
            "username": "user",
        },
    )

    assert response.status_code == 409
    assert "已存在" in response.json()["detail"]


def test_list_smb_connections(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")
    _create_smb_connection(client, "conn_2")

    response = client.get("/storage/smb-connections")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["results"][0]["id"] == "conn_1"
    assert body["results"][1]["id"] == "conn_2"


def test_get_smb_connection(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    response = client.get("/storage/smb-connections/conn_1")

    assert response.status_code == 200
    assert response.json()["id"] == "conn_1"
    assert response.json()["password_set"] is True


def test_get_smb_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/storage/smb-connections/nonexistent")

    assert response.status_code == 404


def test_update_smb_connection(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    response = client.post(
        "/storage/smb-connections/conn_1/update",
        json={
            "name": "更新后的连接",
            "host": "new.example.invalid",
            "share": "media",
            "username": "user",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "更新后的连接"
    assert response.json()["host"] == "new.example.invalid"
    assert response.json()["password_set"] is True


def test_update_smb_connection_empty_password_keeps_old(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    response = client.post(
        "/storage/smb-connections/conn_1/update",
        json={
            "name": "更新后的连接",
            "host": "new.example.invalid",
            "share": "media",
            "username": "user",
            "password": "",
        },
    )

    assert response.status_code == 200
    conn = db_session.get(SmbConnection, "conn_1")
    assert conn is not None
    assert conn.password == "secret"


def test_update_smb_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/storage/smb-connections/nonexistent/update",
        json={
            "name": "更新",
            "host": "nas.example.invalid",
            "share": "media",
            "username": "user",
        },
    )

    assert response.status_code == 404


def test_enable_disable_smb_connection(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    response = client.post("/storage/smb-connections/conn_1/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    response = client.post("/storage/smb-connections/conn_1/enable")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_test_smb_connection_rejects_bad_path(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/storage/smb-connections/create",
        json={
            "id": "conn_bad",
            "name": "坏路径",
            "host": "nas.example.invalid",
            "share": "media",
            "username": "user",
            "base_path": "../bad",
        },
    )

    assert response.status_code == 422


def test_test_smb_connection_returns_specific_error(db_session: Session, monkeypatch) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    async def fail_test(self):
        raise SmbStorageError("SMB_HOST_UNREACHABLE", "无法连接 SMB 主机或端口。")

    monkeypatch.setattr("sundarr.app.services.smb_connection_service.SmbWriter.test_connection", fail_test)

    response = client.post("/storage/smb-connections/conn_1/test")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error_code"] == "SMB_HOST_UNREACHABLE"


def test_browse_smb_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/storage/smb-connections/nonexistent/browse", params={"path": "Movies"})

    assert response.status_code == 404


def test_browse_smb_connection_rejects_path_outside_root(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    response = client.get("/storage/smb-connections/conn_1/browse", params={"path": "../outside"})

    assert response.status_code == 400


def test_update_smb_connection_interrupts_running_tasks(db_session: Session) -> None:
    from sundarr.app.models import TransferLog, TransferTask

    client = make_client(db_session)
    _create_smb_connection(client, "conn_1")

    db_session.add(
        TransferTask(
            id="task_running",
            link_id="link_1",
            status="downloading",
            mode="copy",
            target_type="smb",
            target_path="Movies/Movie.mkv",
            source_config_snapshot={"connection_id": "conn_1", "host": "nas.example.invalid"},
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
            source_config_snapshot={"connection_id": "conn_1", "host": "nas.example.invalid"},
        )
    )
    db_session.commit()

    response = client.post(
        "/storage/smb-connections/conn_1/update",
        json={
            "name": "更新后的连接",
            "host": "new.example.invalid",
            "share": "media",
            "username": "user",
        },
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
