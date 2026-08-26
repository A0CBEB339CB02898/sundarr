"""
Sundarr 插件系统

提供统一的插件注册、发现和管理机制，支持多种插件类型：
- Source: 搜索源插件
- CloudProvider: 网盘 Provider 插件
- Notification: 通知渠道插件
- Crawler: 爬虫插件（豆瓣等）
- LinkValidator: 链接验证器插件
- LinkExtractor: 链接提取器插件
- TaskProcessor: 任务处理器插件
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
