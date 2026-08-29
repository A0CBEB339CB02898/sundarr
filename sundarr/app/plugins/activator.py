"""Manifest v2 单插件候选 Activation。"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sundarr.app.sources.base import SourceModel

from .base import PluginManifest, PluginType
from .config import build_sensitive_log_filter, validate_plugin_config
from .contracts import (
    CatalogCapabilities,
    CatalogOperation,
    CatalogProvider,
    PluginHealthResult,
    WatchlistProvider,
)
from .loader import PluginLoader, plugin_loader
from .http import plugin_http_client_factory
from .runtime import PluginActivation, PluginContext
from .runtime_registry import (
    RuntimePluginRegistry,
    catalog_provider_registry,
    get_runtime_registry,
    source_registry,
    watchlist_provider_registry,
)


_REGISTRY_CAPABILITIES: dict[PluginType, str] = {
    PluginType.SOURCE: "core.source_registry.v1",
    PluginType.CATALOG_PROVIDER: "core.catalog_registry.v1",
    PluginType.WATCHLIST_PROVIDER: "core.watchlist_registry.v1",
}

_ALLOWED_PROVIDES: dict[PluginType, frozenset[str]] = {
    PluginType.SOURCE: frozenset({"source.search.v1", "source.detail.v1"}),
    PluginType.CATALOG_PROVIDER: frozenset(
        {
            "catalog.search.v1",
            "catalog.trending.v1",
            "catalog.categories.v1",
            "catalog.detail.v1",
        }
    ),
    PluginType.WATCHLIST_PROVIDER: frozenset({"watchlist.pull.v1"}),
}

_OPERATION_CAPABILITIES: dict[CatalogOperation, str] = {
    CatalogOperation.SEARCH: "catalog.search.v1",
    CatalogOperation.TRENDING: "catalog.trending.v1",
    CatalogOperation.CATEGORIES: "catalog.categories.v1",
    CatalogOperation.DETAIL: "catalog.detail.v1",
}


class CandidateActivationError(RuntimeError):
    """候选插件激活失败，并保留可诊断的 Activation。"""

    def __init__(
        self,
        activation: PluginActivation,
        cause: BaseException,
    ) -> None:
        self.activation = activation
        self.cause = cause
        super().__init__(f"插件 {activation.plugin_id} 候选激活失败：{cause}")


@dataclass(frozen=True)
class PreparedPluginCandidate:
    """已通过入口、合同和健康检查，但尚未对外可见的候选。"""

    activation: PluginActivation
    instance: Any
    registry: RuntimePluginRegistry[Any]


def build_core_capabilities(
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """创建 B4 使用的最小 Core 能力集合。"""

    capabilities: dict[str, Any] = {
        "core.source_registry.v1": source_registry,
        "core.catalog_registry.v1": catalog_provider_registry,
        "core.watchlist_registry.v1": watchlist_provider_registry,
    }
    for name, value in (extra or {}).items():
        if name in capabilities:
            raise ValueError(f"不能覆盖内置 Core 能力：{name}")
        capabilities[name] = value
    capabilities.setdefault("core.http.v1", plugin_http_client_factory)
    return capabilities


class PluginActivator:
    """负责一个 v2 Manifest 的候选校验和激活。"""

    def __init__(
        self,
        *,
        loader: PluginLoader | None = None,
        extra_capabilities: Mapping[str, Any] | None = None,
    ) -> None:
        self.loader = loader or plugin_loader
        self.capabilities = build_core_capabilities(extra_capabilities)

    async def activate_candidate(
        self,
        manifest: PluginManifest,
        repo_path: Path,
        *,
        plugin_config: Mapping[str, Any] | None = None,
        repository_id: str | None = None,
        commit_hash: str | None = None,
    ) -> PluginActivation:
        """激活单插件候选；失败时清理副作用并抛出诊断异常。"""

        candidate = await self.prepare_candidate(
            manifest,
            repo_path,
            plugin_config=plugin_config,
            repository_id=repository_id,
            commit_hash=commit_hash,
        )
        try:
            candidate.registry.register(manifest.id, candidate.instance)
            candidate.activation.activate(candidate.instance)
            return candidate.activation
        except Exception as exc:
            await candidate.activation.fail(exc)
            raise CandidateActivationError(candidate.activation, exc) from exc

    async def prepare_candidate(
        self,
        manifest: PluginManifest,
        repo_path: Path,
        *,
        plugin_config: Mapping[str, Any] | None = None,
        repository_id: str | None = None,
        commit_hash: str | None = None,
    ) -> PreparedPluginCandidate:
        """准备一个不写入 Registry 的候选，供仓库级编排统一提交。"""

        validated_config = validate_plugin_config(manifest.config_schema, plugin_config)
        declared_capabilities = {
            name: self.capabilities[name]
            for name in manifest.requires
            if name in self.capabilities
        }
        context = PluginContext(
            manifest.id,
            capabilities=declared_capabilities,
            plugin_config=validated_config,
        )
        activation = PluginActivation(
            manifest=manifest,
            context=context,
            repository_id=repository_id,
            commit_hash=commit_hash,
            required_capabilities=manifest.requires,
        )
        log_filter = build_sensitive_log_filter(manifest.config_schema, validated_config)
        if log_filter is not None:
            context.logger.addFilter(log_filter)
            context.register_cleanup(lambda: context.logger.removeFilter(log_filter))

        try:
            self._validate_manifest_runtime_contract(manifest)
            activation.begin_validation()
            _, entry = self.loader.load_entry(manifest, repo_path)
            instance = entry(context)
            if inspect.isawaitable(instance):
                instance = await instance

            registry = get_runtime_registry(manifest.plugin_type)
            registry.validate(manifest.id, instance)
            actual_capabilities = await self._health_check(manifest, instance)

            context.register_cleanup(
                lambda: registry.unregister(
                    manifest.id,
                    expected_instance=instance,
                )
            )
            for capability_name in sorted(actual_capabilities):
                context.provide(capability_name, instance)

            activation.instance = instance
            return PreparedPluginCandidate(
                activation=activation,
                instance=instance,
                registry=registry,
            )
        except Exception as exc:
            await activation.fail(exc)
            raise CandidateActivationError(activation, exc) from exc

    @staticmethod
    def _validate_manifest_runtime_contract(manifest: PluginManifest) -> None:
        if manifest.manifest_version != 2:
            raise ValueError("PluginActivator 只接受 Manifest v2 插件")
        registry_capability = _REGISTRY_CAPABILITIES.get(manifest.plugin_type)
        if registry_capability is None:
            raise ValueError(f"当前阶段不支持激活插件类型：{manifest.plugin_type.value}")
        if registry_capability not in manifest.requires:
            raise ValueError(
                f"插件 {manifest.id} 必须声明依赖 {registry_capability}"
            )
        if any(not name.startswith("core.") for name in manifest.requires):
            raise ValueError("MVP 插件只能 requires Core 宿主能力")

        declared = set(manifest.provides)
        allowed = _ALLOWED_PROVIDES[manifest.plugin_type]
        invalid = sorted(declared - allowed)
        if invalid:
            raise ValueError(
                f"插件 {manifest.id} 声明了不属于其类型的能力：{'、'.join(invalid)}"
            )
        required_provide = {
            PluginType.SOURCE: "source.search.v1",
            PluginType.WATCHLIST_PROVIDER: "watchlist.pull.v1",
        }.get(manifest.plugin_type)
        if required_provide and required_provide not in declared:
            raise ValueError(f"插件 {manifest.id} 必须提供 {required_provide}")

    async def _health_check(
        self,
        manifest: PluginManifest,
        instance: Any,
    ) -> frozenset[str]:
        actual_capabilities = self._type_capabilities(manifest, instance)
        undeclared = sorted(actual_capabilities - set(manifest.provides))
        if undeclared:
            raise ValueError(
                f"插件 {manifest.id} 的运行能力未在 Manifest 声明："
                f"{'、'.join(undeclared)}"
            )

        health_check = getattr(instance, "health_check", None)
        if health_check is not None:
            if not callable(health_check):
                raise TypeError("health_check 必须可调用")
            result = health_check()
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, PluginHealthResult):
                raise TypeError("health_check 必须返回 PluginHealthResult")
            if not result.ok:
                raise RuntimeError(result.message or "插件健康检查失败")

        return frozenset(actual_capabilities)

    @staticmethod
    def _type_capabilities(
        manifest: PluginManifest,
        instance: Any,
    ) -> set[str]:
        if manifest.plugin_type == PluginType.SOURCE:
            if not isinstance(instance, SourceModel):
                raise TypeError("SOURCE 入口必须返回 SourceModel")
            capabilities = {"source.search.v1"}
            if instance.fetch_detail_function is not None:
                capabilities.add("source.detail.v1")
            return capabilities

        if manifest.plugin_type == PluginType.CATALOG_PROVIDER:
            if not isinstance(instance, CatalogProvider):
                raise TypeError("目录插件实例不符合 CatalogProvider 合同")
            capabilities = instance.describe_capabilities()
            if not isinstance(capabilities, CatalogCapabilities):
                raise TypeError("describe_capabilities 必须返回 CatalogCapabilities")
            return {
                _OPERATION_CAPABILITIES[operation]
                for operation in capabilities.operations
            }

        if manifest.plugin_type == PluginType.WATCHLIST_PROVIDER:
            if not isinstance(instance, WatchlistProvider):
                raise TypeError("想看插件实例不符合 WatchlistProvider 合同")
            return {"watchlist.pull.v1"}

        raise ValueError(f"当前阶段不支持激活插件类型：{manifest.plugin_type.value}")


plugin_activator = PluginActivator()
