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


def _create_media_library(
    client: TestClient,
    library_id: str = "lib_movie",
    connection_id: str = "conn_1",
    media_type: str = "movie",
) -> dict:
    return client.post(
        "/media-libraries/create",
        json={
            "id": library_id,
            "name": "电影",
            "media_type": media_type,
            "connection_id": connection_id,
            "base_path": "Movies",
        },
    ).json()


def test_create_media_library(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    response = client.post(
        "/media-libraries/create",
        json={
            "id": "lib_movie",
            "name": "电影",
            "media_type": "movie",
            "connection_id": "conn_1",
            "base_path": "Movies",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "lib_movie"
    assert body["name"] == "电影"
    assert body["media_type"] == "movie"
    assert body["connection_id"] == "conn_1"
    assert body["base_path"] == "/Movies"
    assert body["enabled"] is True


def test_create_media_library_duplicate(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie")

    response = client.post(
        "/media-libraries/create",
        json={
            "id": "lib_movie",
            "name": "重复",
            "media_type": "movie",
            "connection_id": "conn_1",
            "base_path": "Movies",
        },
    )

    assert response.status_code == 409
    assert "已存在" in response.json()["detail"]


def test_create_media_library_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/media-libraries/create",
        json={
            "id": "lib_movie",
            "name": "电影",
            "media_type": "movie",
            "connection_id": "nonexistent",
            "base_path": "Movies",
        },
    )

    assert response.status_code == 404
    assert "SMB 连接不存在" in response.json()["detail"]


def test_create_media_library_rejects_unsafe_path(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    response = client.post(
        "/media-libraries/create",
        json={
            "id": "lib_bad",
            "name": "坏路径",
            "media_type": "movie",
            "connection_id": "conn_1",
            "base_path": "../bad",
        },
    )

    assert response.status_code == 422


def test_list_media_libraries(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie", media_type="movie")
    _create_media_library(client, "lib_series", media_type="series")

    response = client.get("/media-libraries")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["results"][0]["id"] == "lib_movie"
    assert body["results"][1]["id"] == "lib_series"


def test_get_media_library(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie")

    response = client.get("/media-libraries/lib_movie")

    assert response.status_code == 200
    assert response.json()["id"] == "lib_movie"


def test_get_media_library_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/media-libraries/nonexistent")

    assert response.status_code == 404


def test_update_media_library(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie")

    response = client.post(
        "/media-libraries/lib_movie/update",
        json={
            "name": "更新后的电影",
            "media_type": "movie",
            "connection_id": "conn_1",
            "base_path": "NewMovies",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "更新后的电影"
    assert response.json()["base_path"] == "/NewMovies"


def test_update_media_library_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie")

    response = client.post(
        "/media-libraries/lib_movie/update",
        json={
            "name": "更新",
            "media_type": "movie",
            "connection_id": "nonexistent",
            "base_path": "Movies",
        },
    )

    assert response.status_code == 404


def test_update_media_library_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    response = client.post(
        "/media-libraries/nonexistent/update",
        json={
            "name": "更新",
            "media_type": "movie",
            "connection_id": "conn_1",
            "base_path": "Movies",
        },
    )

    assert response.status_code == 404


def test_enable_disable_media_library(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie")

    response = client.post("/media-libraries/lib_movie/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    response = client.post("/media-libraries/lib_movie/enable")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_test_media_library_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/media-libraries/nonexistent/test")

    assert response.status_code == 404


def test_test_media_library_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie")

    conn = db_session.get(SmbConnection, "conn_1")
    assert conn is not None
    conn.id = "changed_id"
    db_session.commit()

    response = client.post("/media-libraries/lib_movie/test")

    assert response.status_code == 404


def test_test_media_library_returns_specific_error(db_session: Session, monkeypatch) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)
    _create_media_library(client, "lib_movie")

    async def fail_list_dir(self, path):
        raise SmbStorageError("SMB_HOST_UNREACHABLE", "无法连接 SMB 主机或端口。")

    async def fail_test(self):
        raise SmbStorageError("SMB_HOST_UNREACHABLE", "无法连接 SMB 主机或端口。")

    monkeypatch.setattr("sundarr.app.services.media_library_service.SmbWriter.list_dir", fail_list_dir)
    monkeypatch.setattr("sundarr.app.services.media_library_service.SmbWriter.test_connection", fail_test)

    response = client.post("/media-libraries/lib_movie/test")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error_code"] == "SMB_HOST_UNREACHABLE"


def test_create_media_library_all_types(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    for media_type in ("movie", "series", "unclassified"):
        response = client.post(
            "/media-libraries/create",
            json={
                "id": f"lib_{media_type}",
                "name": media_type,
                "media_type": media_type,
                "connection_id": "conn_1",
                "base_path": media_type.title(),
            },
        )
        assert response.status_code == 200
        assert response.json()["media_type"] == media_type

    response = client.get("/media-libraries")
    assert response.json()["count"] == 3
