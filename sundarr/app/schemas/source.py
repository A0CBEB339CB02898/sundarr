from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EditableSourceType = Literal["configurable", "document"]
SourceType = Literal["configurable", "document", "code"]


class SourceCreateRequest(BaseModel):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1)
    type: EditableSourceType
    enabled: bool = True
    legal_note: str | None = None
    trust_level: int = Field(default=1, ge=1, le=5)
    config_json: dict[str, Any] = Field(default_factory=dict)


class SourceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    legal_note: str | None = None
    trust_level: int | None = Field(default=None, ge=1, le=5)
    config_json: dict[str, Any] | None = None


class SourceResponse(BaseModel):
    id: str
    name: str
    type: SourceType
    enabled: bool
    legal_note: str | None = None
    trust_level: int
    created_by_user: bool
    config_json: dict[str, Any] = Field(default_factory=dict)
    last_error_code: str | None = None
    last_error_message: str | None = None


class SourceListResponse(BaseModel):
    count: int
    results: list[SourceResponse]


class SourceTestResponse(BaseModel):
    ok: bool
    source_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
