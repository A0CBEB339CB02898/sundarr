from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin


class RemoteMediaLibrary(TimestampMixin, Base):
    __tablename__ = "remote_media_libraries"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    connection_id: Mapped[str] = mapped_column(ForeignKey("smb_connections.id"), nullable=False)
    base_path: Mapped[str] = mapped_column(Text, nullable=False, default="/", server_default="/")
    target_library_id: Mapped[str | None] = mapped_column(ForeignKey("media_libraries.id"), nullable=True)
    scan_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default="60")
    stable_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120, server_default="120")
    delete_source_after_success: Mapped[bool | None] = mapped_column()
    delete_empty_source_dirs: Mapped[bool | None] = mapped_column()
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_test_error_code: Mapped[str | None] = mapped_column(Text)
    last_test_error_message: Mapped[str | None] = mapped_column(Text)
