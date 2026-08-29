"""按 PluginType 隔离的运行实例注册中心。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from threading import RLock
from types import MappingProxyType
from typing import Any, Generic, TypeVar

from sundarr.app.sources.base import SourceModel

from .base import PluginType
from .contracts import CatalogProvider, WatchlistProvider


T = TypeVar("T")
InstanceValidator = Callable[[str, Any], None]
_UNSET = object()
_RUNTIME_REGISTRY_LOCK = RLock()


class RuntimePluginRegistry(Generic[T]):
    """保存一种插件类型的 active 运行实例。"""

    def __init__(
        self,
        plugin_type: PluginType,
        validator: InstanceValidator,
    ) -> None:
        self.plugin_type = plugin_type
        self._validator = validator
        self._instances: dict[str, T] = {}
        # 三类 Registry 共用同一把可重入锁，仓库切换时读者只能看到切换前
        # 或切换后的完整快照，不能看到跨类型的半切换状态。
        self._lock = _RUNTIME_REGISTRY_LOCK

    def register(self, plugin_id: str, instance: T) -> None:
        """注册新实例；已有同 ID 时必须显式使用 replace。"""

        self.validate(plugin_id, instance)
        with self._lock:
            if plugin_id in self._instances:
                raise ValueError(f"插件运行实例 ID 冲突：{plugin_id} 已存在")
            self._instances[plugin_id] = instance

    def replace(self, plugin_id: str, instance: T) -> T | None:
        """原子替换实例，并返回旧实例。"""

        self.validate(plugin_id, instance)
        with self._lock:
            previous = self._instances.get(plugin_id)
            self._instances[plugin_id] = instance
            return previous

    def unregister(
        self,
        plugin_id: str,
        *,
        expected_instance: T | object = _UNSET,
    ) -> bool:
        """注销实例；可用实例身份保护新版本不被旧 cleanup 删除。"""

        with self._lock:
            current = self._instances.get(plugin_id, _UNSET)
            if current is _UNSET:
                return False
            if expected_instance is not _UNSET and current is not expected_instance:
                return False
            del self._instances[plugin_id]
            return True

    def get(self, plugin_id: str) -> T | None:
        """按插件 ID 获取实例。"""

        with self._lock:
            return self._instances.get(plugin_id)

    def require(self, plugin_id: str) -> T:
        """按插件 ID 获取实例；不存在时给出明确错误。"""

        instance = self.get(plugin_id)
        if instance is None:
            raise KeyError(f"未注册的 {self.plugin_type.value} 插件：{plugin_id}")
        return instance

    def get_all(self) -> list[T]:
        """返回当前实例的稳定快照。"""

        with self._lock:
            return list(self._instances.values())

    def snapshot(self) -> Mapping[str, T]:
        """返回按插件 ID 索引的只读快照。"""

        with self._lock:
            return MappingProxyType(dict(self._instances))

    def clear(self) -> None:
        """清空注册中心，主要用于测试和进程关闭。"""

        with self._lock:
            self._instances.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._instances)

    def validate(self, plugin_id: str, instance: T) -> None:
        """只校验合同和 ID，不修改 Registry。"""

        if not plugin_id or not plugin_id.strip():
            raise ValueError("plugin_id 不能为空")
        self._validator(plugin_id, instance)


@contextmanager
def runtime_registry_transaction():
    """锁住全部类型 Registry，供仓库级原子切换使用。"""

    with _RUNTIME_REGISTRY_LOCK:
        yield


def _validate_source(plugin_id: str, instance: Any) -> None:
    if not isinstance(instance, SourceModel):
        raise TypeError("SOURCE 运行实例必须是 SourceModel")
    if instance.id != plugin_id:
        raise ValueError("SOURCE 实例 id 必须与 plugin_id 一致")


def _validate_catalog_provider(plugin_id: str, instance: Any) -> None:
    if not isinstance(instance, CatalogProvider):
        raise TypeError("CATALOG_PROVIDER 运行实例不符合 CatalogProvider 合同")
    if instance.id != plugin_id:
        raise ValueError("CATALOG_PROVIDER 实例 id 必须与 plugin_id 一致")


def _validate_watchlist_provider(plugin_id: str, instance: Any) -> None:
    if not isinstance(instance, WatchlistProvider):
        raise TypeError("WATCHLIST_PROVIDER 运行实例不符合 WatchlistProvider 合同")
    if instance.id != plugin_id:
        raise ValueError("WATCHLIST_PROVIDER 实例 id 必须与 plugin_id 一致")


source_registry = RuntimePluginRegistry[SourceModel](
    PluginType.SOURCE,
    _validate_source,
)
catalog_provider_registry = RuntimePluginRegistry[CatalogProvider](
    PluginType.CATALOG_PROVIDER,
    _validate_catalog_provider,
)
watchlist_provider_registry = RuntimePluginRegistry[WatchlistProvider](
    PluginType.WATCHLIST_PROVIDER,
    _validate_watchlist_provider,
)

_MVP_REGISTRIES: dict[PluginType, RuntimePluginRegistry[Any]] = {
    PluginType.SOURCE: source_registry,
    PluginType.CATALOG_PROVIDER: catalog_provider_registry,
    PluginType.WATCHLIST_PROVIDER: watchlist_provider_registry,
}


def get_runtime_registry(plugin_type: PluginType) -> RuntimePluginRegistry[Any]:
    """取得当前 MVP 类型对应的运行实例 Registry。"""

    try:
        return _MVP_REGISTRIES[plugin_type]
    except KeyError as exc:
        raise ValueError(f"当前阶段不支持激活插件类型：{plugin_type.value}") from exc
