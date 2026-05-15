from fastapi import APIRouter, Query
from fastapi import Depends
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.search import SearchQuery, SearchResponse
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
