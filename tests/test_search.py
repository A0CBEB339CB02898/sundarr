from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.main import create_app
from sundarr.app.core.database import get_db
from sundarr.app.parsers import extract_cloud_links
from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.services.resource_library_service import ResourceLibraryService
from sundarr.app.services.search_service import SearchService
from sundarr.app.sources import BaseSource


class FailingSource(BaseSource):
    id = "failing"
    name = "失败源"
    source_type = "code"
    enabled = True

    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        raise RuntimeError("模拟源失败")


class StaticSource(BaseSource):
    id = "static"
    name = "静态源"
    source_type = "code"
    enabled = True

    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        return [
            RawSearchItem(
                source_id=self.id,
                source_type=self.source_type,
                raw_title="星际穿越 2014 1080p",
                raw_url="https://example.invalid/static",
                raw_content="链接：https://pan.example.invalid/s/static 提取码：abcd",
                fetched_at=datetime.now(UTC),
                metadata={"year": 2014, "type": "movie"},
            )
        ]


def test_extract_cloud_links_with_code() -> None:
    links = extract_cloud_links("夸克：https://pan.example.invalid/s/abc 提取码：1234")

    assert len(links) == 1
    assert links[0].provider == "quark"
    assert links[0].code == "1234"


@pytest.mark.anyio
async def test_search_service_isolates_source_failure() -> None:
    service = SearchService(sources=[FailingSource(), StaticSource()])

    response = await service.search(SearchQuery(keyword="星际穿越", year=2014))

    assert response.count == 1
    assert response.results[0].links[0].code == "abcd"


def test_search_api_returns_candidates(db_session: Session) -> None:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/search", params={"q": "interstellar", "type": "movie", "year": 2014})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["links"][0]["provider"] == "quark"


@pytest.mark.anyio
async def test_resource_library_persists_candidates(db_session: Session) -> None:
    service = SearchService(sources=[StaticSource()])
    library = ResourceLibraryService()

    response = await service.search(SearchQuery(keyword="星际穿越", year=2014))
    library.save_candidates(db_session, response.results)
    stored = library.get_resource(db_session, response.results[0].id)

    assert stored is not None
    assert stored.id == response.results[0].id
    assert stored.links[0].code == "abcd"


def test_resource_api_reads_from_database(db_session: Session) -> None:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    search_response = client.get("/search", params={"q": "interstellar"})
    resource_id = search_response.json()["results"][0]["id"]

    response = client.get(f"/resources/{resource_id}")

    assert response.status_code == 200
    assert response.json()["id"] == resource_id
