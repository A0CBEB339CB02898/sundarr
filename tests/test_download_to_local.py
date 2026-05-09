from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import DownloadToLocalBinding, DownloadToLocalSeenFile, MediaLibrary, SmbConnection, TransferTask


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
            "share": "media",
            "username": "user",
            "password": "secret",
            "base_path": "/",
        },
    ).json()


def _create_media_library(
    client: TestClient,
    library_id: str = "lib_movie",
    connection_id: str = "conn_1",
    media_type: str = "movie",
    base_path: str = "Movies",
) -> dict:
    return client.post(
        "/media-libraries/create",
        json={
            "id": library_id,
            "name": media_type,
            "media_type": media_type,
            "connection_id": connection_id,
            "base_path": base_path,
        },
    ).json()


def _create_binding(
    client: TestClient,
    binding_id: str = "binding_1",
    source_connection_id: str = "conn_1",
    target_library_id: str = "lib_movie",
) -> dict:
    return client.post(
        "/download-to-local/bindings/create",
        json={
            "id": binding_id,
            "name": "电影下载",
            "media_type": "movie",
            "source_connection_id": source_connection_id,
            "source_path": "CloudMovie",
            "target_library_id": target_library_id,
        },
    ).json()


def test_create_binding(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)

    response = client.post(
        "/download-to-local/bindings/create",
        json={
            "id": "binding_1",
            "name": "电影下载",
            "media_type": "movie",
            "source_connection_id": "conn_1",
            "source_path": "CloudMovie",
            "target_library_id": "lib_movie",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "binding_1"
    assert body["media_type"] == "movie"
    assert body["source_connection_id"] == "conn_1"
    assert body["source_path"] == "CloudMovie"
    assert body["target_library_id"] == "lib_movie"


def test_create_binding_duplicate(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    response = client.post(
        "/download-to-local/bindings/create",
        json={
            "id": "binding_1",
            "name": "重复",
            "media_type": "movie",
            "source_connection_id": "conn_1",
            "source_path": "CloudMovie",
            "target_library_id": "lib_movie",
        },
    )

    assert response.status_code == 409


def test_create_binding_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)

    response = client.post(
        "/download-to-local/bindings/create",
        json={
            "id": "binding_1",
            "name": "电影下载",
            "media_type": "movie",
            "source_connection_id": "nonexistent",
            "source_path": "CloudMovie",
            "target_library_id": "lib_movie",
        },
    )

    assert response.status_code == 404
    assert "SMB 连接不存在" in response.json()["detail"]


def test_create_binding_library_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    response = client.post(
        "/download-to-local/bindings/create",
        json={
            "id": "binding_1",
            "name": "电影下载",
            "media_type": "movie",
            "source_connection_id": "conn_1",
            "source_path": "CloudMovie",
            "target_library_id": "nonexistent",
        },
    )

    assert response.status_code == 404
    assert "媒体库不存在" in response.json()["detail"]


def test_create_binding_rejects_unsafe_path(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)

    response = client.post(
        "/download-to-local/bindings/create",
        json={
            "id": "binding_1",
            "name": "电影下载",
            "media_type": "movie",
            "source_connection_id": "conn_1",
            "source_path": "../bad",
            "target_library_id": "lib_movie",
        },
    )

    assert response.status_code == 422


def test_list_bindings(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie", media_type="movie")
    _create_media_library(client, "lib_series", media_type="series")
    _create_binding(client, "binding_1", target_library_id="lib_movie")
    _create_binding(client, "binding_2", target_library_id="lib_series")

    response = client.get("/download-to-local/bindings")

    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_get_binding(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    response = client.get("/download-to-local/bindings/binding_1")

    assert response.status_code == 200
    assert response.json()["id"] == "binding_1"


def test_get_binding_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/download-to-local/bindings/nonexistent")

    assert response.status_code == 404


def test_update_binding(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    response = client.post(
        "/download-to-local/bindings/binding_1/update",
        json={
            "name": "更新后的绑定",
            "media_type": "movie",
            "source_connection_id": "conn_1",
            "source_path": "NewCloudMovie",
            "target_library_id": "lib_movie",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "更新后的绑定"
    assert response.json()["source_path"] == "NewCloudMovie"


def test_update_binding_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)

    response = client.post(
        "/download-to-local/bindings/nonexistent/update",
        json={
            "name": "更新",
            "media_type": "movie",
            "source_connection_id": "conn_1",
            "source_path": "CloudMovie",
            "target_library_id": "lib_movie",
        },
    )

    assert response.status_code == 404


def test_enable_disable_binding(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    response = client.post("/download-to-local/bindings/binding_1/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    response = client.post("/download-to-local/bindings/binding_1/enable")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_test_binding_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/download-to-local/bindings/nonexistent/test")

    assert response.status_code == 404


def test_test_binding_returns_result(db_session: Session, monkeypatch) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    async def mock_list_dir(self, path=""):
        return []

    monkeypatch.setattr("sundarr.app.services.download_to_local_service.SmbWriter.list_dir", mock_list_dir)
    monkeypatch.setattr("sundarr.app.services.download_to_local_service.SmbWriter.test_connection", mock_list_dir)

    response = client.post("/download-to-local/bindings/binding_1/test")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["source_ok"] is True
    assert response.json()["target_ok"] is True


def test_get_config_default(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/download-to-local/config")

    assert response.status_code == 200
    assert response.json()["delete_source_after_success"] is True
    assert response.json()["stable_seconds"] == 120


def test_save_config(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/download-to-local/config/save",
        json={
            "delete_source_after_success": False,
            "delete_empty_source_dirs": True,
            "scan_interval_seconds": 30,
            "stable_seconds": 60,
            "unclassified_library_id": "lib_unc",
        },
    )

    assert response.status_code == 200
    assert response.json()["delete_source_after_success"] is False
    assert response.json()["stable_seconds"] == 60
    assert response.json()["unclassified_library_id"] == "lib_unc"


def test_scan_binding_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/download-to-local/scan",
        json={"binding_id": "nonexistent"},
    )

    assert response.status_code == 404


def test_scan_returns_results(db_session: Session, monkeypatch) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    async def mock_list_source_dir(self, db, binding, path):
        return [
            {"name": "movie1.mkv", "path": "CloudMovie/movie1.mkv", "is_dir": False, "size": 1024, "modified_at": "123"},
        ]

    monkeypatch.setattr(
        "sundarr.app.services.download_to_local_service.DownloadToLocalService._list_source_dir",
        mock_list_source_dir,
    )

    response = client.post("/download-to-local/scan", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["scanned_bindings"] == 1
    assert body["discovered_count"] == 1


def test_list_discovered(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/download-to-local/discovered")

    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_create_tasks_binding_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/download-to-local/tasks/create",
        json={"binding_id": "nonexistent"},
    )

    assert response.status_code == 404


def test_create_tasks_creates_from_stable_seen_files(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    db_session.add(
        DownloadToLocalSeenFile(
            id="seen_1",
            binding_id="binding_1",
            source_fingerprint="conn_1|CloudMovie|CloudMovie/movie1.mkv",
            source_path="CloudMovie/movie1.mkv",
            source_size=1024,
            source_mtime="123",
            status="stable",
        )
    )
    db_session.commit()

    response = client.post("/download-to-local/tasks/create", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 1
    assert body["skipped_count"] == 0
    assert len(body["tasks"]) == 1
    assert body["tasks"][0]["mode"] == "download_to_local"

    seen = db_session.get(DownloadToLocalSeenFile, "seen_1")
    assert seen is not None
    assert seen.status == "queued"
    assert seen.task_id is not None


def test_create_tasks_skips_non_stable(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    db_session.add(
        DownloadToLocalSeenFile(
            id="seen_1",
            binding_id="binding_1",
            source_fingerprint="conn_1|CloudMovie|CloudMovie/movie1.mkv",
            source_path="CloudMovie/movie1.mkv",
            source_size=1024,
            source_mtime="123",
            status="discovered",
        )
    )
    db_session.commit()

    response = client.post("/download-to-local/tasks/create", json={})

    assert response.status_code == 200
    assert response.json()["created_count"] == 0


def test_create_tasks_skips_already_queued(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)
    _create_binding(client, "binding_1")

    db_session.add(
        DownloadToLocalSeenFile(
            id="seen_1",
            binding_id="binding_1",
            source_fingerprint="conn_1|CloudMovie|CloudMovie/movie1.mkv",
            source_path="CloudMovie/movie1.mkv",
            source_size=1024,
            source_mtime="123",
            status="stable",
            task_id="existing_task",
        )
    )
    db_session.commit()

    response = client.post("/download-to-local/tasks/create", json={})

    assert response.status_code == 200
    assert response.json()["created_count"] == 0


def test_create_tasks_skips_missing_binding(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client)

    db_session.add(
        DownloadToLocalSeenFile(
            id="seen_1",
            binding_id="nonexistent",
            source_fingerprint="conn_1|CloudMovie|CloudMovie/movie1.mkv",
            source_path="CloudMovie/movie1.mkv",
            source_size=1024,
            source_mtime="123",
            status="stable",
        )
    )
    db_session.commit()

    response = client.post("/download-to-local/tasks/create", json={})

    assert response.status_code == 200
    assert response.json()["created_count"] == 0
    assert response.json()["skipped_count"] == 1

    seen = db_session.get(DownloadToLocalSeenFile, "seen_1")
    assert seen is not None
    assert seen.status == "failed"
