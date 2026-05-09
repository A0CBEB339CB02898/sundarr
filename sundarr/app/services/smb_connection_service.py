from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.models import MediaLibrary, RemoteMediaLibrary, SmbConnection, SyncSeenFile, TransferLog, TransferTask
from sundarr.app.schemas.smb_connection import (
    SmbBrowseEntry,
    SmbBrowseResponse,
    SmbConnectionCreateRequest,
    SmbConnectionListResponse,
    SmbConnectionResponse,
    SmbConnectionTestResponse,
    SmbConnectionUpdateRequest,
)
from sundarr.app.storage import SmbConfig, SmbWriter
from sundarr.app.storage.smb import SmbStorageError

RUNNING_TRANSFER_STATUSES = {
    "staging_to_cloud",
    "cloud_ready",
    "downloading",
    "verifying",
    "renaming",
    "cleaning_cloud",
    "cleaning_source",
}


class SmbConnectionService:
    def list_connections(self, db: Session, page: int = 1, page_size: int = 20) -> SmbConnectionListResponse:
        query = db.query(SmbConnection).order_by(SmbConnection.created_at, SmbConnection.id)
        count = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        results = [self._to_response(db, row) for row in rows]
        return SmbConnectionListResponse(count=count, page=page, page_size=page_size, results=results)

    def get_connection(self, db: Session, connection_id: str) -> SmbConnectionResponse | None:
        conn = db.get(SmbConnection, connection_id)
        return self._to_response(db, conn) if conn else None

    def create_connection(self, db: Session, request: SmbConnectionCreateRequest) -> SmbConnectionResponse:
        if db.get(SmbConnection, request.id) is not None:
            raise ValueError("SMB_CONNECTION_EXISTS")
        self._validate_base_path(request.base_path)
        conn = SmbConnection(
            id=request.id,
            name=request.name,
            enabled=request.enabled,
            host=request.host,
            port=request.port,
            share=request.share,
            username=request.username,
            password=request.password,
            domain=request.domain or None,
            base_path=request.base_path,
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)
        return self._to_response(db, conn)

    def update_connection(self, db: Session, connection_id: str, request: SmbConnectionUpdateRequest) -> SmbConnectionResponse:
        conn = db.get(SmbConnection, connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        self._validate_base_path(request.base_path)

        old_value = self._conn_to_config_dict(conn)
        conn.name = request.name
        conn.enabled = request.enabled
        conn.host = request.host
        conn.port = request.port
        conn.share = request.share
        conn.username = request.username
        if request.password:
            conn.password = request.password
        conn.domain = request.domain or None
        conn.base_path = request.base_path

        new_value = self._conn_to_config_dict(conn)
        if old_value != new_value:
            self._interrupt_running_tasks(db, connection_id)

        db.commit()
        db.refresh(conn)
        return self._to_response(db, conn)

    def enable_connection(self, db: Session, connection_id: str) -> SmbConnectionResponse:
        return self._set_enabled(db, connection_id, True)

    def disable_connection(self, db: Session, connection_id: str) -> SmbConnectionResponse:
        return self._set_enabled(db, connection_id, False)

    def delete_connection(self, db: Session, connection_id: str, action: str) -> None:
        conn = db.get(SmbConnection, connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        if action == "unbind":
            for lib in db.query(MediaLibrary).filter(MediaLibrary.connection_id == connection_id).all():
                lib.connection_id = None
            for lib in db.query(RemoteMediaLibrary).filter(RemoteMediaLibrary.connection_id == connection_id).all():
                lib.connection_id = None
                lib.enabled = False
        elif action == "delete":
            for lib in db.query(RemoteMediaLibrary).filter(RemoteMediaLibrary.connection_id == connection_id).all():
                db.query(SyncSeenFile).filter(SyncSeenFile.binding_id == lib.id).delete()
                db.delete(lib)
            for lib in db.query(MediaLibrary).filter(MediaLibrary.connection_id == connection_id).all():
                db.delete(lib)
        db.delete(conn)
        db.commit()

    async def test_connection(self, db: Session, connection_id: str) -> SmbConnectionTestResponse:
        conn = db.get(SmbConnection, connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        return await self._test_with_config(self._conn_to_full_dict(conn))

    async def test_new_connection(self, request: SmbConnectionCreateRequest | SmbConnectionUpdateRequest) -> SmbConnectionTestResponse:
        config_dict = {
            "host": request.host,
            "port": request.port,
            "share": request.share,
            "username": request.username,
            "password": request.password,
            "domain": request.domain,
            "base_path": request.base_path,
        }
        return await self._test_with_config(config_dict)

    async def browse(self, db: Session, connection_id: str, path: str) -> SmbBrowseResponse:
        conn = db.get(SmbConnection, connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        config = SmbConfig.from_dict(self._conn_to_full_dict(conn))
        writer = SmbWriter(config)
        entries = await writer.list_dir(path)
        return SmbBrowseResponse(
            connection_id=connection_id,
            path=path,
            entries=[SmbBrowseEntry(**entry) for entry in entries],
        )

    async def _test_with_config(self, config_dict: dict[str, Any]) -> SmbConnectionTestResponse:
        try:
            self._validate_base_path(config_dict.get("base_path", "/"))
            writer = SmbWriter(SmbConfig.from_dict(config_dict))
            await writer.test_connection()
        except SmbStorageError as exc:
            return SmbConnectionTestResponse(ok=False, error_code=exc.code, error_message=exc.message)
        except ValueError as exc:
            return SmbConnectionTestResponse(ok=False, error_code=str(exc), error_message=self._message_for_error(str(exc)))
        return SmbConnectionTestResponse(ok=True)

    def _set_enabled(self, db: Session, connection_id: str, enabled: bool) -> SmbConnectionResponse:
        conn = db.get(SmbConnection, connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        conn.enabled = enabled
        db.commit()
        db.refresh(conn)
        return self._to_response(db, conn)

    def _interrupt_running_tasks(self, db: Session, connection_id: str) -> None:
        tasks = (
            db.query(TransferTask)
            .filter(TransferTask.status.in_(RUNNING_TRANSFER_STATUSES))
            .all()
        )
        for task in tasks:
            snapshot = task.source_config_snapshot or task.storage_config_snapshot or {}
            if snapshot.get("connection_id") == connection_id or snapshot.get("host"):
                task.status = "failed"
                task.error_code = "STORAGE_CONFIG_CHANGED"
                task.error_message = "SMB 连接配置已变更，任务已中断，可使用最新配置重试。"
                task.retryable = True
                db.add(
                    TransferLog(
                        id=uuid4().hex,
                        task_id=task.id,
                        level="warning",
                        event="storage_config_changed",
                        message="SMB 连接配置已变更，运行中任务已中断。",
                        data_json={"error_code": "STORAGE_CONFIG_CHANGED", "connection_id": connection_id},
                    )
                )

    def _validate_base_path(self, base_path: str) -> None:
        normalized = base_path.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("SMB_PATH_INVALID")

    def _conn_to_config_dict(self, conn: SmbConnection) -> dict[str, Any]:
        return {
            "host": conn.host,
            "port": conn.port,
            "share": conn.share,
            "username": conn.username,
            "domain": conn.domain or "",
            "base_path": conn.base_path,
        }

    def _conn_to_full_dict(self, conn: SmbConnection) -> dict[str, Any]:
        value = self._conn_to_config_dict(conn)
        value["password"] = conn.password
        return value

    def _to_response(self, db: Session, conn: SmbConnection) -> SmbConnectionResponse:
        bound_local = [lib.name for lib in db.query(MediaLibrary).filter(MediaLibrary.connection_id == conn.id).all()]
        bound_remote = [lib.name for lib in db.query(RemoteMediaLibrary).filter(RemoteMediaLibrary.connection_id == conn.id).all()]
        return SmbConnectionResponse(
            id=conn.id,
            name=conn.name,
            enabled=conn.enabled,
            host=conn.host,
            port=conn.port,
            share=conn.share,
            username=conn.username,
            password_set=bool(conn.password),
            domain=conn.domain or "",
            base_path=conn.base_path,
            bound_local_libraries=bound_local,
            bound_remote_libraries=bound_remote,
            created_at=conn.created_at.isoformat() if conn.created_at else None,
            updated_at=conn.updated_at.isoformat() if conn.updated_at else None,
        )

    def _message_for_error(self, error_code: str) -> str:
        messages = {
            "SMB_PATH_INVALID": "SMB 路径配置无效。",
            "SMB_PATH_OUTSIDE_ROOT": "SMB 路径超出允许范围。",
            "SMB_CLIENT_NOT_INSTALLED": "SMB 客户端依赖未安装，暂不能连接真实 SMB。",
            "SMB_CONNECT_FAILED": "SMB 连接或认证失败。",
            "SMB_HOST_UNREACHABLE": "无法连接 SMB 主机或端口。",
            "SMB_AUTH_FAILED": "SMB 认证失败。",
            "SMB_PERMISSION_DENIED": "SMB 权限不足。",
            "SMB_SHARE_NOT_FOUND": "SMB 共享不存在或名称不正确。",
        }
        return messages.get(error_code, "SMB 连接测试失败。")


smb_connection_service = SmbConnectionService()
