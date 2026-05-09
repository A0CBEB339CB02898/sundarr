from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.media_library import (
    MediaLibraryCreateRequest,
    MediaLibraryDeleteRequest,
    MediaLibraryListResponse,
    MediaLibraryResponse,
    MediaLibraryTestResponse,
    MediaLibraryUpdateRequest,
)
from sundarr.app.services.media_library_service import media_library_service

router = APIRouter(tags=["media-libraries"])


@router.get("/media-libraries", response_model=MediaLibraryListResponse)
async def list_media_libraries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> MediaLibraryListResponse:
    return media_library_service.list_libraries(db, page=page, page_size=page_size)


@router.post("/media-libraries/create", response_model=MediaLibraryResponse)
async def create_media_library(
    request: MediaLibraryCreateRequest, db: Session = Depends(get_db)
) -> MediaLibraryResponse:
    try:
        return media_library_service.create_library(db, request)
    except ValueError as exc:
        raise _media_library_error(exc) from exc


@router.get("/media-libraries/{library_id}", response_model=MediaLibraryResponse)
async def get_media_library(library_id: str, db: Session = Depends(get_db)) -> MediaLibraryResponse:
    lib = media_library_service.get_library(db, library_id)
    if lib is None:
        raise HTTPException(status_code=404, detail="媒体库不存在。")
    return lib


@router.post("/media-libraries/{library_id}/update", response_model=MediaLibraryResponse)
async def update_media_library(
    library_id: str, request: MediaLibraryUpdateRequest, db: Session = Depends(get_db)
) -> MediaLibraryResponse:
    try:
        return media_library_service.update_library(db, library_id, request)
    except ValueError as exc:
        raise _media_library_error(exc) from exc


@router.post("/media-libraries/{library_id}/enable", response_model=MediaLibraryResponse)
async def enable_media_library(library_id: str, db: Session = Depends(get_db)) -> MediaLibraryResponse:
    try:
        return media_library_service.enable_library(db, library_id)
    except ValueError as exc:
        raise _media_library_error(exc) from exc


@router.post("/media-libraries/{library_id}/disable", response_model=MediaLibraryResponse)
async def disable_media_library(library_id: str, db: Session = Depends(get_db)) -> MediaLibraryResponse:
    try:
        return media_library_service.disable_library(db, library_id)
    except ValueError as exc:
        raise _media_library_error(exc) from exc


@router.post("/media-libraries/{library_id}/test", response_model=MediaLibraryTestResponse)
async def test_media_library(library_id: str, db: Session = Depends(get_db)) -> MediaLibraryTestResponse:
    try:
        return await media_library_service.test_library(db, library_id)
    except ValueError as exc:
        raise _media_library_error(exc) from exc


@router.post("/media-libraries/{library_id}/delete")
async def delete_media_library(
    library_id: str, request: MediaLibraryDeleteRequest, db: Session = Depends(get_db)
) -> dict:
    try:
        media_library_service.delete_library(db, library_id, request.action)
        return {"ok": True}
    except ValueError as exc:
        raise _media_library_error(exc) from exc


def _media_library_error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    messages = {
        "MEDIA_LIBRARY_EXISTS": "媒体库已存在。",
        "MEDIA_LIBRARY_NOT_FOUND": "媒体库不存在。",
        "SMB_CONNECTION_NOT_FOUND": "SMB 连接不存在。",
        "SMB_PATH_INVALID": "媒体库路径配置无效。",
    }
    if error_code == "MEDIA_LIBRARY_EXISTS":
        status_code = 409
    elif error_code in ("MEDIA_LIBRARY_NOT_FOUND", "SMB_CONNECTION_NOT_FOUND"):
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=messages.get(error_code, "媒体库请求无效。"))
