"""媒体发现 Core 的数据、API 和想看合同回归。"""

from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import MediaExternalId, MediaSubject, WatchlistSyncState
from sundarr.app.plugins.contracts import (
    CatalogAttribution,
    CatalogCapabilities,
    CatalogFilter,
    CatalogFilterOption,
    CatalogItem,
    CatalogOperation,
    CatalogPage,
    CatalogQuery,
    CatalogSort,
    MediaType,
    WatchlistItem,
    WatchlistPage,
    WatchlistPullRequest,
)
from sundarr.app.plugins.conformance import (
    CatalogConformanceProbe,
    run_catalog_provider_conformance,
    run_watchlist_provider_conformance,
)
from sundarr.app.plugins.runtime_registry import (
    catalog_provider_registry,
    watchlist_provider_registry,
)
from sundarr.app.services.media_discovery_service import (
    MediaIdentityConflictError,
    media_discovery_service,
)
from sundarr.app.services.poster_proxy_service import (
    PosterFetchError,
    PosterPayload,
    poster_proxy_service,
)


@dataclass
class ContractCatalogProvider:
    id: str = "contract-catalog"
    detail_media_type: MediaType | None = None

    def describe_capabilities(self) -> CatalogCapabilities:
        return CatalogCapabilities(
            operations=frozenset(CatalogOperation),
            filters=frozenset(CatalogFilter),
            sorts=frozenset(CatalogSort),
            operation_filters={
                CatalogOperation.SEARCH: frozenset(
                    {CatalogFilter.MEDIA_TYPE, CatalogFilter.GENRE, CatalogFilter.YEAR}
                ),
                CatalogOperation.TRENDING: frozenset({CatalogFilter.MEDIA_TYPE}),
                CatalogOperation.CATEGORIES: frozenset(CatalogFilter),
            },
            operation_sorts={
                CatalogOperation.SEARCH: frozenset(),
                CatalogOperation.TRENDING: frozenset(),
                CatalogOperation.CATEGORIES: frozenset(CatalogSort),
            },
            attribution=CatalogAttribution(
                provider_name="测试目录",
                homepage_url="https://catalog.example.invalid",
                notice="测试目录来源声明",
                image_referer_url="https://catalog.example.invalid/",
            ),
            identity_namespaces=frozenset({"tmdb.movie"}),
            filter_options={
                CatalogFilter.GENRE: (CatalogFilterOption("878", "科幻"),),
                CatalogFilter.REGION: (CatalogFilterOption("US", "美国"),),
            },
        )

    async def search(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item(query.keyword or "搜索结果"),), continuation_token="next-2")

    async def trending(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item("热门电影"),))

    async def categories(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item(query.genres[0] if query.genres else "分类电影"),))

    async def get_detail(self, external_id: str, media_type: MediaType | None = None) -> CatalogItem:
        self.detail_media_type = media_type
        return self._item("真实合同详情", external_id=external_id)

    def _item(self, title: str, external_id: str = "603") -> CatalogItem:
        return CatalogItem(
            external_id=external_id,
            external_id_provider="tmdb.movie",
            title=title,
            media_type=MediaType.MOVIE,
            year=1999,
            poster_url="https://image.example.invalid/poster.jpg",
            external_ids={"imdb": "tt0133093"},
            original_title="The Matrix",
            overview="一名程序员发现世界并非表面所见。",
            release_date=date(1999, 3, 31),
            genres=("科幻", "动作"),
            regions=("美国",),
            rating=8.7,
            vote_count=26000,
            backdrop_url="https://image.example.invalid/backdrop.jpg",
            image_urls=("https://image.example.invalid/poster.jpg",),
        )


@dataclass
class ContractWatchlistProvider:
    id: str = "contract-watchlist"

    async def pull(self, request: WatchlistPullRequest) -> WatchlistPage:
        return WatchlistPage(
            items=(
                WatchlistItem(
                    subject=CatalogItem(
                        external_id="603",
                        external_id_provider="tmdb.movie",
                        title="黑客帝国",
                        media_type=MediaType.MOVIE,
                        year=1999,
                    ),
                    external_record_id="wanted-603",
                ),
            ),
            next_cursor="cursor-2",
        )


@dataclass
class FailingWatchlistProvider:
    id: str = "failing-watchlist"

    async def pull(self, request: WatchlistPullRequest) -> WatchlistPage:
        raise RuntimeError("请求失败 token=should-not-leak")


