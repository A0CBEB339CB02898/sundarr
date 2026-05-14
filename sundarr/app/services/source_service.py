from sundarr.app.schemas.source import (
    SourceListResponse,
    SourceResponse,
    SourceTestLog,
    SourceTestRequest,
    SourceTestResponse,
)
from sundarr.app.schemas.search import SearchQuery
from sundarr.app.sources import get_registered_sources


class SourceService:
    def list_sources(self, page: int = 1, page_size: int = 20) -> SourceListResponse:
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 100))
        registered = [self._registered_to_response(source) for source in get_registered_sources()]
        results = registered
        count = len(results)
        results = results[(safe_page - 1) * safe_page_size : safe_page * safe_page_size]
        return SourceListResponse(count=count, page=safe_page, page_size=safe_page_size, results=results)

    def get_source(self, source_id: str) -> SourceResponse | None:
        registered = next((source for source in get_registered_sources() if source.id == source_id), None)
        if registered is None:
            return None
        return self._registered_to_response(registered)

    async def test_source(self, source_id: str, request: SourceTestRequest) -> SourceTestResponse | None:
        source = next((item for item in get_registered_sources() if item.id == source_id), None)
        if source is None:
            return None
        logs = [
            SourceTestLog(step="prepare", status="ok", message="已读取代码注册源。", data={"source_id": source.id}),
            SourceTestLog(step="query", status="ok", message="已构造测试搜索请求。", data={"keyword": request.keyword, "result_type": request.result_type}),
        ]
        try:
            items = await source.search_function(
                SearchQuery(keyword=request.keyword, result_type=request.result_type, limit=request.limit)
            )
        except Exception as exc:
            logs.append(SourceTestLog(step="search", status="error", message="搜索源执行失败。", data={"error": str(exc)}))
            return SourceTestResponse(
                ok=False,
                source_id=source.id,
                logs=logs,
                error_code="SOURCE_SEARCH_FAILED",
                error_message=str(exc),
            )
        logs.append(SourceTestLog(step="search", status="ok", message="搜索源执行完成。", data={"raw_count": len(items)}))
        preview = [item.model_dump(mode="json") for item in items[: request.limit]]
        logs.append(SourceTestLog(step="preview", status="ok", message="已生成预览结果。", data={"preview_count": len(preview)}))
        return SourceTestResponse(
            ok=True,
            source_id=source.id,
            items=preview,
            logs=logs,
        )

    def _registered_to_response(self, source) -> SourceResponse:
        return SourceResponse(
            id=source.id,
            name=source.name,
            type="code",
            description=source.description,
        )


source_service = SourceService()
