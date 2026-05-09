from sqlalchemy import Boolean, ForeignKey, Text
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
