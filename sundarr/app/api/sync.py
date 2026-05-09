from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.sync import (
    SyncBindingCreateRequest,
    SyncBindingListResponse,
    SyncBindingResponse,
    SyncBindingTestResponse,
    SyncBindingUpdateRequest,
    SyncConfigRequest,
    SyncConfigResponse,
    SyncDiscoveredListResponse,
    SyncScanRequest,
    SyncScanResponse,
    SyncTaskCreateRequest,
    SyncTaskCreateResponse,
)
from sundarr.app.services.sync_service import sync_service

router = APIRouter(tags=["sync"])


@router.get("/sync/config", response_model=SyncConfigResponse)
async def get_sync_config(db: Session = Depends(get_db)) -> SyncConfigResponse:
    return sync_service.get_config(db)


@router.post("/sync/config/save", response_model=SyncConfigResponse)
async def save_sync_config(request: SyncConfigRequest, db: Session = Depends(get_db)) -> SyncConfigResponse:
    return sync_service.save_config(db, request)


@router.get("/sync/bindings", response_model=SyncBindingListResponse)
async def list_sync_bindings(db: Session = Depends(get_db)) -> SyncBindingListResponse:
    return sync_service.list_bindings(db)


@router.post("/sync/bindings/create", response_model=SyncBindingResponse)
async def create_sync_binding(request: SyncBindingCreateRequest, db: Session = Depends(get_db)) -> SyncBindingResponse:
    try:
        return sync_service.create_binding(db, request)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/sync/bindings/{binding_id}", response_model=SyncBindingResponse)
async def get_sync_binding(binding_id: str, db: Session = Depends(get_db)) -> SyncBindingResponse:
    binding = sync_service.get_binding(db, binding_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="同步绑定不存在。")
    return binding


@router.post("/sync/bindings/{binding_id}/update", response_model=SyncBindingResponse)
async def update_sync_binding(
    binding_id: str, request: SyncBindingUpdateRequest, db: Session = Depends(get_db)
) -> SyncBindingResponse:
    try:
        return sync_service.update_binding(db, binding_id, request)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/sync/bindings/{binding_id}/enable", response_model=SyncBindingResponse)
async def enable_sync_binding(binding_id: str, db: Session = Depends(get_db)) -> SyncBindingResponse:
    try:
        return sync_service.enable_binding(db, binding_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/sync/bindings/{binding_id}/disable", response_model=SyncBindingResponse)
async def disable_sync_binding(binding_id: str, db: Session = Depends(get_db)) -> SyncBindingResponse:
    try:
        return sync_service.disable_binding(db, binding_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/sync/bindings/{binding_id}/test", response_model=SyncBindingTestResponse)
async def test_sync_binding(binding_id: str, db: Session = Depends(get_db)) -> SyncBindingTestResponse:
    try:
        return await sync_service.test_binding(db, binding_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/sync/scan", response_model=SyncScanResponse)
async def scan_sync_sources(request: SyncScanRequest | None = None, db: Session = Depends(get_db)) -> SyncScanResponse:
    try:
        return await sync_service.scan(db, request or SyncScanRequest())
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/sync/discovered", response_model=SyncDiscoveredListResponse)
async def list_sync_discovered(db: Session = Depends(get_db)) -> SyncDiscoveredListResponse:
    return sync_service.list_discovered(db)


@router.post("/sync/tasks/create", response_model=SyncTaskCreateResponse)
async def create_sync_tasks(
    request: SyncTaskCreateRequest | None = None, db: Session = Depends(get_db)
) -> SyncTaskCreateResponse:
    try:
        return sync_service.create_tasks(db, request or SyncTaskCreateRequest())
    except ValueError as exc:
        raise _error(exc) from exc


def _error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    messages = {
        "SYNC_BINDING_EXISTS": "同步绑定已存在。",
        "SYNC_BINDING_NOT_FOUND": "同步绑定不存在。",
        "REMOTE_MEDIA_LIBRARY_NOT_FOUND": "远程媒体库不存在。",
        "MEDIA_LIBRARY_NOT_FOUND": "媒体库不存在。",
        "SMB_CONNECTION_NOT_FOUND": "SMB 连接不存在。",
        "LIBRARY_NOT_FOUND": "媒体库不存在。",
        "SMB_PATH_INVALID": "路径配置无效。",
    }
    if error_code == "SYNC_BINDING_EXISTS":
        status_code = 409
    elif error_code in ("SYNC_BINDING_NOT_FOUND", "REMOTE_MEDIA_LIBRARY_NOT_FOUND", "MEDIA_LIBRARY_NOT_FOUND", "SMB_CONNECTION_NOT_FOUND", "LIBRARY_NOT_FOUND"):
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=messages.get(error_code, "同步请求无效。"))
