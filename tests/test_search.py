from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.main import create_app
from sundarr.app.models import Resource, ResourceLink
from sundarr.app.core.database import get_db
from sundarr.app.parsers import extract_cloud_links
from sundarr.app.schemas.search import RawSearchItem, ResourceFavoriteRequest, ResourceLinkFavoriteRequest, SearchQuery
from sundarr.app.services.link_validator import LinkValidator
from sundarr.app.services.resource_library_service import ResourceLibraryService
from sundarr.app.services.search_service import SearchService
from sundarr.app.sources import SourceModel
from sundarr.app.sources.seedhub import SeedHubSource


async def failing_search(query: SearchQuery) -> list[RawSearchItem]:
    raise RuntimeError("模拟源失败")


async def static_search(query: SearchQuery) -> list[RawSearchItem]:
    return [
        RawSearchItem(
            source_id="static",
            source_type="code",
            raw_title="星际穿越 2014 1080p",
            raw_url="https://example.invalid/static",
            raw_content="链接：https://pan.quark.cn/s/static 提取码：abcd",
            fetched_at=datetime.now(UTC),
            metadata={"year": 2014},
        )
    ]


async def metadata_sparse_search(query: SearchQuery) -> list[RawSearchItem]:
    return [
        RawSearchItem(
            source_id="sparse",
            source_type="code",
            raw_title="银河护卫队",
            raw_url="https://example.invalid/sparse",
            raw_content="银河护卫队 2023 4K 链接：https://pan.quark.cn/s/sparse 提取码：efgh",
            fetched_at=datetime.now(UTC),
        )
    ]


async def duplicate_search(query: SearchQuery) -> list[RawSearchItem]:
    item = (await static_search(query))[0]
    item.source_id = "duplicate"
    return [item]


def static_source() -> SourceModel:
    return SourceModel(id="static", name="静态源", description="测试用静态源。", homepage_url="https://example.invalid/static", search_function=static_search)


def metadata_sparse_source() -> SourceModel:
    return SourceModel(id="sparse", name="字段稀疏源", description="测试字段兜底提取。", homepage_url="https://example.invalid/sparse", search_function=metadata_sparse_search)


def failing_source() -> SourceModel:
    return SourceModel(id="failing", name="失败源", description="测试用失败源。", homepage_url="https://example.invalid/failing", search_function=failing_search)


def duplicate_source() -> SourceModel:
    return SourceModel(id="duplicate", name="重复源", description="测试用重复源。", homepage_url="https://example.invalid/duplicate", search_function=duplicate_search)


def test_extract_cloud_links_with_code() -> None:
    links = extract_cloud_links("夸克：https://pan.quark.cn/s/abc 提取码：1234")

    assert len(links) == 1
    assert links[0].provider == "quark"
    assert links[0].code == "1234"


def test_seedhub_source_parses_detail_html() -> None:
    source = SeedHubSource()
    source._resolve_seedhub_link = lambda _link: "https://pan.quark.cn/s/resolved"  # type: ignore[method-assign]
    item = source._parse_detail(
        "https://seedhub.cc/detail/1",
        """
        <html>
          <head><title>测试电影 2024 - SeedHub</title></head>
          <body>
            <a href="magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567">磁力</a>
            <p>夸克：https://pan.quark.cn/s/example 提取码：abcd</p>
            <a data-link="quark" title="资源" href="/link_start/?redirect_to=pan_id_1&amp;movie_title=x">下载</a>
          </body>
        </html>
        """,
    )

    assert item is not None
    assert item.raw_title == "测试电影 2024"
    assert "pan.quark.cn" in item.raw_content


def test_seedhub_source_uses_real_search_route() -> None:
    source = SeedHubSource()

    assert source._search_url("怪奇物语") == "https://www.seedhub.cc/s/%E6%80%AA%E5%A5%87%E7%89%A9%E8%AF%AD/"


