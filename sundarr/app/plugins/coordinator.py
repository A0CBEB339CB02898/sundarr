"""通用 v2 插件仓库的候选编排和原子切换。"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .activator import PluginActivator, PreparedPluginCandidate, plugin_activator
from .base import PluginManifest, PluginType
from .runtime import PluginActivation
from .runtime_registry import get_runtime_registry, runtime_registry_transaction


@dataclass(frozen=True)
class RepositoryActivationResult:
    """一次仓库版本切换的稳定结果。"""

    repository_id: str
    commit_hash: str
    activations: tuple[PluginActivation, ...]

    @property
    def plugin_ids(self) -> tuple[str, ...]:
        return tuple(item.plugin_id for item in self.activations)


class RepositoryActivationError(RuntimeError):
    """仓库候选中至少一个插件失败，旧版本保持不变。"""

    def __init__(self, repository_id: str, commit_hash: str, cause: BaseException) -> None:
        self.repository_id = repository_id
        self.commit_hash = commit_hash
        self.cause = cause
        super().__init__(f"插件仓库 {repository_id} 候选 {commit_hash} 激活失败：{cause}")


class RepositoryActivationCoordinator:
    """维护当前进程内的仓库 Activation，并提供仓库级切换语义。"""

    def __init__(self, *, activator: PluginActivator | None = None) -> None:
        self.activator = activator or plugin_activator
        self._by_repository: dict[str, dict[str, PluginActivation]] = {}
        self._by_plugin: dict[str, PluginActivation] = {}
        self._switch_lock = asyncio.Lock()

    async def activate_repository(
        self,
        *,
        repository_id: str,
        commit_hash: str,
        repo_path: Path,
        manifests: Sequence[PluginManifest],
        configs: Mapping[str, Mapping[str, Any]] | None = None,
        enabled_plugin_ids: set[str] | frozenset[str] | None = None,
        allowed_types: set[PluginType] | frozenset[PluginType] | None = None,
    ) -> RepositoryActivationResult:
        """先完整准备全部候选，再让同仓库本进程插件一次性可见。"""

        selected = [
            manifest
            for manifest in manifests
            if (enabled_plugin_ids is None or manifest.id in enabled_plugin_ids)
            and (allowed_types is None or manifest.plugin_type in allowed_types)
        ]
        prepared: list[PreparedPluginCandidate] = []
        try:
            for manifest in selected:
                prepared.append(
                    await self.activator.prepare_candidate(
                        manifest,
                        repo_path,
                        plugin_config=(configs or {}).get(manifest.id),
                        repository_id=repository_id,
                        commit_hash=commit_hash,
                    )
                )
        except Exception as exc:
            await self._fail_prepared(prepared, exc)
            raise RepositoryActivationError(repository_id, commit_hash, exc) from exc

        old_activations: list[PluginActivation] = []
        try:
            async with self._switch_lock:
                old_map = self._by_repository.get(repository_id, {})
                old_activations = list(old_map.values())
                self._validate_ownership(repository_id, prepared)
                with runtime_registry_transaction():
                    for plugin_id, activation in old_map.items():
                        if plugin_id not in {item.activation.plugin_id for item in prepared}:
                            get_runtime_registry(activation.manifest.plugin_type).unregister(
                                plugin_id,
                                expected_instance=activation.instance,
                            )
                    for item in prepared:
                        item.registry.replace(item.activation.plugin_id, item.instance)
                    for item in prepared:
                        item.activation.activate(item.instance)

                    for plugin_id in old_map:
                        self._by_plugin.pop(plugin_id, None)
                    new_map = {
                        item.activation.plugin_id: item.activation for item in prepared
                    }
                    if new_map:
                        self._by_repository[repository_id] = new_map
                    else:
                        self._by_repository.pop(repository_id, None)
                    self._by_plugin.update(new_map)
        except Exception as exc:
            # activate() 仅做内存状态封闭，正常不会失败；这里仍保守恢复旧 Registry。
            with runtime_registry_transaction():
                for item in prepared:
                    item.registry.unregister(
                        item.activation.plugin_id,
                        expected_instance=item.instance,
                    )
                for old in old_activations:
                    get_runtime_registry(old.manifest.plugin_type).replace(
                        old.plugin_id,
                        old.instance,
                    )
            await self._fail_prepared(prepared, exc)
            raise RepositoryActivationError(repository_id, commit_hash, exc) from exc

        for activation in old_activations:
            await activation.dispose()
        return RepositoryActivationResult(
            repository_id=repository_id,
            commit_hash=commit_hash,
            activations=tuple(item.activation for item in prepared),
        )

    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """从当前进程禁用一个插件并执行确定清理。"""

        async with self._switch_lock:
            activation = self._by_plugin.pop(plugin_id, None)
            if activation is None:
                return False
            repo_map = self._by_repository.get(activation.repository_id or "", {})
            repo_map.pop(plugin_id, None)
            if not repo_map and activation.repository_id:
                self._by_repository.pop(activation.repository_id, None)
            with runtime_registry_transaction():
                get_runtime_registry(activation.manifest.plugin_type).unregister(
                    plugin_id,
                    expected_instance=activation.instance,
                )
        await activation.dispose()
        return True

    async def deactivate_repository(self, repository_id: str) -> int:
        """释放当前进程中属于指定仓库的全部插件。"""

        async with self._switch_lock:
            repo_map = self._by_repository.pop(repository_id, {})
            with runtime_registry_transaction():
                for plugin_id, activation in repo_map.items():
                    self._by_plugin.pop(plugin_id, None)
                    get_runtime_registry(activation.manifest.plugin_type).unregister(
                        plugin_id,
                        expected_instance=activation.instance,
                    )
        for activation in repo_map.values():
            await activation.dispose()
        return len(repo_map)

    async def dispose_all(self) -> None:
        """释放当前进程全部外部 v2 Activation。"""

        for repository_id in tuple(self._by_repository):
            await self.deactivate_repository(repository_id)

    def get(self, plugin_id: str) -> PluginActivation | None:
        return self._by_plugin.get(plugin_id)

    def snapshot(self) -> Mapping[str, PluginActivation]:
        return MappingProxyType(dict(self._by_plugin))

    def repository_snapshot(self, repository_id: str) -> Mapping[str, PluginActivation]:
        return MappingProxyType(dict(self._by_repository.get(repository_id, {})))

    def _validate_ownership(
        self,
        repository_id: str,
        prepared: Sequence[PreparedPluginCandidate],
    ) -> None:
        for item in prepared:
            plugin_id = item.activation.plugin_id
            owner = self._by_plugin.get(plugin_id)
            current = item.registry.get(plugin_id)
            if owner is not None and owner.repository_id != repository_id:
                raise ValueError(f"插件 ID 已由其他仓库占用：{plugin_id}")
            if current is not None and owner is None:
                raise ValueError(f"插件 ID 已由 Core 或兼容插件占用：{plugin_id}")

    @staticmethod
    async def _fail_prepared(
        prepared: Sequence[PreparedPluginCandidate],
        error: BaseException,
    ) -> None:
        for item in reversed(prepared):
            await item.activation.fail(error)


repository_activation_coordinator = RepositoryActivationCoordinator()
