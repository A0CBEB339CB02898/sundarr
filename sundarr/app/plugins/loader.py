"""
插件加载器

负责从 Git 仓库加载插件，支持锁定 commit、错误隔离。
"""

import importlib
import logging
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .base import LoadedPlugin, PluginManifest, PluginType
from .registry import plugin_registry

logger = logging.getLogger(__name__)


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
    ) -> LoadedPlugin:
        """
        从 Git 仓库加载插件

        Args:
            repo_url: Git 仓库 URL
            branch: 分支名称（默认为 "main"）
            commit: 指定的 commit hash（如果为 None 则使用最新）

        Returns:
            已加载的插件实例

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

        logger.info(f"插件加载成功：{manifest.name} ({manifest.id})")
        return loaded

    def load_from_local(
        self,
        local_path: Path,
    ) -> LoadedPlugin:
        """
        从本地目录加载插件

        主要用于开发和测试。

        Args:
            local_path: 本地插件目录路径

        Returns:
            已加载的插件实例

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

    def _parse_manifest(self, repo_path: Path) -> PluginManifest:
        """
        解析插件清单文件（sundarr_plugin.toml）

        Args:
            repo_path: 仓库路径

        Returns:
            插件清单对象

        Raises:
            FileNotFoundError: 如果清单文件不存在
            ValueError: 如果清单格式错误
        """
        manifest_path = repo_path / "sundarr_plugin.toml"

        if not manifest_path.exists():
            raise FileNotFoundError(f"插件清单文件不存在：{manifest_path}")

        with open(manifest_path, "rb") as f:
            data = tomllib.load(f)

        # 验证必填字段
        required_fields = [
            "id",
            "name",
            "version",
            "plugin_type",
            "entry",
        ]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"插件清单缺少必填字段：{field}")

        # 解析插件类型
        try:
            plugin_type = PluginType(data["plugin_type"])
        except ValueError:
            raise ValueError(f"无效的插件类型：{data['plugin_type']}")

        return PluginManifest(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            plugin_type=plugin_type,
            description=data.get("description", ""),
            author=data.get("author", ""),
            homepage_url=data.get("homepage_url", ""),
            adapter_api_version=data.get("adapter_api_version", "1.0"),
            entry=data["entry"],
            config_schema=data.get("config_schema", {}),
            dependencies=data.get("dependencies", []),
        )

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
        module_path, function_name = manifest.entry.split(":")

        # 将仓库路径添加到 sys.path
        sys.path.insert(0, str(repo_path))

        try:
            # 导入模块
            module = importlib.import_module(module_path)

            # 获取入口函数
            entry_func = getattr(module, function_name)

            # 调用入口函数创建实例
            instance = entry_func()

            # 验证实例类型
            self._validate_instance(instance, manifest.plugin_type)

            return module, instance

        except Exception as e:
            logger.error(f"加载插件失败：{manifest.name} - {e}")
            raise

        finally:
            # 从 sys.path 中移除仓库路径
            if str(repo_path) in sys.path:
                sys.path.remove(str(repo_path))

    def _validate_instance(self, instance: Any, plugin_type: PluginType) -> None:
        """
        验证插件实例是否符合其类型的接口规范

        Args:
            instance: 插件实例
            plugin_type: 插件类型

        Raises:
            TypeError: 如果实例类型不匹配
        """
        # 基本验证：实例不能为 None
        if instance is None:
            raise TypeError("插件实例不能为 None")

        # 对于 Source 类型，验证是否为 SourceModel 或返回 SourceModel 的 callable
        if plugin_type == PluginType.SOURCE:
            # SourceModel 是 frozen dataclass，直接检查类型
            # 这里只做基本检查，具体验证在使用时进行
            pass

        # 对于其他类型，后续阶段再实现具体验证
        # 当前阶段只做基本检查

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
