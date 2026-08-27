"""Manifest v2 Activation 测试插件。"""

from dataclasses import dataclass

from sundarr.app.plugins.contracts import (
    CatalogCapabilities,
    CatalogFilter,
    CatalogItem,
    CatalogOperation,
    CatalogPage,
    CatalogQuery,
    CatalogSort,
    MediaType,
    PluginHealthResult,
    WatchlistItem,
    WatchlistPage,
    WatchlistPullRequest,
)
from sundarr.app.plugins.runtime import PluginContext
from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import SourceModel


def activate_source(context: PluginContext) -> SourceModel:
    timeout = context.plugin_config["timeout"]

    async def search(query: SearchQuery) -> list[RawSearchItem]:
        return []

    return SourceModel(
        id=context.plugin_id,
        name=f"Fixture 搜索源（{timeout}s）",
        description="用于 v2 Activation 测试",
        homepage_url="https://example.invalid/source",
        search_function=search,
    )


@dataclass
class FixtureCatalogProvider:
    id: str
    health_ok: bool
    http_client: object

    def describe_capabilities(self) -> CatalogCapabilities:
        return CatalogCapabilities(
            operations=frozenset(CatalogOperation),
            filters=frozenset(CatalogFilter),
            sorts=frozenset(CatalogSort),
        )

    async def health_check(self) -> PluginHealthResult:
        return PluginHealthResult(
            ok=self.health_ok,
            message="Fixture 目录健康检查失败" if not self.health_ok else "",
        )

    async def search(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item(query.keyword or "搜索结果"),))

    async def trending(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(items=(self._item("热门资源"),))

    async def categories(self, query: CatalogQuery) -> CatalogPage:
        title = query.genres[0] if query.genres else "分类资源"
        return CatalogPage(items=(self._item(title),))

    async def get_detail(
        self,
        external_id: str,
        media_type: MediaType | None = None,
    ) -> CatalogItem:
        return self._item("详情", external_id, media_type or MediaType.MOVIE)

    @staticmethod
    def _item(
        title: str,
        external_id: str = "fixture-item",
        media_type: MediaType = MediaType.MOVIE,
    ) -> CatalogItem:
        return CatalogItem(
            external_id=external_id,
            title=title,
            media_type=media_type,
            year=2026,
        )


def activate_catalog(context: PluginContext) -> FixtureCatalogProvider:
    return FixtureCatalogProvider(
        id=context.plugin_id,
        health_ok=context.plugin_config["health_ok"],
        http_client=context.require("core.http.v1"),
    )


@dataclass
class FixtureWatchlistProvider:
    id: str
    user_id: str

    async def pull(self, request: WatchlistPullRequest) -> WatchlistPage:
        subject = CatalogItem(
            external_id=f"wanted-{self.user_id}",
            title="Fixture 想看资源",
            media_type=MediaType.SERIES,
        )
        return WatchlistPage(
            items=(WatchlistItem(subject=subject),),
            next_cursor="next" if request.cursor is None else None,
        )


def activate_watchlist(context: PluginContext) -> FixtureWatchlistProvider:
    return FixtureWatchlistProvider(
        id=context.plugin_id,
        user_id=context.plugin_config["user_id"],
    )
