"""当前 MVP 插件类型的公共运行协议。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from sundarr.app.sources.base import SourceModel


SourceProvider = SourceModel


class MediaType(str, Enum):
    """目录和想看插件使用的最小媒体类型。"""

    MOVIE = "movie"
    SERIES = "series"


class CatalogSort(str, Enum):
    """媒体发现 MVP 的公共排序方式。"""

    POPULARITY = "popularity"
    RATING = "rating"
    RELEASE_DATE = "release_date"


class CatalogOperation(str, Enum):
    """目录插件可声明支持的运行操作。"""

    SEARCH = "search"
    TRENDING = "trending"
    CATEGORIES = "categories"
    DETAIL = "detail"


class CatalogFilter(str, Enum):
    """媒体发现 MVP 的公共筛选字段。"""

    MEDIA_TYPE = "media_type"
    GENRE = "genre"
    REGION = "region"
    YEAR = "year"


@dataclass(frozen=True)
class PluginHealthResult:
    """插件可选动态健康检查的统一结果。"""

    ok: bool
    message: str = ""
    details: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


@dataclass(frozen=True)
class CatalogCapabilities:
    """目录 Provider 在当前配置下实际支持的能力。"""

    operations: frozenset[CatalogOperation]
    media_types: frozenset[MediaType] = field(
        default_factory=lambda: frozenset(MediaType)
    )
    filters: frozenset[CatalogFilter] = field(default_factory=frozenset)
    sorts: frozenset[CatalogSort] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operations", frozenset(self.operations))
        object.__setattr__(self, "media_types", frozenset(self.media_types))
        object.__setattr__(self, "filters", frozenset(self.filters))
        object.__setattr__(self, "sorts", frozenset(self.sorts))
        if not self.operations:
            raise ValueError("目录 Provider 至少需要支持一个操作")


@dataclass(frozen=True)
class CatalogQuery:
    """Core 传给目录 Provider 的公共查询。"""

    keyword: str | None = None
    media_type: MediaType | None = None
    genres: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    year_from: int | None = None
    year_to: int | None = None
    sort: CatalogSort | None = None
    limit: int = 20
    continuation_token: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "genres", tuple(self.genres))
        object.__setattr__(self, "regions", tuple(self.regions))
        if len(self.genres) > 1:
            raise ValueError("MVP 目录查询最多接受一个题材")
        if len(self.regions) > 1:
            raise ValueError("MVP 目录查询最多接受一个地区")
        if self.year_from is not None and self.year_from < 1:
            raise ValueError("year_from 必须是正整数")
        if self.year_to is not None and self.year_to < 1:
            raise ValueError("year_to 必须是正整数")
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("year_from 不能晚于 year_to")
        if not 1 <= self.limit <= 100:
            raise ValueError("limit 必须在 1 到 100 之间")
        if self.continuation_token == "":
            raise ValueError("continuation_token 不能为空字符串")


@dataclass(frozen=True)
class CatalogItem:
    """目录插件返回的规范化前媒体候选。"""

    external_id: str
    title: str
    media_type: MediaType
    year: int | None = None
    poster_url: str | None = None
    external_ids: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.external_id.strip():
            raise ValueError("external_id 不能为空")
        if not self.title.strip():
            raise ValueError("title 不能为空")
        if self.year is not None and self.year < 1:
            raise ValueError("year 必须是正整数")
        object.__setattr__(
            self,
            "external_ids",
            MappingProxyType(dict(self.external_ids)),
        )


@dataclass(frozen=True)
class CatalogPage:
    """使用不透明 continuation token 的目录结果页。"""

    items: tuple[CatalogItem, ...]
    continuation_token: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        if self.continuation_token == "":
            raise ValueError("continuation_token 不能为空字符串")


@runtime_checkable
class CatalogProvider(Protocol):
    """CATALOG_PROVIDER v1 的最小执行合同。"""

    id: str

    def describe_capabilities(self) -> CatalogCapabilities: ...

    async def search(self, query: CatalogQuery) -> CatalogPage: ...

    async def trending(self, query: CatalogQuery) -> CatalogPage: ...

    async def categories(self, query: CatalogQuery) -> CatalogPage: ...

    async def get_detail(
        self,
        external_id: str,
        media_type: MediaType | None = None,
    ) -> CatalogItem: ...


@dataclass(frozen=True)
class WatchlistPullRequest:
    """Core 调度想看同步时传入的增量读取请求。"""

    cursor: str | None = None
    limit: int = 100

    def __post_init__(self) -> None:
        if self.cursor == "":
            raise ValueError("cursor 不能为空字符串")
        if not 1 <= self.limit <= 500:
            raise ValueError("limit 必须在 1 到 500 之间")


@dataclass(frozen=True)
class WatchlistItem:
    """想看插件返回的单个外部列表项。"""

    subject: CatalogItem
    external_record_id: str | None = None
    added_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.external_record_id == "":
            raise ValueError("external_record_id 不能为空字符串")


@dataclass(frozen=True)
class WatchlistPage:
    """想看列表的增量读取结果。"""

    items: tuple[WatchlistItem, ...]
    next_cursor: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        if self.next_cursor == "":
            raise ValueError("next_cursor 不能为空字符串")


@runtime_checkable
class WatchlistProvider(Protocol):
    """WATCHLIST_PROVIDER v1 的最小执行合同。"""

    id: str

    async def pull(self, request: WatchlistPullRequest) -> WatchlistPage: ...
