import shutil
from pathlib import Path
from typing import AsyncIterator

from sundarr.app.cloud.base import CloudFile, CloudProvider


class LocalCloudProvider(CloudProvider):
    name = "local"

    def __init__(self, staging_root: Path, share_root: Path, chunk_size: int = 1024 * 1024) -> None:
        self.staging_root = staging_root.resolve()
        self.share_root = share_root.resolve()
        self.chunk_size = chunk_size
        self.staging_root.mkdir(parents=True, exist_ok=True)
        self.share_root.mkdir(parents=True, exist_ok=True)

    async def save_share(self, url: str, code: str | None, target_dir: str) -> str:
        source_path = self._resolve_share_url(url)
        target_path = self._resolve_staging_path(target_dir)
        if target_path.exists():
            shutil.rmtree(target_path)
        target_path.mkdir(parents=True, exist_ok=True)

        if source_path.is_dir():
            for child in source_path.iterdir():
                destination = target_path / child.name
                if child.is_dir():
                    shutil.copytree(child, destination)
                else:
                    shutil.copy2(child, destination)
        else:
            shutil.copy2(source_path, target_path / source_path.name)

        return self._to_cloud_path(target_path)

    async def list_files(self, path: str) -> list[CloudFile]:
        root = self._resolve_staging_path(path)
        if not root.exists():
            return []

        files: list[CloudFile] = []
        for file_path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative_path = file_path.relative_to(self.staging_root).as_posix()
            files.append(
                CloudFile(
                    id=relative_path,
                    path=f"/{relative_path}",
                    name=file_path.name,
                    size=file_path.stat().st_size,
                )
            )
        return files

    async def open_file_stream(self, file_id: str, offset: int = 0) -> AsyncIterator[bytes]:
        file_path = self._resolve_staging_path(file_id)
        with file_path.open("rb") as file:
            file.seek(offset)
            while chunk := file.read(self.chunk_size):
                yield chunk

    async def delete(self, path: str) -> None:
        target_path = self._resolve_staging_path(path)
        if target_path == self.staging_root:
            raise ValueError("CLOUD_STAGING_DELETE_ROOT_FORBIDDEN")
        if target_path.is_dir():
            shutil.rmtree(target_path)
        elif target_path.exists():
            target_path.unlink()

    def _resolve_share_url(self, url: str) -> Path:
        prefix = "local://"
        if not url.startswith(prefix):
            raise ValueError("LOCAL_SHARE_URL_INVALID")
        relative = url[len(prefix) :].strip("/")
        path = (self.share_root / relative).resolve()
        if not self._is_relative_to(path, self.share_root):
            raise ValueError("LOCAL_SHARE_PATH_OUTSIDE_ROOT")
        if not path.exists():
            raise ValueError("LOCAL_SHARE_NOT_FOUND")
        return path

    def _resolve_staging_path(self, path: str) -> Path:
        relative = path.strip("/")
        if relative == "Sundarr/_staging":
            relative = ""
        elif relative.startswith("Sundarr/_staging/"):
            relative = relative.removeprefix("Sundarr/_staging/")
        resolved = (self.staging_root / relative).resolve()
        if not self._is_relative_to(resolved, self.staging_root):
            raise ValueError("CLOUD_STAGING_PATH_OUTSIDE_ROOT")
        return resolved

    def _to_cloud_path(self, path: Path) -> str:
        relative = path.relative_to(self.staging_root).as_posix()
        return f"/Sundarr/_staging/{relative}"

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
