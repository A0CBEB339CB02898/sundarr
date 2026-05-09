from typing import Literal

from pydantic import BaseModel, Field, field_validator

from sundarr.app.schemas.transfer import TransferResponse

MediaType = Literal["movie", "series", "unclassified"]


class DtlConfigRequest(BaseModel):
    delete_source_after_success: bool = True
    delete_empty_source_dirs: bool = True
    scan_interval_seconds: int = Field(default=60, ge=5, le=86400)
    stable_seconds: int = Field(default=120, ge=5, le=86400)
    unclassified_library_id: str = ""


class DtlConfigResponse(DtlConfigRequest):
    pass


class DtlBindingCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    enabled: bool = True
    media_type: MediaType
    source_connection_id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    target_library_id: str = Field(min_length=1)
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None

    @field_validator("source_path")
    @classmethod
    def reject_unsafe_source_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("来源路径不能包含 ..。")
        return value


class DtlBindingUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    enabled: bool = True
    media_type: MediaType
    source_connection_id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    target_library_id: str = Field(min_length=1)
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None

    @field_validator("source_path")
    @classmethod
    def reject_unsafe_source_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("来源路径不能包含 ..。")
        return value


class DtlBindingResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    media_type: MediaType
    source_connection_id: str
    source_path: str
    target_library_id: str
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DtlBindingListResponse(BaseModel):
    count: int
    results: list[DtlBindingResponse]


class DtlBindingTestResponse(BaseModel):
    ok: bool
    source_ok: bool = False
    target_ok: bool = False
    error_code: str | None = None
    error_message: str | None = None


class DtlScanRequest(BaseModel):
    binding_id: str | None = None


class DtlDiscoveredFileResponse(BaseModel):
    id: str
    binding_id: str | None = None
    source_fingerprint: str
    source_path: str
    source_size: int | None = None
    source_mtime: str | None = None
    status: str
    task_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DtlScanResponse(BaseModel):
    scanned_bindings: int
    discovered_count: int
    stable_count: int
    results: list[DtlDiscoveredFileResponse] = Field(default_factory=list)


class DtlDiscoveredListResponse(BaseModel):
    count: int
    results: list[DtlDiscoveredFileResponse]


class DtlTaskCreateRequest(BaseModel):
    binding_id: str | None = None


class DtlTaskCreateResponse(BaseModel):
    created_count: int
    skipped_count: int
    tasks: list[TransferResponse] = Field(default_factory=list)
