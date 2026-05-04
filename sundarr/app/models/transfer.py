from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin
from sundarr.app.models.types import JsonObject


class TransferTask(TimestampMixin, Base):
    __tablename__ = "transfer_tasks"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id"))
    link_id: Mapped[str] = mapped_column(ForeignKey("resource_links.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    cloud_staging_path: Mapped[str | None] = mapped_column(Text)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_library: Mapped[str | None] = mapped_column(Text)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JsonObject)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    done_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    speed_bytes_per_sec: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    retryable: Mapped[bool | None] = mapped_column(Boolean)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TransferFile(TimestampMixin, Base):
    __tablename__ = "transfer_files"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("transfer_tasks.id"), nullable=False, index=True)
    cloud_file_id: Mapped[str | None] = mapped_column(Text)
    cloud_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    temp_path: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    done_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)


class TransferLog(Base):
    __tablename__ = "transfer_logs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("transfer_tasks.id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    data_json: Mapped[dict[str, Any] | None] = mapped_column(JsonObject)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
