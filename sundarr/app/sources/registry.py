"""
搜索源注册中心

管理所有搜索源。当前无内置搜索源，全部通过外部插件仓库加载。
"""

import logging
from typing import List

from sundarr.app.plugins.base import PluginType
from sundarr.app.plugins.registry import plugin_registry
from sundarr.app.sources.base import SourceModel

logger = logging.getLogger(__name__)


def get_builtin_sources() -> List[SourceModel]:
    """
    获取内置源。当前无内置搜索源。

    Returns:
        内置搜索源列表
    """
    return []


def get_external_sources() -> List[SourceModel]:
    """
    获取外部插件搜索源

    从插件注册中心获取所有类型为 SOURCE 的插件，并提取 SourceModel 实例。

    Returns:
        外部搜索源列表
    """
    # 延迟导入，避免 plugins 合同加载 SourceModel 时形成包初始化环。
    from sundarr.app.plugins.runtime_registry import source_registry

    external_plugins = plugin_registry.get_plugins_by_type(PluginType.SOURCE)
    sources = source_registry.get_all()
    runtime_source_ids = {source.id for source in sources}

    for plugin in external_plugins:
        if plugin.status != "loaded":
            continue

        try:
            # 如果实例已经是 SourceModel，直接使用
            if isinstance(plugin.instance, SourceModel):
                if plugin.instance.id not in runtime_source_ids:
                    sources.append(plugin.instance)
            # 如果实例是 callable（返回 SourceModel 或 List[SourceModel] 的函数）
            elif callable(plugin.instance):
                result = plugin.instance()
                if isinstance(result, list):
                    sources.extend(
                        source for source in result if source.id not in runtime_source_ids
                    )
                elif isinstance(result, SourceModel):
                    if result.id not in runtime_source_ids:
                        sources.append(result)
                else:
                    logger.warning(
                        f"插件 {plugin.manifest.id} 的入口函数返回了无效类型：{type(result)}"
                    )
            else:
                logger.warning(
                    f"插件 {plugin.manifest.id} 的实例类型无效：{type(plugin.instance)}"
                )
        except Exception as e:
            logger.error(f"加载插件 {plugin.manifest.id} 失败：{e}")

    return sources


def get_registered_sources() -> List[SourceModel]:
    """
    获取所有已注册的搜索源（当前全部来自外部插件）

    合并内置源和外部插件源，并检查 ID 冲突。

    Returns:
        所有搜索源列表

    Raises:
        ValueError: 如果外部源 ID 与内置源冲突
    """
    builtin = get_builtin_sources()
    external = get_external_sources()

    # 检查 ID 冲突
    builtin_ids = {s.id for s in builtin}
    for ext in external:
        if ext.id in builtin_ids:
            logger.error(f"外部源 ID 冲突：{ext.id} 已被内置源占用")
            raise ValueError(f"外部源 ID 冲突：{ext.id} 已被内置源占用")

    logger.info(f"已注册 {len(builtin)} 个内置源，{len(external)} 个外部源")
    return builtin + external


def get_source_by_id(source_id: str) -> SourceModel:
    """
    根据 ID 获取搜索源
    Args:
        source_id: 搜索源 ID
    Returns:
        搜索源实例
    Raises:
        ValueError: 如果搜索源不存在
    """
    sources = get_registered_sources()
    for source in sources:
        if source.id == source_id:
            return source
    raise ValueError(f"搜索源不存在：{source_id}")


def list_source_ids() -> List[str]:
    """
    获取所有搜索源 ID
    Returns:
        搜索源 ID 列表
    """
    sources = get_registered_sources()
    return [s.id for s in sources]
