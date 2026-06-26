"""
插件管理器

负责插件的生命周期管理，包括加载、卸载、启用、禁用等。
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .base import LoadedPlugin, PluginManifest, PluginType
from .loader import plugin_loader
from .registry import plugin_registry

logger = logging.getLogger(__name__)


class PluginManager:
    """
    插件管理器

    负责插件的生命周期管理，包括：
    - 从数据库加载已配置的插件仓库
    - 更新、回滚插件仓库
    - 启用、禁用插件
    - 管理插件配置

    使用方式：
        from sundarr.app.plugins.manager import plugin_manager

        # 加载所有已配置的仓库
        plugin_manager.load_all_repositories(session)

        # 更新仓库
        plugin_manager.update_repository(session, repo_id)

        # 启用/禁用插件
        plugin_manager.enable_plugin(session, plugin_id)
        plugin_manager.disable_plugin(session, plugin_id)
    """

    def load_all_repositories(self, session: Session) -> Dict[str, Any]:
        """
        加载所有已配置的仓库

        从数据库中读取已配置的插件仓库，然后逐个加载。

        Args:
            session: 数据库会话

        Returns:
            加载结果统计
        """
        from ..models.plugin import PluginRepository

        repos = session.query(PluginRepository).filter(
            PluginRepository.enabled == True
        ).all()

        stats = {
            "total": len(repos),
            "loaded": 0,
            "error": 0,
            "errors": [],
        }

        for repo in repos:
            try:
                loaded = plugin_loader.load_from_repo(
                    repo_url=repo.repo_url,
                    branch=repo.branch,
                    commit=repo.current_commit,
                )
                plugin_registry.register_external(loaded)

                # 更新数据库状态
                repo.status = "loaded"
                repo.last_error = None
                repo.current_commit = loaded.commit_hash
                stats["loaded"] += 1

            except Exception as e:
                # 更新数据库状态
                repo.status = "error"
                repo.last_error = str(e)
                stats["error"] += 1
                stats["errors"].append({
                    "repo": repo.name,
                    "error": str(e),
                })

                logger.error(f"加载插件仓库失败：{repo.name} - {e}")

        session.commit()

        logger.info(
            f"插件仓库加载完成：总计 {stats['total']}，"
            f"成功 {stats['loaded']}，失败 {stats['error']}"
        )

        return stats

    def update_repository(
        self,
        session: Session,
        repo_id: str,
        new_commit: Optional[str] = None,
    ) -> LoadedPlugin:
        """
        更新仓库到最新或指定 commit

        Args:
            session: 数据库会话
            repo_id: 仓库 ID
            new_commit: 新的 commit hash（如果为 None 则更新到最新）

        Returns:
            更新后的已加载插件实例

        Raises:
            ValueError: 如果仓库不存在
        """
        from ..models.plugin import PluginRepository

        repo = session.get(PluginRepository, repo_id)
        if not repo:
            raise ValueError(f"仓库不存在：{repo_id}")

        # 保存旧 commit 用于回滚
        repo.previous_commit = repo.current_commit

        try:
            # 更新仓库
            actual_commit = plugin_loader.update_repo(
                repo_url=repo.repo_url,
                branch=repo.branch,
                new_commit=new_commit,
            )

            # 重新加载插件
            loaded = plugin_loader.load_from_repo(
                repo_url=repo.repo_url,
                branch=repo.branch,
                commit=actual_commit,
            )

            # 注销旧插件
            plugin_registry.unregister(loaded.manifest.id)

            # 注册新插件
            plugin_registry.register_external(loaded)

            # 更新数据库状态
            repo.current_commit = actual_commit
            repo.status = "loaded"
            repo.last_error = None

            session.commit()

            logger.info(f"仓库更新成功：{repo.name} -> {actual_commit}")
            return loaded

        except Exception as e:
            # 更新数据库状态
            repo.status = "error"
            repo.last_error = str(e)
            session.commit()

            logger.error(f"仓库更新失败：{repo.name} - {e}")
            raise

    def rollback_repository(
        self,
        session: Session,
        repo_id: str,
    ) -> LoadedPlugin:
        """
        回滚仓库到上一个 commit

        Args:
            session: 数据库会话
            repo_id: 仓库 ID

        Returns:
            回滚后的已加载插件实例

        Raises:
            ValueError: 如果仓库不存在或没有可回滚的版本
        """
        from ..models.plugin import PluginRepository

        repo = session.get(PluginRepository, repo_id)
        if not repo:
            raise ValueError(f"仓库不存在：{repo_id}")

        if not repo.previous_commit:
            raise ValueError(f"没有可回滚的版本：{repo.name}")

        return self.update_repository(session, repo_id, repo.previous_commit)

    def enable_plugin(
        self,
        session: Session,
        plugin_id: str,
    ) -> None:
        """
        启用插件

        Args:
            session: 数据库会话
            plugin_id: 插件 ID
        """
        from ..models.plugin import PluginConfig

        plugin = plugin_registry.get_plugin(plugin_id)
        if plugin:
            plugin.status = "loaded"

        # 更新数据库中的状态
        config = session.query(PluginConfig).filter(
            PluginConfig.plugin_id == plugin_id
        ).first()

        if config:
            config.enabled = True
            session.commit()

        logger.info(f"插件已启用：{plugin_id}")

    def disable_plugin(
        self,
        session: Session,
        plugin_id: str,
    ) -> None:
        """
        禁用插件

        Args:
            session: 数据库会话
            plugin_id: 插件 ID
        """
        from ..models.plugin import PluginConfig

        plugin = plugin_registry.get_plugin(plugin_id)
        if plugin:
            plugin.status = "disabled"

        # 更新数据库中的状态
        config = session.query(PluginConfig).filter(
            PluginConfig.plugin_id == plugin_id
        ).first()

        if config:
            config.enabled = False
            session.commit()

        logger.info(f"插件已禁用：{plugin_id}")

    def get_plugin_config(
        self,
        session: Session,
        plugin_id: str,
    ) -> Dict[str, Any]:
        """
        获取插件配置

        Args:
            session: 数据库会话
            plugin_id: 插件 ID

        Returns:
            插件配置字典
        """
        from ..models.plugin import PluginConfig

        config = session.query(PluginConfig).filter(
            PluginConfig.plugin_id == plugin_id
        ).first()

        return config.config_data if config else {}

    def update_plugin_config(
        self,
        session: Session,
        plugin_id: str,
        config_data: Dict[str, Any],
    ) -> None:
        """
        更新插件配置

        Args:
            session: 数据库会话
            plugin_id: 插件 ID
            config_data: 新的配置数据
        """
        from ..models.plugin import PluginConfig

        config = session.query(PluginConfig).filter(
            PluginConfig.plugin_id == plugin_id
        ).first()

        if not config:
            # 获取插件类型
            plugin = plugin_registry.get_plugin(plugin_id)
            plugin_type = plugin.manifest.plugin_type.value if plugin else "unknown"

            config = PluginConfig(
                plugin_id=plugin_id,
                plugin_type=plugin_type,
                config_data=config_data,
            )
            session.add(config)
        else:
            config.config_data = config_data

        session.commit()
        logger.info(f"插件配置已更新：{plugin_id}")

    def get_plugins_by_type(
        self,
        plugin_type: PluginType,
    ) -> List[LoadedPlugin]:
        """
        获取指定类型的所有插件

        Args:
            plugin_type: 插件类型

        Returns:
            插件列表
        """
        return plugin_registry.get_plugins_by_type(plugin_type)

    def get_all_plugins(self) -> List[LoadedPlugin]:
        """
        获取所有插件

        Returns:
            插件列表
        """
        return plugin_registry.get_all_plugins()

    def get_plugin_stats(self) -> Dict[str, int]:
        """
        获取插件统计信息

        Returns:
            统计信息字典
        """
        return plugin_registry.get_plugin_count()

    def remove_repository(
        self,
        session: Session,
        repo_id: str,
    ) -> None:
        """
        删除仓库

        Args:
            session: 数据库会话
            repo_id: 仓库 ID
        """
        from ..models.plugin import PluginRepository, PluginConfig

        repo = session.get(PluginRepository, repo_id)
        if not repo:
            raise ValueError(f"仓库不存在：{repo_id}")

        # 从注册中心注销插件
        # 这里需要找到该仓库加载的所有插件并注销
        # 简化实现：只注销当前 commit 对应的插件
        if repo.current_commit:
            # 尝试加载插件以获取 ID
            try:
                loaded = plugin_loader.load_from_repo(
                    repo_url=repo.repo_url,
                    branch=repo.branch,
                    commit=repo.current_commit,
                )
                plugin_registry.unregister(loaded.manifest.id)

                # 删除插件配置
                session.query(PluginConfig).filter(
                    PluginConfig.plugin_id == loaded.manifest.id
                ).delete()

            except Exception:
                pass

        # 删除本地仓库
        plugin_loader.remove_repo(repo.repo_url)

        # 删除数据库记录
        session.delete(repo)
        session.commit()

        logger.info(f"仓库已删除：{repo.name}")

    def add_repository(
        self,
        session: Session,
        repo_url: str,
        branch: str = "main",
        name: Optional[str] = None,
        auto_update: bool = False,
    ) -> LoadedPlugin:
        """
        添加新仓库

        Args:
            session: 数据库会话
            repo_url: Git 仓库 URL
            branch: 分支名称
            name: 仓库名称（如果为 None 则从 URL 提取）
            auto_update: 是否自动更新

        Returns:
            加载的插件实例
        """
        from ..models.plugin import PluginRepository

        # 如果未提供名称，从 URL 提取
        if name is None:
            name = repo_url.split("/")[-1].replace(".git", "")

        # 加载插件
        loaded = plugin_loader.load_from_repo(
            repo_url=repo_url,
            branch=branch,
        )

        # 注册到注册中心
        plugin_registry.register_external(loaded)

        # 保存到数据库
        repo = PluginRepository(
            name=name,
            repo_url=repo_url,
            branch=branch,
            current_commit=loaded.commit_hash,
            auto_update=auto_update,
            enabled=True,
            status="loaded",
        )
        session.add(repo)
        session.commit()

        logger.info(f"仓库已添加：{name} ({repo_url})")
        return loaded


# 全局单例
plugin_manager = PluginManager()
