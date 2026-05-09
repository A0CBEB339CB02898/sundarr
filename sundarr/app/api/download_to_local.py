from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.download_to_local import (
    DtlBindingCreateRequest,
    DtlBindingListResponse,
    DtlBindingResponse,
    DtlBindingTestResponse,
    DtlBindingUpdateRequest,
    DtlConfigRequest,
    DtlConfigResponse,
    DtlDiscoveredListResponse,
    DtlScanRequest,
    DtlScanResponse,
    DtlTaskCreateRequest,
    DtlTaskCreateResponse,
)
from sundarr.app.services.download_to_local_service import download_to_local_service

router = APIRouter(tags=["download-to-local"])


@router.get("/download-to-local/config", response_model=DtlConfigResponse)
async def get_dtl_config(db: Session = Depends(get_db)) -> DtlConfigResponse:
    return download_to_local_service.get_config(db)


@router.post("/download-to-local/config/save", response_model=DtlConfigResponse)
async def save_dtl_config(request: DtlConfigRequest, db: Session = Depends(get_db)) -> DtlConfigResponse:
    return download_to_local_service.save_config(db, request)


@router.get("/download-to-local/bindings", response_model=DtlBindingListResponse)
async def list_dtl_bindings(db: Session = Depends(get_db)) -> DtlBindingListResponse:
    return download_to_local_service.list_bindings(db)


@router.post("/download-to-local/bindings/create", response_model=DtlBindingResponse)
async def create_dtl_binding(
    request: DtlBindingCreateRequest, db: Session = Depends(get_db)
) -> DtlBindingResponse:
    try:
        return download_to_local_service.create_binding(db, request)
    except ValueError as exc:
        raise _dtl_error(exc) from exc


@router.get("/download-to-local/bindings/{binding_id}", response_model=DtlBindingResponse)
async def get_dtl_binding(binding_id: str, db: Session = Depends(get_db)) -> DtlBindingResponse:
    binding = download_to_local_service.get_binding(db, binding_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="下载绑定不存在。")
    return binding


@router.post("/download-to-local/bindings/{binding_id}/update", response_model=DtlBindingResponse)
async def update_dtl_binding(
    binding_id: str, request: DtlBindingUpdateRequest, db: Session = Depends(get_db)
) -> DtlBindingResponse:
    try:
        return download_to_local_service.update_binding(db, binding_id, request)
    except ValueError as exc:
        raise _dtl_error(exc) from exc


@router.post("/download-to-local/bindings/{binding_id}/enable", response_model=DtlBindingResponse)
async def enable_dtl_binding(binding_id: str, db: Session = Depends(get_db)) -> DtlBindingResponse:
    try:
        return download_to_local_service.enable_binding(db, binding_id)
    except ValueError as exc:
        raise _dtl_error(exc) from exc


@router.post("/download-to-local/bindings/{binding_id}/disable", response_model=DtlBindingResponse)
async def disable_dtl_binding(binding_id: str, db: Session = Depends(get_db)) -> DtlBindingResponse:
    try:
        return download_to_local_service.disable_binding(db, binding_id)
    except ValueError as exc:
        raise _dtl_error(exc) from exc


@router.post("/download-to-local/bindings/{binding_id}/test", response_model=DtlBindingTestResponse)
async def test_dtl_binding(binding_id: str, db: Session = Depends(get_db)) -> DtlBindingTestResponse:
    try:
        return await download_to_local_service.test_binding(db, binding_id)
    except ValueError as exc:
        raise _dtl_error(exc) from exc


@router.post("/download-to-local/scan", response_model=DtlScanResponse)
async def scan_dtl_sources(
    request: DtlScanRequest | None = None, db: Session = Depends(get_db)
) -> DtlScanResponse:
    try:
        return await download_to_local_service.scan(db, request or DtlScanRequest())
    except ValueError as exc:
        raise _dtl_error(exc) from exc


@router.get("/download-to-local/discovered", response_model=DtlDiscoveredListResponse)
async def list_dtl_discovered(db: Session = Depends(get_db)) -> DtlDiscoveredListResponse:
    return download_to_local_service.list_discovered(db)


@router.post("/download-to-local/tasks/create", response_model=DtlTaskCreateResponse)
async def create_dtl_tasks(
    request: DtlTaskCreateRequest | None = None, db: Session = Depends(get_db)
) -> DtlTaskCreateResponse:
    try:
        return download_to_local_service.create_tasks(db, request or DtlTaskCreateRequest())
    except ValueError as exc:
        raise _dtl_error(exc) from exc


def _dtl_error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    messages = {
        "DTL_BINDING_EXISTS": "下载绑定已存在。",
        "DTL_BINDING_NOT_FOUND": "下载绑定不存在。",
        "SMB_CONNECTION_NOT_FOUND": "SMB 连接不存在。",
        "MEDIA_LIBRARY_NOT_FOUND": "媒体库不存在。",
        "DTL_SOURCE_PATH_INVALID": "来源路径无效。",
        "SMB_PATH_INVALID": "路径配置无效。",
    }
    if error_code == "DTL_BINDING_EXISTS":
        status_code = 409
    elif error_code in ("DTL_BINDING_NOT_FOUND", "SMB_CONNECTION_NOT_FOUND", "MEDIA_LIBRARY_NOT_FOUND"):
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=messages.get(error_code, "下载到本地请求无效。"))
