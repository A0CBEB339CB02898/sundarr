"""真实 SMB 主链路验收；默认跳过，只能写入随机验收子目录。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from sundarr.app.core.database import get_session_factory
from sundarr.app.models import (
    MediaLibrary,
    RemoteMediaLibrary,
    SmbConnection,
    SyncBinding,
    SyncSeenFile,
    TransferFile,
    TransferLog,
    TransferTask,
)
from sundarr.app.plugins.secrets import decode_secret_text
from sundarr.app.schemas.sync import SyncScanRequest, SyncTaskCreateRequest
from sundarr.app.services.sync_service import sync_service
from sundarr.app.services.transfer_service import transfer_service
from sundarr.app.storage import SmbConfig, SmbWriter
from sundarr.app.worker import (
    RUNNING_TASK_STATUSES,
    claim_pending_tasks,
    process_claimed_tasks,
    process_sync_task,
    recover_running_tasks,
)
from sundarr.app.worker_config import WorkerSettings


CONFIRM_VALUE = "I_UNDERSTAND_THIS_WRITES_AND_DELETES_TEST_FILES"
ACCEPTANCE_ROOT = ".sundarr-acceptance"

pytestmark = [pytest.mark.anyio, pytest.mark.real_smb]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _required_environment() -> tuple[str, str]:
    if os.environ.get("SUNDARR_REAL_SMB_ACCEPT") != CONFIRM_VALUE:
        pytest.skip("未显式确认真实 SMB 写入与删除")
    source_id = os.environ.get("SUNDARR_REAL_SMB_SOURCE_CONNECTION_ID", "").strip()
    target_id = os.environ.get("SUNDARR_REAL_SMB_TARGET_CONNECTION_ID", "").strip()
    if not source_id or not target_id:
        pytest.skip("未提供真实 SMB 来源和目标连接 ID")
    if source_id == target_id:
        pytest.fail("真实验收要求来源和目标使用不同 SMB 连接")
    return source_id, target_id


def _writer(connection: SmbConnection) -> SmbWriter:
    return SmbWriter(
        SmbConfig(
            host=connection.host,
            port=connection.port,
            share=connection.share,
            username=connection.username,
            password=decode_secret_text(connection.password),
            domain=connection.domain or "",
            base_path=connection.base_path,
        )
    )


async def _write_file(writer: SmbWriter, path: str, content: bytes) -> None:
    if await writer.exists(path):
        raise AssertionError(f"随机验收路径意外存在：{path}")
    with await writer.open_append(path) as handle:
        handle.write(content)


async def _remove_empty_tree(writer: SmbWriter, paths: list[str]) -> None:
    for path in paths:
        if await writer.exists(path):
            try:
                await writer.remove_empty_dir(path)
            except Exception:
                # 只删空目录；并发验收或诊断残留存在时保留现场，不扩大删除范围。
                pass


async def _remove_direct_test_files(writer: SmbWriter, root: str) -> None:
    if not await writer.exists(root):
        return
    for entry in await writer.list_dir(root):
        path = str(entry["path"])
        if entry.get("is_dir"):
            raise AssertionError(f"验收目录出现非预期子目录，已保留现场：{path}")
        await writer.remove(path)


def _acceptance_payload(label: str, size: int = 3 * 1024 * 1024) -> bytes:
    seed = f"Sundarr Phase 10.5.3 {label}\n".encode()
    return (seed * (size // len(seed) + 1))[:size]


async def test_real_smb_sync_recovery_retry_and_cancel() -> None:
    source_connection_id, target_connection_id = _required_environment()
    run_id = f"phase-10-5-3-{uuid4().hex[:12]}"
    record_prefix = f"acceptance-{run_id}"
    run_root = f"{ACCEPTANCE_ROOT}/{run_id}"
    source_root = f"{run_root}/source"
    target_root = f"{run_root}/target"
    library_id = f"{record_prefix}-local"
    remote_id = f"{record_prefix}-remote"
    binding_id = f"{record_prefix}-binding"
    filenames = {
        "happy": "正常传输.bin",
        "recovery": "重启恢复.bin",
        "cancel": "取消任务.bin",
    }
    payloads = {name: _acceptance_payload(name) for name in filenames}

    session_factory = get_session_factory()
    with session_factory() as session:
        source_connection = session.get(SmbConnection, source_connection_id)
        target_connection = session.get(SmbConnection, target_connection_id)
        if source_connection is None or target_connection is None:
            pytest.fail("真实 SMB 验收连接不存在")
        if not source_connection.enabled or not target_connection.enabled:
            pytest.fail("真实 SMB 验收连接未启用")
        competing = session.query(TransferTask).filter(TransferTask.status.in_(RUNNING_TASK_STATUSES)).count()
        if competing:
            pytest.fail(f"发现 {competing} 个既有运行态任务；请先处理后再执行真实验收")
        pending = session.query(TransferTask).filter(TransferTask.status == "pending").count()
        if pending:
            pytest.fail(f"发现 {pending} 个既有待处理任务；请先处理后再执行真实验收")

        source_writer = _writer(source_connection)
        target_writer = _writer(target_connection)
        source_paths = {name: f"{source_root}/{filename}" for name, filename in filenames.items()}
        target_paths = {name: f"{target_root}/{filename}" for name, filename in filenames.items()}
        try:
            await source_writer.mkdirs(source_root)
            await target_writer.mkdirs(target_root)
            for name, path in source_paths.items():
                await _write_file(source_writer, path, payloads[name])

            local_library = MediaLibrary(
                id=library_id,
                name=f"真实验收目标 {run_id}",
                media_type="unclassified",
                enabled=True,
                connection_id=target_connection_id,
                base_path=f"/{target_root}",
                last_test_ok=True,
            )
            remote_library = RemoteMediaLibrary(
                id=remote_id,
                name=f"真实验收来源 {run_id}",
                media_type="unclassified",
                enabled=True,
                connection_id=source_connection_id,
                base_path=f"/{source_root}",
                target_library_id=None,
                scan_interval_seconds=5,
                stable_seconds=5,
                delete_source_after_success=True,
                delete_empty_source_dirs=True,
                last_test_ok=True,
            )
            binding = SyncBinding(
                id=binding_id,
                name=f"真实验收绑定 {run_id}",
                enabled=True,
                media_type="unclassified",
                remote_library_id=remote_id,
                local_library_id=library_id,
                delete_source_after_success=True,
                delete_empty_source_dirs=True,
            )
            session.add_all([local_library, remote_library, binding])
            session.commit()

            first_scan = await sync_service.scan(session, SyncScanRequest(binding_id=binding_id))
            assert first_scan.discovered_count == 3
            assert first_scan.stable_count == 0

            # 稳定性门至少等待 Manifest/Schema 允许的最小 5 秒，不篡改文件时间或数据库时间。
            await asyncio.sleep(5.2)
            second_scan = await sync_service.scan(session, SyncScanRequest(binding_id=binding_id))
            assert second_scan.stable_count == 3
            created = await sync_service.create_tasks(session, SyncTaskCreateRequest(binding_id=binding_id))
            assert created.created_count == 3

            tasks = {
                task.source_path.rsplit("/", 1)[-1]: task
                for task in session.query(TransferTask).filter(TransferTask.binding_id == binding_id).all()
            }
            assert set(tasks) == set(filenames.values())
            happy_task = tasks[filenames["happy"]]
            recovery_task = tasks[filenames["recovery"]]
            cancel_task = tasks[filenames["cancel"]]
            recovery_task.status = "paused"
            cancel_task.status = "paused"
            session.commit()

            claimed = claim_pending_tasks(session, WorkerSettings(enabled=True, concurrency=1))
            assert [item.id for item in claimed] == [happy_task.id]
            await process_claimed_tasks(session_factory, [happy_task.id], None)
            session.expire_all()
            session.refresh(happy_task)
            assert happy_task.status == "completed"
            assert happy_task.done_bytes == len(payloads["happy"])
            assert not await source_writer.exists(source_paths["happy"])
            assert await target_writer.exists(target_paths["happy"])
            assert not await target_writer.exists(f"{target_paths['happy']}.sundarr.downloading")
            assert await target_writer.checksum_md5(target_paths["happy"]) == hashlib.md5(
                payloads["happy"], usedforsecurity=False
            ).hexdigest()

            recovery_task.status = "pending"
            cancel_task.status = "pending"
            session.commit()
            recovery_file = session.query(TransferFile).filter(TransferFile.task_id == recovery_task.id).one()
            partial_size = 1024 * 1024
            with await target_writer.open_append(recovery_file.temp_path) as handle:
                handle.write(payloads["recovery"][:partial_size])
            recovery_task.status = "downloading"
            recovery_task.started_at = datetime.now(UTC)
            recovery_task.done_bytes = partial_size
            recovery_file.status = "downloading"
            recovery_file.done_bytes = partial_size
            session.commit()

            assert recover_running_tasks(session) == 1
            session.refresh(recovery_task)
            assert recovery_task.status == "failed"
            assert recovery_task.retryable is True
            assert recovery_task.error_code == "WORKER_RECOVERY_REQUIRED"
            assert await source_writer.exists(source_paths["recovery"])
            assert await target_writer.size(recovery_file.temp_path) == partial_size

            retried = transfer_service.retry_transfer(session, recovery_task.id)
            assert retried.status == "pending"
            await process_sync_task(session, recovery_task, source_writer, target_writer)
            session.refresh(recovery_task)
            assert recovery_task.status == "completed"
            assert recovery_task.retry_count == 1
            assert not await source_writer.exists(source_paths["recovery"])
            assert not await target_writer.exists(recovery_file.temp_path)
            assert await target_writer.checksum_md5(target_paths["recovery"]) == hashlib.md5(
                payloads["recovery"], usedforsecurity=False
            ).hexdigest()
            recovery_events = {
                row.event for row in session.query(TransferLog).filter(TransferLog.task_id == recovery_task.id).all()
            }
            assert {"worker_startup_recovered", "task_retried", "sync_copy_resumed"} <= recovery_events

            cancelled = transfer_service.cancel_transfer(session, cancel_task.id)
            assert cancelled.status == "cancelled"
            await process_sync_task(session, cancel_task, source_writer, target_writer)
            session.refresh(cancel_task)
            assert cancel_task.status == "cancelled"
            assert await source_writer.exists(source_paths["cancel"])
            assert not await target_writer.exists(target_paths["cancel"])
            assert not await target_writer.exists(f"{target_paths['cancel']}.sundarr.downloading")

            print(
                json.dumps(
                    {
                        "run_id": run_id,
                        "source_connection_id": source_connection_id,
                        "target_connection_id": target_connection_id,
                        "normal_task": happy_task.id,
                        "recovery_task": recovery_task.id,
                        "cancel_task": cancel_task.id,
                        "normal_md5": await target_writer.checksum_md5(target_paths["happy"]),
                        "recovery_md5": await target_writer.checksum_md5(target_paths["recovery"]),
                        "result": "passed",
                    },
                    ensure_ascii=False,
                )
            )
        finally:
            session.rollback()
            await _remove_direct_test_files(source_writer, source_root)
            await _remove_direct_test_files(target_writer, target_root)
            await _remove_empty_tree(source_writer, [source_root, run_root, ACCEPTANCE_ROOT])
            await _remove_empty_tree(target_writer, [target_root, run_root, ACCEPTANCE_ROOT])

            acceptance_bindings = [
                row[0]
                for row in session.query(SyncBinding.id).filter(
                    (SyncBinding.remote_library_id == remote_id) | (SyncBinding.local_library_id == library_id)
                )
            ]
            known_task_ids = [
                row[0] for row in session.query(TransferTask.id).filter(TransferTask.binding_id.in_(acceptance_bindings))
            ]
            if known_task_ids:
                session.query(TransferLog).filter(TransferLog.task_id.in_(known_task_ids)).delete(
                    synchronize_session=False
                )
                session.query(TransferFile).filter(TransferFile.task_id.in_(known_task_ids)).delete(
                    synchronize_session=False
                )
            if acceptance_bindings:
                session.query(SyncSeenFile).filter(SyncSeenFile.binding_id.in_(acceptance_bindings)).delete(
                    synchronize_session=False
                )
                session.query(TransferTask).filter(TransferTask.binding_id.in_(acceptance_bindings)).delete(
                    synchronize_session=False
                )
                session.query(SyncBinding).filter(SyncBinding.id.in_(acceptance_bindings)).delete(
                    synchronize_session=False
                )
            session.query(RemoteMediaLibrary).filter(RemoteMediaLibrary.id == remote_id).delete(synchronize_session=False)
            session.query(MediaLibrary).filter(MediaLibrary.id == library_id).delete(synchronize_session=False)
            session.commit()

            assert not await source_writer.exists(run_root), f"来源 SMB 验收目录未清理：{run_root}"
            assert not await target_writer.exists(run_root), f"目标 SMB 验收目录未清理：{run_root}"
            assert session.query(SyncBinding).filter(SyncBinding.id.in_(acceptance_bindings)).count() == 0
            assert session.query(RemoteMediaLibrary).filter(RemoteMediaLibrary.id == remote_id).count() == 0
            assert session.query(MediaLibrary).filter(MediaLibrary.id == library_id).count() == 0
