from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.source import (
    SourceCreateRequest,
    SourceListResponse,
    SourceResponse,
    SourceTestResponse,
    SourceUpdateRequest,
)
from sundarr.app.services.source_service import source_service

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=SourceListResponse)
async def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SourceListResponse:
    return source_service.list_sources(db, page=page, page_size=page_size)


@router.post("/sources/create", response_model=SourceResponse)
async def create_source(request: SourceCreateRequest, db: Session = Depends(get_db)) -> SourceResponse:
    try:
        return source_service.create_source(db, request)
    except ValueError as exc:
        raise _source_error(exc) from exc


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str, db: Session = Depends(get_db)) -> SourceResponse:
    source = source_service.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="媒体源不存在。")
    return source


@router.post("/sources/{source_id}/update", response_model=SourceResponse)
async def update_source(
    source_id: str,
    request: SourceUpdateRequest,
    db: Session = Depends(get_db),
) -> SourceResponse:
    try:
        source = source_service.update_source(db, source_id, request)
    except ValueError as exc:
        raise _source_error(exc) from exc
    if source is None:
        raise HTTPException(status_code=404, detail="媒体源不存在。")
    return source


@router.post("/sources/{source_id}/enable", response_model=SourceResponse)
async def enable_source(source_id: str, db: Session = Depends(get_db)) -> SourceResponse:
    return _set_source_enabled(db, source_id, True)


@router.post("/sources/{source_id}/disable", response_model=SourceResponse)
async def disable_source(source_id: str, db: Session = Depends(get_db)) -> SourceResponse:
    return _set_source_enabled(db, source_id, False)


@router.post("/sources/{source_id}/test", response_model=SourceTestResponse)
async def test_source(source_id: str, db: Session = Depends(get_db)) -> SourceTestResponse:
    result = source_service.test_source(db, source_id)
    if result is None:
        raise HTTPException(status_code=404, detail="媒体源不存在。")
    return result


def _set_source_enabled(db: Session, source_id: str, enabled: bool) -> SourceResponse:
    try:
        source = source_service.set_enabled(db, source_id, enabled)
    except ValueError as exc:
        raise _source_error(exc) from exc
    if source is None:
        raise HTTPException(status_code=404, detail="媒体源不存在。")
    return source


def _source_error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    status_code = 409 if error_code == "SOURCE_ALREADY_EXISTS" else 400
    messages = {
        "SOURCE_ALREADY_EXISTS": "媒体源已存在。",
        "SOURCE_TYPE_NOT_EDITABLE": "该类型媒体源不能通过 Web Console 编辑。",
        "SOURCE_CODE_ONLY": "媒体源现在统一由代码注册，不能通过 Web Console 创建或编辑。",
    }
    return HTTPException(status_code=status_code, detail=messages.get(error_code, "媒体源请求无效。"))
