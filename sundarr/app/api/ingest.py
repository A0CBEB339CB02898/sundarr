from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.ingest import (
    IngestBindingCreateRequest,
    IngestBindingListResponse,
    IngestBindingResponse,
    IngestBindingTestResponse,
    IngestBindingUpdateRequest,
    IngestConfigRequest,
    IngestConfigResponse,
    IngestDiscoveredListResponse,
    IngestScanRequest,
    IngestScanResponse,
    IngestTaskCreateRequest,
    IngestTaskCreateResponse,
)
from sundarr.app.services.ingest_service import ingest_service

router = APIRouter(tags=["ingest"])


@router.get("/ingest/config", response_model=IngestConfigResponse)
async def get_ingest_config(db: Session = Depends(get_db)) -> IngestConfigResponse:
    return ingest_service.get_config(db)


@router.post("/ingest/config/save", response_model=IngestConfigResponse)
async def save_ingest_config(request: IngestConfigRequest, db: Session = Depends(get_db)) -> IngestConfigResponse:
    return ingest_service.save_config(db, request)


@router.get("/ingest/bindings", response_model=IngestBindingListResponse)
async def list_ingest_bindings(db: Session = Depends(get_db)) -> IngestBindingListResponse:
    return ingest_service.list_bindings(db)


@router.post("/ingest/bindings/create", response_model=IngestBindingResponse)
async def create_ingest_binding(request: IngestBindingCreateRequest, db: Session = Depends(get_db)) -> IngestBindingResponse:
    try:
        return ingest_service.create_binding(db, request)
    except ValueError as exc:
        raise _ingest_error(exc) from exc


@router.get("/ingest/bindings/{binding_id}", response_model=IngestBindingResponse)
async def get_ingest_binding(binding_id: str, db: Session = Depends(get_db)) -> IngestBindingResponse:
    binding = ingest_service.get_binding(db, binding_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="导入绑定不存在。")
    return binding


@router.post("/ingest/bindings/{binding_id}/update", response_model=IngestBindingResponse)
async def update_ingest_binding(
    binding_id: str,
    request: IngestBindingUpdateRequest,
    db: Session = Depends(get_db),
) -> IngestBindingResponse:
    try:
        return ingest_service.update_binding(db, binding_id, request)
    except ValueError as exc:
        raise _ingest_error(exc) from exc


@router.post("/ingest/bindings/{binding_id}/enable", response_model=IngestBindingResponse)
async def enable_ingest_binding(binding_id: str, db: Session = Depends(get_db)) -> IngestBindingResponse:
    try:
        return ingest_service.enable_binding(db, binding_id)
    except ValueError as exc:
        raise _ingest_error(exc) from exc


@router.post("/ingest/bindings/{binding_id}/disable", response_model=IngestBindingResponse)
async def disable_ingest_binding(binding_id: str, db: Session = Depends(get_db)) -> IngestBindingResponse:
    try:
        return ingest_service.disable_binding(db, binding_id)
    except ValueError as exc:
        raise _ingest_error(exc) from exc


@router.post("/ingest/bindings/{binding_id}/test", response_model=IngestBindingTestResponse)
async def test_ingest_binding(binding_id: str, db: Session = Depends(get_db)) -> IngestBindingTestResponse:
    try:
        return ingest_service.test_binding(db, binding_id)
    except ValueError as exc:
        raise _ingest_error(exc) from exc


@router.post("/ingest/scan", response_model=IngestScanResponse)
async def scan_ingest_sources(request: IngestScanRequest | None = None, db: Session = Depends(get_db)) -> IngestScanResponse:
    try:
        return await ingest_service.scan(db, request or IngestScanRequest())
    except ValueError as exc:
        raise _ingest_error(exc) from exc


@router.get("/ingest/discovered", response_model=IngestDiscoveredListResponse)
async def list_ingest_discovered(db: Session = Depends(get_db)) -> IngestDiscoveredListResponse:
    return ingest_service.list_discovered(db)


@router.post("/ingest/tasks/create", response_model=IngestTaskCreateResponse)
async def create_ingest_tasks(
    request: IngestTaskCreateRequest | None = None,
    db: Session = Depends(get_db),
) -> IngestTaskCreateResponse:
    try:
        return ingest_service.create_tasks(db, request or IngestTaskCreateRequest())
    except ValueError as exc:
        raise _ingest_error(exc) from exc


def _ingest_error(exc: ValueError) -> HTTPException:
    messages = {
        "INGEST_BINDING_EXISTS": "导入绑定已存在。",
        "INGEST_BINDING_NOT_FOUND": "导入绑定不存在。",
        "INGEST_SOURCE_PATH_INVALID": "导入来源路径无效。",
    }
    if str(exc) == "INGEST_BINDING_EXISTS":
        status_code = 409
    elif str(exc) == "INGEST_BINDING_NOT_FOUND":
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=messages.get(str(exc), "导入配置请求无效。"))
