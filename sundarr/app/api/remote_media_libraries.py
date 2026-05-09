from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.remote_media_library import (
    RemoteMediaLibraryCreateRequest,
    RemoteMediaLibraryListResponse,
    RemoteMediaLibraryResponse,
    RemoteMediaLibraryTestResponse,
    RemoteMediaLibraryUpdateRequest,
)
from sundarr.app.services.remote_media_library_service import remote_media_library_service

router = APIRouter(tags=["remote-media-libraries"])


@router.get("/remote-media-libraries", response_model=RemoteMediaLibraryListResponse)
async def list_remote_media_libraries(db: Session = Depends(get_db)) -> RemoteMediaLibraryListResponse:
    return remote_media_library_service.list_libraries(db)


@router.post("/remote-media-libraries/create", response_model=RemoteMediaLibraryResponse)
async def create_remote_media_library(
    request: RemoteMediaLibraryCreateRequest, db: Session = Depends(get_db)
) -> RemoteMediaLibraryResponse:
    try:
        return remote_media_library_service.create_library(db, request)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/remote-media-libraries/{library_id}", response_model=RemoteMediaLibraryResponse)
async def get_remote_media_library(library_id: str, db: Session = Depends(get_db)) -> RemoteMediaLibraryResponse:
    lib = remote_media_library_service.get_library(db, library_id)
    if lib is None:
        raise HTTPException(status_code=404, detail="远程媒体库不存在。")
    return lib


@router.post("/remote-media-libraries/{library_id}/update", response_model=RemoteMediaLibraryResponse)
async def update_remote_media_library(
    library_id: str, request: RemoteMediaLibraryUpdateRequest, db: Session = Depends(get_db)
) -> RemoteMediaLibraryResponse:
    try:
        return remote_media_library_service.update_library(db, library_id, request)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/remote-media-libraries/{library_id}/enable", response_model=RemoteMediaLibraryResponse)
async def enable_remote_media_library(library_id: str, db: Session = Depends(get_db)) -> RemoteMediaLibraryResponse:
    try:
        return remote_media_library_service.enable_library(db, library_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/remote-media-libraries/{library_id}/disable", response_model=RemoteMediaLibraryResponse)
async def disable_remote_media_library(library_id: str, db: Session = Depends(get_db)) -> RemoteMediaLibraryResponse:
    try:
        return remote_media_library_service.disable_library(db, library_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/remote-media-libraries/{library_id}/test", response_model=RemoteMediaLibraryTestResponse)
async def test_remote_media_library(library_id: str, db: Session = Depends(get_db)) -> RemoteMediaLibraryTestResponse:
    try:
        return await remote_media_library_service.test_library(db, library_id)
    except ValueError as exc:
        raise _error(exc) from exc


def _error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    messages = {
        "REMOTE_MEDIA_LIBRARY_EXISTS": "远程媒体库已存在。",
        "REMOTE_MEDIA_LIBRARY_NOT_FOUND": "远程媒体库不存在。",
        "SMB_CONNECTION_NOT_FOUND": "SMB 连接不存在。",
        "SMB_PATH_INVALID": "远程媒体库路径配置无效。",
    }
    if error_code == "REMOTE_MEDIA_LIBRARY_EXISTS":
        status_code = 409
    elif error_code in ("REMOTE_MEDIA_LIBRARY_NOT_FOUND", "SMB_CONNECTION_NOT_FOUND"):
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=messages.get(error_code, "远程媒体库请求无效。"))
