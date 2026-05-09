from sqlalchemy import BigInteger, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin


class DownloadToLocalBinding(TimestampMixin, Base):
    __tablename__ = "download_to_local_bindings"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_connection_id: Mapped[str] = mapped_column(ForeignKey("smb_connections.id"), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_library_id: Mapped[str] = mapped_column(ForeignKey("media_libraries.id"), nullable=False)
    delete_source_after_success: Mapped[bool | None] = mapped_column()
    delete_empty_source_dirs: Mapped[bool | None] = mapped_column()


class DownloadToLocalSeenFile(TimestampMixin, Base):
    __tablename__ = "download_to_local_seen_files"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    binding_id: Mapped[str | None] = mapped_column(ForeignKey("download_to_local_bindings.id"), index=True)
    source_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_size: Mapped[int | None] = mapped_column(BigInteger)
    source_mtime: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("transfer_tasks.id"))
