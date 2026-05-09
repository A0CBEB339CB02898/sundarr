from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.models import (
    DownloadToLocalBinding,
    DownloadToLocalSeenFile,
    MediaLibrary,
    Setting,
    SmbConnection,
    TransferFile,
    TransferTask,
)
from sundarr.app.schemas.download_to_local import (
    DtlBindingCreateRequest,
    DtlBindingListResponse,
    DtlBindingResponse,
    DtlBindingTestResponse,
    DtlBindingUpdateRequest,
    DtlConfigRequest,
    DtlConfigResponse,
    DtlDiscoveredFileResponse,
    DtlDiscoveredListResponse,
    DtlScanRequest,
    DtlScanResponse,
    DtlTaskCreateRequest,
    DtlTaskCreateResponse,
)
from sundarr.app.services.transfer_service import transfer_service
from sundarr.app.storage import SmbConfig, SmbWriter
from sundarr.app.storage.smb import SmbStorageError

DTL_CONFIG_KEY = "download_to_local.config"
DEFAULT_DTL_CONFIG = {
    "delete_source_after_success": True,
    "delete_empty_source_dirs": True,
    "scan_interval_seconds": 60,
    "stable_seconds": 120,
    "unclassified_library_id": "",
}


class DownloadToLocalService:
    def __init__(self) -> None:
        self._list_dir_override: Callable[[SmbConnection, str], Awaitable[list[dict]]] | None = None

    def get_config(self, db: Session) -> DtlConfigResponse:
        setting = db.get(Setting, DTL_CONFIG_KEY)
        return DtlConfigResponse(**(setting.value_json if setting else DEFAULT_DTL_CONFIG))

    def save_config(self, db: Session, request: DtlConfigRequest) -> DtlConfigResponse:
        value = request.model_dump()
        setting = db.get(Setting, DTL_CONFIG_KEY)
        if setting is None:
            setting = Setting(key=DTL_CONFIG_KEY, value_json=value, is_sensitive=False)
            db.add(setting)
        else:
            setting.value_json = value
            setting.is_sensitive = False
        db.commit()
        db.refresh(setting)
        return DtlConfigResponse(**setting.value_json)

    def list_bindings(self, db: Session) -> DtlBindingListResponse:
        rows = db.query(DownloadToLocalBinding).order_by(DownloadToLocalBinding.created_at, DownloadToLocalBinding.id).all()
        results = [self._binding_to_response(row) for row in rows]
        return DtlBindingListResponse(count=len(results), results=results)

    def get_binding(self, db: Session, binding_id: str) -> DtlBindingResponse | None:
        binding = db.get(DownloadToLocalBinding, binding_id)
        return self._binding_to_response(binding) if binding else None

    def create_binding(self, db: Session, request: DtlBindingCreateRequest) -> DtlBindingResponse:
        if db.get(DownloadToLocalBinding, request.id) is not None:
            raise ValueError("DTL_BINDING_EXISTS")
        if db.get(SmbConnection, request.source_connection_id) is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        if db.get(MediaLibrary, request.target_library_id) is None:
            raise ValueError("MEDIA_LIBRARY_NOT_FOUND")
        self._validate_path(request.source_path)
        binding = DownloadToLocalBinding(
            id=request.id,
            name=request.name,
            enabled=request.enabled,
            media_type=request.media_type,
            source_connection_id=request.source_connection_id,
            source_path=request.source_path,
            target_library_id=request.target_library_id,
            delete_source_after_success=request.delete_source_after_success,
            delete_empty_source_dirs=request.delete_empty_source_dirs,
        )
        db.add(binding)
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    def update_binding(self, db: Session, binding_id: str, request: DtlBindingUpdateRequest) -> DtlBindingResponse:
        binding = db.get(DownloadToLocalBinding, binding_id)
        if binding is None:
            raise ValueError("DTL_BINDING_NOT_FOUND")
        if db.get(SmbConnection, request.source_connection_id) is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        if db.get(MediaLibrary, request.target_library_id) is None:
            raise ValueError("MEDIA_LIBRARY_NOT_FOUND")
        self._validate_path(request.source_path)

        binding.name = request.name
        binding.enabled = request.enabled
        binding.media_type = request.media_type
        binding.source_connection_id = request.source_connection_id
        binding.source_path = request.source_path
        binding.target_library_id = request.target_library_id
        binding.delete_source_after_success = request.delete_source_after_success
        binding.delete_empty_source_dirs = request.delete_empty_source_dirs
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    def enable_binding(self, db: Session, binding_id: str) -> DtlBindingResponse:
        return self._set_binding_enabled(db, binding_id, True)

    def disable_binding(self, db: Session, binding_id: str) -> DtlBindingResponse:
        return self._set_binding_enabled(db, binding_id, False)

    async def test_binding(self, db: Session, binding_id: str) -> DtlBindingTestResponse:
        binding = db.get(DownloadToLocalBinding, binding_id)
        if binding is None:
            raise ValueError("DTL_BINDING_NOT_FOUND")
        source_ok = await self._test_source(db, binding.source_connection_id, binding.source_path)
        target_ok = await self._test_target(db, binding.target_library_id)
        if source_ok and target_ok:
            return DtlBindingTestResponse(ok=True, source_ok=True, target_ok=True)
        error_code = "DTL_SOURCE_FAILED" if not source_ok else "DTL_TARGET_FAILED"
        return DtlBindingTestResponse(ok=False, source_ok=source_ok, target_ok=target_ok, error_code=error_code)

    async def scan(self, db: Session, request: DtlScanRequest) -> DtlScanResponse:
        bindings_query = db.query(DownloadToLocalBinding).filter(DownloadToLocalBinding.enabled.is_(True))
        if request.binding_id:
            bindings_query = bindings_query.filter(DownloadToLocalBinding.id == request.binding_id)
        bindings = bindings_query.order_by(DownloadToLocalBinding.created_at, DownloadToLocalBinding.id).all()
        if request.binding_id and not bindings:
            raise ValueError("DTL_BINDING_NOT_FOUND")

        config = self.get_config(db)
        results: list[DownloadToLocalSeenFile] = []
        for binding in bindings:
            entries = await self._scan_binding(db, binding)
            for entry in entries:
                seen = self._upsert_seen_file(db, binding, entry, config.stable_seconds)
                results.append(seen)
        db.commit()
        for seen in results:
            db.refresh(seen)
        return DtlScanResponse(
            scanned_bindings=len(bindings),
            discovered_count=sum(1 for item in results if item.status == "discovered"),
            stable_count=sum(1 for item in results if item.status == "stable"),
            results=[self._seen_file_to_response(item) for item in results],
        )

    def list_discovered(self, db: Session) -> DtlDiscoveredListResponse:
        rows = db.query(DownloadToLocalSeenFile).order_by(
            DownloadToLocalSeenFile.updated_at.desc(), DownloadToLocalSeenFile.created_at.desc()
        ).all()
        results = [self._seen_file_to_response(row) for row in rows]
        return DtlDiscoveredListResponse(count=len(results), results=results)

    def create_tasks(self, db: Session, request: DtlTaskCreateRequest) -> DtlTaskCreateResponse:
        query = db.query(DownloadToLocalSeenFile).filter(
            DownloadToLocalSeenFile.status == "stable", DownloadToLocalSeenFile.task_id.is_(None)
        )
        if request.binding_id:
            query = query.filter(DownloadToLocalSeenFile.binding_id == request.binding_id)
            if db.get(DownloadToLocalBinding, request.binding_id) is None:
                raise ValueError("DTL_BINDING_NOT_FOUND")

        seen_files = query.order_by(DownloadToLocalSeenFile.updated_at, DownloadToLocalSeenFile.id).all()
        tasks: list[TransferTask] = []
        skipped_count = 0
        for seen in seen_files:
            binding = db.get(DownloadToLocalBinding, seen.binding_id) if seen.binding_id else None
            if binding is None:
                seen.status = "failed"
                skipped_count += 1
                continue
            task = self._create_transfer_task_for_seen_file(db, binding, seen)
            tasks.append(task)
        db.commit()
        for task in tasks:
            db.refresh(task)
        return DtlTaskCreateResponse(
            created_count=len(tasks),
            skipped_count=skipped_count,
            tasks=[transfer_service._to_response(task) for task in tasks],
        )

    def _set_binding_enabled(self, db: Session, binding_id: str, enabled: bool) -> DtlBindingResponse:
        binding = db.get(DownloadToLocalBinding, binding_id)
        if binding is None:
            raise ValueError("DTL_BINDING_NOT_FOUND")
        binding.enabled = enabled
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    async def _test_source(self, db: Session, connection_id: str, source_path: str) -> bool:
        conn = db.get(SmbConnection, connection_id)
        if conn is None:
            return False
        try:
            self._validate_path(source_path)
            config = SmbConfig(
                host=conn.host, port=conn.port, share=conn.share,
                username=conn.username, password=conn.password,
                domain=conn.domain or "", base_path=conn.base_path,
            )
            writer = SmbWriter(config)
            target = source_path.strip().replace("\\", "/").strip("/")
            if target:
                await writer.list_dir(target)
            else:
                await writer.test_connection()
            return True
        except (SmbStorageError, ValueError):
            return False

    async def _test_target(self, db: Session, library_id: str) -> bool:
        lib = db.get(MediaLibrary, library_id)
        if lib is None:
            return False
        conn = db.get(SmbConnection, lib.connection_id)
        if conn is None:
            return False
        try:
            self._validate_path(lib.base_path)
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

    async def _scan_binding(self, db: Session, binding: DownloadToLocalBinding) -> list[dict]:
        return await self._scan_dir(db, binding, "")

    async def _scan_dir(self, db: Session, binding: DownloadToLocalBinding, path: str) -> list[dict]:
        entries = await self._list_source_dir(db, binding, path)
        files: list[dict] = []
        for entry in entries:
            if entry.get("is_dir"):
                files.extend(await self._scan_dir(db, binding, str(entry.get("path", ""))))
            else:
                files.append(entry)
        return files

    async def _list_source_dir(self, db: Session, binding: DownloadToLocalBinding, path: str) -> list[dict]:
        if self._list_dir_override is not None:
            return await self._list_dir_override(binding.source_connection_id, path)
        conn = db.get(SmbConnection, binding.source_connection_id)
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
        self, db: Session, binding: DownloadToLocalBinding, entry: dict, stable_seconds: int
    ) -> DownloadToLocalSeenFile:
        source_path = str(entry.get("path", "")).strip("/")
        source_size = entry.get("size")
        source_mtime = str(entry.get("modified_at") or "") or None
        fingerprint = self._source_fingerprint(binding, source_path)
        seen = db.query(DownloadToLocalSeenFile).filter(
            DownloadToLocalSeenFile.source_fingerprint == fingerprint
        ).one_or_none()
        if seen is None:
            seen = DownloadToLocalSeenFile(
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

    def _source_fingerprint(self, binding: DownloadToLocalBinding, source_path: str) -> str:
        conn_id = binding.source_connection_id
        return f"{conn_id}|{binding.source_path}|{source_path}"

    def _age_seconds(self, value: datetime | None) -> float:
        if value is None:
            return 0
        current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - current).total_seconds()

    def _create_transfer_task_for_seen_file(
        self, db: Session, binding: DownloadToLocalBinding, seen: DownloadToLocalSeenFile
    ) -> TransferTask:
        lib = db.get(MediaLibrary, binding.target_library_id)
        if lib is None:
            raise ValueError("MEDIA_LIBRARY_NOT_FOUND")
        conn = db.get(SmbConnection, binding.source_connection_id)
        if conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")
        target_conn = db.get(SmbConnection, lib.connection_id)
        if target_conn is None:
            raise ValueError("SMB_CONNECTION_NOT_FOUND")

        target_path = self._build_target_path(lib.base_path, seen.source_path)
        source_config_snapshot = {
            "connection_id": binding.source_connection_id,
            "host": conn.host,
            "port": conn.port,
            "share": conn.share,
            "username": conn.username,
            "domain": conn.domain or "",
            "base_path": conn.base_path,
            "password": conn.password,
        }
        storage_config_snapshot = {
            "connection_id": lib.connection_id,
            "host": target_conn.host,
            "port": target_conn.port,
            "share": target_conn.share,
            "username": target_conn.username,
            "domain": target_conn.domain or "",
            "base_path": target_conn.base_path,
            "password": target_conn.password,
        }
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
                temp_path=f"{target_path}.downloading",
                filename=target_path.rsplit("/", 1)[-1] or target_path,
                size_bytes=seen.source_size or 0,
                status="pending",
            )
        )
        seen.task_id = task.id
        seen.status = "queued"
        return task

    def _build_target_path(self, library_base_path: str, source_path: str) -> str:
        normalized_source = source_path.replace("\\", "/").strip("/")
        normalized_base = library_base_path.replace("\\", "/").strip("/")
        if not normalized_source or ".." in normalized_source.split("/"):
            raise ValueError("DTL_SOURCE_PATH_INVALID")
        if normalized_base:
            return f"{normalized_base}/{normalized_source}"
        return normalized_source

    def _validate_path(self, path: str) -> None:
        normalized = path.replace("\\", "/")
        if ".." in normalized.split("/"):
            raise ValueError("SMB_PATH_INVALID")

    def _binding_to_response(self, binding: DownloadToLocalBinding) -> DtlBindingResponse:
        return DtlBindingResponse(
            id=binding.id,
            name=binding.name,
            enabled=binding.enabled,
            media_type=binding.media_type,
            source_connection_id=binding.source_connection_id,
            source_path=binding.source_path,
            target_library_id=binding.target_library_id,
            delete_source_after_success=binding.delete_source_after_success,
            delete_empty_source_dirs=binding.delete_empty_source_dirs,
            created_at=binding.created_at.isoformat() if binding.created_at else None,
            updated_at=binding.updated_at.isoformat() if binding.updated_at else None,
        )

    def _seen_file_to_response(self, seen: DownloadToLocalSeenFile) -> DtlDiscoveredFileResponse:
        return DtlDiscoveredFileResponse(
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


download_to_local_service = DownloadToLocalService()
