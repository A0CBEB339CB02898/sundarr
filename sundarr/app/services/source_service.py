from sqlalchemy.orm import Session

from sundarr.app.models import ResourceLink, Source
from sundarr.app.schemas.source import (
    SourceListResponse,
    SourceResponse,
    SourceTestLog,
    SourceTestRequest,
    SourceTestResponse,
)
from sundarr.app.schemas.search import SearchQuery
from sundarr.app.sources import get_registered_sources
from sundarr.app.sources.base import SourceModel


class SourceService:
    def _get_registered_sources(self) -> list[SourceModel]:
        return get_registered_sources()

    def sync_registered_sources(self, db: Session) -> int:
        registered = self._get_registered_sources()
        registered_ids = {source.id for source in registered}
        changed = 0
        for source in registered:
            row = db.get(Source, source.id)
            if row is None:
                row = Source(id=source.id, name=source.name)
                db.add(row)
                changed += 1
            before = (row.name, row.description, row.homepage_url)
            row.name = source.name
            row.description = source.description
            row.homepage_url = source.homepage_url
            if before != (row.name, row.description, row.homepage_url):
                changed += 1
        stale_query = db.query(Source)
        if registered_ids:
            stale_query = stale_query.filter(Source.id.notin_(registered_ids))
        stale_sources = stale_query.all()
        for stale in stale_sources:
            db.query(ResourceLink).filter(ResourceLink.source_id == stale.id).update({ResourceLink.source_id: None})
            db.delete(stale)
            changed += 1
        db.commit()
        return changed

    def list_sources(self, db: Session, page: int = 1, page_size: int = 20) -> SourceListResponse:
        self.sync_registered_sources(db)
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 100))
        query = db.query(Source).order_by(Source.name.asc(), Source.id.asc())
        count = query.count()
        rows = query.offset((safe_page - 1) * safe_page_size).limit(safe_page_size).all()
        results = [self._row_to_response(row) for row in rows]
        return SourceListResponse(count=count, page=safe_page, page_size=safe_page_size, results=results)

    def get_source(self, db: Session, source_id: str) -> SourceResponse | None:
        self.sync_registered_sources(db)
        row = db.get(Source, source_id)
        if row is None:
            return None
        return self._row_to_response(row)

    async def test_source(self, source_id: str, request: SourceTestRequest) -> SourceTestResponse | None:
        source = next((item for item in self._get_registered_sources() if item.id == source_id), None)
        if source is None:
            return None
        logs: list[SourceTestLog] = [
            SourceTestLog(step="prepare", status="ok", message="已读取搜索源定义。", data={"source_id": source.id}),
            SourceTestLog(step="query", status="ok", message="已构造测试搜索请求。", data={"keyword": request.keyword, "result_type": request.result_type}),
        ]
        try:
            query = SearchQuery(keyword=request.keyword, result_type=request.result_type, limit=request.limit)
            if source.test_function is not None:
                execution = await source.test_function(query)
                items = execution.items
                logs.extend(
                    SourceTestLog(step=log.step, status=log.status, message=log.message, data=log.data)
                    for log in execution.logs
                )
            else:
                items = await source.search_function(query)
        except Exception as exc:
            logs.append(SourceTestLog(step="search", status="error", message="搜索源执行失败。", data={"error": str(exc)}))
            return SourceTestResponse(
                ok=False,
                source_id=source.id,
                logs=logs,
                error_code="SOURCE_SEARCH_FAILED",
                error_message=str(exc),
            )
        if source.test_function is None:
            logs.append(SourceTestLog(step="search", status="ok", message="搜索源执行完成。", data={"raw_count": len(items)}))
        preview = [item.model_dump(mode="json") for item in items[: request.limit]]
        logs.append(SourceTestLog(step="preview", status="ok", message="已生成预览结果。", data={"preview_count": len(preview)}))
        return SourceTestResponse(
            ok=True,
            source_id=source.id,
            items=preview,
            logs=logs,
        )

    def _row_to_response(self, source: Source) -> SourceResponse:
        return SourceResponse(
            id=source.id,
            name=source.name,
            description=source.description,
            homepage_url=source.homepage_url,
        )

source_service = SourceService()
