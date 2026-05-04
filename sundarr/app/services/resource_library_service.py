from sqlalchemy.orm import Session

from sundarr.app.models import Resource, ResourceLink, Source
from sundarr.app.schemas.search import ResourceCandidate, ResourceLinkResult


class ResourceLibraryService:
    def save_candidates(self, db: Session, candidates: list[ResourceCandidate]) -> None:
        for candidate in candidates:
            self._ensure_source(db, candidate)
            self._upsert_resource(db, candidate)
            for link in candidate.links:
                self._upsert_link(db, candidate, link)
        db.commit()

    def get_resource(self, db: Session, resource_id: str) -> ResourceCandidate | None:
        resource = db.get(Resource, resource_id)
        if resource is None:
            return None

        links = (
            db.query(ResourceLink)
            .filter(ResourceLink.resource_id == resource_id)
            .order_by(ResourceLink.created_at.asc())
            .all()
        )
        return self._to_candidate(resource, links)

    def _ensure_source(self, db: Session, candidate: ResourceCandidate) -> None:
        if db.get(Source, candidate.source_id) is not None:
            return

        db.add(
            Source(
                id=candidate.source_id,
                name=candidate.source_id,
                type="code",
                enabled=True,
                legal_note="搜索过程中自动记录的来源占位。",
                created_by_user=False,
            )
        )

    def _upsert_resource(self, db: Session, candidate: ResourceCandidate) -> None:
        resource = db.get(Resource, candidate.id)
        if resource is None:
            resource = Resource(id=candidate.id, title=candidate.title)
            db.add(resource)

        resource.title = candidate.title
        resource.normalized_title = candidate.normalized_title
        resource.original_title = candidate.original_title
        resource.type = candidate.type
        resource.year = candidate.year
        resource.quality = candidate.quality
        resource.score = candidate.score
        resource.metadata_json = {"explanation": candidate.explanation}

    def _upsert_link(self, db: Session, candidate: ResourceCandidate, link: ResourceLinkResult) -> None:
        resource_link = db.get(ResourceLink, link.id)
        if resource_link is None:
            resource_link = ResourceLink(id=link.id, resource_id=candidate.id, provider=link.provider, url=link.url)
            db.add(resource_link)

        resource_link.resource_id = candidate.id
        resource_link.provider = link.provider
        resource_link.url = link.url
        resource_link.code = link.code
        resource_link.valid = link.valid
        resource_link.risk_level = link.risk_level
        resource_link.source_id = candidate.source_id
        resource_link.source_url = candidate.source_url

    def _to_candidate(self, resource: Resource, links: list[ResourceLink]) -> ResourceCandidate:
        explanation = "来自资源库。"
        if resource.metadata_json and isinstance(resource.metadata_json.get("explanation"), str):
            explanation = resource.metadata_json["explanation"]

        return ResourceCandidate(
            id=resource.id,
            title=resource.title,
            normalized_title=resource.normalized_title or resource.title,
            original_title=resource.original_title,
            type=resource.type or "unknown",
            year=resource.year,
            quality=resource.quality,
            score=resource.score,
            explanation=explanation,
            source_id=links[0].source_id if links and links[0].source_id else "unknown",
            source_url=links[0].source_url if links else None,
            links=[
                ResourceLinkResult(
                    id=link.id,
                    provider=link.provider,
                    url=link.url,
                    code=link.code,
                    valid=link.valid,
                    risk_level=link.risk_level,
                )
                for link in links
            ],
        )


resource_library_service = ResourceLibraryService()
