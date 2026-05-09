from uuid import uuid4

from sqlalchemy.orm import Session, object_session

from sundarr.app.models import ResourceLink, Setting, TransferFile, TransferLog, TransferTask
from sundarr.app.schemas.transfer import TransferCreateRequest, TransferLogResponse, TransferResponse

CANCELLABLE_TRANSFER_STATUSES = {"pending", "staging_to_cloud", "cloud_ready", "downloading", "verifying"}
CANCELLABLE_FILE_STATUSES = {"pending", "downloading", "verified"}
SENSITIVE_LOG_KEYS = {"password", "token", "cookie", "secret"}


class TransferService:
    def create_transfer(self, db: Session, request: TransferCreateRequest) -> TransferResponse:
        link = db.get(ResourceLink, request.link_id)
        if link is None:
            raise ValueError("RESOURCE_LINK_NOT_FOUND")

        task = TransferTask(
            id=uuid4().hex,
            resource_id=link.resource_id,
            link_id=link.id,
            status="pending",
            mode=request.mode,
            target_type=request.target_type,
            target_library=request.target_library,
            target_path=request.target_path,
            storage_config_snapshot=None,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return self._to_response(task)

    def get_transfer(self, db: Session, task_id: str) -> TransferResponse | None:
        task = db.get(TransferTask, task_id)
        return self._to_response(task) if task else None

    def list_transfers(self, db: Session, limit: int = 30) -> list[TransferResponse]:
        safe_limit = max(1, min(limit, 100))
        tasks = db.query(TransferTask).order_by(TransferTask.updated_at.desc(), TransferTask.created_at.desc()).limit(safe_limit).all()
        return [self._to_response(task) for task in tasks]

    def cancel_transfer(self, db: Session, task_id: str) -> TransferResponse:
        task = db.get(TransferTask, task_id)
        if task is None:
            raise ValueError("TRANSFER_TASK_NOT_FOUND")
        if task.status not in CANCELLABLE_TRANSFER_STATUSES:
            raise ValueError("TRANSFER_TASK_NOT_CANCELLABLE")

        previous_status = task.status
        task.status = "cancelled"
        task.error_code = "TASK_CANCELLED"
        task.error_message = "任务已取消。"
        task.retryable = False
        files = db.query(TransferFile).filter(TransferFile.task_id == task.id, TransferFile.status.in_(CANCELLABLE_FILE_STATUSES)).all()
        for file in files:
            file.status = "cancelled"
            file.error_code = "TASK_CANCELLED"
            file.error_message = "任务已取消。"
        db.add(
            TransferLog(
                id=uuid4().hex,
                task_id=task.id,
                level="info",
                event="task_cancelled",
                message="任务已取消，保留 .downloading 文件和 cloud staging。",
                data_json={"previous_status": previous_status},
            )
        )
        db.commit()
        db.refresh(task)
        return self._to_response(task)

    def retry_transfer(self, db: Session, task_id: str) -> TransferResponse:
        task = db.get(TransferTask, task_id)
        if task is None:
            raise ValueError("TRANSFER_TASK_NOT_FOUND")
        if task.status != "failed" or task.retryable is not True:
            raise ValueError("TRANSFER_TASK_NOT_RETRYABLE")

        previous_error_code = task.error_code
        task.status = "pending"
        task.error_code = None
        task.error_message = None
        task.retryable = None
        task.retry_count += 1
        task.done_bytes = 0
        task.completed_at = None
        task.storage_config_snapshot = None
        db.add(
            TransferLog(
                id=uuid4().hex,
                task_id=task.id,
                level="info",
                event="task_retried",
                message="任务已重新入队，保留 .downloading 文件和 cloud staging。",
                data_json={"previous_error_code": previous_error_code, "retry_count": task.retry_count},
            )
        )
        db.commit()
        db.refresh(task)
        return self._to_response(task)

    def list_transfer_logs(self, db: Session, task_id: str) -> list[TransferLogResponse]:
        task = db.get(TransferTask, task_id)
        if task is None:
            raise ValueError("TRANSFER_TASK_NOT_FOUND")

        logs = (
            db.query(TransferLog)
            .filter(TransferLog.task_id == task_id)
            .order_by(TransferLog.created_at, TransferLog.id)
            .all()
        )
        return [
            TransferLogResponse(
                id=log.id,
                task_id=log.task_id,
                level=log.level,
                event=log.event,
                message=log.message,
                data=self._sanitize_log_data(log.data_json),
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ]

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
            source_type=task.source_type,
            source_path=task.source_path,
            ingest_seen_file_id=task.ingest_seen_file_id,
            total_bytes=task.total_bytes,
            done_bytes=task.done_bytes,
            progress=self._progress(task),
            current_file=self._current_file(task),
            error_code=task.error_code,
            error_message=task.error_message,
            retryable=task.retryable,
            retry_count=task.retry_count,
            created_at=task.created_at.isoformat() if task.created_at else None,
            updated_at=task.updated_at.isoformat() if task.updated_at else None,
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

    def _sanitize_log_data(self, value):
        if isinstance(value, dict):
            return {
                key: self._sanitize_log_data(item)
                for key, item in value.items()
                if not any(sensitive in key.lower() for sensitive in SENSITIVE_LOG_KEYS)
            }
        if isinstance(value, list):
            return [self._sanitize_log_data(item) for item in value]
        return value


transfer_service = TransferService()