@pytest.fixture(autouse=True)
def clear_discovery_registries():
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()
    yield
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_discover_search_detail_and_follow_use_public_contract(db_session: Session) -> None:
    provider = ContractCatalogProvider()
    catalog_provider_registry.register("contract-catalog", provider)
    client = make_client(db_session)

    providers = client.get("/discover/providers")
    assert providers.status_code == 200
    assert providers.json()[0]["identity_namespaces"] == ["tmdb.movie"]
    assert providers.json()[0]["filter_options"]["genre"] == [{"value": "878", "label": "科幻"}]
    assert providers.json()[0]["operation_filters"]["search"] == ["genre", "media_type", "year"]
    assert providers.json()[0]["operation_sorts"]["search"] == []
    assert providers.json()[0]["attribution"] == {
        "provider_name": "测试目录",
        "homepage_url": "https://catalog.example.invalid",
        "notice": "测试目录来源声明",
        "logo_url": None,
        "image_referer_url": "https://catalog.example.invalid/",
    }

    response = client.get("/discover/search", params={"q": "黑客帝国", "refresh": "true"})

    assert response.status_code == 200
    page = response.json()
    assert page["provider_id"] == "contract-catalog"
    assert page["continuation_token"] == "next-2"
    assert page["items"][0]["canonical_title"] == "黑客帝国"
    assert page["items"][0]["external_ids"]["tmdb.movie"] == "603"
    media_subject_id = page["items"][0]["media_subject_id"]

    detail_response = client.get(f"/discover/{media_subject_id}", params={"refresh": "true"})
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"] == "一名程序员发现世界并非表面所见。"
    assert detail["rating"] == 8.7
    assert detail["rating_provider"] == "contract-catalog"
    assert provider.detail_media_type == MediaType.MOVIE

    followed = client.post(f"/discover/{media_subject_id}/follow")
    assert followed.status_code == 200
    assert followed.json()["followed"] is True
    assert client.get(f"/discover/{media_subject_id}").json()["followed"] is True

    unfollowed = client.delete(f"/discover/{media_subject_id}/follow")
    assert unfollowed.status_code == 200
    assert unfollowed.json()["followed"] is False


