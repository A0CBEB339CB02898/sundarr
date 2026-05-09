from sqlalchemy.orm import Session

from sundarr.app.models import MediaLibrary, RemoteMediaLibrary, SmbConnection
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
    def list_libraries(self, db: Session) -> RemoteMediaLibraryListResponse:
        rows = db.query(RemoteMediaLibrary).order_by(RemoteMediaLibrary.created_at, RemoteMediaLibrary.id).all()
        results = [self._to_response(row) for row in rows]
        return RemoteMediaLibraryListResponse(count=len(results), results=results)

    def get_library(self, db: Session, library_id: str) -> RemoteMediaLibraryResponse | None:
        lib = db.get(RemoteMediaLibrary, library_id)
        return self._to_response(lib) if lib else None

    def create_library(self, db: Session, request: RemoteMediaLibraryCreateRequest) -> RemoteMediaLibraryResponse:
        if db.get(RemoteMediaLibrary, request.id) is not None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_EXISTS")
        conn = db.get(SmbConnection, request.connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        self._validate_path(request.base_path)
        lib = RemoteMediaLibrary(
            id=request.id,
            name=request.name,
            media_type=request.media_type,
            enabled=request.enabled,
            connection_id=request.connection_id,
            base_path=request.base_path,
        )
        db.add(lib)
        db.commit()
        db.refresh(lib)
        return self._to_response(lib)

    def update_library(self, db: Session, library_id: str, request: RemoteMediaLibraryUpdateRequest) -> RemoteMediaLibraryResponse:
        lib = db.get(RemoteMediaLibrary, library_id)
        if lib is None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_NOT_FOUND")
        conn = db.get(SmbConnection, request.connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        self._validate_path(request.base_path)

        lib.name = request.name
        lib.media_type = request.media_type
        lib.enabled = request.enabled
        lib.connection_id = request.connection_id
        lib.base_path = request.base_path
        db.commit()
        db.refresh(lib)
        return self._to_response(lib)

    def enable_library(self, db: Session, library_id: str) -> RemoteMediaLibraryResponse:
        return self._set_enabled(db, library_id, True)

    def disable_library(self, db: Session, library_id: str) -> RemoteMediaLibraryResponse:
        return self._set_enabled(db, library_id, False)

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
        return self._to_response(lib)

    def _validate_path(self, base_path: str) -> None:
        normalized = base_path.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("SMB_PATH_INVALID")

    def _to_response(self, lib: RemoteMediaLibrary) -> RemoteMediaLibraryResponse:
        return RemoteMediaLibraryResponse(
            id=lib.id,
            name=lib.name,
            media_type=lib.media_type,
            enabled=lib.enabled,
            connection_id=lib.connection_id,
            base_path=lib.base_path,
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
