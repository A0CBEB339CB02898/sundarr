from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.storage import StorageConfigRequest, StorageConfigResponse, StorageConfigTestResponse
from sundarr.app.services.storage_config_service import storage_config_service

router = APIRouter(tags=["storage"])


@router.get("/storage/config", response_model=StorageConfigResponse)
async def get_storage_config(db: Session = Depends(get_db)) -> StorageConfigResponse:
    return storage_config_service.get_config(db)


@router.post("/storage/config/save", response_model=StorageConfigResponse)
async def save_storage_config(request: StorageConfigRequest, db: Session = Depends(get_db)) -> StorageConfigResponse:
    return storage_config_service.save_config(db, request)


@router.post("/storage/config/test", response_model=StorageConfigTestResponse)
async def test_storage_config(request: StorageConfigRequest) -> StorageConfigTestResponse:
    return storage_config_service.test_config(request)
