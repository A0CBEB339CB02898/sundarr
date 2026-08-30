"""插件仓库、配置与进程内 Activation 的统一管理入口。"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from .base import PluginManifest, PluginType
from .config import (
    REDACTED_VALUE,
    missing_required_plugin_config,
    redact_plugin_config,
    redact_plugin_error,
    validate_plugin_config,
)
from .coordinator import RepositoryActivationCoordinator, RepositoryActivationError, repository_activation_coordinator
from .loader import PluginLoader, plugin_loader
from .registry import plugin_registry
from .secrets import config_requires_encryption, decode_plugin_config, encode_plugin_config

logger = logging.getLogger(__name__)


class PluginProcessRole(str, Enum):
    API = "api"
    WORKER = "worker"
    ALL = "all"


_ROLE_TYPES: dict[PluginProcessRole, frozenset[PluginType]] = {
    PluginProcessRole.API: frozenset({PluginType.SOURCE, PluginType.CATALOG_PROVIDER}),
    PluginProcessRole.WORKER: frozenset({PluginType.WATCHLIST_PROVIDER}),
    PluginProcessRole.ALL: frozenset({PluginType.SOURCE, PluginType.CATALOG_PROVIDER, PluginType.WATCHLIST_PROVIDER}),
}


@dataclass(frozen=True)
class ManagedRepositoryResult:
    repository_id: str
    commit_hash: str
    plugin_ids: tuple[str, ...]


class PluginManager:
    """以数据库期望状态驱动当前进程的插件运行实例。"""

    def __init__(
        self,
        *,
        loader: PluginLoader | None = None,
        coordinator: RepositoryActivationCoordinator | None = None,
        process_role: PluginProcessRole = PluginProcessRole.API,
    ) -> None:
        self.loader = loader or plugin_loader
        self.coordinator = coordinator or repository_activation_coordinator
        self.process_role = process_role
        self._repository_signatures: dict[str, tuple[Any, ...]] = {}

    async def load_all_repositories(
        self,
        session: Session,
        *,
        process_role: PluginProcessRole | None = None,
    ) -> dict[str, Any]:
        """离线恢复 enabled 仓库的锁定版本；单仓库失败不阻断其他仓库。"""

        from ..models.plugin import PluginRepository

        role = process_role or self.process_role
        repositories = session.query(PluginRepository).filter(PluginRepository.enabled.is_(True)).all()
        stats: dict[str, Any] = {"total": len(repositories), "loaded": 0, "error": 0, "errors": []}
        for repository in repositories:
            if not repository.current_commit:
                continue
            try:
                await self._activate_repository(
                    session,
                    repository,
                    target_commit=repository.current_commit,
                    fetch=False,
                    process_role=role,
                    advance_commit=False,
                )
                stats["loaded"] += 1
            except Exception as exc:
                stats["error"] += 1
                stats["errors"].append({
                    "repository_id": repository.id,
                    "error": repository.last_error or str(exc),
                })
        return stats

    async def reconcile_repositories(
        self,
        session: Session,
        *,
        process_role: PluginProcessRole | None = None,
    ) -> dict[str, Any]:
        """只在数据库期望状态变化时重载，用于 Worker 轮询跨进程启停。"""

        from ..models.plugin import PluginRepository

        role = process_role or self.process_role
        repositories = {
            item.id: item
            for item in session.query(PluginRepository)
            .filter(PluginRepository.enabled.is_(True), PluginRepository.current_commit.is_not(None))
            .all()
        }
        stats: dict[str, Any] = {"checked": len(repositories), "reloaded": 0, "disabled": 0, "error": 0}
        for repository_id in self.coordinator.repository_ids():
            if repository_id not in repositories:
                await self.coordinator.deactivate_repository(repository_id)
                self._repository_signatures.pop(repository_id, None)
                stats["disabled"] += 1
        for repository in repositories.values():
            signature = self._repository_signature(repository, role)
            if self._repository_signatures.get(repository.id) == signature:
                continue
            try:
                await self._activate_repository(
                    session,
                    repository,
                    target_commit=repository.current_commit,
                    fetch=False,
                    process_role=role,
                    advance_commit=False,
                )
                stats["reloaded"] += 1
            except Exception:
                stats["error"] += 1
        return stats

    async def add_repository(
        self,
        session: Session,
        *,
        repo_url: str,
        branch: str = "main",
        name: str | None = None,
        auto_update: bool = False,
        configs: Mapping[str, Mapping[str, Any]] | None = None,
        disabled_plugin_ids: set[str] | None = None,
    ) -> ManagedRepositoryResult:
        from ..models.plugin import PluginRepository

        existing = session.query(PluginRepository).filter(PluginRepository.repo_url == repo_url).first()
        if existing is not None:
            raise ValueError(f"插件仓库已存在：{repo_url}")
        repository = PluginRepository(
            id=uuid4().hex,
            name=name or self.loader.repository_path(repo_url).name,
            repo_url=repo_url,
            branch=branch,
            auto_update=auto_update,
            enabled=True,
            status="pending",
        )
        session.add(repository)
        session.flush()
        try:
            return await self._activate_repository(
                session,
                repository,
                target_commit=None,
                fetch=True,
                process_role=self.process_role,
                advance_commit=True,
                config_overrides=configs,
                disabled_plugin_ids=disabled_plugin_ids,
            )
        except Exception:
            session.commit()
            raise

    async def update_repository(
        self,
        session: Session,
        repo_id: str,
        new_commit: str | None = None,
    ) -> ManagedRepositoryResult:
        repository = self._require_repository(session, repo_id)
        return await self._activate_repository(
            session,
            repository,
            target_commit=new_commit,
            fetch=True,
            process_role=self.process_role,
            advance_commit=True,
        )

    async def rollback_repository(self, session: Session, repo_id: str) -> ManagedRepositoryResult:
        repository = self._require_repository(session, repo_id)
        if not repository.previous_commit:
            raise ValueError(f"仓库没有可回滚版本：{repository.name}")
        return await self._activate_repository(
            session,
            repository,
            target_commit=repository.previous_commit,
            fetch=True,
            process_role=self.process_role,
            advance_commit=True,
        )

    async def enable_plugin(self, session: Session, plugin_id: str) -> ManagedRepositoryResult | None:
        config = self._require_plugin_config(session, plugin_id)
        config.enabled = True
        config.status = "pending"
        config.last_error = None
        session.commit()
        repository = config.repository
        if repository is None or not repository.current_commit:
            return None
        if PluginType(config.plugin_type) not in _ROLE_TYPES[self.process_role]:
            return None
        return await self._activate_repository(
            session,
            repository,
            target_commit=repository.current_commit,
            fetch=False,
            process_role=self.process_role,
            advance_commit=False,
        )

    async def disable_plugin(self, session: Session, plugin_id: str) -> None:
        config = self._require_plugin_config(session, plugin_id)
        config.enabled = False
        config.status = "disabled"
        config.last_error = None
        session.commit()
        await self.coordinator.deactivate_plugin(plugin_id)

    def get_plugin_config(self, session: Session, plugin_id: str) -> dict[str, Any]:
        config = self._require_plugin_config(session, plugin_id)
        manifest = self._find_manifest(config.repository, plugin_id)
        return redact_plugin_config(manifest.config_schema, self._decode_config(config.config_data))

    async def update_plugin_config(
        self,
        session: Session,
        plugin_id: str,
        config_data: Mapping[str, Any],
    ) -> ManagedRepositoryResult | None:
        config = self._require_plugin_config(session, plugin_id)
        manifest = self._find_manifest(config.repository, plugin_id)
        submitted = dict(config_data)
        existing_values = self._decode_config(config.config_data)
        for field_name, field_schema in manifest.config_schema.items():
            if not isinstance(field_schema, Mapping):
                continue
            is_secret = field_schema.get("type") == "password" or field_schema.get("secret") is True
            if is_secret and submitted.get(field_name) == REDACTED_VALUE and field_name in existing_values:
                submitted[field_name] = existing_values[field_name]
        validated = validate_plugin_config(manifest.config_schema, submitted)
        config.config_data = self._encode_config(validated, manifest.config_schema)
        config.status = "pending" if config.enabled else "disabled"
        config.last_error = None
        session.commit()
        repository = config.repository
        if not config.enabled or repository is None or not repository.current_commit:
            return None
        if manifest.plugin_type not in _ROLE_TYPES[self.process_role]:
            return None
        return await self._activate_repository(
            session,
            repository,
            target_commit=repository.current_commit,
            fetch=False,
            process_role=self.process_role,
            advance_commit=False,
        )

    async def remove_repository(self, session: Session, repo_id: str) -> None:
        from ..models.plugin import PluginConfig

        repository = self._require_repository(session, repo_id)
        await self.coordinator.deactivate_repository(repo_id)
        configs = session.query(PluginConfig).filter(PluginConfig.repository_id == repo_id).all()
        for config in configs:
            plugin_registry.unregister(config.plugin_id)
            session.delete(config)
        repo_url = repository.repo_url
        session.delete(repository)
        session.commit()
        self._repository_signatures.pop(repo_id, None)
        self.loader.remove_repo(repo_url)

    def list_plugins(self, session: Session) -> list[dict[str, Any]]:
        """返回数据库声明状态和当前进程 Activation 的合并视图。"""

        from ..models.plugin import PluginConfig

        rows: list[dict[str, Any]] = []
        for config in session.query(PluginConfig).all():
            activation = self.coordinator.get(config.plugin_id)
            manifest = activation.manifest if activation else self._find_manifest(config.repository, config.plugin_id)
            try:
                config_values = self._decode_config(config.config_data)
                config_error = None
            except ValueError as exc:
                config_values = {}
                config_error = str(exc)
            missing_fields = missing_required_plugin_config(manifest.config_schema, config_values)
            rows.append({
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "plugin_type": manifest.plugin_type.value,
                "description": manifest.description,
                "author": manifest.author,
                "homepage_url": manifest.homepage_url,
                "repository_id": config.repository_id,
                "enabled": bool(config.enabled),
                "status": activation.status.value if activation else config.status,
                "error": config.last_error or config_error,
                "commit_hash": activation.commit_hash if activation else None,
                "config": redact_plugin_config(manifest.config_schema, config_values),
                "config_schema": manifest.config_schema,
                "missing_required_config": missing_fields,
                "configuration_required": bool(missing_fields),
                "requires": list(manifest.requires),
                "provides": list(manifest.provides),
                "cleanup_count": activation.context.cleanup_count if activation else 0,
            })
        return rows

    def activation_diagnostics(self) -> list[dict[str, Any]]:
        return [self._activation_diagnostic(item) for item in self.coordinator.snapshot().values()]

    def activation_diagnostic(self, plugin_id: str) -> dict[str, Any] | None:
        activation = self.coordinator.get(plugin_id)
        return self._activation_diagnostic(activation) if activation else None

    async def dispose_all(self) -> None:
        await self.coordinator.dispose_all()

    async def _activate_repository(
        self,
        session: Session,
        repository: Any,
        *,
        target_commit: str | None,
        fetch: bool,
        process_role: PluginProcessRole,
        advance_commit: bool,
        config_overrides: Mapping[str, Mapping[str, Any]] | None = None,
        disabled_plugin_ids: set[str] | None = None,
    ) -> ManagedRepositoryResult:
        locked_commit_before = repository.current_commit
        repo_path, actual_commit = self.loader.prepare_repository(
            repository.repo_url,
            repository.branch,
            target_commit,
            fetch=fetch,
        )
        self.loader.invalidate_repository_modules(repo_path)
        manifests = self.loader.parse_manifests(repo_path)
        if manifests[0].manifest_version == 1:
            return self._activate_legacy_repository(
                session,
                repository,
                repo_path,
                actual_commit,
                advance_commit=advance_commit,
            )

        config_rows = self._ensure_config_rows(
            session,
            repository.id,
            manifests,
            config_overrides=config_overrides,
            disabled_plugin_ids=disabled_plugin_ids,
        )
        session.flush()
        config_values = {plugin_id: self._decode_config(row.config_data) for plugin_id, row in config_rows.items()}
        enabled_ids = {plugin_id for plugin_id, row in config_rows.items() if row.enabled}
        selected_manifests = [item for item in manifests if item.plugin_type in _ROLE_TYPES[process_role]]
        try:
            result = await self.coordinator.activate_repository(
                repository_id=repository.id,
                commit_hash=actual_commit,
                repo_path=repo_path,
                manifests=selected_manifests,
                configs=config_values,
                enabled_plugin_ids=enabled_ids,
                allowed_types=_ROLE_TYPES[process_role],
                dispose_previous=False,
            )
        except RepositoryActivationError as exc:
            self._record_activation_error(repository, config_rows, manifests, config_values, exc)
            session.commit()
            if locked_commit_before:
                try:
                    self.loader.prepare_repository(
                        repository.repo_url,
                        repository.branch,
                        locked_commit_before,
                        fetch=False,
                    )
                except Exception:
                    logger.exception("恢复插件仓库锁定 checkout 失败：repository_id=%s", repository.id)
            raise

        now = datetime.now(UTC)
        active_ids = set(result.plugin_ids)
        for manifest in selected_manifests:
            row = config_rows[manifest.id]
            row.status = "active" if manifest.id in active_ids else "disabled"
            row.last_error = None
        if advance_commit:
            old_commit = repository.current_commit
            if old_commit and old_commit != actual_commit:
                repository.previous_commit = old_commit
            repository.current_commit = actual_commit
        repository.status = "loaded"
        repository.last_error = None
        repository.last_checked_at = now
        repository.last_loaded_at = now
        try:
            session.commit()
        except Exception:
            session.rollback()
            await self.coordinator.rollback_switch(result)
            if locked_commit_before:
                try:
                    self.loader.prepare_repository(
                        repository.repo_url,
                        repository.branch,
                        locked_commit_before,
                        fetch=False,
                    )
                except Exception:
                    logger.exception("数据库提交失败后恢复插件 checkout 失败：repository_id=%s", repository.id)
            raise
        await self.coordinator.finalize_switch(result)
        self._repository_signatures[repository.id] = self._repository_signature(repository, process_role)
        return ManagedRepositoryResult(repository.id, actual_commit, result.plugin_ids)

    def _activate_legacy_repository(
        self,
        session: Session,
        repository: Any,
        repo_path: Path,
        actual_commit: str,
        *,
        advance_commit: bool,
    ) -> ManagedRepositoryResult:
        loaded = self.loader.load_from_local(repo_path)
        loaded_items = loaded if isinstance(loaded, list) else [loaded]
        for item in loaded_items:
            item.commit_hash = actual_commit
            plugin_registry.register_external(item)
        if advance_commit:
            old_commit = repository.current_commit
            if old_commit and old_commit != actual_commit:
                repository.previous_commit = old_commit
            repository.current_commit = actual_commit
        repository.status = "loaded"
        repository.last_error = None
        repository.last_loaded_at = datetime.now(UTC)
        session.commit()
        return ManagedRepositoryResult(repository.id, actual_commit, tuple(item.manifest.id for item in loaded_items))

    @staticmethod
    def _ensure_config_rows(
        session: Session,
        repository_id: str,
        manifests: Sequence[PluginManifest],
        *,
        config_overrides: Mapping[str, Mapping[str, Any]] | None,
        disabled_plugin_ids: set[str] | None,
    ) -> dict[str, Any]:
        from ..models.plugin import PluginConfig

        existing = {
            item.plugin_id: item
            for item in session.query(PluginConfig).filter(PluginConfig.repository_id == repository_id).all()
        }
        for manifest in manifests:
            row = existing.get(manifest.id)
            created = row is None
            if row is None:
                row = PluginConfig(
                    id=uuid4().hex,
                    plugin_id=manifest.id,
                    plugin_type=manifest.plugin_type.value,
                    config_data="{}",
                    enabled=manifest.id not in (disabled_plugin_ids or set()),
                    status="pending",
                    repository_id=repository_id,
                )
                session.add(row)
                existing[manifest.id] = row
            else:
                row.plugin_type = manifest.plugin_type.value
            if config_overrides and manifest.id in config_overrides:
                validated = validate_plugin_config(manifest.config_schema, config_overrides[manifest.id])
                row.config_data = PluginManager._encode_config(validated, manifest.config_schema)
            elif created:
                initial_values = {
                    field_name: field_schema["default"]
                    for field_name, field_schema in manifest.config_schema.items()
                    if isinstance(field_schema, Mapping) and "default" in field_schema
                }
                missing_fields = missing_required_plugin_config(manifest.config_schema, initial_values)
                if missing_fields:
                    row.enabled = False
                    row.status = "disabled"
                    row.config_data = PluginManager._encode_config(initial_values, manifest.config_schema)
                else:
                    validated = validate_plugin_config(manifest.config_schema, initial_values)
                    row.config_data = PluginManager._encode_config(validated, manifest.config_schema)
            else:
                values = PluginManager._decode_config(row.config_data)
                if config_requires_encryption(row.config_data, values, manifest.config_schema):
                    row.config_data = PluginManager._encode_config(values, manifest.config_schema)
        return {manifest.id: existing[manifest.id] for manifest in manifests}

    @staticmethod
    def _record_activation_error(
        repository: Any,
        config_rows: Mapping[str, Any],
        manifests: Sequence[PluginManifest],
        configs: Mapping[str, Mapping[str, Any]],
        error: RepositoryActivationError,
    ) -> None:
        manifest_map = {item.id: item for item in manifests}
        failing_id = error.plugin_id
        if failing_id and failing_id in manifest_map:
            manifest = manifest_map[failing_id]
            message = redact_plugin_error(error.cause, manifest.config_schema, configs.get(failing_id))
            config_rows[failing_id].status = "error"
            config_rows[failing_id].last_error = message
        else:
            message = str(error.cause)[:1000]
        repository.status = "error"
        repository.last_error = message
        repository.last_checked_at = datetime.now(UTC)

    def _find_manifest(self, repository: Any, plugin_id: str) -> PluginManifest:
        if repository is None:
            raise ValueError(f"插件缺少所属仓库：{plugin_id}")
        repo_path = self.loader.repository_path(repository.repo_url)
        for manifest in self.loader.parse_manifests(repo_path):
            if manifest.id == plugin_id:
                return manifest
        raise ValueError(f"仓库清单中不存在插件：{plugin_id}")

    @staticmethod
    def _repository_signature(repository: Any, role: PluginProcessRole) -> tuple[Any, ...]:
        relevant_types = {item.value for item in _ROLE_TYPES[role]}
        configs = tuple(
            sorted(
                (
                    item.plugin_id,
                    item.plugin_type,
                    bool(item.enabled),
                    item.config_data or "{}",
                )
                for item in repository.configs
                if item.plugin_type in relevant_types
            )
        )
        return repository.current_commit, role.value, configs

    @staticmethod
    def _require_repository(session: Session, repo_id: str) -> Any:
        from ..models.plugin import PluginRepository

        repository = session.get(PluginRepository, repo_id)
        if repository is None:
            raise ValueError(f"插件仓库不存在：{repo_id}")
        return repository

    @staticmethod
    def _require_plugin_config(session: Session, plugin_id: str) -> Any:
        from ..models.plugin import PluginConfig

        config = session.query(PluginConfig).filter(PluginConfig.plugin_id == plugin_id).first()
        if config is None:
            raise ValueError(f"插件不存在：{plugin_id}")
        return config

    @staticmethod
    def _decode_config(value: str | Mapping[str, Any] | None) -> dict[str, Any]:
        return decode_plugin_config(value)

    @staticmethod
    def _encode_config(value: Mapping[str, Any], schema: Mapping[str, Any] | None = None) -> str:
        return encode_plugin_config(value, schema)

    @staticmethod
    def _activation_diagnostic(activation: Any) -> dict[str, Any]:
        return {
            "plugin_id": activation.plugin_id,
            "repository_id": activation.repository_id,
            "commit_hash": activation.commit_hash,
            "status": activation.status.value,
            "requires": list(activation.required_capabilities),
            "provides": sorted(activation.provided_capabilities),
            "cleanup_count": activation.context.cleanup_count,
            "error": activation.error,
            "activated_at": activation.activated_at.isoformat() if activation.activated_at else None,
        }


plugin_manager = PluginManager()
