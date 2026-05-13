from sqlalchemy.orm import Session

from sundarr.app.models import Source
from sundarr.app.schemas.source import (
    SourceCreateRequest,
    SourceListResponse,
    SourceResponse,
    SourceTestResponse,
    SourceUpdateRequest,
)
from sundarr.app.sources import get_registered_sources


class SourceService:
    def list_sources(self, db: Session, page: int = 1, page_size: int = 20) -> SourceListResponse:
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 100))
        registered = [self._registered_to_response(source) for source in get_registered_sources()]
        stored = {source.id: source for source in db.query(Source).all()}
        results = [
            self._merge_registered_response(response, stored.get(response.id))
            for response in registered
        ]
        count = len(results)
        results = results[(safe_page - 1) * safe_page_size : safe_page * safe_page_size]
        return SourceListResponse(count=count, page=safe_page, page_size=safe_page_size, results=results)

    def get_source(self, db: Session, source_id: str) -> SourceResponse | None:
        registered = next((source for source in get_registered_sources() if source.id == source_id), None)
        if registered is None:
            return None
        return self._merge_registered_response(self._registered_to_response(registered), db.get(Source, source_id))

    def create_source(self, db: Session, request: SourceCreateRequest) -> SourceResponse:
        raise ValueError("SOURCE_CODE_ONLY")

    def update_source(self, db: Session, source_id: str, request: SourceUpdateRequest) -> SourceResponse | None:
        if self.get_source(db, source_id) is None:
            return None
        raise ValueError("SOURCE_CODE_ONLY")

    def set_enabled(self, db: Session, source_id: str, enabled: bool) -> SourceResponse | None:
        if self.get_source(db, source_id) is None:
            return None
        raise ValueError("SOURCE_CODE_ONLY")

    def test_source(self, db: Session, source_id: str) -> SourceTestResponse | None:
        source = self.get_source(db, source_id)
        if source is None:
            return None
        return SourceTestResponse(
            ok=True,
            source_id=source.id,
            items=[
                {
                    "source_id": source.id,
                    "source_type": source.type,
                    "raw_title": source.name,
                    "raw_url": "",
                    "raw_content": "代码型搜索源已注册，实际连通性由 /search 聚合链路验证。",
                }
            ],
        )

    def _registered_to_response(self, source) -> SourceResponse:
        descriptor = source.describe()
        return SourceResponse(
            id=descriptor.id,
            name=descriptor.name,
            type="code",
            enabled=descriptor.enabled,
            legal_note=descriptor.legal_note,
            trust_level=3,
            created_by_user=False,
            config_json={"description": descriptor.description},
            last_error_code=None,
            last_error_message=None,
        )

    def _merge_registered_response(self, response: SourceResponse, stored: Source | None) -> SourceResponse:
        if stored is None:
            return response
        response.last_error_code = stored.last_error_code
        response.last_error_message = stored.last_error_message
        return response


source_service = SourceService()
