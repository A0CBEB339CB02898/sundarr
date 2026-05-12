from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import Source


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_create_and_list_document_source(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post(
        "/sources/create",
        json={
            "id": "my_doc",
            "name": "我的文档源",
            "type": "document",
            "legal_note": "个人维护的资源表。",
            "config_json": {
                "items": [
                    {
                        "title": "星际穿越 2014 1080p",
                        "link": "https://pan.example.invalid/s/doc",
                    }
                ]
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == "my_doc"

    list_response = client.get("/sources")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["page"] == 1
    assert list_response.json()["page_size"] == 20


def test_update_enable_disable_source(db_session: Session) -> None:
    client = make_client(db_session)
    client.post(
        "/sources/create",
        json={"id": "site", "name": "站点", "type": "configurable", "config_json": {"search_url": "https://example.invalid/search?q={keyword}", "selectors": {"item": ".item"}}},
    )

    update_response = client.post("/sources/site/update", json={"name": "新站点", "trust_level": 2})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "新站点"

    disable_response = client.post("/sources/site/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    enable_response = client.post("/sources/site/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True


def test_code_source_cannot_be_edited_from_api(db_session: Session) -> None:
    db_session.add(Source(id="code_source", name="代码源", type="code", enabled=True, created_by_user=False))
    db_session.commit()
    client = make_client(db_session)

    response = client.post("/sources/code_source/update", json={"name": "不应修改"})

    assert response.status_code == 400
    assert response.json()["detail"] == "该类型媒体源不能通过 Web Console 编辑。"


def test_source_test_returns_preview_items(db_session: Session) -> None:
    client = make_client(db_session)
    client.post(
        "/sources/create",
        json={
            "id": "doc_test",
            "name": "文档测试源",
            "type": "document",
            "config_json": {
                "items": [
                    {
                        "title": "星际穿越 2014 1080p",
                        "link": "https://pan.example.invalid/s/test",
                    }
                ]
            },
        },
    )

    response = client.post("/sources/doc_test/test")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["items"][0]["source_id"] == "doc_test"


def test_invalid_source_test_records_error(db_session: Session) -> None:
    client = make_client(db_session)
    client.post("/sources/create", json={"id": "bad_doc", "name": "坏文档源", "type": "document", "config_json": {}})

    response = client.post("/sources/bad_doc/test")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error_code"] == "SOURCE_CONFIG_INVALID"

    source_response = client.get("/sources/bad_doc")
    assert source_response.json()["last_error_code"] == "SOURCE_CONFIG_INVALID"
