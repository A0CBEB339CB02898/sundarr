from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    legal_note: Mapped[str | None] = mapped_column(Text)
    trust_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    last_error_code: Mapped[str | None] = mapped_column(Text)
    last_error_message: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
