from fastapi import APIRouter, HTTPException, Query
from fastapi import Depends
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.search import FetchDetailRequest, ResourceCandidate, SearchQuery, SearchResponse
from sundarr.app.services.resource_library_service import resource_library_service
from sundarr.app.services.search_service import search_service
from sundarr.app.services.source_service import source_service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1),
    year: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SearchResponse:
    source_service.sync_registered_sources(db)
    query = SearchQuery(keyword=q, year=year, limit=limit)
    response = await search_service.search(query)
    resource_library_service.mark_favorites(db, response.results)
    for source_result in response.source_results:
        resource_library_service.mark_favorites(db, source_result.results)
    return response


@router.post("/search/detail", response_model=ResourceCandidate)
async def fetch_detail(
    request: FetchDetailRequest,
    db: Session = Depends(get_db),
) -> ResourceCandidate:
    result = await search_service.fetch_detail(request.source_id, request.detail_url)
    if result is None:
        raise HTTPException(status_code=404, detail="无法获取该资源的详情。")
    resource_library_service.mark_favorites(db, [result])
    return result
