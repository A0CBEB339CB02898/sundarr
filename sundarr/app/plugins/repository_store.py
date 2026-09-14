"""插件 Git 仓库缓存、定位和清理。"""

from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)


def validate_repository_url(repo_url: str) -> str:
    """拒绝把 HTTP Git 凭据嵌入持久化仓库地址。"""

    value = repo_url.strip()
    if not value:
        raise ValueError("插件仓库 URL 不能为空")
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and (parsed.username or parsed.password):
        raise ValueError("插件仓库 URL 不能包含用户名、密码或访问令牌")
    return value


def redact_repository_url(repo_url: str) -> str:
    """兼容展示历史数据，但绝不回显 URL 中可能存在的凭据。"""

    parsed = urlsplit(repo_url)
    if parsed.scheme not in {"http", "https"} or not (parsed.username or parsed.password):
        return repo_url
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    port = f":{parsed.port}" if parsed.port else ""
    return urlunsplit((parsed.scheme, f"{hostname}{port}", parsed.path, parsed.query, parsed.fragment))


class PluginRepositoryStore:
    """只负责插件仓库的 Git 生命周期，不解析或执行插件代码。"""

    repos_dir: Path

    def repository_path(self, repo_url: str) -> Path:
        normalized_url = repo_url.rstrip("/\\").replace("\\", "/")
        repo_name = normalized_url.rsplit("/", 1)[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        repo_name = re.sub(r"[^A-Za-z0-9._-]+", "-", repo_name).strip(".-")
        if not repo_name or repo_name in {".", ".."}:
            raise ValueError("无法从仓库 URL 推导本地目录")
        legacy_path = self.repos_dir / repo_name
        if legacy_path.is_dir():
            try:
                remote = subprocess.run(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=str(legacy_path), capture_output=True, text=True, check=True,
                ).stdout.strip()
                if remote == repo_url:
                    return legacy_path
            except subprocess.CalledProcessError:
                pass
        digest = hashlib.sha256(repo_url.encode("utf-8")).hexdigest()[:12]
        return self.repos_dir / f"{repo_name[:32]}-{digest}"

    def _clone_or_fetch(
        self, repo_url: str, branch: str, commit: Optional[str], repo_path: Path,
    ) -> str:
        if not repo_path.exists():
            logger.info("克隆插件仓库：%s", repo_path.name)
            subprocess.run(
                ["git", "clone", "--branch", branch, repo_url, str(repo_path)],
                check=True, capture_output=True,
            )
        else:
            logger.info("更新插件仓库：%s", repo_path.name)
            subprocess.run(["git", "fetch"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(["git", "checkout", branch], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(["git", "pull"], cwd=str(repo_path), check=True, capture_output=True)
        if commit:
            logger.info("切换到 commit：%s", commit)
            subprocess.run(["git", "checkout", commit], cwd=str(repo_path), check=True, capture_output=True)
            return self._current_commit(repo_path)
        return self._current_commit(repo_path)

    @staticmethod
    def _current_commit(repo_path: Path) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_path), capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    @staticmethod
    def _resolve_commit(repo_path: Path, commit: str) -> str:
        result = subprocess.run(
            ["git", "rev-parse", commit], cwd=str(repo_path), capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    def update_repo(self, repo_url: str, branch: str = "main", new_commit: Optional[str] = None) -> str:
        repo_path = self.repository_path(repo_url)
        if not repo_path.exists():
            raise FileNotFoundError(f"仓库不存在：{repo_path}")
        return self._clone_or_fetch(repo_url, branch, new_commit, repo_path)

    def remove_repo(self, repo_url: str) -> bool:
        import os
        import shutil
        import stat

        repo_path = self.repository_path(repo_url)
        if not repo_path.exists():
            return False
        resolved_root = self.repos_dir.resolve()
        resolved_repo = repo_path.resolve()
        if resolved_repo == resolved_root or not resolved_repo.is_relative_to(resolved_root):
            raise ValueError("拒绝删除插件缓存根目录之外的路径")

        def make_writable_and_retry(function, path, error):
            if not isinstance(error, PermissionError):
                raise error
            os.chmod(path, stat.S_IWRITE)
            function(path)

        shutil.rmtree(resolved_repo, onexc=make_writable_and_retry)
        logger.info("已删除仓库：%s", repo_path)
        return True

    def list_repos(self) -> List[Dict[str, str]]:
        repos: list[dict[str, str]] = []
        for repo_dir in self.repos_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            try:
                repo_url = subprocess.run(
                    ["git", "remote", "get-url", "origin"], cwd=str(repo_dir),
                    capture_output=True, text=True, check=True,
                ).stdout.strip()
            except subprocess.CalledProcessError:
                repo_url = "unknown"
            try:
                commit = self._current_commit(repo_dir)
            except subprocess.CalledProcessError:
                commit = "unknown"
            repos.append({"name": repo_dir.name, "path": str(repo_dir), "url": repo_url, "commit": commit})
        return repos
