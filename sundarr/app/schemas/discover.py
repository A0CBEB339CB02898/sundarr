"""媒体发现 Core 的公共 API Schema。"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class CatalogFilterOptionResponse(BaseModel):
    value: str
    label: str


class CatalogAttributionResponse(BaseModel):
    provider_name: str
    homepage_url: str
    notice: str
    logo_url: str | None = None


class CatalogProviderResponse(BaseModel):
    id: str
    identity_namespaces: list[str]
    operations: list[str]
    media_types: list[str]
    filters: list[str]
    sorts: list[str]
    operation_filters: dict[str, list[str]] = Field(default_factory=dict)
    operation_sorts: dict[str, list[str]] = Field(default_factory=dict)
    attribution: CatalogAttributionResponse | None = None
    filter_options: dict[str, list[CatalogFilterOptionResponse]] = Field(default_factory=dict)


class MediaSubjectSummary(BaseModel):
    media_subject_id: str
    media_type: str
    canonical_title: str
    release_year: int | None = None
    poster_url: str | None = None
    provider_id: str
    external_id: str
    external_ids: dict[str, str] = Field(default_factory=dict)
    followed: bool = False
    watchlisted: bool = False
    degraded: bool = False


class DiscoverPageResponse(BaseModel):
    items: list[MediaSubjectSummary]
    continuation_token: str | None = None
    provider_id: str
    degraded: bool = False
    cached_at: datetime | None = None


class MediaSubjectDetail(MediaSubjectSummary):
    original_title: str | None = None
    overview: str | None = None
    release_date: date | None = None
    genres: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    rating: float | None = None
    rating_provider: str | None = None
    vote_count: int | None = None
    backdrop_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    snapshot_updated_at: datetime | None = None


class FollowResponse(BaseModel):
    media_subject_id: str
    followed: bool
    followed_at: datetime | None = None


class WatchlistSyncResponse(BaseModel):
    provider_id: str
    pulled_count: int
    next_cursor: str | None = None
    last_synced_at: datetime


class WatchlistPageResponse(BaseModel):
    items: list[MediaSubjectSummary]
    count: int
