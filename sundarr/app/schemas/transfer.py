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
    "completed",
    "failed",
    "cancelled",
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
    link_id: str
    status: TransferStatus
    mode: str
    cloud_staging_path: str | None = None
    target_type: str
    target_library: str | None = None
    target_path: str
    total_bytes: int
    done_bytes: int
    progress: float = 0
    current_file: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool | None = None
    retry_count: int


class TransferLogResponse(BaseModel):
    id: str
    task_id: str
    level: str
    event: str
    message: str | None = None
    data: dict | None = None
    created_at: str