def test_poster_relay_uses_persisted_url_and_provider_referer(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_provider_registry.register("contract-catalog", ContractCatalogProvider())
    client = make_client(db_session)
    search = client.get("/discover/search", params={"q": "黑客帝国", "refresh": "true"})
    media_subject_id = search.json()["items"][0]["media_subject_id"]
    calls: list[tuple[str, str | None]] = []

    async def download(url: str, referer: str | None) -> PosterPayload:
        calls.append((url, referer))
        return PosterPayload(body=b"real-image", media_type="image/jpeg")

    monkeypatch.setattr(poster_proxy_service, "_download", download)
    response = client.get(
        f"/discover/{media_subject_id}/poster",
        params={"provider_id": "contract-catalog"},
    )

    assert response.status_code == 200
    assert response.content == b"real-image"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert calls == [
        (
            "https://image.example.invalid/poster.jpg",
            "https://catalog.example.invalid/",
        )
    ]


def test_poster_relay_rejects_open_proxy_and_isolates_upstream_failure(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_provider_registry.register("contract-catalog", ContractCatalogProvider())
    client = make_client(db_session)
    search = client.get("/discover/search", params={"q": "黑客帝国", "refresh": "true"})
    media_subject_id = search.json()["items"][0]["media_subject_id"]

    arbitrary = client.get(
        f"/discover/{media_subject_id}/poster",
        params={
            "provider_id": "contract-catalog",
            "url": "https://attacker.example/secret",
        },
    )
    mismatch = client.get(
        f"/discover/{media_subject_id}/poster",
        params={"provider_id": "another-provider"},
    )

    async def fail_download(url: str, referer: str | None) -> PosterPayload:
        raise PosterFetchError("上游海报读取失败")

    monkeypatch.setattr(poster_proxy_service, "_download", fail_download)
    upstream_failure = client.get(
        f"/discover/{media_subject_id}/poster",
        params={"provider_id": "contract-catalog"},
    )

    assert arbitrary.status_code == 422
    assert "url" in arbitrary.json()["detail"]
    assert mismatch.status_code == 409
    assert upstream_failure.status_code == 502
    assert upstream_failure.json()["detail"] == "上游海报读取失败"


def test_discover_rejects_multiple_genres_and_missing_provider(db_session: Session) -> None:
    client = make_client(db_session)

    no_provider = client.get("/discover/trending")
    assert no_provider.status_code == 503
    assert "没有已启用" in no_provider.json()["detail"]

    catalog_provider_registry.register("contract-catalog", ContractCatalogProvider())
    invalid = client.get("/discover/search?q=test&genre=科幻&genre=动作")
    assert invalid.status_code == 422
    assert "最多接受一个题材" in invalid.json()["detail"]


def test_discover_validates_filters_and_sorts_for_each_operation(db_session: Session) -> None:
    catalog_provider_registry.register("contract-catalog", ContractCatalogProvider())
    client = make_client(db_session)

    unsupported_region = client.get("/discover/search?q=test&region=US")
    unsupported_sort = client.get("/discover/search?q=test&sort=rating")
    supported_categories = client.get(
        "/discover/categories?region=US&sort=rating&refresh=true"
    )

    assert unsupported_region.status_code == 422
    assert "不支持筛选：region" in unsupported_region.json()["detail"]
    assert unsupported_sort.status_code == 422
    assert "不支持排序：rating" in unsupported_sort.json()["detail"]
    assert supported_categories.status_code == 200


def test_external_ids_merge_exactly_and_conflicts_are_rejected(db_session: Session) -> None:
    first = ContractCatalogProvider("provider-a")._item("黑客帝国")
    subject = media_discovery_service.upsert_item(db_session, "provider-a", first)
    db_session.commit()

    same = CatalogItem(
        external_id="douban-1291843",
        external_id_provider="douban",
        title="黑客帝国",
        media_type=MediaType.MOVIE,
        external_ids={"tmdb.movie": "603"},
    )
    merged = media_discovery_service.upsert_item(db_session, "provider-b", same)
    db_session.commit()

    assert merged.id == subject.id
    assert db_session.query(MediaSubject).count() == 1
    assert {row.provider for row in db_session.query(MediaExternalId).all()} >= {
        "provider-a",
        "provider-b",
        "tmdb.movie",
        "douban",
    }

    other = MediaSubject(
        id="other-subject",
        media_type="movie",
        canonical_title="另一个条目",
        snapshot_source="manual",
        snapshot_updated_at=media_discovery_service._now(),
    )
    db_session.add(other)
    db_session.add(
        MediaExternalId(
            id="other-id",
            media_subject_id=other.id,
            provider="imdb",
            external_id="tt-conflict",
        )
    )
    db_session.commit()

    with pytest.raises(MediaIdentityConflictError):
        media_discovery_service.upsert_item(
            db_session,
            "provider-c",
            CatalogItem(
                external_id="603",
                external_id_provider="tmdb.movie",
                title="冲突条目",
                media_type=MediaType.MOVIE,
                external_ids={"imdb": "tt-conflict"},
            ),
        )


def test_watchlist_sync_persists_cursor_and_reuses_media_identity(db_session: Session) -> None:
    catalog_provider_registry.register("contract-catalog", ContractCatalogProvider())
    watchlist_provider_registry.register("contract-watchlist", ContractWatchlistProvider())
    client = make_client(db_session)

    search = client.get("/discover/search", params={"q": "黑客帝国", "refresh": "true"})
    media_subject_id = search.json()["items"][0]["media_subject_id"]
    synced = client.post("/discover/watchlist/contract-watchlist/sync")

    assert synced.status_code == 200
    assert synced.json()["pulled_count"] == 1
    assert synced.json()["next_cursor"] == "cursor-2"
    assert db_session.get(WatchlistSyncState, "contract-watchlist").cursor == "cursor-2"
    watchlist = client.get("/discover/watchlist").json()
    assert watchlist["count"] == 1
    assert watchlist["items"][0]["media_subject_id"] == media_subject_id
    assert watchlist["items"][0]["watchlisted"] is True


def test_watchlist_first_identity_can_use_catalog_detail_provider(db_session: Session) -> None:
    watchlist_provider_registry.register("contract-watchlist", ContractWatchlistProvider())
    client = make_client(db_session)

    synced = client.post("/discover/watchlist/contract-watchlist/sync")
    media_subject_id = client.get("/discover/watchlist").json()["items"][0]["media_subject_id"]

    assert synced.status_code == 200
    catalog_provider_registry.register("contract-catalog", ContractCatalogProvider())
    detail = client.get(f"/discover/{media_subject_id}", params={"refresh": "true"})
    assert detail.status_code == 200
    assert detail.json()["overview"] == "一名程序员发现世界并非表面所见。"


def test_watchlist_failure_does_not_persist_or_return_plugin_secrets(db_session: Session) -> None:
    watchlist_provider_registry.register("failing-watchlist", FailingWatchlistProvider())
    client = make_client(db_session)

    response = client.post("/discover/watchlist/failing-watchlist/sync")
    state = db_session.get(WatchlistSyncState, "failing-watchlist")

    assert response.status_code == 502
    assert "should-not-leak" not in response.text
    assert state is not None
    assert "should-not-leak" not in (state.last_error or "")
    assert state.retry_count == 1


@pytest.mark.anyio
async def test_public_conformance_runner_covers_declared_operations() -> None:
    catalog_report = await run_catalog_provider_conformance(
        ContractCatalogProvider(),
        CatalogConformanceProbe(
            query=CatalogQuery(keyword="黑客帝国"),
            detail_external_id="603",
            detail_media_type=MediaType.MOVIE,
        ),
    )
    watchlist_report = await run_watchlist_provider_conformance(ContractWatchlistProvider())

    assert catalog_report.checks == {
        "categories": 1,
        "detail": 1,
        "search": 1,
        "trending": 1,
    }
    assert watchlist_report.checks == {"pull": 1}
