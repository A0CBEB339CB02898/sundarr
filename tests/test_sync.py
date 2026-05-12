from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import MediaLibrary, RemoteMediaLibrary, SmbConnection, SyncBinding, SyncSeenFile, TransferTask
from sundarr.app.schemas.sync import SyncTaskCreateRequest
from sundarr.app.services.sync_service import sync_service


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


def _create_local_library_with_type(client: TestClient, library_id: str, media_type: str, base_path: str) -> dict:
    return client.post(
        "/media-libraries/create",
        json={"id": library_id, "name": library_id, "media_type": media_type, "connection_id": "conn_1", "base_path": base_path},
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


def test_create_sync_binding_rejects_media_type_mismatch(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_local_library_with_type(client, "lib_series", "series", "Series")
    _create_remote_library(client)

    response = client.post(
        "/sync/bindings/create",
        json={
            "id": "sync_bad",
            "name": "错误绑定",
            "media_type": "movie",
            "remote_library_id": "rml_remote",
            "local_library_id": "lib_series",
        },
    )

    assert response.status_code == 400
    assert "类型不一致" in response.json()["detail"]


@pytest.mark.anyio
async def test_sync_scan_uses_binding_and_flattens_remote_base_path(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_local_library_with_type(client, "lib_movie", "movie", "Movies")
    _create_remote_library(client)
    client.post(
        "/sync/bindings/create",
        json={"id": "sync_movie", "name": "电影同步", "media_type": "movie", "remote_library_id": "rml_remote", "local_library_id": "lib_movie"},
    )

    async def list_dir(_connection_id: str, path: str) -> list[dict]:
        assert path == "CloudMovie"
        return [
            {"path": "CloudMovie/Movie.mkv", "is_dir": False, "size": 4, "modified_at": "100"},
            {"path": "CloudMovie/Tmp.mkv.sundarr.downloading", "is_dir": False, "size": 4, "modified_at": "100"},
        ]

    sync_service._list_dir_override = list_dir
    try:
        response = client.post("/sync/scan", json={"binding_id": "sync_movie"})
        assert response.status_code == 200
        assert response.json()["discovered_count"] == 1
        seen = db_session.query(SyncSeenFile).one()
        seen.updated_at = datetime.now(timezone.utc) - timedelta(seconds=180)
        db_session.commit()

        response = client.post("/sync/scan", json={"binding_id": "sync_movie"})
        assert response.status_code == 200
        assert response.json()["stable_count"] == 1

        response = await sync_service.create_tasks(db_session, SyncTaskCreateRequest(binding_id="sync_movie"))
        assert response.created_count == 1
    finally:
        sync_service._list_dir_override = None

    tasks = db_session.query(TransferTask).all()
    assert len(tasks) == 1
    assert tasks[0].target_path == "Movies/Movie.mkv"


@pytest.mark.anyio
async def test_create_sync_tasks_marks_existing_same_md5_completed(db_session: Session, monkeypatch) -> None:
    db_session.add_all(
        [
            SmbConnection(id="conn_source", name="来源", host="nas.example.invalid", share="source", username="user", password=None, base_path="/"),
            SmbConnection(id="conn_target", name="目标", host="nas.example.invalid", share="target", username="user", password=None, base_path="/"),
            RemoteMediaLibrary(id="rml_remote", name="远程电影", media_type="movie", connection_id="conn_source", base_path="CloudMovie"),
            MediaLibrary(id="lib_movie", name="本地电影", media_type="movie", connection_id="conn_target", base_path="Movies"),
            SyncBinding(id="sync_movie", name="电影同步", media_type="movie", remote_library_id="rml_remote", local_library_id="lib_movie"),
            SyncSeenFile(
                id="seen_movie",
                binding_id="sync_movie",
                source_fingerprint="sync_movie|rml_remote|CloudMovie/Movie.mkv",
                source_path="CloudMovie/Movie.mkv",
                source_size=4,
                source_mtime="100",
                status="stable",
            ),
        ]
    )
    db_session.commit()

    class FakeWriter:
        files = {
            "source": {"CloudMovie/Movie.mkv": b"same"},
            "target": {"Movies/Movie.mkv": b"same"},
        }

        def __init__(self, config) -> None:
            self.share = config.share

        async def exists(self, path: str) -> bool:
            return path in self.files[self.share]

        async def size(self, path: str) -> int:
            return len(self.files[self.share][path])

        async def checksum_md5(self, path: str) -> str:
            import hashlib

            return hashlib.md5(self.files[self.share][path], usedforsecurity=False).hexdigest()

    monkeypatch.setattr("sundarr.app.services.sync_service.SmbWriter", FakeWriter)

    response = await sync_service.create_tasks(db_session, type("Request", (), {"binding_id": "sync_movie"})())

    assert response.created_count == 0
    assert response.skipped_count == 1
    assert db_session.query(TransferTask).count() == 0
    assert db_session.get(SyncSeenFile, "seen_movie").status == "completed"


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
    _create_local_library_with_type(client, "lib_series", "series", "Series")
    client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_series", "name": "远程剧集", "media_type": "series", "connection_id": "conn_1", "base_path": "CloudSeries"},
    )

    client.post(
        "/sync/bindings/create",
        json={"id": "sync_1", "name": "同步1", "media_type": "movie", "remote_library_id": "rml_remote", "local_library_id": "lib_local"},
    )
    client.post(
        "/sync/bindings/create",
        json={"id": "sync_2", "name": "同步2", "media_type": "series", "remote_library_id": "rml_series", "local_library_id": "lib_series"},
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