def test_seedhub_source_parses_movie_cards() -> None:
    source = SeedHubSource()
    html = '''
      <a title="怪奇物语" class="image" href="/movies/119254/">封面</a>
      <a title="重复" class="image" href="/movies/119254/">封面</a>
      <a title="别的" class="image" href="/movies/1754/">封面</a>
    '''

    assert source._parse_detail_urls(html) == [
        "https://www.seedhub.cc/movies/119254/",
        "https://www.seedhub.cc/movies/1754/",
    ]


def test_seedhub_source_normalizes_redirect_link() -> None:
    source = SeedHubSource()

    assert source._normalize_seedhub_download_link("/link_start/?redirect_to=pan_id_1&movie_title=怪奇物语 4K") == "/link_start/?redirect_to=pan_id_1"


def test_seedhub_source_detects_supported_netdisk_links() -> None:
    source = SeedHubSource()

    assert "https://115.com/s/abc123" in source._extract_direct_links("115 https://115.com/s/abc123")
    assert source._contains_supported_link("123云盘 https://www.123pan.com/s/a-b")


def test_extract_cloud_links_supports_more_netdisk_providers() -> None:
    links = extract_cloud_links("UC https://drive.uc.cn/s/abc 123 https://www.123pan.com/s/a-b 天翼 https://cloud.189.cn/t/ABC")

    assert {link.provider for link in links} >= {"uc", "123pan", "tianyi"}


@pytest.mark.anyio
async def test_search_service_isolates_source_failure() -> None:
    service = SearchService(sources=[failing_source(), static_source()], validator=LinkValidator(enable_network=False))

    response = await service.search(SearchQuery(keyword="星际穿越", year=2014))

    assert response.count == 1
    assert response.results[0].year == 2014
    assert response.results[0].links[0].name == "星际穿越 1080P"
    assert response.results[0].links[0].code == "abcd"
    assert response.results[0].links[0].quality == "1080P"
    assert response.results[0].links[0].validation_status == "unknown"
    assert response.source_results[0].source_id == "failing"
    assert response.source_results[0].error is not None
    assert response.source_results[1].count == 1


@pytest.mark.anyio
async def test_search_service_dedupes_by_real_link() -> None:
    service = SearchService(sources=[static_source(), duplicate_source()], validator=LinkValidator(enable_network=False))

    response = await service.search(SearchQuery(keyword="星际穿越", result_type="quark"))

    assert response.count == 1
    assert len(response.results[0].links) == 1
    assert {group.source_id: group.count for group in response.source_results} == {"static": 1, "duplicate": 1}


@pytest.mark.anyio
async def test_search_service_fills_year_quality_and_link_name_from_content() -> None:
    service = SearchService(sources=[metadata_sparse_source()], validator=LinkValidator(enable_network=False))

    response = await service.search(SearchQuery(keyword="银河护卫队"))

    candidate = response.results[0]
    assert candidate.year == 2023
    assert candidate.links[0].quality == "4K"
    assert candidate.links[0].name == "银河护卫队 4K"


