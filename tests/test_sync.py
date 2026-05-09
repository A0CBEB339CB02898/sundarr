from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import MediaLibrary, RemoteMediaLibrary, SmbConnection, SyncBinding, SyncSeenFile


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _create_smb_connection(client: TestClient, connection_id: str = "conn_1") -> dict:
    return client.post(
        "/storage/smb-connections/create",
        json={"id": connection_id, "name": "测试连接", "host": "nas.example.invalid", "share": "media", "username": "user", "password": "secret", "base_path": "/"},
    ).json()


def _create_local_library(client: TestClient, library_id: str = "lib_local") -> dict:
    return client.post(
        "/media-libraries/create",
        json={"id": library_id, "name": "本地媒体库", "media_type": "movie", "connection_id": "conn_1", "base_path": "Movies"},
    ).json()


def _create_remote_library(client: TestClient, library_id: str = "rml_remote") -> dict:
    return client.post(
        "/remote-media-libraries/create",
        json={"id": library_id, "name": "远程媒体库", "media_type": "movie", "connection_id": "conn_1", "base_path": "CloudMovie"},
    ).json()


def test_create_sync_binding(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_local_library(client)
    _create_remote_library(client)

    response = client.post(
        "/sync/bindings/create",
        json={
            "id": "sync_1",
            "name": "同步绑定",
            "media_type": "movie",
            "remote_library_id": "rml_remote",
            "local_library_id": "lib_local",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "sync_1"
    assert body["remote_library_id"] == "rml_remote"
    assert body["local_library_id"] == "lib_local"


def test_create_sync_binding_duplicate(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_local_library(client)
    _create_remote_library(client)

    client.post(
        "/sync/bindings/create",
        json={"id": "sync_1", "name": "同步", "media_type": "movie", "remote_library_id": "rml_remote", "local_library_id": "lib_local"},
    )

    response = client.post(
        "/sync/bindings/create",
        json={"id": "sync_1", "name": "重复", "media_type": "movie", "remote_library_id": "rml_remote", "local_library_id": "lib_local"},
    )

    assert response.status_code == 409


def test_create_sync_binding_remote_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_local_library(client)

    response = client.post(
        "/sync/bindings/create",
        json={"id": "sync_1", "name": "同步", "media_type": "movie", "remote_library_id": "nonexistent", "local_library_id": "lib_local"},
    )

    assert response.status_code == 404


def test_create_sync_binding_local_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_remote_library(client)

    response = client.post(
        "/sync/bindings/create",
        json={"id": "sync_1", "name": "同步", "media_type": "movie", "remote_library_id": "rml_remote", "local_library_id": "nonexistent"},
    )

    assert response.status_code == 404


def test_list_sync_bindings(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_local_library(client)
    _create_remote_library(client)

    client.post(
        "/sync/bindings/create",
        json={"id": "sync_1", "name": "同步1", "media_type": "movie", "remote_library_id": "rml_remote", "local_library_id": "lib_local"},
    )
    client.post(
        "/sync/bindings/create",
        json={"id": "sync_2", "name": "同步2", "media_type": "series", "remote_library_id": "rml_remote", "local_library_id": "lib_local"},
    )

    response = client.get("/sync/bindings")

    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_enable_disable_sync_binding(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_local_library(client)
    _create_remote_library(client)

    client.post(
        "/sync/bindings/create",
        json={"id": "sync_1", "name": "同步", "media_type": "movie", "remote_library_id": "rml_remote", "local_library_id": "lib_local"},
    )

    response = client.post("/sync/bindings/sync_1/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    response = client.post("/sync/bindings/sync_1/enable")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_get_sync_config_default(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/sync/config")

    assert response.status_code == 200
    assert response.json()["delete_source_after_success"] is True
    assert response.json()["stable_seconds"] == 120


def test_save_sync_config(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/sync/config/save",
        json={
            "delete_source_after_success": False,
            "delete_empty_source_dirs": True,
            "scan_interval_seconds": 30,
            "stable_seconds": 60,
            "unclassified_library_id": "lib_unc",
        },
    )

    assert response.status_code == 200
    assert response.json()["stable_seconds"] == 60


def test_list_sync_discovered(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/sync/discovered")

    assert response.status_code == 200
    assert response.json()["count"] == 0
