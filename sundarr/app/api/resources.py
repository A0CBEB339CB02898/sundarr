from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.search import ResourceCandidate
from sundarr.app.services.resource_library_service import resource_library_service

router = APIRouter(tags=["resources"])


@router.get("/resources/{resource_id}", response_model=ResourceCandidate)
async def get_resource(resource_id: str, db: Session = Depends(get_db)) -> ResourceCandidate:
    resource = resource_library_service.get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="资源不存在。")
    return resource
