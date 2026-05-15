from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.search import (
    ResourceCandidate,
    ResourceFavoriteRequest,
    ResourceLinkFavoriteRequest,
    ResourceLinkResult,
    SearchResponse,
)
from sundarr.app.services.resource_library_service import resource_library_service

router = APIRouter(tags=["resources"])


@router.get("/resources/favorites", response_model=list[ResourceCandidate])
async def list_favorite_resources(db: Session = Depends(get_db)) -> list[ResourceCandidate]:
    return resource_library_service.list_favorite_resources(db)


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


@router.get("/resource-links/favorites", response_model=list[ResourceLinkResult])
async def list_favorite_links(db: Session = Depends(get_db)) -> list[ResourceLinkResult]:
    return resource_library_service.list_favorite_links(db)


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


@router.post("/resource-links/{link_id}/refresh", response_model=ResourceLinkResult)
async def refresh_link(link_id: str, db: Session = Depends(get_db)) -> ResourceLinkResult:
    link = await resource_library_service.refresh_link(db, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="资源链接不存在。")
    return link
