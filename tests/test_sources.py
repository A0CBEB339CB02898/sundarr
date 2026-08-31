from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import Source
from sundarr.app.plugins.conformance import SourceConformanceProbe, run_source_conformance
from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources import SourceModel


async def static_search(query: SearchQuery) -> list[RawSearchItem]:
    return [
        RawSearchItem(
            source_id="legacy",
            source_type="code",
            raw_title=f"{query.keyword} 测试结果",
            raw_url="https://example.invalid/source",
            raw_content="夸克：https://pan.quark.cn/s/source 提取码：abcd",
            fetched_at=datetime.now(UTC),
        )
    ]


async def static_detail(detail_url: str) -> RawSearchItem:
    return RawSearchItem(
        source_id="legacy",
        source_type="code",
        raw_title="测试影片 (2024)",
        raw_url=detail_url,
        raw_content="夸克：https://pan.quark.cn/s/source-detail 提取码：abcd",
        fetched_at=datetime.now(UTC),
    )

def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_sources_are_listed_from_code_registry(db_session: Session) -> None:
    db_session.add(Source(id="legacy", name="观影", description="旧数据", homepage_url="https://legacy.invalid"))
    db_session.commit()
    client = make_client(db_session)

    list_response = client.get("/sources")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0
    assert list_response.json()["page"] == 1
    assert list_response.json()["page_size"] == 20
    # ????????????????
    assert list_response.json()["results"] == []
    assert db_session.get(Source, "legacy") is None



def test_source_mutation_endpoints_are_removed(db_session: Session) -> None:
    client = make_client(db_session)

    create_response = client.post(
        "/sources/create",
        json={"id": "site", "name": "站点", "type": "document"},
    )
    assert create_response.status_code == 405

    update_response = client.post("/sources/legacy/update", json={"name": "不应修改"})
    assert update_response.status_code == 404

    disable_response = client.post("/sources/legacy/disable")
    assert disable_response.status_code == 404


def test_source_test_returns_registered_source_preview(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    import sundarr.app.services.source_service as source_service_module

    monkeypatch.setattr(
        source_service_module,
        "get_registered_sources",
        lambda: [
            SourceModel(
                id="legacy",
                name="Legacy",
                description="测试源",
                homepage_url="https://example.invalid",
                search_function=static_search,
            )
        ],
    )
    client = make_client(db_session)

    response = client.post("/sources/legacy/test", json={"keyword": "星际穿越", "result_type": "quark", "limit": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["items"][0]["source_id"] == "legacy"
    assert [log["step"] for log in body["logs"]] == ["prepare", "query", "search", "preview"]


def test_unknown_source_returns_404(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/sources/not_exists/test")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_public_source_conformance_runner_covers_search_and_detail() -> None:
    source = SourceModel(
        id="legacy",
        name="Legacy",
        description="合同测试源",
        homepage_url="https://example.invalid",
        search_function=static_search,
        fetch_detail_function=static_detail,
    )

    report = await run_source_conformance(
        source,
        SourceConformanceProbe(query=SearchQuery(keyword="测试影片", limit=1)),
    )

    assert report.plugin_id == "legacy"
    assert report.checks == {"search": 1, "detail": 1}
