from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import Source
from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources import SourceModel


async def static_search(query: SearchQuery) -> list[RawSearchItem]:
    return [
        RawSearchItem(
            source_id="seedhub",
            source_type="code",
            raw_title=f"{query.keyword} 测试结果",
            raw_url="https://example.invalid/source",
            raw_content="夸克：https://pan.quark.cn/s/source 提取码：abcd",
            fetched_at=datetime.now(UTC),
        )
    ]

def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_sources_are_listed_from_code_registry(db_session: Session) -> None:
    db_session.add(Source(id="legacy", name="观影", type="code", enabled=True, legal_note="旧数据"))
    db_session.commit()
    client = make_client(db_session)

    list_response = client.get("/sources")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["page"] == 1
    assert list_response.json()["page_size"] == 20
    assert list_response.json()["results"][0]["id"] == "seedhub"
    assert {item["id"] for item in list_response.json()["results"]} == {"seedhub"}
    assert set(list_response.json()["results"][0]) == {"id", "name", "type", "description"}


def test_source_mutation_endpoints_are_removed(db_session: Session) -> None:
    client = make_client(db_session)

    create_response = client.post(
        "/sources/create",
        json={"id": "site", "name": "站点", "type": "document"},
    )
    assert create_response.status_code == 405

    update_response = client.post("/sources/seedhub/update", json={"name": "不应修改"})
    assert update_response.status_code == 404

    disable_response = client.post("/sources/seedhub/disable")
    assert disable_response.status_code == 404


def test_source_test_returns_registered_source_preview(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import sundarr.app.services.source_service as source_service_module

    monkeypatch.setattr(
        source_service_module,
        "get_registered_sources",
        lambda: [
            SourceModel(
                id="seedhub",
                name="SeedHub",
                description="测试源",
                search_function=static_search,
            )
        ],
    )
    client = make_client(db_session)

    response = client.post("/sources/seedhub/test", json={"keyword": "星际穿越", "result_type": "quark", "limit": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["items"][0]["source_id"] == "seedhub"
    assert [log["step"] for log in body["logs"]] == ["prepare", "query", "search", "preview"]


def test_unknown_source_returns_404(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/sources/not_exists/test")

    assert response.status_code == 404
