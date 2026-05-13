from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SmbConnectionCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    enabled: bool = True
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
        normalized = value.replace("\\", "/").replace("//", "/").rstrip("/") or "/"
        if ".." in normalized.split("/"):
            raise ValueError("SMB 路径不能包含 ..。")
        return normalized


class SmbConnectionUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    enabled: bool = True
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
        normalized = value.replace("\\", "/").replace("//", "/").rstrip("/") or "/"
        if ".." in normalized.split("/"):
            raise ValueError("SMB 路径不能包含 ..。")
        return normalized


class SmbConnectionResponse(BaseModel):
    id: str
    name: str
    enabled: bool
    host: str
    port: int
    share: str
    username: str
    password_set: bool
    domain: str = ""
    base_path: str = "/"
    bound_local_libraries: list[str] = Field(default_factory=list)
    bound_remote_libraries: list[str] = Field(default_factory=list)
    last_test_ok: bool | None = None
    last_test_error_code: str | None = None
    last_test_error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SmbConnectionListResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 20
    results: list[SmbConnectionResponse]


class SmbConnectionTestResponse(BaseModel):
    ok: bool
    error_code: str | None = None
    error_message: str | None = None


class SmbBrowseEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int | None = None
    modified_at: str | None = None


class SmbBrowseResponse(BaseModel):
    connection_id: str
    path: str
    entries: list[SmbBrowseEntry] = Field(default_factory=list)


class SmbConnectionDeleteRequest(BaseModel):
    action: str = Field(pattern="^(delete|unbind|cancel)$")


class SmbConnectionDeletePreview(BaseModel):
    affected_local_libraries: list[str] = Field(default_factory=list)
    affected_remote_libraries: list[str] = Field(default_factory=list)
    affected_sync_bindings: int = 0
    affected_tasks: int = 0
