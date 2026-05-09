from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.smb_connection import (
    SmbBrowseResponse,
    SmbConnectionCreateRequest,
    SmbConnectionDeleteRequest,
    SmbConnectionListResponse,
    SmbConnectionResponse,
    SmbConnectionTestResponse,
    SmbConnectionUpdateRequest,
)
from sundarr.app.services.smb_connection_service import smb_connection_service

router = APIRouter(tags=["smb-connections"])


@router.get("/storage/smb-connections", response_model=SmbConnectionListResponse)
async def list_smb_connections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SmbConnectionListResponse:
    return smb_connection_service.list_connections(db, page=page, page_size=page_size)


@router.post("/storage/smb-connections/create", response_model=SmbConnectionResponse)
async def create_smb_connection(
    request: SmbConnectionCreateRequest, db: Session = Depends(get_db)
) -> SmbConnectionResponse:
    try:
        return smb_connection_service.create_connection(db, request)
    except ValueError as exc:
        raise _smb_connection_error(exc) from exc


@router.get("/storage/smb-connections/{connection_id}", response_model=SmbConnectionResponse)
async def get_smb_connection(connection_id: str, db: Session = Depends(get_db)) -> SmbConnectionResponse:
    conn = smb_connection_service.get_connection(db, connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="SMB 连接不存在。")
    return conn


@router.post("/storage/smb-connections/{connection_id}/update", response_model=SmbConnectionResponse)
async def update_smb_connection(
    connection_id: str, request: SmbConnectionUpdateRequest, db: Session = Depends(get_db)
) -> SmbConnectionResponse:
    try:
        return smb_connection_service.update_connection(db, connection_id, request)
    except ValueError as exc:
        raise _smb_connection_error(exc) from exc


@router.post("/storage/smb-connections/{connection_id}/enable", response_model=SmbConnectionResponse)
async def enable_smb_connection(connection_id: str, db: Session = Depends(get_db)) -> SmbConnectionResponse:
    try:
        return smb_connection_service.enable_connection(db, connection_id)
    except ValueError as exc:
        raise _smb_connection_error(exc) from exc


@router.post("/storage/smb-connections/{connection_id}/disable", response_model=SmbConnectionResponse)
async def disable_smb_connection(connection_id: str, db: Session = Depends(get_db)) -> SmbConnectionResponse:
    try:
        return smb_connection_service.disable_connection(db, connection_id)
    except ValueError as exc:
        raise _smb_connection_error(exc) from exc


@router.post("/storage/smb-connections/{connection_id}/test", response_model=SmbConnectionTestResponse)
async def test_smb_connection(connection_id: str, db: Session = Depends(get_db)) -> SmbConnectionTestResponse:
    try:
        return await smb_connection_service.test_connection(db, connection_id)
    except ValueError as exc:
        raise _smb_connection_error(exc) from exc


@router.post("/storage/smb-connections/test-new", response_model=SmbConnectionTestResponse)
async def test_new_smb_connection(
    request: SmbConnectionCreateRequest, db: Session = Depends(get_db)
) -> SmbConnectionTestResponse:
    return await smb_connection_service.test_new_connection(request)


@router.post("/storage/smb-connections/browse-new", response_model=SmbBrowseResponse)
async def browse_new_smb_connection(
    request: SmbConnectionCreateRequest, path: str = "", db: Session = Depends(get_db)
) -> SmbBrowseResponse:
    return await smb_connection_service.browse_new_connection(request, path)


@router.get("/storage/smb-connections/{connection_id}/browse", response_model=SmbBrowseResponse)
async def browse_smb_connection(
    connection_id: str, path: str = "", db: Session = Depends(get_db)
) -> SmbBrowseResponse:
    try:
        return await smb_connection_service.browse(db, connection_id, path)
    except ValueError as exc:
        raise _smb_connection_error(exc) from exc


@router.post("/storage/smb-connections/{connection_id}/delete")
async def delete_smb_connection(
    connection_id: str, request: SmbConnectionDeleteRequest, db: Session = Depends(get_db)
) -> dict:
    try:
        smb_connection_service.delete_connection(db, connection_id, request.action)
        return {"ok": True}
    except ValueError as exc:
        raise _smb_connection_error(exc) from exc


def _smb_connection_error(exc: ValueError) -> HTTPException:
    error_code = str(exc)
    messages = {
        "SMB_CONNECTION_EXISTS": "SMB 连接已存在。",
        "SMB_CONNECTION_NOT_FOUND": "SMB 连接不存在。",
        "SMB_PATH_INVALID": "SMB 路径配置无效。",
        "SMB_PATH_OUTSIDE_ROOT": "SMB 路径超出允许范围。",
        "SMB_CLIENT_NOT_INSTALLED": "SMB 客户端依赖未安装，暂不能连接真实 SMB。",
        "SMB_CONNECT_FAILED": "SMB 连接或认证失败。",
        "SMB_HOST_UNREACHABLE": "无法连接 SMB 主机或端口。",
        "SMB_AUTH_FAILED": "SMB 认证失败。",
        "SMB_PERMISSION_DENIED": "SMB 权限不足。",
        "SMB_SHARE_NOT_FOUND": "SMB 共享不存在或名称不正确。",
    }
    if error_code == "SMB_CONNECTION_EXISTS":
        status_code = 409
    elif error_code == "SMB_CONNECTION_NOT_FOUND":
        status_code = 404
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=messages.get(error_code, "SMB 连接请求无效。"))
