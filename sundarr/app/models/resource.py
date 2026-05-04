from typing import Any

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin
from sundarr.app.models.types import JsonObject


class Resource(TimestampMixin, Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str | None] = mapped_column(Text)
    original_title: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    season: Mapped[int | None] = mapped_column(Integer)
    episodes: Mapped[str | None] = mapped_column(Text)
    quality: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    subtitle: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    poster: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JsonObject)


class ResourceLink(TimestampMixin, Base):
    __tablename__ = "resource_links"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"))
    source_url: Mapped[str | None] = mapped_column(Text)
    valid: Mapped[bool | None] = mapped_column(Boolean)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, default="unknown", server_default="unknown")
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default="unknown", server_default="unknown")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
