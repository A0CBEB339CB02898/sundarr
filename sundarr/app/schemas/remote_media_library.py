from pydantic import BaseModel, Field, field_validator

from sundarr.app.schemas.media_library import MediaType


class RemoteMediaLibraryCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    media_type: MediaType
    enabled: bool = True
    connection_id: str = Field(min_length=1)
    base_path: str = "/"
    target_library_id: str | None = None
    scan_interval_seconds: int = Field(default=60, ge=5, le=86400)
    stable_seconds: int = Field(default=120, ge=5, le=86400)
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None

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
    target_library_id: str | None = None
    scan_interval_seconds: int = Field(default=60, ge=5, le=86400)
    stable_seconds: int = Field(default=120, ge=5, le=86400)
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None

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
    target_library_id: str | None = None
    target_library_name: str | None = None
    scan_interval_seconds: int = 60
    stable_seconds: int = 120
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RemoteMediaLibraryListResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 20
    results: list[RemoteMediaLibraryResponse]


class RemoteMediaLibraryTestResponse(BaseModel):
    ok: bool
    error_code: str | None = None
    error_message: str | None = None


class RemoteMediaLibraryDeleteRequest(BaseModel):
    action: str = Field(pattern="^(delete|cancel)$")


class RemoteMediaLibraryDeletePreview(BaseModel):
    affected_sync_files: int = 0
    affected_tasks: int = 0
