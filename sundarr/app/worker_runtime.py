"""Worker 常驻循环、自动扫描与插件恢复编排。"""

from __future__ import annotations

import asyncio
import signal
import time

from sqlalchemy.orm import Session

from sundarr.app.models import RemoteMediaLibrary, SyncBinding, TransferTask
from sundarr.app.plugins.coordinator import RepositoryActivationCoordinator
from sundarr.app.plugins.manager import PluginManager, PluginProcessRole
from sundarr.app.plugins.runtime_registry import watchlist_provider_registry


class WorkerRuntime:
    """只编排 Worker 生命周期；任务领取和传输实现保留在任务模块。"""

    def __init__(
        self,
        poll_interval_seconds: float = 5.0,
        plugin_manager: PluginManager | None = None,
    ) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._running = True
        self._last_scan_times: dict[str, float] = {}
        self._last_watchlist_sync_times: dict[str, float] = {}
        self.plugin_manager = plugin_manager or PluginManager(
            process_role=PluginProcessRole.WORKER,
            coordinator=RepositoryActivationCoordinator(),
        )

    def stop(self, signum: int | None = None, frame: object | None = None) -> None:
        self._running = False

    def run(self) -> None:
        # 延迟取得兼容入口，使既有部署和测试仍可替换 worker.get_session_factory。
        from sundarr.app import worker as worker_tasks

        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        session_factory = worker_tasks.get_session_factory()
        print("Sundarr Worker 已启动。", flush=True)
        with session_factory() as session:
            plugin_stats = asyncio.run(
                self.plugin_manager.load_all_repositories(
                    session,
                    process_role=PluginProcessRole.WORKER,
                )
            )
        print(
            f"Worker 插件恢复完成：成功 {plugin_stats['loaded']}，失败 {plugin_stats['error']}。",
            flush=True,
        )
        with session_factory() as session:
            recovered_count = worker_tasks.recover_running_tasks(session)
        if recovered_count:
            print(f"Sundarr Worker 已保守恢复 {recovered_count} 个运行态任务。", flush=True)
        while self._running:
            claimed_ids: list[str] = []
            local_runtime = None
            with session_factory() as session:
                asyncio.run(
                    self.plugin_manager.reconcile_repositories(
                        session,
                        process_role=PluginProcessRole.WORKER,
                    )
                )
                settings = worker_tasks.load_worker_settings(session)
                self._auto_scan_and_create_tasks(session)
                if settings.enabled:
                    self._auto_sync_watchlists(session)
                claimed = worker_tasks.claim_pending_tasks(session, settings)
                claimed_ids = [task.id for task in claimed]
                local_runtime = worker_tasks.load_local_runtime_config(session)
            if not settings.enabled:
                print("Sundarr Worker 已禁用，保持空转。", flush=True)
            elif claimed:
                print(f"Sundarr Worker 已领取 {len(claimed)} 个任务。", flush=True)
                asyncio.run(
                    worker_tasks.process_claimed_tasks(
                        session_factory,
                        claimed_ids,
                        local_runtime,
                    )
                )
            time.sleep(self.poll_interval_seconds)
        asyncio.run(self.plugin_manager.dispose_all())
        print("Sundarr Worker 已停止。", flush=True)

    def _auto_scan_and_create_tasks(self, session: Session) -> None:
        bindings = session.query(SyncBinding).filter(SyncBinding.enabled.is_(True)).all()
        now = time.time()
        for binding in bindings:
            remote_lib = session.get(RemoteMediaLibrary, binding.remote_library_id)
            if remote_lib is None or not remote_lib.enabled:
                continue
            interval = remote_lib.scan_interval_seconds or 60
            last = self._last_scan_times.get(binding.id, 0)
            if now - last < interval:
                continue
            self._last_scan_times[binding.id] = now
            try:
                from sundarr.app.services.sync_service import sync_service
                from sundarr.app.schemas.sync import SyncScanRequest, SyncTaskCreateRequest

                asyncio.run(sync_service.scan(session, SyncScanRequest(binding_id=binding.id)))
                asyncio.run(sync_service.create_tasks(session, SyncTaskCreateRequest(binding_id=binding.id)))
                pending_count = session.query(TransferTask).filter(TransferTask.status == "pending").count()
                print(f"Worker 自动扫描 [{binding.name}] 完成，待处理任务: {pending_count}", flush=True)
            except Exception as exc:
                print(f"Worker 自动扫描 [{binding.name}] 失败: {exc}", flush=True)

    def _auto_sync_watchlists(self, session: Session) -> None:
        from sundarr.app import worker as worker_tasks

        interval = worker_tasks.load_watchlist_sync_interval(session)
        now = time.time()
        for provider_id in watchlist_provider_registry.snapshot():
            last = self._last_watchlist_sync_times.get(provider_id, 0)
            if now - last < interval:
                continue
            self._last_watchlist_sync_times[provider_id] = now
            try:
                from sundarr.app.services.watchlist_service import watchlist_service

                result = asyncio.run(watchlist_service.sync(session, provider_id))
                print(
                    f"Worker 想看同步 [{provider_id}] 完成，新增或刷新 {result.pulled_count} 项。",
                    flush=True,
                )
            except Exception as exc:
                print(f"Worker 想看同步 [{provider_id}] 失败: {exc}", flush=True)
