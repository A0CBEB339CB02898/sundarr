from pydantic import BaseModel, Field, field_validator

from sundarr.app.schemas.media_library import MediaType


class SyncBindingCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    enabled: bool = True
    media_type: MediaType
    remote_library_id: str = Field(min_length=1)
    local_library_id: str = Field(min_length=1)
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None


class SyncBindingUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    enabled: bool = True
    media_type: MediaType
    remote_library_id: str = Field(min_length=1)
    local_library_id: str = Field(min_length=1)
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None


class SyncBindingResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    media_type: MediaType
    remote_library_id: str
    local_library_id: str
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SyncBindingListResponse(BaseModel):
    count: int
    results: list[SyncBindingResponse]


class SyncBindingTestResponse(BaseModel):
    ok: bool
    remote_ok: bool = False
    local_ok: bool = False
    error_code: str | None = None
    error_message: str | None = None


class SyncConfigRequest(BaseModel):
    delete_source_after_success: bool = True
    delete_empty_source_dirs: bool = True
    scan_interval_seconds: int = Field(default=60, ge=5, le=86400)
    stable_seconds: int = Field(default=120, ge=5, le=86400)
    unclassified_library_id: str = ""


class SyncConfigResponse(SyncConfigRequest):
    pass


class SyncScanRequest(BaseModel):
    binding_id: str | None = None
    remote_library_id: str | None = None


class SyncDiscoveredFileResponse(BaseModel):
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


class SyncScanResponse(BaseModel):
    scanned_bindings: int
    discovered_count: int
    stable_count: int
    results: list[SyncDiscoveredFileResponse] = Field(default_factory=list)


class SyncDiscoveredListResponse(BaseModel):
    count: int
    results: list[SyncDiscoveredFileResponse]


class SyncTaskCreateRequest(BaseModel):
    binding_id: str | None = None


class SyncTaskCreateResponse(BaseModel):
    created_count: int
    skipped_count: int
    tasks: list[dict] = Field(default_factory=list)
