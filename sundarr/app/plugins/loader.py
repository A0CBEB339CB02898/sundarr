"""
插件加载器

负责从 Git 仓库加载插件，支持锁定 commit、错误隔离。
"""

import importlib
import logging
import subprocess
import sys
from pathlib import Path
from threading import RLock
from typing import Any, Callable, List, Optional

from .base import LoadedPlugin, PluginManifest, PluginType
from .manifest_parser import PluginManifestParser
from .repository_store import (
    PluginRepositoryStore,
    redact_repository_url,  # noqa: F401 - 保留既有公开导入路径
    validate_repository_url,
)

logger = logging.getLogger(__name__)

_IMPORT_LOCK = RLock()


class PluginLoader(PluginRepositoryStore, PluginManifestParser):
    """
    插件加载器

    负责从 Git 仓库加载插件，支持：
    - Clone 或 fetch 仓库
    - 解析插件清单（sundarr_plugin.toml）
    - 动态导入模块
    - 创建插件实例
    - 错误隔离（单个插件加载失败不影响其他插件）

    使用方式：
        from sundarr.app.plugins.loader import plugin_loader

        # 从 Git 仓库加载插件
        loaded = plugin_loader.load_from_repo(
            repo_url="https://github.com/user/quark-provider.git",
            branch="main",
            commit="abc123"
        )

        # 注册到注册中心
        plugin_registry.register_external(loaded)
    """

    def __init__(
        self,
        repos_dir: Optional[Path] = None,
        allowed_repos: Optional[List[str]] = None,
    ):
        """
        初始化插件加载器

        Args:
            repos_dir: 本地仓库目录（默认为 ~/.sundarr/plugins/repos）
            allowed_repos: 允许的仓库 URL 列表（如果为空则不限制）
        """
        if repos_dir is None:
            repos_dir = Path.home() / ".sundarr" / "plugins" / "repos"

        self.repos_dir = Path(repos_dir)
        self.repos_dir.mkdir(parents=True, exist_ok=True)

        self.allowed_repos = allowed_repos or []

    def load_from_repo(
        self,
        repo_url: str,
        branch: str = "main",
        commit: Optional[str] = None,
    ) -> LoadedPlugin | list[LoadedPlugin]:
        """
        从 Git 仓库加载插件

        对于 SOURCE 类型且入口函数返回 list[SourceModel] 的仓库，
        会自动展开为多个 LoadedPlugin，每个 SourceModel 一个。

        Args:
            repo_url: Git 仓库 URL
            branch: 分支名称（默认为 "main"）
            commit: 指定的 commit hash（如果为 None 则使用最新）

        Returns:
            单个已加载插件实例，或展开后的插件列表

        Raises:
            ValueError: 如果仓库不在允许列表中
            FileNotFoundError: 如果插件清单文件不存在
            ImportError: 如果模块导入失败
        """
        repo_url = validate_repository_url(repo_url)
        # 检查仓库是否在允许列表中
        if self.allowed_repos and repo_url not in self.allowed_repos:
            raise ValueError(f"仓库不在允许列表中：{repo_url}")

        repo_path = self.repository_path(repo_url)

        # Clone 或 fetch 仓库
        actual_commit = self._clone_or_fetch(repo_url, branch, commit, repo_path)

        # 解析清单
        manifest = self._parse_manifest(repo_path)

        # 加载模块
        module, instance = self._load_plugin(manifest, repo_path)

        # 创建已加载插件实例
        loaded = LoadedPlugin(
            manifest=manifest,
            module=module,
            instance=instance,
            status="loaded",
            commit_hash=actual_commit,
            repo_path=str(repo_path),
        )

        # 对于 SOURCE 类型返回 list 的仓库，展开为多个独立插件
        if manifest.plugin_type == PluginType.SOURCE and isinstance(instance, list):
            expanded: list[LoadedPlugin] = []
            for source in instance:
                source_manifest = PluginManifest(
                    id=source.id,
                    name=source.name,
                    version=manifest.version,
                    plugin_type=PluginType.SOURCE,
                    description=source.description,
                    author=manifest.author,
                    homepage_url=source.homepage_url,
                    plugin_api_version=manifest.plugin_api_version,
                    entry=manifest.entry,
                    config_schema=manifest.config_schema,
                )
                expanded.append(LoadedPlugin(
                    manifest=source_manifest,
                    module=module,
                    instance=source,
                    status="loaded",
                    commit_hash=actual_commit,
                    repo_path=str(repo_path),
                ))
            logger.info(
                f"插件仓库加载成功：{manifest.name} ({manifest.id})，展开 {len(expanded)} 个搜索源"
            )
            return expanded

        logger.info(f"插件加载成功：{manifest.name} ({manifest.id})")
        return loaded

    def prepare_repository(
        self,
        repo_url: str,
        branch: str = "main",
        commit: Optional[str] = None,
        *,
        fetch: bool = True,
    ) -> tuple[Path, str]:
        """准备仓库工作目录；启动恢复可禁止网络 fetch 并只切换锁定 commit。"""

        repo_url = validate_repository_url(repo_url)
        if self.allowed_repos and repo_url not in self.allowed_repos:
            raise ValueError(f"仓库不在允许列表中：{repo_url}")
        repo_path = self.repository_path(repo_url)
        if fetch:
            actual_commit = self._clone_or_fetch(repo_url, branch, commit, repo_path)
        else:
            if not commit:
                raise ValueError("离线恢复必须指定锁定 commit")
            if not repo_path.is_dir():
                raise FileNotFoundError(f"插件仓库本地缓存不存在：{repo_path}")
            subprocess.run(
                ["git", "checkout", "--detach", commit],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            actual_commit = self._current_commit(repo_path)
            if actual_commit != self._resolve_commit(repo_path, commit):
                raise RuntimeError("插件仓库未能恢复到锁定 commit")
        return repo_path, actual_commit

    def invalidate_repository_modules(self, repo_path: Path) -> None:
        """丢弃该仓库的导入缓存，使候选版本重新执行仓库代码。"""

        resolved_repo = Path(repo_path).resolve()
        with _IMPORT_LOCK:
            stale_names: list[str] = []
            for module_name, module in tuple(sys.modules.items()):
                module_file = getattr(module, "__file__", None)
                if not module_file:
                    continue
                try:
                    if Path(module_file).resolve().is_relative_to(resolved_repo):
                        stale_names.append(module_name)
                except (OSError, ValueError):
                    continue
            for module_name in stale_names:
                sys.modules.pop(module_name, None)
            importlib.invalidate_caches()

    def load_from_local(
        self,
        local_path: Path,
    ) -> LoadedPlugin | list[LoadedPlugin]:
        """
        从本地目录加载插件

        主要用于开发和测试。

        Args:
            local_path: 本地插件目录路径

        Returns:
            单个已加载插件实例，或展开后的插件列表

        Raises:
            FileNotFoundError: 如果插件清单文件不存在
            ImportError: 如果模块导入失败
        """
        local_path = Path(local_path)

        if not local_path.exists():
            raise FileNotFoundError(f"本地插件目录不存在：{local_path}")

        # 解析清单
        manifest = self._parse_manifest(local_path)

        # 加载模块
        module, instance = self._load_plugin(manifest, local_path)

        # 创建已加载插件实例
        loaded = LoadedPlugin(
            manifest=manifest,
            module=module,
            instance=instance,
            status="loaded",
            repo_path=str(local_path),
        )

        # 对于 SOURCE 类型返回 list 的仓库，展开为多个独立插件
        if manifest.plugin_type == PluginType.SOURCE and isinstance(instance, list):
            expanded: list[LoadedPlugin] = []
            for source in instance:
                source_manifest = PluginManifest(
                    id=source.id,
                    name=source.name,
                    version=manifest.version,
                    plugin_type=PluginType.SOURCE,
                    description=source.description,
                    author=manifest.author,
                    homepage_url=source.homepage_url,
                    plugin_api_version=manifest.plugin_api_version,
                    entry=manifest.entry,
                    config_schema=manifest.config_schema,
                )
                expanded.append(LoadedPlugin(
                    manifest=source_manifest,
                    module=module,
                    instance=source,
                    status="loaded",
                    repo_path=str(local_path),
                ))
            logger.info(
                f"本地插件加载成功：{manifest.name} ({manifest.id})，展开 {len(expanded)} 个搜索源"
            )
            return expanded

        logger.info(f"插件加载成功：{manifest.name} ({manifest.id})")
        return loaded

    def _load_plugin(
        self,
        manifest: PluginManifest,
        repo_path: Path,
    ) -> tuple[Any, Any]:
        """
        动态导入模块并创建插件实例

        Args:
            manifest: 插件清单
            repo_path: 仓库路径

        Returns:
            (module, instance) 元组

        Raises:
            ImportError: 如果模块导入失败
            AttributeError: 如果入口函数不存在
        """
        try:
            module, entry_func = self.load_entry(manifest, repo_path)

            # 调用入口函数创建实例
            instance = entry_func()

            # 验证实例类型
            instance = self._normalize_instance(instance, manifest.plugin_type)

            return module, instance

        except Exception as e:
            logger.error(f"加载插件失败：{manifest.name} - {e}")
            raise

    def load_entry(
        self,
        manifest: PluginManifest,
        repo_path: Path,
    ) -> tuple[Any, Callable[..., Any]]:
        """从仓库内导入并校验 Manifest 入口，但不调用入口函数。"""

        repo_path = Path(repo_path).resolve()
        module_path, function_name = manifest.entry.split(":")
        repo_path_text = str(repo_path)

        with _IMPORT_LOCK:
            sys.path.insert(0, repo_path_text)
            try:
                importlib.invalidate_caches()
                existing = sys.modules.get(module_path)
                existing_file = getattr(existing, "__file__", None)
                if existing_file:
                    try:
                        belongs_to_repository = Path(existing_file).resolve().is_relative_to(repo_path)
                    except (OSError, ValueError):
                        belongs_to_repository = False
                    if not belongs_to_repository:
                        root_name = module_path.split(".", 1)[0]
                        for name in tuple(sys.modules):
                            if name == root_name or name.startswith(f"{root_name}."):
                                sys.modules.pop(name, None)
                module = importlib.import_module(module_path)
                module_file = getattr(module, "__file__", None)
                if module_file is None:
                    raise ImportError(f"插件入口模块没有可验证的文件路径：{module_path}")
                resolved_module_file = Path(module_file).resolve()
                if not resolved_module_file.is_relative_to(repo_path):
                    raise ImportError(
                        f"插件入口模块不在仓库目录内：{resolved_module_file}"
                    )
                entry_func = getattr(module, function_name)
                if not callable(entry_func):
                    raise TypeError(f"插件入口不可调用：{manifest.entry}")
                return module, entry_func
            finally:
                if repo_path_text in sys.path:
                    sys.path.remove(repo_path_text)

    def _normalize_instance(self, instance: Any, plugin_type: PluginType) -> Any:
        """
        校验并规范化插件实例。

        Args:
            instance: 插件实例
            plugin_type: 插件类型

        Returns:
            规范化后的实例（SOURCE 类型统一为 list[SourceModel]）
        """

        if plugin_type == PluginType.SOURCE:
            from ..sources.base import SourceModel

            if isinstance(instance, SourceModel):
                return [instance]
            if isinstance(instance, list):
                if not all(isinstance(item, SourceModel) for item in instance):
                    raise TypeError("SOURCE 插件返回的列表必须全部为 SourceModel 实例")
                return instance
            raise TypeError(
                f"SOURCE 插件入口函数必须返回 SourceModel 或 list[SourceModel]，"
                f"实际返回 {type(instance).__name__}"
            )

        if instance is None:
            raise TypeError("插件实例不能为 None")

        return instance
# 全局单例
plugin_loader = PluginLoader()
