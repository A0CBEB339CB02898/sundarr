from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MediaType = Literal["movie", "tv", "anime", "unknown"]


class SearchQuery(BaseModel):
    keyword: str = Field(min_length=1)
    type: MediaType = "unknown"
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
    url: str
    code: str | None = None
    valid: bool | None = None
    risk_level: str = "unknown"


class ResourceCandidate(BaseModel):
    id: str
    title: str
    normalized_title: str
    original_title: str | None = None
    type: MediaType = "unknown"
    year: int | None = None
    quality: str | None = None
    score: float = 0
    explanation: str
    source_id: str
    source_url: str | None = None
    links: list[ResourceLinkResult] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[ResourceCandidate]
