"""
Sundarr 插件系统

提供统一的插件注册、发现和管理机制：
- SOURCE: 具体资源链接搜索
- CATALOG_PROVIDER: 媒体目录
- WATCHLIST_PROVIDER: 外部想看列表
- TRANSFER_DRIVER / NOTIFICATION: 后续扩展点，当前不允许激活
"""

from .base import PluginType, PluginManifest, LoadedPlugin
from .registry import PluginRegistry, plugin_registry
from .runtime import (
    ActivationStatus,
    MissingCapabilityError,
    PluginActivation,
    PluginContext,
    PluginContextClosedError,
)

__all__ = [
    "PluginType",
    "PluginManifest",
    "LoadedPlugin",
    "PluginRegistry",
    "plugin_registry",
    "ActivationStatus",
    "MissingCapabilityError",
    "PluginActivation",
    "PluginContext",
    "PluginContextClosedError",
]
