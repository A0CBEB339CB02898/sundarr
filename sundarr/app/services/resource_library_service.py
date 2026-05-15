from datetime import UTC, datetime

from sqlalchemy.orm import Session

from sundarr.app.models import Resource, ResourceLink
from sundarr.app.schemas.search import (
    ResourceCandidate,
    ResourceFavoriteRequest,
    ResourceLinkFavoriteRequest,
    ResourceLinkResult,
    SearchQuery,
    SearchResponse,
)
from sundarr.app.services.search_service import search_service


class ResourceLibraryService:
    def mark_favorites(self, db: Session, candidates: list[ResourceCandidate]) -> list[ResourceCandidate]:
        if not candidates:
            return candidates

        resource_map = {
            resource.id: resource
            for resource in db.query(Resource).filter(Resource.id.in_([candidate.id for candidate in candidates])).all()
        }
        link_map = {
            link.id: link
            for link in db.query(ResourceLink).filter(ResourceLink.id.in_([link.id for candidate in candidates for link in candidate.links])).all()
        }
        for candidate in candidates:
            stored_resource = resource_map.get(candidate.id)
            if stored_resource and stored_resource.favorited_at is not None:
                candidate.is_favorited = True
                candidate.favorited_at = stored_resource.favorited_at
            for link in candidate.links:
                stored_link = link_map.get(link.id)
                if stored_link and stored_link.favorited_at is not None:
                    link.is_favorited = True
                    link.favorited_at = stored_link.favorited_at
        return candidates

    def favorite_resource(self, db: Session, request: ResourceFavoriteRequest) -> ResourceCandidate:
        resource = self._get_or_create_resource(db, request)
        resource.favorited_at = self._now()
        for link in request.links:
            resource_link = db.get(ResourceLink, link.id)
            if resource_link is None:
                resource_link = ResourceLink(
                    id=link.id,
                    resource_id=resource.id,
                    provider=link.provider,
                    name=link.name,
                    url=link.url,
                    favorited_at=self._now(),
                )
                db.add(resource_link)
            resource_link.resource_id = resource.id
            resource_link.provider = link.provider
            resource_link.name = link.name
            resource_link.url = link.url
            resource_link.code = link.code
            resource_link.quality = link.quality
            resource_link.valid = link.valid
            resource_link.last_checked_at = link.checked_at
            resource_link.source_id = link.source_id
            resource_link.source_url = link.source_url
            resource_link.published_at = link.published_at
            resource_link.favorited_at = self._now()
        db.commit()
        db.refresh(resource)
        return self._to_candidate(resource, self._get_links(db, resource.id))

    def unfavorite_resource(self, db: Session, resource_id: str) -> bool:
        resource = db.get(Resource, resource_id)
        if resource is None:
            return False
        resource.favorited_at = None
        db.commit()
        return True

    def list_favorite_resources(self, db: Session, page: int = 1, page_size: int = 20) -> tuple[int, list[ResourceCandidate]]:
        base_q = db.query(Resource).filter(Resource.favorited_at.is_not(None))
        count = base_q.count()
        resources = (
            base_q
            .order_by(Resource.favorited_at.desc(), Resource.updated_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
            .all()
        )
        return count, [self._to_candidate(resource, self._get_links(db, resource.id)) for resource in resources]

    def get_resource(self, db: Session, resource_id: str) -> ResourceCandidate | None:
        resource = db.get(Resource, resource_id)
        if resource is None:
            return None
        return self._to_candidate(resource, self._get_links(db, resource_id))

    async def refresh_resource(self, db: Session, resource_id: str) -> SearchResponse | None:
        resource = db.get(Resource, resource_id)
        if resource is None:
            return None
        keyword = resource.original_title or resource.title
        response = await search_service.search(SearchQuery(keyword=keyword, year=resource.year))
        self.mark_favorites(db, response.results)
        for source_result in response.source_results:
            self.mark_favorites(db, source_result.results)
        return response

    def favorite_link(self, db: Session, request: ResourceLinkFavoriteRequest) -> ResourceLinkResult:
        resource = self._get_or_create_resource(db, request.resource)
        resource_link = db.get(ResourceLink, request.link.id)
        if resource_link is None:
            resource_link = ResourceLink(
                id=request.link.id,
                resource_id=resource.id,
                provider=request.link.provider,
                name=request.link.name,
                url=request.link.url,
                favorited_at=self._now(),
            )
            db.add(resource_link)

        resource_link.resource_id = resource.id
        resource_link.provider = request.link.provider
        resource_link.name = request.link.name
        resource_link.url = request.link.url
        resource_link.code = request.link.code
        resource_link.quality = request.link.quality
        resource_link.valid = request.link.valid
        resource_link.last_checked_at = request.link.checked_at
        resource_link.source_id = request.link.source_id
        resource_link.source_url = request.link.source_url
        resource_link.published_at = request.link.published_at
        resource_link.favorited_at = self._now()
        db.commit()
        db.refresh(resource_link)
        return self._to_link_result(resource_link)

    def unfavorite_link(self, db: Session, link_id: str) -> bool:
        resource_link = db.get(ResourceLink, link_id)
        if resource_link is None:
            return False
        resource_id = resource_link.resource_id
        db.delete(resource_link)
        db.flush()
        resource = db.get(Resource, resource_id)
        if resource is not None and resource.favorited_at is None:
            has_links = db.query(ResourceLink).filter(ResourceLink.resource_id == resource_id).first() is not None
            if not has_links:
                db.delete(resource)
        db.commit()
        return True

    def list_favorite_links(self, db: Session, page: int = 1, page_size: int = 20) -> tuple[int, list[ResourceLinkResult]]:
        base_q = db.query(ResourceLink).filter(ResourceLink.favorited_at.is_not(None))
        count = base_q.count()
        links = (
            base_q
            .order_by(ResourceLink.favorited_at.desc(), ResourceLink.updated_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
            .all()
        )
        return count, [self._to_link_result(link) for link in links]

    def get_link(self, db: Session, link_id: str) -> ResourceLinkResult | None:
        link = db.get(ResourceLink, link_id)
        return self._to_link_result(link) if link is not None else None


    def _get_or_create_resource(self, db: Session, request: ResourceFavoriteRequest) -> Resource:
        resource = db.get(Resource, request.id)
        if resource is None:
            resource = Resource(id=request.id, title=request.title, normalized_title=request.normalized_title)
            db.add(resource)
        resource.title = request.title
        resource.normalized_title = request.normalized_title
        resource.original_title = request.original_title
        resource.year = request.year
        return resource

    def _get_links(self, db: Session, resource_id: str) -> list[ResourceLink]:
        return (
            db.query(ResourceLink)
            .filter(ResourceLink.resource_id == resource_id)
            .order_by(ResourceLink.created_at.asc())
            .all()
        )

    def _to_candidate(self, resource: Resource, links: list[ResourceLink]) -> ResourceCandidate:
        return ResourceCandidate(
            id=resource.id,
            title=resource.title,
            normalized_title=resource.normalized_title or resource.title,
            original_title=resource.original_title,
            year=resource.year,
            source_id=links[0].source_id if links and links[0].source_id else "favorite",
            source_url=links[0].source_url if links else None,
            is_favorited=resource.favorited_at is not None,
            favorited_at=resource.favorited_at,
            links=[self._to_link_result(link) for link in links],
        )

    def _to_link_result(self, link: ResourceLink) -> ResourceLinkResult:
        return ResourceLinkResult(
            id=link.id,
            provider=link.provider,
            name=link.name,
            url=link.url,
            code=link.code,
            quality=link.quality,
            valid=link.valid,
            checked_at=link.last_checked_at,
            source_id=link.source_id,
            source_url=link.source_url,
            published_at=link.published_at,
            is_favorited=link.favorited_at is not None,
            favorited_at=link.favorited_at,
            validation_status="valid" if link.valid is True else "invalid" if link.valid is False else "unknown",
        )

    def _now(self) -> datetime:
        return datetime.now(UTC)


resource_library_service = ResourceLibraryService()
