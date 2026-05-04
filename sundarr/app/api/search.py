from fastapi import APIRouter, Query

from sundarr.app.schemas.search import MediaType, SearchQuery, SearchResponse
from sundarr.app.services.search_service import search_service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1),
    type: MediaType = "unknown",
    year: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    query = SearchQuery(keyword=q, type=type, year=year, limit=limit)
    return await search_service.search(query)
