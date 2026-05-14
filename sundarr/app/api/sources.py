from fastapi import APIRouter, HTTPException, Query
from fastapi import Depends
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.source import (
    SourceListResponse,
    SourceResponse,
    SourceTestRequest,
    SourceTestResponse,
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


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str, db: Session = Depends(get_db)) -> SourceResponse:
    source = source_service.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="媒体源不存在。")
    return source


@router.post("/sources/{source_id}/test", response_model=SourceTestResponse)
async def test_source(
    source_id: str,
    request: SourceTestRequest | None = None,
) -> SourceTestResponse:
    result = await source_service.test_source(source_id, request or SourceTestRequest())
    if result is None:
        raise HTTPException(status_code=404, detail="媒体源不存在。")
    return result
