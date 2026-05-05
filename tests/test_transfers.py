from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import Resource, ResourceLink, Setting, TransferTask
from sundarr.app.services.storage_config_service import STORAGE_CONFIG_KEY


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
    db_session.add(
        Setting(
            key=STORAGE_CONFIG_KEY,
            value_json={"host": "nas.example.invalid", "share": "share", "username": "user", "password": "secret"},
            is_sensitive=True,
        )
    )
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
    assert task.storage_config_snapshot == {"host": "nas.example.invalid", "share": "share", "username": "user", "password": "secret"}

    get_response = client.get(f"/transfers/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


def test_create_transfer_rejects_missing_link(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/transfers", json={"link_id": "missing", "target_path": "Movies/Movie.mkv"})

    assert response.status_code == 404
    assert response.json()["detail"] == "资源链接不存在。"
