from fastapi import APIRouter, HTTPException

from sundarr.app.schemas.search import ResourceCandidate
from sundarr.app.services.search_service import search_service

router = APIRouter(tags=["resources"])


@router.get("/resources/{resource_id}", response_model=ResourceCandidate)
async def get_resource(resource_id: str) -> ResourceCandidate:
    resource = search_service.get_resource(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在或尚未通过搜索入库。")
    return resource
