from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

class SourceResponse(BaseModel):
    id: str
    name: str
    description: str
    homepage_url: str


class SourceListResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 20
    results: list[SourceResponse]


class SourceTestRequest(BaseModel):
    keyword: str = Field(default="星际穿越", min_length=1)
    result_type: str = "all"
    limit: int = Field(default=5, ge=1, le=20)


class SourceTestLog(BaseModel):
    step: str
    status: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class SourceTestResponse(BaseModel):
    ok: bool
    source_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    logs: list[SourceTestLog] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
