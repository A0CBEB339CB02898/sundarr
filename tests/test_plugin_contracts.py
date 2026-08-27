"""MVP 插件运行合同和类型专用 Registry 测试。"""

from dataclasses import dataclass

import pytest

from sundarr.app.plugins.base import LoadedPlugin, PluginManifest, PluginType
from sundarr.app.plugins.contracts import (
    CatalogCapabilities,
    CatalogFilter,
    CatalogItem,
    CatalogOperation,
    CatalogPage,
    CatalogProvider,
    CatalogQuery,
    CatalogSort,
    MediaType,
    WatchlistItem,
    WatchlistPage,
    WatchlistProvider,
    WatchlistPullRequest,
)
from sundarr.app.plugins.registry import plugin_registry
from sundarr.app.plugins.runtime_registry import (
    catalog_provider_registry,
    get_runtime_registry,
    source_registry,
    watchlist_provider_registry,
)
from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import SourceModel
from sundarr.app.sources.registry import get_external_sources


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_registries():
    plugin_registry.clear()
    source_registry.clear()
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()
    yield
    plugin_registry.clear()
    source_registry.clear()
    catalog_provider_registry.clear()
    watchlist_provider_registry.clear()


async def _empty_search(_: SearchQuery) -> list[RawSearchItem]:
    return []


def _source(source_id: str) -> SourceModel:
    return SourceModel(
        id=source_id,
        name=f"搜索源 {source_id}",
        description="测试搜索源",
        homepage_url="https://example.invalid",
        search_function=_empty_search,
    )


@dataclass
class FakeCatalogProvider:
    id: str

    def describe_capabilities(self) -> CatalogCapabilities:
        return CatalogCapabilities(
            operations=frozenset(CatalogOperation),
            filters=frozenset(CatalogFilter),
            sorts=frozenset(CatalogSort),
        )

    async def search(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item(query.keyword or "搜索结果"),))

    async def trending(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item("热门资源"),))

    async def categories(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item(query.genres[0]),))

    async def get_detail(
        self,
        external_id: str,
        media_type: MediaType | None = None,
    ) -> CatalogItem:
        return self._item("详情", external_id, media_type or MediaType.MOVIE)

    @staticmethod
    def _item(
        title: str,
        external_id: str = "item-1",
        media_type: MediaType = MediaType.MOVIE,
    ) -> CatalogItem:
        return CatalogItem(
            external_id=external_id,
            title=title,
            media_type=media_type,
            year=2026,
            external_ids={"example": external_id},
        )


@dataclass
class FakeWatchlistProvider:
    id: str

    async def pull(self, request: WatchlistPullRequest) -> WatchlistPage:
        subject = CatalogItem(
            external_id="wanted-1",
            title="想看资源",
            media_type=MediaType.SERIES,
        )
        return WatchlistPage(
            items=(WatchlistItem(subject=subject),),
            next_cursor="cursor-2" if request.cursor is None else None,
        )


async def test_catalog_and_watchlist_contracts_can_be_called() -> None:
    catalog = FakeCatalogProvider("mock-catalog")
    watchlist = FakeWatchlistProvider("mock-watchlist")

    assert isinstance(catalog, CatalogProvider)
    assert isinstance(watchlist, WatchlistProvider)
    assert CatalogOperation.SEARCH in catalog.describe_capabilities().operations

    search_page = await catalog.search(CatalogQuery(keyword="星际穿越"))
    watchlist_page = await watchlist.pull(WatchlistPullRequest())

    assert search_page.items[0].title == "星际穿越"
    assert search_page.items[0].external_ids == {"example": "item-1"}
    assert watchlist_page.items[0].subject.media_type == MediaType.SERIES
    assert watchlist_page.next_cursor == "cursor-2"


async def test_catalog_query_enforces_confirmed_mvp_boundaries() -> None:
    query = CatalogQuery(
        genres=["科幻"],
        regions=["美国"],
        year_from=2020,
        year_to=2026,
        sort=CatalogSort.POPULARITY,
    )

    assert query.genres == ("科幻",)
    assert query.regions == ("美国",)

    with pytest.raises(ValueError, match="最多接受一个题材"):
        CatalogQuery(genres=("科幻", "剧情"))
    with pytest.raises(ValueError, match="最多接受一个地区"):
        CatalogQuery(regions=("中国", "美国"))
    with pytest.raises(ValueError, match="不能晚于"):
        CatalogQuery(year_from=2026, year_to=2020)
    with pytest.raises(ValueError, match="limit"):
        CatalogQuery(limit=0)


async def test_type_specific_registries_reject_wrong_contract_and_id() -> None:
    source = _source("source-a")
    catalog = FakeCatalogProvider("catalog-a")
    watchlist = FakeWatchlistProvider("watchlist-a")

    source_registry.register("source-a", source)
    catalog_provider_registry.register("catalog-a", catalog)
    watchlist_provider_registry.register("watchlist-a", watchlist)

    assert source_registry.require("source-a") is source
    assert catalog_provider_registry.require("catalog-a") is catalog
    assert watchlist_provider_registry.require("watchlist-a") is watchlist
    assert get_runtime_registry(PluginType.SOURCE) is source_registry

    with pytest.raises(TypeError, match="SourceModel"):
        source_registry.register("wrong", catalog)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="必须与 plugin_id 一致"):
        catalog_provider_registry.register("another-id", catalog)
    with pytest.raises(ValueError, match="不支持激活"):
        get_runtime_registry(PluginType.TRANSFER_DRIVER)


async def test_registry_replace_and_identity_safe_cleanup() -> None:
    old = FakeCatalogProvider("catalog-a")
    new = FakeCatalogProvider("catalog-a")
    catalog_provider_registry.register("catalog-a", old)

    with pytest.raises(ValueError, match="ID 冲突"):
        catalog_provider_registry.register("catalog-a", new)

    previous = catalog_provider_registry.replace("catalog-a", new)

    assert previous is old
    assert catalog_provider_registry.require("catalog-a") is new
    assert not catalog_provider_registry.unregister(
        "catalog-a",
        expected_instance=old,
    )
    assert catalog_provider_registry.unregister(
        "catalog-a",
        expected_instance=new,
    )
    assert catalog_provider_registry.get("catalog-a") is None


async def test_source_registry_precedes_flat_v1_compatibility_result() -> None:
    active_source = _source("same-source")
    legacy_source = _source("same-source")
    source_registry.register("same-source", active_source)
    plugin_registry.register_external(
        LoadedPlugin(
            manifest=PluginManifest(
                id="legacy-bundle",
                name="旧 SOURCE 包",
                version="1.0.0",
                plugin_type=PluginType.SOURCE,
                entry="legacy:get_sources",
                plugin_api_version="1.0",
            ),
            module=None,
            instance=lambda: [legacy_source, _source("legacy-only")],
            status="loaded",
        )
    )

    sources = get_external_sources()

    assert [source.id for source in sources] == ["same-source", "legacy-only"]
    assert sources[0] is active_source
