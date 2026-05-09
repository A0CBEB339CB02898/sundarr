from pydantic import BaseModel, Field, field_validator

from sundarr.app.schemas.media_library import MediaType


class RemoteMediaLibraryCreateRequest(BaseModel):
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
            raise ValueError("远程媒体库路径不能包含 ..。")
        return value or "/"


class RemoteMediaLibraryUpdateRequest(BaseModel):
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
            raise ValueError("远程媒体库路径不能包含 ..。")
        return value or "/"


class RemoteMediaLibraryResponse(BaseModel):
    id: str
    name: str
    media_type: MediaType
    enabled: bool
    connection_id: str
    base_path: str
    created_at: str | None = None
    updated_at: str | None = None


class RemoteMediaLibraryListResponse(BaseModel):
    count: int
    results: list[RemoteMediaLibraryResponse]


class RemoteMediaLibraryTestResponse(BaseModel):
    ok: bool
    error_code: str | None = None
    error_message: str | None = None
