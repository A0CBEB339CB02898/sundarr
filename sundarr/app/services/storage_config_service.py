from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from sundarr.app.models import Setting, TransferLog, TransferTask
from sundarr.app.schemas.storage import StorageConfigRequest, StorageConfigResponse, StorageConfigTestResponse

STORAGE_CONFIG_KEY = "storage.smb"
RUNNING_TRANSFER_STATUSES = {
    "staging_to_cloud",
    "cloud_ready",
    "downloading",
    "verifying",
    "renaming",
    "cleaning_cloud",
}


class StorageConfigService:
    def get_config(self, db: Session) -> StorageConfigResponse:
        setting = db.get(Setting, STORAGE_CONFIG_KEY)
        return self._to_response(setting.value_json if setting else {})

    def save_config(self, db: Session, request: StorageConfigRequest) -> StorageConfigResponse:
        current = db.get(Setting, STORAGE_CONFIG_KEY)
        value = request.model_dump()
        old_value = current.value_json if current else {}

        if not value.get("password") and old_value.get("password"):
            value["password"] = old_value["password"]

        self._validate_value(value)
        config_changed = current is not None and old_value != value

        if current is None:
            current = Setting(key=STORAGE_CONFIG_KEY, value_json=value, is_sensitive=True)
            db.add(current)
        else:
            current.value_json = value
            current.is_sensitive = True
        if config_changed:
            self._interrupt_running_tasks(db)
        db.commit()
        db.refresh(current)
        return self._to_response(current.value_json)

    def test_config(self, request: StorageConfigRequest) -> StorageConfigTestResponse:
        try:
            self._validate_value(request.model_dump())
        except ValueError as exc:
            return StorageConfigTestResponse(ok=False, error_code=str(exc), error_message=self._message_for_error(str(exc)))
        return StorageConfigTestResponse(ok=True)

    def _validate_value(self, value: dict[str, Any]) -> None:
        if value.get("type") != "smb":
            raise ValueError("STORAGE_CONFIG_INVALID")
        for field_name in ("host", "share", "username"):
            if not isinstance(value.get(field_name), str) or not value[field_name].strip():
                raise ValueError("STORAGE_CONFIG_INVALID")
        base_path = value.get("base_path", "/")
        if not isinstance(base_path, str) or ".." in base_path.replace("\\", "/").split("/"):
            raise ValueError("SMB_PATH_INVALID")
        libraries = value.get("libraries", {})
        if not isinstance(libraries, dict) or not all(isinstance(item, str) for item in libraries.values()):
            raise ValueError("STORAGE_CONFIG_INVALID")

    def _to_response(self, value: dict[str, Any]) -> StorageConfigResponse:
        return StorageConfigResponse(
            type="smb",
            host=str(value.get("host", "")),
            port=int(value.get("port", 445)),
            share=str(value.get("share", "")),
            username=str(value.get("username", "")),
            password_set=bool(value.get("password")),
            domain=str(value.get("domain", "")),
            base_path=str(value.get("base_path", "/")),
            libraries={str(key): str(item) for key, item in value.get("libraries", {}).items()},
        )

    def _interrupt_running_tasks(self, db: Session) -> None:
        tasks = (
            db.query(TransferTask)
            .filter(TransferTask.status.in_(RUNNING_TRANSFER_STATUSES), TransferTask.target_type == "smb")
            .all()
        )
        for task in tasks:
            task.status = "failed"
            task.error_code = "STORAGE_CONFIG_CHANGED"
            task.error_message = "SMB 配置已变更，任务已中断，可使用最新配置重试。"
            task.retryable = True
            db.add(
                TransferLog(
                    id=uuid4().hex,
                    task_id=task.id,
                    level="warning",
                    event="storage_config_changed",
                    message="SMB 配置已变更，运行中任务已中断。",
                    data_json={"error_code": "STORAGE_CONFIG_CHANGED"},
                )
            )

    def _message_for_error(self, error_code: str) -> str:
        messages = {
            "STORAGE_CONFIG_INVALID": "存储配置无效。",
            "SMB_PATH_INVALID": "SMB 路径配置无效。",
        }
        return messages.get(error_code, "存储配置测试失败。")


storage_config_service = StorageConfigService()
