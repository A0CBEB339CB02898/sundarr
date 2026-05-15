from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ResultType = Literal["all", "magnet", "quark", "aliyun", "baidu", "xunlei", "unknown"]
LinkValidationStatus = Literal["unchecked", "checking", "valid", "invalid", "unknown", "error"]


class SearchQuery(BaseModel):
    keyword: str = Field(min_length=1)
    result_type: ResultType = "all"
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    limit: int = Field(default=20, ge=1, le=50)


class RawSearchItem(BaseModel):
    source_id: str
    source_type: str
    raw_title: str
    raw_url: str | None = None
    raw_content: str
    published_at: datetime | None = None
    fetched_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class CloudLink(BaseModel):
    provider: str
    url: str
    code: str | None = None
    raw_text: str
    confidence: float = Field(ge=0, le=1)


class ResourceLinkResult(BaseModel):
    id: str
    provider: str
    name: str | None = None
    url: str
    code: str | None = None
    quality: str | None = None
    valid: bool | None = None
    validation_status: LinkValidationStatus = "unchecked"
    validation_message: str | None = None
    checked_at: datetime | None = None
    source_id: str | None = None
    source_url: str | None = None
    published_at: datetime | None = None
    is_favorited: bool = False
    favorited_at: datetime | None = None


class ResourceCandidate(BaseModel):
    id: str
    title: str
    normalized_title: str
    original_title: str | None = None
    year: int | None = None
    source_id: str
    source_url: str | None = None
    is_favorited: bool = False
    favorited_at: datetime | None = None
    links: list[ResourceLinkResult] = Field(default_factory=list)


class ResourceFavoriteRequest(BaseModel):
    id: str
    title: str
    normalized_title: str
    original_title: str | None = None
    year: int | None = None
    links: list[ResourceLinkResult] = Field(default_factory=list)


class ResourceLinkFavoriteRequest(BaseModel):
    resource: ResourceFavoriteRequest
    link: ResourceLinkResult


class SourceSearchResult(BaseModel):
    source_id: str
    source_name: str
    count: int
    results: list[ResourceCandidate] = Field(default_factory=list)
    error: str | None = None


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[ResourceCandidate]
    source_results: list[SourceSearchResult] = Field(default_factory=list)


class ResourceFavoritesListResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 20
    results: list[ResourceCandidate] = Field(default_factory=list)


class ResourceLinksFavoritesListResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 20
    results: list[ResourceLinkResult] = Field(default_factory=list)
