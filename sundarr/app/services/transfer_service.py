from uuid import uuid4

from sqlalchemy.orm import Session, object_session

from sundarr.app.models import ResourceLink, Setting, TransferFile, TransferTask
from sundarr.app.schemas.transfer import TransferCreateRequest, TransferResponse
from sundarr.app.services.storage_config_service import STORAGE_CONFIG_KEY


class TransferService:
    def create_transfer(self, db: Session, request: TransferCreateRequest) -> TransferResponse:
        link = db.get(ResourceLink, request.link_id)
        if link is None:
            raise ValueError("RESOURCE_LINK_NOT_FOUND")

        storage_config = db.get(Setting, STORAGE_CONFIG_KEY)
        task = TransferTask(
            id=uuid4().hex,
            resource_id=link.resource_id,
            link_id=link.id,
            status="pending",
            mode=request.mode,
            target_type=request.target_type,
            target_library=request.target_library,
            target_path=request.target_path,
            storage_config_snapshot=storage_config.value_json if storage_config else None,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return self._to_response(task)

    def get_transfer(self, db: Session, task_id: str) -> TransferResponse | None:
        task = db.get(TransferTask, task_id)
        return self._to_response(task) if task else None

    def _to_response(self, task: TransferTask) -> TransferResponse:
        return TransferResponse(
            id=task.id,
            resource_id=task.resource_id,
            link_id=task.link_id,
            status=task.status,
            mode=task.mode,
            cloud_staging_path=task.cloud_staging_path,
            target_type=task.target_type,
            target_library=task.target_library,
            target_path=task.target_path,
            total_bytes=task.total_bytes,
            done_bytes=task.done_bytes,
            progress=self._progress(task),
            current_file=self._current_file(task),
            error_code=task.error_code,
            error_message=task.error_message,
            retryable=task.retryable,
            retry_count=task.retry_count,
        )

    def _progress(self, task: TransferTask) -> float:
        if task.total_bytes <= 0:
            return 100.0 if task.status == "completed" else 0.0
        return round(min(100.0, task.done_bytes / task.total_bytes * 100), 2)

    def _current_file(self, task: TransferTask) -> str | None:
        task_session = object_session(task)
        if task_session is None:
            return None
        file = (
            task_session.query(TransferFile)
            .filter(TransferFile.task_id == task.id, TransferFile.status.in_(["pending", "downloading", "verified", "failed"]))
            .order_by(TransferFile.created_at, TransferFile.id)
            .first()
        )
        return file.filename if file else None


transfer_service = TransferService()
