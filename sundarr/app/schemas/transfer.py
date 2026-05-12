from typing import Literal

from pydantic import BaseModel, Field

TransferStatus = Literal[
    "pending",
    "staging_to_cloud",
    "cloud_ready",
    "downloading",
    "verifying",
    "renaming",
    "cleaning_cloud",
    "cleaning_source",
    "completed",
    "failed",
    "cancelled",
    "paused",
]


class TransferCreateRequest(BaseModel):
    link_id: str = Field(min_length=1)
    mode: str = "copy"
    target_type: Literal["smb"] = "smb"
    target_library: str | None = None
    target_path: str = Field(min_length=1)


class TransferResponse(BaseModel):
    id: str
    resource_id: str | None = None
    link_id: str | None = None
    status: TransferStatus
    mode: str
    cloud_staging_path: str | None = None
    target_type: str
    target_library: str | None = None
    target_path: str
    source_type: str | None = None
    source_path: str | None = None
    sync_seen_file_id: str | None = None
    total_bytes: int
    done_bytes: int
    speed_bytes_per_sec: int = 0
    progress: float = 0
    current_file: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool | None = None
    retry_count: int
    created_at: str | None = None
    updated_at: str | None = None


class TransferListResponse(BaseModel):
    count: int
    page: int = 1
    page_size: int = 20
    results: list[TransferResponse]


class TransferLogResponse(BaseModel):
    id: str
    task_id: str
    level: str
    event: str
    message: str | None = None
    data: dict | None = None
    created_at: str
