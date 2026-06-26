"""
插件注册中心

提供统一的插件注册、发现和管理机制。
"""

from typing import Dict, List, Optional
from .base import PluginManifest, LoadedPlugin, PluginType


class PluginRegistry:
    """
    统一插件注册中心

    管理所有已注册的插件，包括内置插件和外部插件。
    提供按类型、ID 等条件查询插件的功能。

    使用方式：
        from sundarr.app.plugins.registry import plugin_registry

        # 注册内置插件
        plugin_registry.register_builtin(builtin_plugin)

        # 注册外部插件
        plugin_registry.register_external(external_plugin)

        # 获取所有搜索源插件
        source_plugins = plugin_registry.get_plugins_by_type(PluginType.SOURCE)

        # 获取特定插件
        plugin = plugin_registry.get_plugin("quark-provider")
    """

    def __init__(self):
        self._plugins: Dict[str, LoadedPlugin] = {}
        self._builtin_plugins: Dict[str, LoadedPlugin] = {}

    def register_builtin(self, plugin: LoadedPlugin) -> None:
        """
        注册内置插件

        内置插件随系统启动自动加载，优先级高于外部插件。

        Args:
            plugin: 已加载的插件实例

        Raises:
            ValueError: 如果插件 ID 已存在
        """
        if plugin.manifest.id in self._builtin_plugins:
            raise ValueError(f"内置插件 ID 冲突：{plugin.manifest.id} 已存在")

        self._builtin_plugins[plugin.manifest.id] = plugin

    def register_external(self, plugin: LoadedPlugin) -> None:
        """
        注册外部插件

        外部插件从 Git 仓库或本地目录加载。

        Args:
            plugin: 已加载的插件实例

        Raises:
            ValueError: 如果插件 ID 与内置插件冲突
        """
        if plugin.manifest.id in self._builtin_plugins:
            raise ValueError(
                f"外部插件 ID 冲突：{plugin.manifest.id} 已被内置插件占用"
            )

        self._plugins[plugin.manifest.id] = plugin

    def unregister(self, plugin_id: str) -> bool:
        """
        注销插件

        Args:
            plugin_id: 插件 ID

        Returns:
            是否成功注销
        """
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[LoadedPlugin]:
        """
        获取插件

        优先从外部插件中查找，如果未找到则从内置插件中查找。

        Args:
            plugin_id: 插件 ID

        Returns:
            插件实例，如果未找到则返回 None
        """
        return self._plugins.get(plugin_id) or self._builtin_plugins.get(plugin_id)

    def get_plugins_by_type(
        self,
        plugin_type: PluginType,
        include_disabled: bool = False,
    ) -> List[LoadedPlugin]:
        """
        按类型获取插件

        Args:
            plugin_type: 插件类型
            include_disabled: 是否包含已禁用的插件

        Returns:
            指定类型的插件列表
        """
        all_plugins = {**self._builtin_plugins, **self._plugins}

        return [
            p
            for p in all_plugins.values()
            if p.manifest.plugin_type == plugin_type
            and (include_disabled or p.status == "loaded")
        ]

    def get_all_plugins(
        self,
        include_disabled: bool = False,
    ) -> List[LoadedPlugin]:
        """
        获取所有插件

        Args:
            include_disabled: 是否包含已禁用的插件

        Returns:
            所有插件列表
        """
        all_plugins = {**self._builtin_plugins, **self._plugins}

        if include_disabled:
            return list(all_plugins.values())

        return [p for p in all_plugins.values() if p.status == "loaded"]

    def get_builtin_plugins(self) -> List[LoadedPlugin]:
        """
        获取所有内置插件

        Returns:
            内置插件列表
        """
        return list(self._builtin_plugins.values())

    def get_external_plugins(self) -> List[LoadedPlugin]:
        """
        获取所有外部插件

        Returns:
            外部插件列表
        """
        return list(self._plugins.values())

    def has_plugin(self, plugin_id: str) -> bool:
        """
        检查插件是否存在

        Args:
            plugin_id: 插件 ID

        Returns:
            插件是否存在
        """
        return (
            plugin_id in self._plugins or plugin_id in self._builtin_plugins
        )

    def is_plugin_loaded(self, plugin_id: str) -> bool:
        """
        检查插件是否已加载

        Args:
            plugin_id: 插件 ID

        Returns:
            插件是否已加载
        """
        plugin = self.get_plugin(plugin_id)
        return plugin is not None and plugin.status == "loaded"

    def clear(self) -> None:
        """
        清除所有插件

        主要用于测试。
        """
        self._plugins.clear()
        self._builtin_plugins.clear()

    def get_plugin_count(self) -> Dict[str, int]:
        """
        获取插件统计信息

        Returns:
            包含各类型插件数量的字典
        """
        all_plugins = self.get_all_plugins(include_disabled=True)

        stats = {
            "total": len(all_plugins),
            "builtin": len(self._builtin_plugins),
            "external": len(self._plugins),
            "loaded": len([p for p in all_plugins if p.status == "loaded"]),
            "error": len([p for p in all_plugins if p.status == "error"]),
            "disabled": len([p for p in all_plugins if p.status == "disabled"]),
        }

        # 按类型统计
        for plugin_type in PluginType:
            stats[plugin_type.value] = len(
                [p for p in all_plugins if p.manifest.plugin_type == plugin_type]
            )

        return stats


# 全局单例
plugin_registry = PluginRegistry()
