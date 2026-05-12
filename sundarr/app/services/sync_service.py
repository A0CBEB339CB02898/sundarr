from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.models import (
    MediaLibrary,
    RemoteMediaLibrary,
    Setting,
    SmbConnection,
    SyncBinding,
    SyncSeenFile,
    TransferFile,
    TransferTask,
)
from sundarr.app.schemas.sync import (
    SyncBindingCreateRequest,
    SyncBindingListResponse,
    SyncBindingResponse,
    SyncBindingTestResponse,
    SyncBindingUpdateRequest,
    SyncConfigRequest,
    SyncConfigResponse,
    SyncDiscoveredFileResponse,
    SyncDiscoveredListResponse,
    SyncScanRequest,
    SyncScanResponse,
    SyncTaskCreateRequest,
    SyncTaskCreateResponse,
)
from sundarr.app.services.transfer_service import transfer_service
from sundarr.app.storage import SmbConfig, SmbWriter, StorageWriter
from sundarr.app.storage.smb import SmbStorageError

SYNC_CONFIG_KEY = "download_to_local.config"
DOWNLOADING_SUFFIX = ".sundarr.downloading"


class SyncService:
    def __init__(self) -> None:
        self._list_dir_override: Callable[[str, str], Awaitable[list[dict]]] | None = None

    def get_config(self, db: Session) -> SyncConfigResponse:
        setting = db.get(Setting, SYNC_CONFIG_KEY)
        if setting is None:
            return SyncConfigResponse()
        return SyncConfigResponse(**setting.value_json)

    def save_config(self, db: Session, request: SyncConfigRequest) -> SyncConfigResponse:
        value = request.model_dump()
        setting = db.get(Setting, SYNC_CONFIG_KEY)
        if setting is None:
            setting = Setting(key=SYNC_CONFIG_KEY, value_json=value, is_sensitive=False)
            db.add(setting)
        else:
            setting.value_json = value
            setting.is_sensitive = False
        db.commit()
        db.refresh(setting)
        return SyncConfigResponse(**setting.value_json)

    def list_bindings(self, db: Session) -> SyncBindingListResponse:
        rows = db.query(SyncBinding).order_by(SyncBinding.created_at, SyncBinding.id).all()
        results = [self._binding_to_response(row) for row in rows]
        return SyncBindingListResponse(count=len(results), results=results)

    def get_binding(self, db: Session, binding_id: str) -> SyncBindingResponse | None:
        binding = db.get(SyncBinding, binding_id)
        return self._binding_to_response(binding) if binding else None

    def create_binding(self, db: Session, request: SyncBindingCreateRequest) -> SyncBindingResponse:
        if db.get(SyncBinding, request.id) is not None:
            raise ValueError("SYNC_BINDING_EXISTS")
        remote_lib = db.get(RemoteMediaLibrary, request.remote_library_id)
        if remote_lib is None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_NOT_FOUND")
        local_lib = db.get(MediaLibrary, request.local_library_id)
        if local_lib is None:
            raise ValueError("MEDIA_LIBRARY_NOT_FOUND")
        self._validate_binding_media_type(remote_lib, local_lib, request.media_type)
        binding = SyncBinding(
            id=request.id,
            name=request.name,
            enabled=request.enabled,
            media_type=request.media_type,
            remote_library_id=request.remote_library_id,
            local_library_id=request.local_library_id,
            delete_source_after_success=request.delete_source_after_success,
            delete_empty_source_dirs=request.delete_empty_source_dirs,
        )
        db.add(binding)
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    def update_binding(self, db: Session, binding_id: str, request: SyncBindingUpdateRequest) -> SyncBindingResponse:
        binding = db.get(SyncBinding, binding_id)
        if binding is None:
            raise ValueError("SYNC_BINDING_NOT_FOUND")
        remote_lib = db.get(RemoteMediaLibrary, request.remote_library_id)
        if remote_lib is None:
            raise ValueError("REMOTE_MEDIA_LIBRARY_NOT_FOUND")
        local_lib = db.get(MediaLibrary, request.local_library_id)
        if local_lib is None:
            raise ValueError("MEDIA_LIBRARY_NOT_FOUND")
        self._validate_binding_media_type(remote_lib, local_lib, request.media_type)

        binding.name = request.name
        binding.enabled = request.enabled
        binding.media_type = request.media_type
        binding.remote_library_id = request.remote_library_id
        binding.local_library_id = request.local_library_id
        binding.delete_source_after_success = request.delete_source_after_success
        binding.delete_empty_source_dirs = request.delete_empty_source_dirs
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    def enable_binding(self, db: Session, binding_id: str) -> SyncBindingResponse:
        return self._set_binding_enabled(db, binding_id, True)

    def disable_binding(self, db: Session, binding_id: str) -> SyncBindingResponse:
        return self._set_binding_enabled(db, binding_id, False)

    async def test_binding(self, db: Session, binding_id: str) -> SyncBindingTestResponse:
        binding = db.get(SyncBinding, binding_id)
        if binding is None:
            raise ValueError("SYNC_BINDING_NOT_FOUND")
        remote_ok = await self._test_remote_library(db, binding.remote_library_id)
        local_ok = await self._test_local_library(db, binding.local_library_id)
        if remote_ok and local_ok:
            return SyncBindingTestResponse(ok=True, remote_ok=True, local_ok=True)
        error_code = "SYNC_REMOTE_FAILED" if not remote_ok else "SYNC_LOCAL_FAILED"
        return SyncBindingTestResponse(ok=False, remote_ok=remote_ok, local_ok=local_ok, error_code=error_code)

    async def scan(self, db: Session, request: SyncScanRequest) -> SyncScanResponse:
        bindings_query = db.query(SyncBinding).filter(SyncBinding.enabled.is_(True))
        if request.binding_id:
            bindings_query = bindings_query.filter(SyncBinding.id == request.binding_id)
        bindings = bindings_query.order_by(SyncBinding.created_at, SyncBinding.id).all()
        if request.binding_id and not bindings:
            raise ValueError("SYNC_BINDING_NOT_FOUND")

        results: list[SyncSeenFile] = []
        scanned_count = 0
        for binding in bindings:
            remote_lib = db.get(RemoteMediaLibrary, binding.remote_library_id)
            local_lib = db.get(MediaLibrary, binding.local_library_id)
            if remote_lib is None or local_lib is None or not remote_lib.enabled:
                continue
            try:
                self._validate_binding_media_type(remote_lib, local_lib, binding.media_type)
            except ValueError:
                continue
            scanned_count += 1
            stable_seconds = remote_lib.stable_seconds or 120
            entries = await self._scan_dir(db, remote_lib, remote_lib.base_path)
            for entry in entries:
                seen = self._upsert_seen_file(db, binding, remote_lib, entry, stable_seconds)
                results.append(seen)
        db.commit()
        for seen in results:
            db.refresh(seen)
        return SyncScanResponse(
            scanned_bindings=scanned_count,
            discovered_count=sum(1 for item in results if item.status == "discovered"),
            stable_count=sum(1 for item in results if item.status == "stable"),
            results=[self._seen_file_to_response(item) for item in results],
        )

    def list_discovered(self, db: Session) -> SyncDiscoveredListResponse:
        rows = db.query(SyncSeenFile).order_by(SyncSeenFile.updated_at.desc(), SyncSeenFile.created_at.desc()).all()
        results = [self._seen_file_to_response(row) for row in rows]
        return SyncDiscoveredListResponse(count=len(results), results=results)

    async def create_tasks(self, db: Session, request: SyncTaskCreateRequest) -> SyncTaskCreateResponse:
        query = db.query(SyncSeenFile).filter(SyncSeenFile.status == "stable", SyncSeenFile.task_id.is_(None))
        if request.binding_id:
            query = query.filter(SyncSeenFile.binding_id == request.binding_id)
            if db.get(SyncBinding, request.binding_id) is None:
                raise ValueError("SYNC_BINDING_NOT_FOUND")

        seen_files = query.order_by(SyncSeenFile.updated_at, SyncSeenFile.id).all()
        tasks: list[TransferTask] = []
        skipped_count = 0
        for seen in seen_files:
            binding = db.get(SyncBinding, seen.binding_id) if seen.binding_id else None
            if binding is None:
                seen.status = "failed"
                skipped_count += 1
                continue
            remote_lib = db.get(RemoteMediaLibrary, binding.remote_library_id)
            local_lib = db.get(MediaLibrary, binding.local_library_id)
            if remote_lib is None or local_lib is None or not remote_lib.enabled:
                seen.status = "failed"
                skipped_count += 1
                continue
            try:
                self._validate_binding_media_type(remote_lib, local_lib, binding.media_type)
            except ValueError:
                seen.status = "failed"
                skipped_count += 1
                continue
            task = await self._create_transfer_task_for_seen_file(db, binding, remote_lib, local_lib, seen)
            if task is None:
                skipped_count += 1
                continue
            tasks.append(task)
        db.commit()
        for task in tasks:
            db.refresh(task)
        return SyncTaskCreateResponse(
            created_count=len(tasks),
            skipped_count=skipped_count,
            tasks=[transfer_service._to_response(task).model_dump() for task in tasks],
        )

    def _set_binding_enabled(self, db: Session, binding_id: str, enabled: bool) -> SyncBindingResponse:
        binding = db.get(SyncBinding, binding_id)
        if binding is None:
            raise ValueError("SYNC_BINDING_NOT_FOUND")
        binding.enabled = enabled
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    async def _test_remote_library(self, db: Session, library_id: str) -> bool:
        lib = db.get(RemoteMediaLibrary, library_id)
        if lib is None:
            return False
        conn = db.get(SmbConnection, lib.connection_id)
        if conn is None:
            return False
        try:
            config = SmbConfig(
                host=conn.host, port=conn.port, share=conn.share,
                username=conn.username, password=conn.password,
                domain=conn.domain or "", base_path=conn.base_path,
            )
            writer = SmbWriter(config)
            target = lib.base_path.strip().replace("\\", "/").strip("/")
            if target:
                await writer.list_dir(target)
            else:
                await writer.test_connection()
            return True
        except (SmbStorageError, ValueError):
            return False

    async def _test_local_library(self, db: Session, library_id: str) -> bool:
        lib = db.get(MediaLibrary, library_id)
        if lib is None:
            return False
        conn = db.get(SmbConnection, lib.connection_id)
        if conn is None:
            return False
        try:
            config = SmbConfig(
                host=conn.host, port=conn.port, share=conn.share,
                username=conn.username, password=conn.password,
                domain=conn.domain or "", base_path=conn.base_path,
            )
            writer = SmbWriter(config)
            target = lib.base_path.strip().replace("\\", "/").strip("/")
            if target:
                await writer.list_dir(target)
            else:
                await writer.test_connection()
            return True
        except (SmbStorageError, ValueError):
            return False

    async def _scan_dir(self, db: Session, lib: RemoteMediaLibrary, path: str) -> list[dict]:
        entries = await self._list_source_dir(db, lib, path)
        files: list[dict] = []
        for entry in entries:
            if entry.get("is_dir"):
                files.extend(await self._scan_dir(db, lib, str(entry.get("path", ""))))
            else:
                source_path = str(entry.get("path", "")).replace("\\", "/").strip("/")
                if not source_path.endswith(DOWNLOADING_SUFFIX):
                    files.append(entry)
        return files

    async def _list_source_dir(self, db: Session, lib: RemoteMediaLibrary, path: str) -> list[dict]:
        if self._list_dir_override is not None:
            return await self._list_dir_override(lib.connection_id, path)
        conn = db.get(SmbConnection, lib.connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        config = SmbConfig(
            host=conn.host, port=conn.port, share=conn.share,
            username=conn.username, password=conn.password,
            domain=conn.domain or "", base_path=conn.base_path,
        )
        writer = SmbWriter(config)
        return await writer.list_dir(path)

    def _upsert_seen_file(
        self,
        db: Session,
        binding: SyncBinding,
        remote_lib: RemoteMediaLibrary,
        entry: dict,
        stable_seconds: int,
    ) -> SyncSeenFile:
        source_path = str(entry.get("path", "")).strip("/")
        source_size = entry.get("size")
        source_mtime = str(entry.get("modified_at") or "") or None
        fingerprint = f"{binding.id}|{remote_lib.id}|{source_path}"
        seen = db.query(SyncSeenFile).filter(SyncSeenFile.source_fingerprint == fingerprint).one_or_none()
        if seen is None:
            seen = SyncSeenFile(
                id=uuid4().hex,
                binding_id=binding.id,
                source_fingerprint=fingerprint,
                source_path=source_path,
                source_size=int(source_size) if source_size is not None else None,
                source_mtime=source_mtime,
                status="discovered",
            )
            db.add(seen)
            return seen

        same_file = (
            seen.source_size == (int(source_size) if source_size is not None else None)
            and seen.source_mtime == source_mtime
        )
        if same_file and self._age_seconds(seen.updated_at) >= stable_seconds and seen.status in {"discovered", "stable"}:
            seen.status = "stable"
        else:
            seen.source_size = int(source_size) if source_size is not None else None
            seen.source_mtime = source_mtime
            if seen.status != "stable" or not same_file:
                seen.status = "discovered"
        return seen

    def _age_seconds(self, value: datetime | None) -> float:
        if value is None:
            return 0
        current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - current).total_seconds()

    async def _create_transfer_task_for_seen_file(
        self,
        db: Session,
        binding: SyncBinding,
        remote_lib: RemoteMediaLibrary,
        local_lib: MediaLibrary,
        seen: SyncSeenFile,
    ) -> TransferTask | None:
        remote_conn = db.get(SmbConnection, remote_lib.connection_id)
        local_conn = db.get(SmbConnection, local_lib.connection_id)
        if remote_conn is None or local_conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")

        target_path = self._build_target_path(local_lib.base_path, seen.source_path, remote_lib.base_path)
        source_config_snapshot = {
            "connection_id": remote_lib.connection_id,
            "host": remote_conn.host,
            "port": remote_conn.port,
            "share": remote_conn.share,
            "username": remote_conn.username,
            "domain": remote_conn.domain or "",
            "base_path": remote_conn.base_path,
            "password": remote_conn.password,
        }
        storage_config_snapshot = {
            "connection_id": local_lib.connection_id,
            "host": local_conn.host,
            "port": local_conn.port,
            "share": local_conn.share,
            "username": local_conn.username,
            "domain": local_conn.domain or "",
            "base_path": local_conn.base_path,
            "password": local_conn.password,
        }
        source_writer = SmbWriter(SmbConfig.from_dict(source_config_snapshot))
        target_writer = SmbWriter(SmbConfig.from_dict(storage_config_snapshot))
        if await self._target_already_completed(source_writer, target_writer, seen.source_path, target_path, seen.source_size or 0):
            seen.status = "completed"
            return None

        task = TransferTask(
            id=uuid4().hex,
            resource_id=None,
            link_id=None,
            status="pending",
            mode="download_to_local",
            target_type="smb",
            target_library=binding.media_type,
            target_path=target_path,
            source_type="smb",
            source_path=seen.source_path,
            source_config_snapshot=source_config_snapshot,
            storage_config_snapshot=storage_config_snapshot,
            sync_seen_file_id=seen.id,
            total_bytes=seen.source_size or 0,
        )
        db.add(task)
        db.flush()
        db.add(
            TransferFile(
                id=uuid4().hex,
                task_id=task.id,
                cloud_file_id=None,
                cloud_path=seen.source_path,
                target_path=target_path,
                temp_path=f"{target_path}.sundarr.downloading",
                filename=target_path.rsplit("/", 1)[-1] or target_path,
                size_bytes=seen.source_size or 0,
                status="pending",
            )
        )
        seen.task_id = task.id
        seen.status = "queued"
        return task

    async def _target_already_completed(
        self,
        source_writer: StorageWriter,
        target_writer: StorageWriter,
        source_path: str,
        target_path: str,
        expected_size: int,
    ) -> bool:
        try:
            if not await target_writer.exists(target_path):
                return False
            if expected_size and await target_writer.size(target_path) != expected_size:
                return False
            return await source_writer.checksum_md5(source_path) == await target_writer.checksum_md5(target_path)
        except NotImplementedError:
            return False
        except ValueError:
            return False

    def _build_target_path(self, library_base_path: str, source_path: str, remote_base_path: str = "") -> str:
        normalized_source = source_path.replace("\\", "/").strip("/")
        normalized_remote_base = remote_base_path.replace("\\", "/").strip("/")
        normalized_base = library_base_path.replace("\\", "/").strip("/")
        if not normalized_source or ".." in normalized_source.split("/"):
            raise ValueError("SYNC_SOURCE_PATH_INVALID")
        if normalized_source.endswith(DOWNLOADING_SUFFIX):
            raise ValueError("SYNC_SOURCE_PATH_INVALID")
        source_parts = normalized_source.split("/")
        remote_base_parts = [part for part in normalized_remote_base.split("/") if part]
        if remote_base_parts and source_parts[: len(remote_base_parts)] == remote_base_parts:
            source_parts = source_parts[len(remote_base_parts):]
        normalized_source = "/".join(source_parts)
        if not normalized_source:
            raise ValueError("SYNC_SOURCE_PATH_INVALID")
        if normalized_base:
            return f"{normalized_base}/{normalized_source}"
        return normalized_source

    def _validate_binding_media_type(self, remote_lib: RemoteMediaLibrary, local_lib: MediaLibrary, media_type: str) -> None:
        if remote_lib.media_type != media_type or local_lib.media_type != media_type:
            raise ValueError("SYNC_MEDIA_TYPE_MISMATCH")

    def _binding_to_response(self, binding: SyncBinding) -> SyncBindingResponse:
        return SyncBindingResponse(
            id=binding.id,
            name=binding.name,
            enabled=binding.enabled,
            media_type=binding.media_type,
            remote_library_id=binding.remote_library_id,
            local_library_id=binding.local_library_id,
            delete_source_after_success=binding.delete_source_after_success,
            delete_empty_source_dirs=binding.delete_empty_source_dirs,
            created_at=binding.created_at.isoformat() if binding.created_at else None,
            updated_at=binding.updated_at.isoformat() if binding.updated_at else None,
        )

    def _seen_file_to_response(self, seen: SyncSeenFile) -> SyncDiscoveredFileResponse:
        return SyncDiscoveredFileResponse(
            id=seen.id,
            binding_id=seen.binding_id,
            source_fingerprint=seen.source_fingerprint,
            source_path=seen.source_path,
            source_size=seen.source_size,
            source_mtime=seen.source_mtime,
            status=seen.status,
            task_id=seen.task_id,
            created_at=seen.created_at.isoformat() if seen.created_at else None,
            updated_at=seen.updated_at.isoformat() if seen.updated_at else None,
        )


sync_service = SyncService()
