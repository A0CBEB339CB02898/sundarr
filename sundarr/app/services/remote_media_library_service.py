from sqlalchemy.orm import Session

from sundarr.app.models import MediaLibrary, RemoteMediaLibrary, SmbConnection, SyncSeenFile, TransferTask
from sundarr.app.schemas.remote_media_library import (
    RemoteMediaLibraryCreateRequest,
    RemoteMediaLibraryListResponse,
    RemoteMediaLibraryResponse,
    RemoteMediaLibraryTestResponse,
    RemoteMediaLibraryUpdateRequest,
)
from sundarr.app.storage import SmbConfig, SmbWriter
from sundarr.app.storage.smb import SmbStorageError


class RemoteMediaLibraryService:
    def list_libraries(self, db: Session, page: int = 1, page_size: int = 20) -> RemoteMediaLibraryListResponse:
        query = db.query(RemoteMediaLibrary).order_by(RemoteMediaLibrary.created_at, RemoteMediaLibrary.id)
        count = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        results = [self._to_response(db, row) for row in rows]
        return RemoteMediaLibraryListResponse(count=count, page=page, page_size=page_size, results=results)

    def get_library(self, db: Session, library_id: str) -> RemoteMediaLibraryResponse | None:
        lib = db.get(RemoteMediaLibrary, library_id)
        return self._to_response(db, lib) if lib else None

    def create_library(self, db: Session, request: RemoteMediaLibraryCreateRequest) -> RemoteMediaLibraryResponse:
        if db.get(RemoteMediaLibrary, request.id) is not None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_EXISTS")
        conn = db.get(SmbConnection, request.connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        if request.target_library_id:
            target = db.get(MediaLibrary, request.target_library_id)
            if target is None:
                raise ValueError("MEDIA_LIBRARY_NOT_FOUND")
        self._validate_path(request.base_path)
        lib = RemoteMediaLibrary(
            id=request.id,
            name=request.name,
            media_type=request.media_type,
            enabled=request.enabled,
            connection_id=request.connection_id,
            base_path=request.base_path,
            target_library_id=request.target_library_id,
            scan_interval_seconds=request.scan_interval_seconds,
            stable_seconds=request.stable_seconds,
            delete_source_after_success=request.delete_source_after_success,
            delete_empty_source_dirs=request.delete_empty_source_dirs,
        )
        db.add(lib)
        db.commit()
        db.refresh(lib)
        return self._to_response(db, lib)

    def update_library(self, db: Session, library_id: str, request: RemoteMediaLibraryUpdateRequest) -> RemoteMediaLibraryResponse:
        lib = db.get(RemoteMediaLibrary, library_id)
        if lib is None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_NOT_FOUND")
        conn = db.get(SmbConnection, request.connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        if request.target_library_id:
            target = db.get(MediaLibrary, request.target_library_id)
            if target is None:
                raise ValueError("MEDIA_LIBRARY_NOT_FOUND")
        self._validate_path(request.base_path)

        lib.name = request.name
        lib.media_type = request.media_type
        lib.enabled = request.enabled
        lib.connection_id = request.connection_id
        lib.base_path = request.base_path
        lib.target_library_id = request.target_library_id
        lib.scan_interval_seconds = request.scan_interval_seconds
        lib.stable_seconds = request.stable_seconds
        lib.delete_source_after_success = request.delete_source_after_success
        lib.delete_empty_source_dirs = request.delete_empty_source_dirs
        db.commit()
        db.refresh(lib)
        return self._to_response(db, lib)

    def enable_library(self, db: Session, library_id: str) -> RemoteMediaLibraryResponse:
        return self._set_enabled(db, library_id, True)

    def disable_library(self, db: Session, library_id: str) -> RemoteMediaLibraryResponse:
        return self._set_enabled(db, library_id, False)

    def delete_library(self, db: Session, library_id: str) -> None:
        lib = db.get(RemoteMediaLibrary, library_id)
        if lib is None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_NOT_FOUND")
        db.query(SyncSeenFile).filter(SyncSeenFile.binding_id == library_id).delete()
        db.delete(lib)
        db.commit()

    async def test_library(self, db: Session, library_id: str) -> RemoteMediaLibraryTestResponse:
        lib = db.get(RemoteMediaLibrary, library_id)
        if lib is None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_NOT_FOUND")
        conn = db.get(SmbConnection, lib.connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        return await self._test_with_connection(db, lib.connection_id, lib.base_path)

    async def _test_with_connection(self, db: Session, connection_id: str, base_path: str) -> RemoteMediaLibraryTestResponse:
        conn = db.get(SmbConnection, connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        try:
            self._validate_path(base_path)
            config = SmbConfig(
                host=conn.host, port=conn.port, share=conn.share,
                username=conn.username, password=conn.password,
                domain=conn.domain or "", base_path=conn.base_path,
            )
            writer = SmbWriter(config)
            target = base_path.strip().replace("\\", "/").strip("/")
            if target:
                await writer.list_dir(target)
            else:
                await writer.test_connection()
        except SmbStorageError as exc:
            return RemoteMediaLibraryTestResponse(ok=False, error_code=exc.code, error_message=exc.message)
        except ValueError as exc:
            return RemoteMediaLibraryTestResponse(ok=False, error_code=str(exc), error_message=self._message_for_error(str(exc)))
        return RemoteMediaLibraryTestResponse(ok=True)

    def _set_enabled(self, db: Session, library_id: str, enabled: bool) -> RemoteMediaLibraryResponse:
        lib = db.get(RemoteMediaLibrary, library_id)
        if lib is None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_NOT_FOUND")
        lib.enabled = enabled
        db.commit()
        db.refresh(lib)
        return self._to_response(db, lib)

    def _validate_path(self, base_path: str) -> None:
        normalized = base_path.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("SMB_PATH_INVALID")

    def _to_response(self, db: Session, lib: RemoteMediaLibrary) -> RemoteMediaLibraryResponse:
        target_library_name = None
        if lib.target_library_id:
            target_lib = db.get(MediaLibrary, lib.target_library_id)
            if target_lib:
                target_library_name = target_lib.name
        return RemoteMediaLibraryResponse(
            id=lib.id,
            name=lib.name,
            media_type=lib.media_type,
            enabled=lib.enabled,
            connection_id=lib.connection_id,
            base_path=lib.base_path,
            target_library_id=lib.target_library_id,
            target_library_name=target_library_name,
            scan_interval_seconds=lib.scan_interval_seconds,
            stable_seconds=lib.stable_seconds,
            delete_source_after_success=lib.delete_source_after_success,
            delete_empty_source_dirs=lib.delete_empty_source_dirs,
            created_at=lib.created_at.isoformat() if lib.created_at else None,
            updated_at=lib.updated_at.isoformat() if lib.updated_at else None,
        )

    def _message_for_error(self, error_code: str) -> str:
        messages = {
            "SMB_PATH_INVALID": "远程媒体库路径配置无效。",
            "SMB_CLIENT_NOT_INSTALLED": "SMB 客户端依赖未安装，暂不能连接真实 SMB。",
            "SMB_CONNECT_FAILED": "SMB 连接或认证失败。",
            "SMB_HOST_UNREACHABLE": "无法连接 SMB 主机或端口。",
            "SMB_AUTH_FAILED": "SMB 认证失败。",
            "SMB_PERMISSION_DENIED": "SMB 权限不足。",
            "SMB_SHARE_NOT_FOUND": "SMB 共享不存在或名称不正确。",
        }
        return messages.get(error_code, "远程媒体库测试失败。")


remote_media_library_service = RemoteMediaLibraryService()
