from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin
from sundarr.app.models.types import JsonObject


class IngestBinding(TimestampMixin, Base):
    __tablename__ = "ingest_bindings"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_smb_json: Mapped[dict] = mapped_column(JsonObject, nullable=False)
    target_smb_json: Mapped[dict] = mapped_column(JsonObject, nullable=False)
    delete_source_after_success: Mapped[bool | None] = mapped_column()
    delete_empty_source_dirs: Mapped[bool | None] = mapped_column()


class IngestSeenFile(TimestampMixin, Base):
    __tablename__ = "ingest_seen_files"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    binding_id: Mapped[str | None] = mapped_column(ForeignKey("ingest_bindings.id"))
    source_fingerprint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_size: Mapped[int | None] = mapped_column(BigInteger)
    source_mtime: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("transfer_tasks.id"))
