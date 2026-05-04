from fastapi import APIRouter, Query
from fastapi import Depends
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.search import MediaType, SearchQuery, SearchResponse
from sundarr.app.services.resource_library_service import resource_library_service
from sundarr.app.services.search_service import search_service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1),
    type: MediaType = "unknown",
    year: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SearchResponse:
    query = SearchQuery(keyword=q, type=type, year=year, limit=limit)
    response = await search_service.search(query)
    resource_library_service.save_candidates(db, response.results)
    return response