def test_search_api_returns_candidates(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    import sundarr.app.api.search as search_api

    monkeypatch.setattr(
        search_api,
        "search_service",
        SearchService(sources=[static_source()], validator=LinkValidator(enable_network=False)),
    )

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/search", params={"q": "interstellar", "result_type": "quark", "year": 2014})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["links"][0]["provider"] == "quark"
    assert body["source_results"][0]["source_id"] == "static"
    assert body["source_results"][0]["count"] == 1
    assert db_session.query(Resource).count() == 0
    assert db_session.query(ResourceLink).count() == 0


@pytest.mark.anyio
async def test_resource_library_favorites_resource_and_link(db_session: Session) -> None:
    service = SearchService(sources=[static_source()], validator=LinkValidator(enable_network=False))
    library = ResourceLibraryService()

    response = await service.search(SearchQuery(keyword="星际穿越", year=2014))
    candidate = response.results[0]
    link = candidate.links[0]

    stored_resource = library.favorite_resource(
        db_session,
        ResourceFavoriteRequest(
            id=candidate.id,
            title=candidate.title,
            normalized_title=candidate.normalized_title,
            original_title=candidate.original_title,
            year=candidate.year,
            links=candidate.links,
        ),
    )

    assert stored_resource.is_favorited is True
    assert len(stored_resource.links) == 1
    stored_link = stored_resource.links[0]
    assert stored_link.is_favorited is True
    assert stored_link.name == "星际穿越 1080P"
    assert stored_link.code == "abcd"
    assert stored_link.quality == "1080P"


def test_resource_api_reads_from_database(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    import sundarr.app.api.search as search_api

    monkeypatch.setattr(
        search_api,
        "search_service",
        SearchService(sources=[static_source()], validator=LinkValidator(enable_network=False)),
    )

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    search_response = client.get("/search", params={"q": "interstellar"})
    candidate = search_response.json()["results"][0]
    favorite_response = client.post(
        "/resources/favorite",
        json={
            "id": candidate["id"],
            "title": candidate["title"],
            "normalized_title": candidate["normalized_title"],
            "original_title": candidate["original_title"],
            "year": candidate["year"],
        },
    )
    assert favorite_response.status_code == 200
    resource_id = candidate["id"]

    response = client.get(f"/resources/{resource_id}")

    assert response.status_code == 200
    assert response.json()["id"] == resource_id


def test_resource_link_api_favorites_and_refresh(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    import sundarr.app.api.search as search_api
    import sundarr.app.services.resource_library_service as library_service_module

    monkeypatch.setattr(
        search_api,
        "search_service",
        SearchService(sources=[static_source()], validator=LinkValidator(enable_network=False)),
    )

    class StubValidationResult:
        valid = True
        status = "valid"
        message = "ok"
        checked_at = datetime.now(UTC)

    async def fake_validate(provider: str, url: str):
        return StubValidationResult()

    monkeypatch.setattr(library_service_module.link_validator, "validate", fake_validate)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    search_response = client.get("/search", params={"q": "interstellar"})
    candidate = search_response.json()["results"][0]
    link = candidate["links"][0]

    favorite_response = client.post(
        "/resource-links/favorite",
        json={
            "resource": {
                "id": candidate["id"],
                "title": candidate["title"],
                "normalized_title": candidate["normalized_title"],
                "original_title": candidate["original_title"],
                "year": candidate["year"],
            },
            "link": link,
        },
    )

    assert favorite_response.status_code == 200
    assert favorite_response.json()["is_favorited"] is True

    get_response = client.get(f"/resource-links/{link['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == link["id"]

    refresh_response = client.post(f"/resource-links/{link['id']}/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["validation_status"] == "valid"


@pytest.mark.anyio
async def test_search_marks_favorited_resource_and_link(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    import sundarr.app.api.search as search_api

    service = SearchService(sources=[static_source()], validator=LinkValidator(enable_network=False))

    monkeypatch.setattr(
        search_api,
        "search_service",
        service,
    )

    library = ResourceLibraryService()
    candidate = (await service.search(SearchQuery(keyword="星际穿越", year=2014))).results[0]
    library.favorite_resource(
        db_session,
        ResourceFavoriteRequest(
            id=candidate.id,
            title=candidate.title,
            normalized_title=candidate.normalized_title,
            original_title=candidate.original_title,
            year=candidate.year,
        ),
    )
    library.favorite_link(
        db_session,
        ResourceLinkFavoriteRequest(
            resource=ResourceFavoriteRequest(
                id=candidate.id,
                title=candidate.title,
                normalized_title=candidate.normalized_title,
                original_title=candidate.original_title,
                year=candidate.year,
            ),
            link=candidate.links[0],
        ),
    )

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/search", params={"q": "interstellar", "year": 2014})

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["is_favorited"] is True
    assert body["results"][0]["links"][0]["is_favorited"] is True
