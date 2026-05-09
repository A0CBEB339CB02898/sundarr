from typing import Literal

from pydantic import BaseModel, Field, field_validator

MediaType = Literal["movie", "series", "unclassified"]


class MediaLibraryCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    media_type: MediaType
    enabled: bool = True
    connection_id: str = Field(min_length=1)
    base_path: str = "/"

    @field_validator("base_path")
    @classmethod
    def reject_unsafe_base_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("媒体库路径不能包含 ..。")
        return value or "/"


class MediaLibraryUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    media_type: MediaType
    enabled: bool = True
    connection_id: str = Field(min_length=1)
    base_path: str = "/"

    @field_validator("base_path")
    @classmethod
    def reject_unsafe_base_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("媒体库路径不能包含 ..。")
        return value or "/"


class MediaLibraryResponse(BaseModel):
    id: str
    name: str
    media_type: MediaType
    enabled: bool
    connection_id: str
    base_path: str
    bound_remote_libraries: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class MediaLibraryListResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 20
    results: list[MediaLibraryResponse]


class MediaLibraryTestResponse(BaseModel):
    ok: bool
    error_code: str | None = None
    error_message: str | None = None


class MediaLibraryDeleteRequest(BaseModel):
    action: str = Field(pattern="^(delete|unbind|cancel)$")


class MediaLibraryDeletePreview(BaseModel):
    affected_remote_libraries: list[str] = Field(default_factory=list)
    affected_sync_bindings: int = 0
    affected_tasks: int = 0
