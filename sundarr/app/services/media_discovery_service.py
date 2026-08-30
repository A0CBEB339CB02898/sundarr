"""媒体目录查询、规范身份持久化和降级编排。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.config import get_settings
from sundarr.app.models import MediaExternalId, MediaSubject
from sundarr.app.plugins.contracts import (
    CatalogCapabilities,
    CatalogItem,
    CatalogOperation,
    CatalogPage,
    CatalogProvider,
    CatalogQuery,
    MediaType,
)
from sundarr.app.plugins.runtime_registry import catalog_provider_registry
from sundarr.app.schemas.discover import (
    CatalogProviderResponse,
    DiscoverPageResponse,
    FollowResponse,
    MediaSubjectDetail,
    MediaSubjectSummary,
)
from sundarr.app.services.catalog_cache import catalog_cache


CatalogAction = Literal["search", "trending", "categories"]


class CatalogProviderUnavailableError(RuntimeError):
    pass


class CatalogQueryUnsupportedError(ValueError):
    pass


class MediaIdentityConflictError(RuntimeError):
    pass


class MediaDiscoveryService:
    def list_providers(self) -> list[CatalogProviderResponse]:
        results: list[CatalogProviderResponse] = []
        for provider_id, provider in catalog_provider_registry.snapshot().items():
            capabilities = provider.describe_capabilities()
            results.append(
                CatalogProviderResponse(
                    id=provider_id,
                    identity_namespaces=sorted(capabilities.identity_namespaces),
                    operations=sorted(item.value for item in capabilities.operations),
                    media_types=sorted(item.value for item in capabilities.media_types),
                    filters=sorted(item.value for item in capabilities.filters),
                    sorts=sorted(item.value for item in capabilities.sorts),
                    operation_filters={
                        operation.value: sorted(item.value for item in filters)
                        for operation, filters in capabilities.operation_filters.items()
                    },
                    operation_sorts={
                        operation.value: sorted(item.value for item in sorts)
                        for operation, sorts in capabilities.operation_sorts.items()
                    },
                    attribution=(
                        {
                            "provider_name": capabilities.attribution.provider_name,
                            "homepage_url": capabilities.attribution.homepage_url,
                            "notice": capabilities.attribution.notice,
                            "logo_url": capabilities.attribution.logo_url,
                        }
                        if capabilities.attribution is not None
                        else None
                    ),
                    filter_options={
                        key.value: [
                            {"value": option.value, "label": option.label}
                            for option in options
                        ]
                        for key, options in capabilities.filter_options.items()
                    },
                )
            )
        return results

    async def query(
        self,
        db: Session,
        action: CatalogAction,
        query: CatalogQuery,
        *,
        provider_id: str | None = None,
        refresh: bool = False,
    ) -> DiscoverPageResponse:
        selected_id, provider = self._select_provider(provider_id)
        capabilities = provider.describe_capabilities()
        self._validate_query(action, query, capabilities)
        cache_key = catalog_cache.make_key(
            f"page:{action}",
            {
                "provider_id": selected_id,
                "keyword": query.keyword,
                "media_type": query.media_type.value if query.media_type else None,
                "genres": query.genres,
                "regions": query.regions,
                "year_from": query.year_from,
                "year_to": query.year_to,
                "sort": query.sort.value if query.sort else None,
                "limit": query.limit,
                "continuation_token": query.continuation_token,
            },
        )
        cached = await catalog_cache.get(cache_key)
        if cached and not refresh and self._is_fresh(cached, get_settings().catalog_cache_ttl_seconds):
            return self._cached_page(db, cached, degraded=False)

        try:
            page = await self._call_provider(provider, action, query)
            response = self._persist_page(db, selected_id, page)
            await catalog_cache.set(cache_key, self._cache_payload(response))
            return response
        except (CatalogQueryUnsupportedError, MediaIdentityConflictError):
            raise
        except Exception as exc:
            db.rollback()
            if cached:
                return self._cached_page(db, cached, degraded=True)
            raise CatalogProviderUnavailableError(
                f"目录 Provider {selected_id} 当前不可用，且没有可用缓存"
            ) from exc

    async def get_detail(
        self,
        db: Session,
        media_subject_id: str,
        *,
        provider_id: str | None = None,
        refresh: bool = False,
    ) -> MediaSubjectDetail | None:
        subject = db.get(MediaSubject, media_subject_id)
        if subject is None:
            return None

        try:
            selected_id, provider = self._select_provider_for_subject(db, subject.id, provider_id)
        except CatalogProviderUnavailableError:
            return self._snapshot_detail(db, subject, degraded=True)

        external = self._find_provider_external_id(db, subject.id, selected_id, provider)
        if external is None:
            if provider_id is not None:
                raise CatalogQueryUnsupportedError(
                    f"媒体主体没有 Provider {selected_id} 可识别的外部 ID"
                )
            return self._snapshot_detail(db, subject, degraded=True)

        cache_key = catalog_cache.make_key(
            "detail",
            {
                "provider_id": selected_id,
                "external_id": external.external_id,
                "media_type": subject.media_type,
            },
        )
        cached = await catalog_cache.get(cache_key)
        if cached and not refresh and self._is_fresh(cached, get_settings().catalog_detail_cache_ttl_seconds):
            return self._cached_detail(db, cached, degraded=False)

        try:
            item = await provider.get_detail(
                external.external_id,
                MediaType(subject.media_type),
            )
            stored = self.upsert_item(db, selected_id, item)
            db.commit()
            db.refresh(stored)
            detail = self._detail_from_item(db, stored, selected_id, item)
            await catalog_cache.set(cache_key, self._cache_payload(detail))
            return detail
        except (CatalogQueryUnsupportedError, MediaIdentityConflictError):
            raise
        except Exception:
            db.rollback()
            if cached:
                return self._cached_detail(db, cached, degraded=True)
            subject = db.get(MediaSubject, media_subject_id)
            return self._snapshot_detail(db, subject, degraded=True) if subject else None

    def set_followed(self, db: Session, media_subject_id: str, followed: bool) -> FollowResponse | None:
        subject = db.get(MediaSubject, media_subject_id)
        if subject is None:
            return None
        subject.followed_at = self._now() if followed else None
        db.commit()
        db.refresh(subject)
        return FollowResponse(
            media_subject_id=subject.id,
            followed=subject.followed_at is not None,
            followed_at=subject.followed_at,
        )

    def upsert_item(self, db: Session, provider_id: str, item: CatalogItem) -> MediaSubject:
        external_ids = {key.strip(): value.strip() for key, value in item.external_ids.items() if key.strip() and value.strip()}
        external_ids[provider_id] = item.external_id.strip()
        if item.external_id_provider:
            canonical_provider = item.external_id_provider.strip()
            existing_value = external_ids.get(canonical_provider)
            if existing_value is not None and existing_value != item.external_id.strip():
                raise MediaIdentityConflictError(
                    f"目录项的 {canonical_provider} 外部 ID 声明互相冲突"
                )
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

        now = self._now()
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
                snapshot_source=provider_id,
                snapshot_updated_at=now,
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
        subject.snapshot_source = provider_id
        subject.snapshot_updated_at = now

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
            provider_id=selected_provider,
            external_id=external_id or "unknown",
            external_ids=external_map,
            followed=subject.followed_at is not None,
            watchlisted=subject.watchlisted_at is not None,
            degraded=degraded,
        )

    def _persist_page(self, db: Session, provider_id: str, page: CatalogPage) -> DiscoverPageResponse:
        pairs: list[tuple[MediaSubject, CatalogItem]] = []
        for item in page.items:
            pairs.append((self.upsert_item(db, provider_id, item), item))
        db.commit()
        items = [self._summary_from_item(db, subject, provider_id, item) for subject, item in pairs]
        return DiscoverPageResponse(
            items=items,
            continuation_token=page.continuation_token,
            provider_id=provider_id,
            degraded=False,
            cached_at=self._now(),
        )

    def _summary_from_item(
        self,
        db: Session,
        subject: MediaSubject,
        provider_id: str,
        item: CatalogItem,
    ) -> MediaSubjectSummary:
        summary = self.summary_from_subject(db, subject, provider_id=provider_id)
        summary.external_id = item.external_id
        return summary

    def _detail_from_item(
        self,
        db: Session,
        subject: MediaSubject,
        provider_id: str,
        item: CatalogItem,
    ) -> MediaSubjectDetail:
        summary = self._summary_from_item(db, subject, provider_id, item)
        return MediaSubjectDetail(
            **summary.model_dump(),
            original_title=item.original_title,
            overview=item.overview,
            release_date=item.release_date,
            genres=list(item.genres),
            regions=list(item.regions),
            rating=item.rating,
            rating_provider=provider_id if item.rating is not None else None,
            vote_count=item.vote_count,
            backdrop_url=item.backdrop_url,
            image_urls=list(item.image_urls),
            snapshot_updated_at=subject.snapshot_updated_at,
        )

    def _snapshot_detail(self, db: Session, subject: MediaSubject, *, degraded: bool) -> MediaSubjectDetail:
        summary = self.summary_from_subject(db, subject, degraded=degraded)
        return MediaSubjectDetail(
            **summary.model_dump(),
            snapshot_updated_at=subject.snapshot_updated_at,
        )

    def _select_provider(self, provider_id: str | None) -> tuple[str, CatalogProvider]:
        providers = catalog_provider_registry.snapshot()
        if provider_id is not None:
            provider = providers.get(provider_id)
            if provider is None:
                raise CatalogProviderUnavailableError(f"目录 Provider 未启用：{provider_id}")
            return provider_id, provider
        try:
            return next(iter(providers.items()))
        except StopIteration as exc:
            raise CatalogProviderUnavailableError("当前没有已启用的目录 Provider") from exc

    def _select_provider_for_subject(
        self,
        db: Session,
        media_subject_id: str,
        provider_id: str | None,
    ) -> tuple[str, CatalogProvider]:
        if provider_id is not None:
            return self._select_provider(provider_id)
        providers = catalog_provider_registry.snapshot()
        identities = {
            row.provider
            for row in db.query(MediaExternalId)
            .filter(MediaExternalId.media_subject_id == media_subject_id)
            .all()
        }
        for current_id, provider in providers.items():
            namespaces = provider.describe_capabilities().identity_namespaces
            if current_id in identities or identities.intersection(namespaces):
                return current_id, provider
        raise CatalogProviderUnavailableError("当前没有能识别该媒体主体的目录 Provider")

    def _find_provider_external_id(
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

    def _validate_query(
        self,
        action: CatalogAction,
        query: CatalogQuery,
        capabilities: CatalogCapabilities,
    ) -> None:
        operation = CatalogOperation(action)
        if operation not in capabilities.operations:
            raise CatalogQueryUnsupportedError(f"目录 Provider 不支持 {operation.value} 操作")
        if query.media_type is not None and query.media_type not in capabilities.media_types:
            raise CatalogQueryUnsupportedError(f"目录 Provider 不支持媒体类型：{query.media_type.value}")
        requested_filters = []
        if query.media_type is not None:
            requested_filters.append("media_type")
        if query.genres:
            requested_filters.append("genre")
        if query.regions:
            requested_filters.append("region")
        if query.year_from is not None or query.year_to is not None:
            requested_filters.append("year")
        supported_filters = {item.value for item in capabilities.filters_for(operation)}
        unsupported = [item for item in requested_filters if item not in supported_filters]
        if unsupported:
            raise CatalogQueryUnsupportedError(
                f"目录 Provider 不支持筛选：{'、'.join(unsupported)}"
            )
        if query.sort is not None and query.sort not in capabilities.sorts_for(operation):
            raise CatalogQueryUnsupportedError(f"目录 Provider 不支持排序：{query.sort.value}")

    async def _call_provider(
        self,
        provider: CatalogProvider,
        action: CatalogAction,
        query: CatalogQuery,
    ) -> CatalogPage:
        if action == "search":
            return await provider.search(query)
        if action == "trending":
            return await provider.trending(query)
        return await provider.categories(query)

    def _cache_payload(self, response: DiscoverPageResponse | MediaSubjectDetail) -> dict[str, object]:
        return {
            "cached_at": self._now().isoformat(),
            "response": response.model_dump(mode="json"),
        }

    def _is_fresh(self, cached: dict[str, object], ttl_seconds: int) -> bool:
        cached_at_value = cached.get("cached_at")
        if not isinstance(cached_at_value, str):
            return False
        try:
            cached_at = datetime.fromisoformat(cached_at_value)
        except ValueError:
            return False
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=UTC)
        return (self._now() - cached_at).total_seconds() <= ttl_seconds

    def _cached_page(self, db: Session, cached: dict[str, object], *, degraded: bool) -> DiscoverPageResponse:
        response = DiscoverPageResponse.model_validate(cached.get("response"))
        response.degraded = degraded
        for item in response.items:
            item.degraded = degraded
        self._refresh_flags(db, response.items)
        return response

    def _cached_detail(self, db: Session, cached: dict[str, object], *, degraded: bool) -> MediaSubjectDetail:
        response = MediaSubjectDetail.model_validate(cached.get("response"))
        response.degraded = degraded
        self._refresh_flags(db, [response])
        return response

    def _refresh_flags(self, db: Session, items: list[MediaSubjectSummary]) -> None:
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
            item.followed = subject.followed_at is not None
            item.watchlisted = subject.watchlisted_at is not None

    def _now(self) -> datetime:
        return datetime.now(UTC)


media_discovery_service = MediaDiscoveryService()
