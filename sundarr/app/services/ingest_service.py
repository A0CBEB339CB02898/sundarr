from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.models import IngestBinding, IngestSeenFile, Setting, TransferFile, TransferTask
from sundarr.app.schemas.ingest import (
    IngestBindingCreateRequest,
    IngestBindingListResponse,
    IngestBindingResponse,
    IngestBindingTestResponse,
    IngestBindingUpdateRequest,
    IngestConfigRequest,
    IngestConfigResponse,
    IngestDiscoveredFileResponse,
    IngestDiscoveredListResponse,
    IngestScanRequest,
    IngestScanResponse,
    IngestSmbEndpointRequest,
    IngestSmbEndpointResponse,
    IngestTaskCreateRequest,
    IngestTaskCreateResponse,
)
from sundarr.app.services.transfer_service import transfer_service
from sundarr.app.storage import SmbConfig, SmbWriter

INGEST_CONFIG_KEY = "ingest.config"
DEFAULT_INGEST_CONFIG = {
    "delete_source_after_success": True,
    "delete_empty_source_dirs": True,
    "scan_interval_seconds": 60,
    "stable_seconds": 120,
    "unclassified_target_path": "/unclassified",
}


class IngestService:
    def __init__(self) -> None:
        self._list_dir_override: Callable[[IngestBinding, str], Awaitable[list[dict]]] | None = None

    def get_config(self, db: Session) -> IngestConfigResponse:
        setting = db.get(Setting, INGEST_CONFIG_KEY)
        return IngestConfigResponse(**(setting.value_json if setting else DEFAULT_INGEST_CONFIG))

    def save_config(self, db: Session, request: IngestConfigRequest) -> IngestConfigResponse:
        value = request.model_dump()
        setting = db.get(Setting, INGEST_CONFIG_KEY)
        if setting is None:
            setting = Setting(key=INGEST_CONFIG_KEY, value_json=value, is_sensitive=False)
            db.add(setting)
        else:
            setting.value_json = value
            setting.is_sensitive = False
        db.commit()
        db.refresh(setting)
        return IngestConfigResponse(**setting.value_json)

    def list_bindings(self, db: Session) -> IngestBindingListResponse:
        bindings = db.query(IngestBinding).order_by(IngestBinding.created_at, IngestBinding.id).all()
        results = [self._binding_to_response(binding) for binding in bindings]
        return IngestBindingListResponse(count=len(results), results=results)

    def get_binding(self, db: Session, binding_id: str) -> IngestBindingResponse | None:
        binding = db.get(IngestBinding, binding_id)
        return self._binding_to_response(binding) if binding else None

    def create_binding(self, db: Session, request: IngestBindingCreateRequest) -> IngestBindingResponse:
        if db.get(IngestBinding, request.id) is not None:
            raise ValueError("INGEST_BINDING_EXISTS")
        binding = IngestBinding(
            id=request.id,
            name=request.name,
            enabled=request.enabled,
            media_type=request.media_type,
            source_smb_json=self._endpoint_to_value(request.source_smb),
            target_smb_json=self._endpoint_to_value(request.target_smb),
            delete_source_after_success=request.delete_source_after_success,
            delete_empty_source_dirs=request.delete_empty_source_dirs,
        )
        db.add(binding)
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    def update_binding(self, db: Session, binding_id: str, request: IngestBindingUpdateRequest) -> IngestBindingResponse:
        binding = db.get(IngestBinding, binding_id)
        if binding is None:
            raise ValueError("INGEST_BINDING_NOT_FOUND")

        binding.name = request.name
        binding.enabled = request.enabled
        binding.media_type = request.media_type
        binding.source_smb_json = self._merge_endpoint_password(request.source_smb, binding.source_smb_json)
        binding.target_smb_json = self._merge_endpoint_password(request.target_smb, binding.target_smb_json)
        binding.delete_source_after_success = request.delete_source_after_success
        binding.delete_empty_source_dirs = request.delete_empty_source_dirs
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    def enable_binding(self, db: Session, binding_id: str) -> IngestBindingResponse:
        return self._set_binding_enabled(db, binding_id, True)

    def disable_binding(self, db: Session, binding_id: str) -> IngestBindingResponse:
        return self._set_binding_enabled(db, binding_id, False)

    def test_binding(self, db: Session, binding_id: str) -> IngestBindingTestResponse:
        binding = db.get(IngestBinding, binding_id)
        if binding is None:
            raise ValueError("INGEST_BINDING_NOT_FOUND")
        # Phase 8.1 只校验配置结构；真实 SMB 可读/可写测试在扫描器和 Writer 阶段实现。
        return IngestBindingTestResponse(ok=True, source_ok=False, target_ok=False)

    async def scan(self, db: Session, request: IngestScanRequest) -> IngestScanResponse:
        bindings_query = db.query(IngestBinding).filter(IngestBinding.enabled.is_(True))
        if request.binding_id:
            bindings_query = bindings_query.filter(IngestBinding.id == request.binding_id)
        bindings = bindings_query.order_by(IngestBinding.created_at, IngestBinding.id).all()
        if request.binding_id and not bindings:
            raise ValueError("INGEST_BINDING_NOT_FOUND")

        config = self.get_config(db)
        results: list[IngestSeenFile] = []
        for binding in bindings:
            entries = await self._scan_binding(binding)
            for entry in entries:
                seen = self._upsert_seen_file(db, binding, entry, config.stable_seconds)
                results.append(seen)
        db.commit()
        for seen in results:
            db.refresh(seen)
        return IngestScanResponse(
            scanned_bindings=len(bindings),
            discovered_count=sum(1 for item in results if item.status == "discovered"),
            stable_count=sum(1 for item in results if item.status == "stable"),
            results=[self._seen_file_to_response(item) for item in results],
        )

    def list_discovered(self, db: Session) -> IngestDiscoveredListResponse:
        rows = db.query(IngestSeenFile).order_by(IngestSeenFile.updated_at.desc(), IngestSeenFile.created_at.desc()).all()
        results = [self._seen_file_to_response(row) for row in rows]
        return IngestDiscoveredListResponse(count=len(results), results=results)

    def create_tasks(self, db: Session, request: IngestTaskCreateRequest) -> IngestTaskCreateResponse:
        query = db.query(IngestSeenFile).filter(IngestSeenFile.status == "stable", IngestSeenFile.task_id.is_(None))
        if request.binding_id:
            query = query.filter(IngestSeenFile.binding_id == request.binding_id)
            if db.get(IngestBinding, request.binding_id) is None:
                raise ValueError("INGEST_BINDING_NOT_FOUND")

        seen_files = query.order_by(IngestSeenFile.updated_at, IngestSeenFile.id).all()
        tasks: list[TransferTask] = []
        skipped_count = 0
        for seen in seen_files:
            binding = db.get(IngestBinding, seen.binding_id) if seen.binding_id else None
            if binding is None:
                seen.status = "failed"
                skipped_count += 1
                continue
            task = self._create_transfer_task_for_seen_file(db, binding, seen)
            tasks.append(task)
        db.commit()
        for task in tasks:
            db.refresh(task)
        return IngestTaskCreateResponse(
            created_count=len(tasks),
            skipped_count=skipped_count,
            tasks=[transfer_service._to_response(task) for task in tasks],
        )

    def _set_binding_enabled(self, db: Session, binding_id: str, enabled: bool) -> IngestBindingResponse:
        binding = db.get(IngestBinding, binding_id)
        if binding is None:
            raise ValueError("INGEST_BINDING_NOT_FOUND")
        binding.enabled = enabled
        db.commit()
        db.refresh(binding)
        return self._binding_to_response(binding)

    async def _scan_binding(self, binding: IngestBinding) -> list[dict]:
        return await self._scan_dir(binding, "")

    async def _scan_dir(self, binding: IngestBinding, path: str) -> list[dict]:
        entries = await self._list_source_dir(binding, path)
        files: list[dict] = []
        for entry in entries:
            if entry.get("is_dir"):
                files.extend(await self._scan_dir(binding, str(entry.get("path", ""))))
            else:
                files.append(entry)
        return files

    async def _list_source_dir(self, binding: IngestBinding, path: str) -> list[dict]:
        if self._list_dir_override is not None:
            return await self._list_dir_override(binding, path)
        writer = SmbWriter(SmbConfig.from_dict(binding.source_smb_json))
        return await writer.list_dir(path)

    def _upsert_seen_file(self, db: Session, binding: IngestBinding, entry: dict, stable_seconds: int) -> IngestSeenFile:
        source_path = str(entry.get("path", "")).strip("/")
        source_size = entry.get("size")
        source_mtime = str(entry.get("modified_at") or "") or None
        fingerprint = self._source_fingerprint(binding, source_path)
        seen = db.query(IngestSeenFile).filter(IngestSeenFile.source_fingerprint == fingerprint).one_or_none()
        if seen is None:
            seen = IngestSeenFile(
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

        same_file = seen.source_size == (int(source_size) if source_size is not None else None) and seen.source_mtime == source_mtime
        if same_file and self._age_seconds(seen.updated_at) >= stable_seconds and seen.status in {"discovered", "stable"}:
            seen.status = "stable"
        else:
            seen.source_size = int(source_size) if source_size is not None else None
            seen.source_mtime = source_mtime
            if seen.status != "stable" or not same_file:
                seen.status = "discovered"
        return seen

    def _source_fingerprint(self, binding: IngestBinding, source_path: str) -> str:
        source = binding.source_smb_json
        return "|".join(
            [
                str(source.get("host", "")),
                str(source.get("port", 445)),
                str(source.get("share", "")),
                str(source.get("base_path", "/")),
                source_path,
            ]
        )

    def _age_seconds(self, value: datetime | None) -> float:
        if value is None:
            return 0
        current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - current).total_seconds()

    def _create_transfer_task_for_seen_file(self, db: Session, binding: IngestBinding, seen: IngestSeenFile) -> TransferTask:
        target_path = self._build_target_path(seen.source_path)
        task = TransferTask(
            id=uuid4().hex,
            resource_id=None,
            link_id=None,
            status="pending",
            mode="ingest",
            target_type="smb",
            target_library=binding.media_type,
            target_path=target_path,
            source_type="smb",
            source_path=seen.source_path,
            source_config_snapshot=binding.source_smb_json,
            storage_config_snapshot=binding.target_smb_json,
            ingest_seen_file_id=seen.id,
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

    def _build_target_path(self, source_path: str) -> str:
        normalized = source_path.replace("\\", "/").strip("/")
        if not normalized or ".." in normalized.split("/"):
            raise ValueError("INGEST_SOURCE_PATH_INVALID")
        return normalized

    def _endpoint_to_value(self, endpoint: IngestSmbEndpointRequest) -> dict:
        return endpoint.model_dump()

    def _merge_endpoint_password(self, endpoint: IngestSmbEndpointRequest, old_value: dict) -> dict:
        value = self._endpoint_to_value(endpoint)
        if not value.get("password") and old_value.get("password"):
            value["password"] = old_value["password"]
        return value

    def _binding_to_response(self, binding: IngestBinding) -> IngestBindingResponse:
        return IngestBindingResponse(
            id=binding.id,
            name=binding.name,
            enabled=binding.enabled,
            media_type=binding.media_type,
            source_smb=self._endpoint_to_response(binding.source_smb_json),
            target_smb=self._endpoint_to_response(binding.target_smb_json),
            delete_source_after_success=binding.delete_source_after_success,
            delete_empty_source_dirs=binding.delete_empty_source_dirs,
            created_at=binding.created_at.isoformat() if binding.created_at else None,
            updated_at=binding.updated_at.isoformat() if binding.updated_at else None,
        )

    def _endpoint_to_response(self, value: dict) -> IngestSmbEndpointResponse:
        return IngestSmbEndpointResponse(
            host=str(value.get("host", "")),
            port=int(value.get("port", 445)),
            share=str(value.get("share", "")),
            username=str(value.get("username", "")),
            password_set=bool(value.get("password")),
            domain=str(value.get("domain", "")),
            base_path=str(value.get("base_path", "/")),
        )

    def _seen_file_to_response(self, seen: IngestSeenFile) -> IngestDiscoveredFileResponse:
        return IngestDiscoveredFileResponse(
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


ingest_service = IngestService()
