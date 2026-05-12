from datetime import UTC, datetime

from sqlalchemy.orm import Session

from sundarr.app.models import Source
from sundarr.app.schemas.source import (
    SourceCreateRequest,
    SourceListResponse,
    SourceResponse,
    SourceTestResponse,
    SourceUpdateRequest,
)

EDITABLE_SOURCE_TYPES = {"configurable", "document"}


class SourceService:
    def list_sources(self, db: Session, page: int = 1, page_size: int = 20) -> SourceListResponse:
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 100))
        query = db.query(Source).order_by(Source.created_at.desc(), Source.id.asc())
        count = query.count()
        sources = query.offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
        results = [self._to_response(source) for source in sources]
        return SourceListResponse(count=count, page=safe_page, page_size=safe_page_size, results=results)

    def get_source(self, db: Session, source_id: str) -> SourceResponse | None:
        source = db.get(Source, source_id)
        return self._to_response(source) if source else None

    def create_source(self, db: Session, request: SourceCreateRequest) -> SourceResponse:
        self._ensure_editable_type(request.type)
        if db.get(Source, request.id) is not None:
            raise ValueError("SOURCE_ALREADY_EXISTS")

        source = Source(
            id=request.id,
            name=request.name,
            type=request.type,
            enabled=request.enabled,
            legal_note=request.legal_note,
            trust_level=request.trust_level,
            created_by_user=True,
            config_json=request.config_json,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return self._to_response(source)

    def update_source(self, db: Session, source_id: str, request: SourceUpdateRequest) -> SourceResponse | None:
        source = db.get(Source, source_id)
        if source is None:
            return None
        self._ensure_editable_type(source.type)

        if request.name is not None:
            source.name = request.name
        if request.enabled is not None:
            source.enabled = request.enabled
        if request.legal_note is not None:
            source.legal_note = request.legal_note
        if request.trust_level is not None:
            source.trust_level = request.trust_level
        if request.config_json is not None:
            source.config_json = request.config_json

        db.commit()
        db.refresh(source)
        return self._to_response(source)

    def set_enabled(self, db: Session, source_id: str, enabled: bool) -> SourceResponse | None:
        source = db.get(Source, source_id)
        if source is None:
            return None
        self._ensure_editable_type(source.type)
        source.enabled = enabled
        db.commit()
        db.refresh(source)
        return self._to_response(source)

    def test_source(self, db: Session, source_id: str) -> SourceTestResponse | None:
        source = db.get(Source, source_id)
        if source is None:
            return None

        try:
            items = self._preview_items(source)
            source.last_error_code = None
            source.last_error_message = None
            source.last_checked_at = datetime.now(UTC)
            db.commit()
            return SourceTestResponse(ok=True, source_id=source.id, items=items)
        except ValueError as exc:
            source.last_error_code = str(exc)
            source.last_error_message = self._message_for_error(str(exc))
            source.last_checked_at = datetime.now(UTC)
            db.commit()
            return SourceTestResponse(
                ok=False,
                source_id=source.id,
                error_code=source.last_error_code,
                error_message=source.last_error_message,
            )

    def _preview_items(self, source: Source) -> list[dict[str, str]]:
        config = source.config_json or {}
        if source.type == "document":
            items = config.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError("SOURCE_CONFIG_INVALID")
            first = items[0]
            return [
                {
                    "source_id": source.id,
                    "source_type": source.type,
                    "raw_title": str(first.get("title", source.name)),
                    "raw_url": str(first.get("url", "")),
                    "raw_content": str(first.get("content", first.get("link", ""))),
                }
            ]

        if source.type == "configurable":
            search_url = config.get("search_url")
            selectors = config.get("selectors")
            if not isinstance(search_url, str) or not isinstance(selectors, dict):
                raise ValueError("SOURCE_CONFIG_INVALID")
            return [
                {
                    "source_id": source.id,
                    "source_type": source.type,
                    "raw_title": source.name,
                    "raw_url": search_url,
                    "raw_content": "配置型源测试通过，实际抓取将在后续 Parser 阶段实现。",
                }
            ]

        raise ValueError("SOURCE_TYPE_NOT_TESTABLE")

    def _ensure_editable_type(self, source_type: str) -> None:
        if source_type not in EDITABLE_SOURCE_TYPES:
            raise ValueError("SOURCE_TYPE_NOT_EDITABLE")

    def _to_response(self, source: Source) -> SourceResponse:
        return SourceResponse(
            id=source.id,
            name=source.name,
            type=source.type,
            enabled=source.enabled,
            legal_note=source.legal_note,
            trust_level=source.trust_level,
            created_by_user=source.created_by_user,
            config_json=source.config_json or {},
            last_error_code=source.last_error_code,
            last_error_message=source.last_error_message,
        )

    def _message_for_error(self, error_code: str) -> str:
        messages = {
            "SOURCE_CONFIG_INVALID": "媒体源配置无效。",
            "SOURCE_TYPE_NOT_TESTABLE": "该类型媒体源不能通过 Web Console 测试。",
        }
        return messages.get(error_code, "媒体源测试失败。")


source_service = SourceService()
