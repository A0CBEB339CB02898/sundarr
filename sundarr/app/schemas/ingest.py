from typing import Literal

from pydantic import BaseModel, Field, field_validator

from sundarr.app.schemas.transfer import TransferResponse

IngestMediaType = Literal["movie", "series", "unclassified"]


class IngestSmbEndpointRequest(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(default=445, ge=1, le=65535)
    share: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str | None = None
    domain: str = ""
    base_path: str = "/"

    @field_validator("base_path")
    @classmethod
    def reject_unsafe_base_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("SMB 路径不能包含 ..。")
        return value or "/"


class IngestSmbEndpointResponse(BaseModel):
    host: str = ""
    port: int = 445
    share: str = ""
    username: str = ""
    password_set: bool = False
    domain: str = ""
    base_path: str = "/"


class IngestConfigRequest(BaseModel):
    delete_source_after_success: bool = True
    delete_empty_source_dirs: bool = True
    scan_interval_seconds: int = Field(default=60, ge=5, le=86400)
    stable_seconds: int = Field(default=120, ge=5, le=86400)
    unclassified_target_path: str = "/unclassified"

    @field_validator("unclassified_target_path")
    @classmethod
    def reject_unsafe_unclassified_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("未分类目录不能包含 ..。")
        return value or "/unclassified"


class IngestConfigResponse(IngestConfigRequest):
    pass


class IngestBindingCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    enabled: bool = True
    media_type: IngestMediaType
    source_smb: IngestSmbEndpointRequest
    target_smb: IngestSmbEndpointRequest
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None


class IngestBindingUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    enabled: bool = True
    media_type: IngestMediaType
    source_smb: IngestSmbEndpointRequest
    target_smb: IngestSmbEndpointRequest
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None


class IngestBindingResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    media_type: IngestMediaType
    source_smb: IngestSmbEndpointResponse
    target_smb: IngestSmbEndpointResponse
    delete_source_after_success: bool | None = None
    delete_empty_source_dirs: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IngestBindingListResponse(BaseModel):
    count: int
    results: list[IngestBindingResponse]


class IngestBindingTestResponse(BaseModel):
    ok: bool
    source_ok: bool = False
    target_ok: bool = False
    error_code: str | None = None
    error_message: str | None = None


class IngestScanRequest(BaseModel):
    binding_id: str | None = None


class IngestDiscoveredFileResponse(BaseModel):
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


class IngestScanResponse(BaseModel):
    scanned_bindings: int
    discovered_count: int
    stable_count: int
    results: list[IngestDiscoveredFileResponse] = Field(default_factory=list)


class IngestDiscoveredListResponse(BaseModel):
    count: int
    results: list[IngestDiscoveredFileResponse]


class IngestTaskCreateRequest(BaseModel):
    binding_id: str | None = None


class IngestTaskCreateResponse(BaseModel):
    created_count: int
    skipped_count: int
    tasks: list[TransferResponse] = Field(default_factory=list)
