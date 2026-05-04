from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.storage import (
    StorageBrowseResponse,
    StorageConfigRequest,
    StorageConfigResponse,
    StorageConfigTestResponse,
)
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


@router.get("/storage/browse", response_model=StorageBrowseResponse)
async def browse_storage(path: str = "", db: Session = Depends(get_db)) -> StorageBrowseResponse:
    try:
        return await storage_config_service.browse(db, path)
    except ValueError as exc:
        raise _storage_error(exc) from exc


def _storage_error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    status_code = 404 if error_code == "STORAGE_CONFIG_MISSING" else 400
    messages = {
        "STORAGE_CONFIG_MISSING": "存储配置不存在。",
        "SMB_CLIENT_NOT_INSTALLED": "SMB 客户端依赖未安装，暂不能连接真实 SMB。",
        "SMB_PATH_INVALID": "SMB 路径配置无效。",
        "SMB_PATH_OUTSIDE_ROOT": "SMB 路径超出允许范围。",
    }
    return HTTPException(status_code=status_code, detail=messages.get(error_code, "存储请求无效。"))
