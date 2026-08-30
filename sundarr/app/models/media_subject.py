"""媒体发现中心的持久事实模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sundarr.app.core.database import Base
from sundarr.app.models.mixins import TimestampMixin


class MediaSubject(TimestampMixin, Base):
    """不依赖任何单一目录平台的规范媒体身份。"""

    __tablename__ = "media_subjects"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    media_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    canonical_title: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    release_year: Mapped[int | None] = mapped_column(Integer, index=True)
    last_known_poster_url: Mapped[str | None] = mapped_column(Text)
    snapshot_source: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    followed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    watchlisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class MediaExternalId(TimestampMixin, Base):
    """媒体主体在一个外部平台中的精确身份。"""

    __tablename__ = "media_external_ids"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_media_external_provider_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    media_subject_id: Mapped[str] = mapped_column(
        ForeignKey("media_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)


class WatchlistSyncState(TimestampMixin, Base):
    """Core 为一个想看插件保存的增量游标和错误状态。"""

    __tablename__ = "watchlist_sync_states"

    provider_id: Mapped[str] = mapped_column(Text, primary_key=True)
    cursor: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class MediaWatchlistEntry(TimestampMixin, Base):
    """一个外部想看列表条目与规范媒体主体的绑定。"""

    __tablename__ = "media_watchlist_entries"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "external_record_id",
            name="uq_watchlist_provider_record",
        ),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    external_record_id: Mapped[str] = mapped_column(Text, nullable=False)
    media_subject_id: Mapped[str] = mapped_column(
        ForeignKey("media_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
