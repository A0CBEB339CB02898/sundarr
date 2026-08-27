"""
插件加载器

负责从 Git 仓库加载插件，支持锁定 commit、错误隔离。
"""

import importlib
import logging
import re
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .base import LoadedPlugin, PluginManifest, PluginType
from .registry import plugin_registry

logger = logging.getLogger(__name__)

_PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")
_ENTRY_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*$"
)
_SUPPORTED_PLUGIN_API_VERSION = "1.0"
_SUPPORTED_V2_PLUGIN_TYPES = {
    PluginType.SOURCE,
    PluginType.CATALOG_PROVIDER,
    PluginType.WATCHLIST_PROVIDER,
}
_IMPORT_LOCK = RLock()


class PluginLoader:
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
        # 检查仓库是否在允许列表中
        if self.allowed_repos and repo_url not in self.allowed_repos:
            raise ValueError(f"仓库不在允许列表中：{repo_url}")

        # 提取仓库名称作为目录名
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = self.repos_dir / repo_name

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

    def _clone_or_fetch(
        self,
        repo_url: str,
        branch: str,
        commit: Optional[str],
        repo_path: Path,
    ) -> str:
        """
        Clone 或 fetch Git 仓库

        Args:
            repo_url: Git 仓库 URL
            branch: 分支名称
            commit: 指定的 commit hash
            repo_path: 本地仓库路径

        Returns:
            实际使用的 commit hash

        Raises:
            subprocess.CalledProcessError: 如果 Git 命令执行失败
        """
        if not repo_path.exists():
            # Clone
            logger.info(f"克隆仓库：{repo_url}")
            subprocess.run(
                ["git", "clone", "--branch", branch, repo_url, str(repo_path)],
                check=True,
                capture_output=True,
            )
        else:
            # Fetch and checkout
            logger.info(f"更新仓库：{repo_url}")
            subprocess.run(
                ["git", "fetch"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", branch],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "pull"],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )

        # 如果指定了 commit，checkout 到该 commit
        if commit:
            logger.info(f"切换到 commit：{commit}")
            subprocess.run(
                ["git", "checkout", commit],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
            )
            return commit

        # 获取当前 commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def parse_manifests(self, repo_path: Path) -> list[PluginManifest]:
        """解析仓库中的 flat v1 或通用 v2 插件清单。"""

        repo_path = Path(repo_path).resolve()
        manifest_path = (repo_path / "sundarr_plugin.toml").resolve()
        if not manifest_path.is_relative_to(repo_path):
            raise ValueError("插件清单路径不能超出仓库目录")
        if not manifest_path.is_file():
            raise FileNotFoundError(f"插件清单文件不存在：{manifest_path}")

        with manifest_path.open("rb") as file:
            data = tomllib.load(file)

        manifest_version = data.get("manifest_version")
        if manifest_version is None:
            return [self._parse_flat_v1_manifest(data)]
        if manifest_version != 2:
            raise ValueError(f"不支持的 manifest_version：{manifest_version}")

        plugin_items = data.get("plugins")
        if not isinstance(plugin_items, list) or not plugin_items:
            raise ValueError("通用 v2 插件清单必须包含至少一个 [[plugins]] 声明")

        manifests = [self._parse_v2_manifest_item(item) for item in plugin_items]
        plugin_ids = [manifest.id for manifest in manifests]
        duplicate_ids = sorted({item for item in plugin_ids if plugin_ids.count(item) > 1})
        if duplicate_ids:
            raise ValueError(f"插件清单存在重复 plugin_id：{'、'.join(duplicate_ids)}")
        return manifests

    def _parse_manifest(self, repo_path: Path) -> PluginManifest:
        """
        兼容当前单插件加载链路。

        v2 单 Manifest 候选 Activation 已实现，但旧入口没有仓库级编排语义，仍只处理 flat v1。
        """
        manifests = self.parse_manifests(repo_path)
        if len(manifests) != 1 or manifests[0].manifest_version != 1:
            raise NotImplementedError(
                "通用 v2 必须通过候选 Activation 流程加载，旧 flat v1 入口不执行 v2"
            )
        return manifests[0]

    def _parse_flat_v1_manifest(self, data: Mapping[str, Any]) -> PluginManifest:
        self._require_manifest_fields(data, "id", "name", "version", "plugin_type", "entry")
        plugin_type = self._parse_plugin_type(data["plugin_type"])
        if plugin_type != PluginType.SOURCE:
            raise ValueError("flat v1 插件清单只支持 source 类型")

        plugin_api_version = str(data.get("adapter_api_version", "1.0"))
        self._validate_plugin_api_version(plugin_api_version)
        plugin_id = self._validate_plugin_id(data["id"])
        entry = self._validate_entry(data["entry"])
        config_schema = self._validate_mapping(data.get("config_schema", {}), "config_schema")
        dependencies = self._validate_string_list(data.get("dependencies", []), "dependencies")

        return PluginManifest(
            id=plugin_id,
            name=str(data["name"]),
            version=str(data["version"]),
            plugin_type=plugin_type,
            entry=entry,
            plugin_api_version=plugin_api_version,
            description=str(data.get("description", "")),
            author=str(data.get("author", "")),
            homepage_url=str(data.get("homepage_url", "")),
            config_schema=dict(config_schema),
            manifest_version=1,
            dependencies=dependencies,
        )

    def _parse_v2_manifest_item(self, data: Any) -> PluginManifest:
        if not isinstance(data, Mapping):
            raise ValueError("[[plugins]] 声明必须是 TOML table")
        self._require_manifest_fields(
            data,
            "id",
            "name",
            "version",
            "plugin_type",
            "plugin_api_version",
            "entry",
        )

        plugin_type = self._parse_plugin_type(data["plugin_type"])
        if plugin_type not in _SUPPORTED_V2_PLUGIN_TYPES:
            raise ValueError(f"当前版本尚不能激活插件类型：{plugin_type.value}")

        plugin_api_version = str(data["plugin_api_version"])
        self._validate_plugin_api_version(plugin_api_version)
        runtime = self._validate_mapping(data.get("runtime", {}), "runtime")
        requires = self._validate_string_list(runtime.get("requires", []), "runtime.requires")
        provides = self._validate_string_list(runtime.get("provides", []), "runtime.provides")
        if not provides:
            raise ValueError("通用 v2 插件声明必须提供至少一个 runtime.provides 能力")

        return PluginManifest(
            id=self._validate_plugin_id(data["id"]),
            name=str(data["name"]),
            version=str(data["version"]),
            plugin_type=plugin_type,
            entry=self._validate_entry(data["entry"]),
            plugin_api_version=plugin_api_version,
            description=str(data.get("description", "")),
            author=str(data.get("author", "")),
            homepage_url=str(data.get("homepage_url", "")),
            config_schema=dict(
                self._validate_mapping(data.get("config_schema", {}), "config_schema")
            ),
            manifest_version=2,
            requires=requires,
            provides=provides,
        )

    @staticmethod
    def _require_manifest_fields(data: Mapping[str, Any], *fields: str) -> None:
        for field in fields:
            if field not in data:
                raise ValueError(f"插件清单缺少必填字段：{field}")

    @staticmethod
    def _parse_plugin_type(value: Any) -> PluginType:
        try:
            return PluginType(str(value))
        except ValueError as error:
            raise ValueError(f"无效的插件类型：{value}") from error

    @staticmethod
    def _validate_plugin_id(value: Any) -> str:
        plugin_id = str(value)
        if not _PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise ValueError(f"无效的插件 id：{plugin_id}")
        return plugin_id

    @staticmethod
    def _validate_entry(value: Any) -> str:
        entry = str(value)
        if not _ENTRY_PATTERN.fullmatch(entry):
            raise ValueError(f"无效的插件 entry：{entry}")
        return entry

    @staticmethod
    def _validate_plugin_api_version(value: str) -> None:
        if value != _SUPPORTED_PLUGIN_API_VERSION:
            raise ValueError(f"不支持的 plugin_api_version：{value}")

    @staticmethod
    def _validate_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ValueError(f"插件清单字段 {field_name} 必须是 TOML table")
        return value

    @staticmethod
    def _validate_string_list(value: Any, field_name: str) -> list[str]:
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(f"插件清单字段 {field_name} 必须是非空字符串数组")
        if len(value) != len(set(value)):
            raise ValueError(f"插件清单字段 {field_name} 不能包含重复值")
        return list(value)

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


    def update_repo(
        self,
        repo_url: str,
        branch: str = "main",
        new_commit: Optional[str] = None,
    ) -> str:
        """
        更新仓库到最新或指定 commit

        Args:
            repo_url: Git 仓库 URL
            branch: 分支名称
            new_commit: 新的 commit hash（如果为 None 则更新到最新）

        Returns:
            新的 commit hash
        """
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = self.repos_dir / repo_name

        if not repo_path.exists():
            raise FileNotFoundError(f"仓库不存在：{repo_path}")

        return self._clone_or_fetch(repo_url, branch, new_commit, repo_path)

    def remove_repo(self, repo_url: str) -> bool:
        """
        删除本地仓库

        Args:
            repo_url: Git 仓库 URL

        Returns:
            是否成功删除
        """
        import shutil

        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = self.repos_dir / repo_name

        if repo_path.exists():
            shutil.rmtree(repo_path)
            logger.info(f"已删除仓库：{repo_path}")
            return True

        return False

    def list_repos(self) -> List[Dict[str, str]]:
        """
        列出所有本地仓库

        Returns:
            仓库信息列表
        """
        repos = []

        for repo_dir in self.repos_dir.iterdir():
            if not repo_dir.is_dir():
                continue

            # 获取仓库 URL
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                repo_url = result.stdout.strip()
            except subprocess.CalledProcessError:
                repo_url = "unknown"

            # 获取当前 commit
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commit = result.stdout.strip()
            except subprocess.CalledProcessError:
                commit = "unknown"

            repos.append({
                "name": repo_dir.name,
                "path": str(repo_dir),
                "url": repo_url,
                "commit": commit,
            })

        return repos


# 全局单例
plugin_loader = PluginLoader()
