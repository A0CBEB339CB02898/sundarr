"""想看 Provider 的单次增量同步与持久游标管理。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.models import MediaSubject, MediaWatchlistEntry, WatchlistSyncState
from sundarr.app.plugins.contracts import WatchlistPullRequest
from sundarr.app.plugins.runtime_registry import watchlist_provider_registry
from sundarr.app.schemas.discover import (
    WatchlistPageResponse,
    WatchlistSyncResponse,
)
from sundarr.app.services.media_discovery_service import media_discovery_service


class WatchlistProviderUnavailableError(RuntimeError):
    pass


class WatchlistSyncFailedError(RuntimeError):
    pass


class WatchlistService:
    async def sync(
        self,
        db: Session,
        provider_id: str,
        *,
        limit: int = 100,
    ) -> WatchlistSyncResponse:
        provider = watchlist_provider_registry.get(provider_id)
        if provider is None:
            raise WatchlistProviderUnavailableError(f"想看 Provider 未启用：{provider_id}")
        state = db.get(WatchlistSyncState, provider_id)
        if state is None:
            state = WatchlistSyncState(provider_id=provider_id)
            db.add(state)
            db.flush()

        now = self._now()
        try:
            page = await provider.pull(WatchlistPullRequest(cursor=state.cursor, limit=limit))
            for item in page.items:
                subject = media_discovery_service.upsert_item(db, provider_id, item.subject)
                if subject.watchlisted_at is None:
                    subject.watchlisted_at = item.added_at or now
                record_key = item.external_record_id or f"subject:{subject.id}"
                entry = (
                    db.query(MediaWatchlistEntry)
                    .filter(
                        MediaWatchlistEntry.provider_id == provider_id,
                        MediaWatchlistEntry.external_record_id == record_key,
                    )
                    .first()
                )
                if entry is None:
                    entry = MediaWatchlistEntry(
                        id=uuid4().hex,
                        provider_id=provider_id,
                        external_record_id=record_key,
                        media_subject_id=subject.id,
                        added_at=item.added_at,
                        last_seen_at=now,
                        active=True,
                    )
                    db.add(entry)
                else:
                    entry.media_subject_id = subject.id
                    entry.added_at = item.added_at or entry.added_at
                    entry.last_seen_at = now
                    entry.active = True

            state.cursor = page.next_cursor
            state.last_synced_at = now
            state.last_error = None
            state.retry_count = 0
            db.commit()
            return WatchlistSyncResponse(
                provider_id=provider_id,
                pulled_count=len(page.items),
                next_cursor=page.next_cursor,
                last_synced_at=now,
            )
        except Exception as exc:
            db.rollback()
            safe_error = f"{type(exc).__name__}: 想看 Provider 调用失败"
            state = db.get(WatchlistSyncState, provider_id)
            if state is None:
                state = WatchlistSyncState(provider_id=provider_id)
                db.add(state)
            state.last_error = safe_error
            state.retry_count = (state.retry_count or 0) + 1
            db.commit()
            raise WatchlistSyncFailedError(safe_error) from exc

    def list_entries(
        self,
        db: Session,
        *,
        provider_id: str | None = None,
        limit: int = 100,
    ) -> WatchlistPageResponse:
        query = db.query(MediaWatchlistEntry).filter(MediaWatchlistEntry.active.is_(True))
        if provider_id is not None:
            query = query.filter(MediaWatchlistEntry.provider_id == provider_id)
        entries = query.order_by(MediaWatchlistEntry.added_at.desc()).limit(limit).all()
        items = []
        for entry in entries:
            subject = db.get(MediaSubject, entry.media_subject_id)
            if subject is None:
                continue
            items.append(
                media_discovery_service.summary_from_subject(
                    db,
                    subject,
                    provider_id=subject.snapshot_source,
                )
            )
        return WatchlistPageResponse(items=items, count=len(items))

    def _now(self) -> datetime:
        return datetime.now(UTC)


watchlist_service = WatchlistService()
