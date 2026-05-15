from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.search import (
    ResourceCandidate,
    ResourceFavoriteRequest,
    ResourceFavoritesListResponse,
    ResourceLinkFavoriteRequest,
    ResourceLinkResult,
    ResourceLinksFavoritesListResponse,
    SearchResponse,
)
from sundarr.app.services.resource_library_service import resource_library_service

router = APIRouter(tags=["resources"])


@router.get("/resources/favorites", response_model=ResourceFavoritesListResponse)
async def list_favorite_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ResourceFavoritesListResponse:
    count, results = resource_library_service.list_favorite_resources(db, page=page, page_size=page_size)
    return ResourceFavoritesListResponse(count=count, page=page, page_size=page_size, results=results)


@router.get("/resources/{resource_id}", response_model=ResourceCandidate)
async def get_resource(resource_id: str, db: Session = Depends(get_db)) -> ResourceCandidate:
    resource = resource_library_service.get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在。")
    return resource


@router.post("/resources/favorite", response_model=ResourceCandidate)
async def favorite_resource(request: ResourceFavoriteRequest, db: Session = Depends(get_db)) -> ResourceCandidate:
    return resource_library_service.favorite_resource(db, request)


@router.post("/resources/{resource_id}/unfavorite")
async def unfavorite_resource(resource_id: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    if not resource_library_service.unfavorite_resource(db, resource_id):
        raise HTTPException(status_code=404, detail="资源不存在。")
    return {"ok": True}


@router.post("/resources/{resource_id}/refresh", response_model=SearchResponse)
async def refresh_resource(resource_id: str, db: Session = Depends(get_db)) -> SearchResponse:
    response = await resource_library_service.refresh_resource(db, resource_id)
    if response is None:
        raise HTTPException(status_code=404, detail="资源不存在。")
    return response


@router.get("/resource-links/favorites", response_model=ResourceLinksFavoritesListResponse)
async def list_favorite_links(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ResourceLinksFavoritesListResponse:
    count, results = resource_library_service.list_favorite_links(db, page=page, page_size=page_size)
    return ResourceLinksFavoritesListResponse(count=count, page=page, page_size=page_size, results=results)


@router.get("/resource-links/{link_id}", response_model=ResourceLinkResult)
async def get_link(link_id: str, db: Session = Depends(get_db)) -> ResourceLinkResult:
    link = resource_library_service.get_link(db, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="资源链接不存在。")
    return link


@router.post("/resource-links/favorite", response_model=ResourceLinkResult)
async def favorite_link(request: ResourceLinkFavoriteRequest, db: Session = Depends(get_db)) -> ResourceLinkResult:
    return resource_library_service.favorite_link(db, request)


@router.post("/resource-links/{link_id}/unfavorite")
async def unfavorite_link(link_id: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    if not resource_library_service.unfavorite_link(db, link_id):
        raise HTTPException(status_code=404, detail="资源链接不存在。")
    return {"ok": True}
