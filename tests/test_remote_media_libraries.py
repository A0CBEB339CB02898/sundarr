from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import SmbConnection


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


def test_create_remote_media_library(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    response = client.post(
        "/remote-media-libraries/create",
        json={
            "id": "rml_cloud",
            "name": "云盘媒体库",
            "media_type": "movie",
            "connection_id": "conn_1",
            "base_path": "CloudMovie",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "rml_cloud"
    assert body["name"] == "云盘媒体库"
    assert body["media_type"] == "movie"
    assert body["connection_id"] == "conn_1"
    assert body["base_path"] == "CloudMovie"
    assert body["enabled"] is True


def test_create_remote_media_library_duplicate(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_1", "name": "测试", "media_type": "movie", "connection_id": "conn_1", "base_path": "/"},
    )

    response = client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_1", "name": "重复", "media_type": "movie", "connection_id": "conn_1", "base_path": "/"},
    )

    assert response.status_code == 409


def test_create_remote_media_library_connection_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_1", "name": "测试", "media_type": "movie", "connection_id": "nonexistent", "base_path": "/"},
    )

    assert response.status_code == 404


def test_list_remote_media_libraries(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_1", "name": "云盘1", "media_type": "movie", "connection_id": "conn_1", "base_path": "/cloud1"},
    )
    client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_2", "name": "云盘2", "media_type": "series", "connection_id": "conn_1", "base_path": "/cloud2"},
    )

    response = client.get("/remote-media-libraries")

    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_get_remote_media_library(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_1", "name": "云盘", "media_type": "movie", "connection_id": "conn_1", "base_path": "/cloud"},
    )

    response = client.get("/remote-media-libraries/rml_1")

    assert response.status_code == 200
    assert response.json()["id"] == "rml_1"


def test_get_remote_media_library_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/remote-media-libraries/nonexistent")

    assert response.status_code == 404


def test_enable_disable_remote_media_library(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_1", "name": "云盘", "media_type": "movie", "connection_id": "conn_1", "base_path": "/cloud"},
    )

    response = client.post("/remote-media-libraries/rml_1/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    response = client.post("/remote-media-libraries/rml_1/enable")
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_test_remote_media_library_not_found(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/remote-media-libraries/nonexistent/test")

    assert response.status_code == 404


def test_create_remote_media_library_rejects_unsafe_path(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    response = client.post(
        "/remote-media-libraries/create",
        json={"id": "rml_1", "name": "测试", "media_type": "movie", "connection_id": "conn_1", "base_path": "../bad"},
    )

    assert response.status_code == 422


def test_create_remote_media_library_all_types(db_session: Session) -> None:
    client = make_client(db_session)
    _create_smb_connection(client)

    for media_type in ("movie", "series", "unclassified"):
        response = client.post(
            "/remote-media-libraries/create",
            json={
                "id": f"rml_{media_type}",
                "name": media_type,
                "media_type": media_type,
                "connection_id": "conn_1",
                "base_path": media_type.title(),
            },
        )
        assert response.status_code == 200
        assert response.json()["media_type"] == media_type

    response = client.get("/remote-media-libraries")
    assert response.json()["count"] == 3
