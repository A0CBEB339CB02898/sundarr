from typing import Literal

from pydantic import BaseModel, Field


class StorageConfigRequest(BaseModel):
    type: Literal["smb"] = "smb"
    host: str = Field(min_length=1)
    port: int = Field(default=445, ge=1, le=65535)
    share: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str | None = None
    domain: str = ""
    base_path: str = "/"
    libraries: dict[str, str] = Field(default_factory=dict)


class StorageConfigResponse(BaseModel):
    type: Literal["smb"] = "smb"
    host: str = ""
    port: int = 445
    share: str = ""
    username: str = ""
    password_set: bool = False
    domain: str = ""
    base_path: str = "/"
    libraries: dict[str, str] = Field(default_factory=dict)


class StorageConfigTestResponse(BaseModel):
    ok: bool
    error_code: str | None = None
    error_message: str | None = None


class StorageBrowseEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int | None = None


class StorageBrowseResponse(BaseModel):
    path: str
    entries: list[StorageBrowseEntry] = Field(default_factory=list)
