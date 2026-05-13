from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app

def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_sources_are_listed_from_code_registry(db_session: Session) -> None:
    client = make_client(db_session)

    list_response = client.get("/sources")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["page"] == 1
    assert list_response.json()["page_size"] == 20
    assert list_response.json()["results"][0]["id"] == "seedhub"


def test_sources_cannot_be_created_or_edited_from_api(db_session: Session) -> None:
    client = make_client(db_session)

    create_response = client.post(
        "/sources/create",
        json={"id": "site", "name": "站点", "type": "document"},
    )
    assert create_response.status_code == 400
    assert create_response.json()["detail"] == "媒体源现在统一由代码注册，不能通过 Web Console 创建或编辑。"

    update_response = client.post("/sources/seedhub/update", json={"name": "不应修改"})
    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "媒体源现在统一由代码注册，不能通过 Web Console 创建或编辑。"

    disable_response = client.post("/sources/seedhub/disable")
    assert disable_response.status_code == 400
    assert disable_response.json()["detail"] == "媒体源现在统一由代码注册，不能通过 Web Console 创建或编辑。"


def test_source_test_returns_registered_source_preview(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/sources/seedhub/test")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["items"][0]["source_id"] == "seedhub"


def test_unknown_source_returns_404(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/sources/not_exists/test")

    assert response.status_code == 404
