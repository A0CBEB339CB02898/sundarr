"""媒体主体身份、外部 ID 与最小展示快照持久化。"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.models import MediaExternalId, MediaSubject
from sundarr.app.plugins.contracts import CatalogItem, CatalogProvider
from sundarr.app.schemas.discover import MediaSubjectSummary


class MediaIdentityConflictError(RuntimeError):
    """一个目录项的外部身份无法安全归并。"""


class MediaIdentityService:
    """只负责稳定媒体身份和 PostgreSQL 最小快照，不发起目录请求。"""

    def upsert_item(
        self,
        db: Session,
        provider_id: str,
        item: CatalogItem,
        *,
        now: datetime | None = None,
    ) -> MediaSubject:
        external_ids = {
            key.strip(): value.strip()
            for key, value in item.external_ids.items()
            if key.strip() and value.strip()
        }
        external_ids[provider_id] = item.external_id.strip()
        if item.external_id_provider:
            canonical_provider = item.external_id_provider.strip()
            existing_value = external_ids.get(canonical_provider)
            if existing_value is not None and existing_value != item.external_id.strip():
                raise MediaIdentityConflictError(f"目录项的 {canonical_provider} 外部 ID 声明互相冲突")
            external_ids[canonical_provider] = item.external_id.strip()

        matching_rows: list[MediaExternalId] = []
        for identity_provider, external_id in external_ids.items():
            row = (
                db.query(MediaExternalId)
                .filter(
                    MediaExternalId.provider == identity_provider,
                    MediaExternalId.external_id == external_id,
                )
                .first()
            )
            if row is not None:
                matching_rows.append(row)
        subject_ids = {row.media_subject_id for row in matching_rows}
        if len(subject_ids) > 1:
            raise MediaIdentityConflictError("同一目录项的多个外部 ID 已指向不同媒体主体，拒绝静默合并")

        timestamp = now or datetime.now(UTC)
        if subject_ids:
            subject = db.get(MediaSubject, next(iter(subject_ids)))
            if subject is None:
                raise MediaIdentityConflictError("外部 ID 指向不存在的媒体主体")
        else:
            subject = MediaSubject(
                id=uuid4().hex,
                media_type=item.media_type.value,
                canonical_title=item.title.strip(),
                release_year=item.year,
                last_known_poster_url=item.poster_url,
                last_known_poster_source=provider_id if item.poster_url else None,
                snapshot_source=provider_id,
                snapshot_updated_at=timestamp,
            )
            db.add(subject)
            db.flush()

        subject.media_type = item.media_type.value
        if item.title.strip():
            subject.canonical_title = item.title.strip()
        if item.year is not None:
            subject.release_year = item.year
        if item.poster_url:
            subject.last_known_poster_url = item.poster_url
            subject.last_known_poster_source = provider_id
        subject.snapshot_source = provider_id
        subject.snapshot_updated_at = timestamp

        known = {(row.provider, row.external_id) for row in matching_rows}
        for identity_provider, external_id in external_ids.items():
            if (identity_provider, external_id) in known:
                continue
            db.add(
                MediaExternalId(
                    id=uuid4().hex,
                    media_subject_id=subject.id,
                    provider=identity_provider,
                    external_id=external_id,
                )
            )
        db.flush()
        return subject

    def summary_from_subject(
        self,
        db: Session,
        subject: MediaSubject,
        *,
        provider_id: str | None = None,
        degraded: bool = False,
    ) -> MediaSubjectSummary:
        external_rows = (
            db.query(MediaExternalId)
            .filter(MediaExternalId.media_subject_id == subject.id)
            .order_by(MediaExternalId.created_at.asc())
            .all()
        )
        external_map = {row.provider: row.external_id for row in external_rows}
        selected_provider = provider_id or subject.snapshot_source
        external_id = external_map.get(selected_provider)
        if external_id is None and external_rows:
            selected_provider = external_rows[0].provider
            external_id = external_rows[0].external_id
        return MediaSubjectSummary(
            media_subject_id=subject.id,
            media_type=subject.media_type,
            canonical_title=subject.canonical_title,
            release_year=subject.release_year,
            poster_url=subject.last_known_poster_url,
            poster_provider_id=subject.last_known_poster_source,
            provider_id=selected_provider,
            external_id=external_id or "unknown",
            external_ids=external_map,
            followed=subject.followed_at is not None,
            watchlisted=subject.watchlisted_at is not None,
            degraded=degraded,
        )

    def find_provider_external_id(
        self,
        db: Session,
        media_subject_id: str,
        provider_id: str,
        provider: CatalogProvider,
    ) -> MediaExternalId | None:
        supported = (provider_id, *sorted(provider.describe_capabilities().identity_namespaces))
        rows = (
            db.query(MediaExternalId)
            .filter(
                MediaExternalId.media_subject_id == media_subject_id,
                MediaExternalId.provider.in_(supported),
            )
            .all()
        )
        by_namespace = {row.provider: row for row in rows}
        for namespace in supported:
            if namespace in by_namespace:
                return by_namespace[namespace]
        return None

    def refresh_flags(self, db: Session, items: list[MediaSubjectSummary]) -> None:
        subject_ids = [item.media_subject_id for item in items]
        if not subject_ids:
            return
        subjects = {
            subject.id: subject
            for subject in db.query(MediaSubject).filter(MediaSubject.id.in_(subject_ids)).all()
        }
        for item in items:
            subject = subjects.get(item.media_subject_id)
            if subject is None:
                continue
            item.canonical_title = subject.canonical_title
            item.release_year = subject.release_year
            item.poster_url = subject.last_known_poster_url
            item.followed = subject.followed_at is not None
            item.watchlisted = subject.watchlisted_at is not None


media_identity_service = MediaIdentityService()
