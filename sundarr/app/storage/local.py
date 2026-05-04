import shutil
from pathlib import Path
from typing import BinaryIO

from sundarr.app.storage.base import StorageWriter


class LocalWriter(StorageWriter):
    name = "local"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def exists(self, path: str) -> bool:
        return self._resolve_path(path).exists()

    async def size(self, path: str) -> int:
        target = self._resolve_path(path)
        if not target.exists() or not target.is_file():
            raise ValueError("STORAGE_PATH_NOT_FOUND")
        return target.stat().st_size

    async def mkdirs(self, path: str) -> None:
        self._resolve_path(path).mkdir(parents=True, exist_ok=True)

    async def open_append(self, path: str) -> BinaryIO:
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target.open("ab")

    async def rename(self, src: str, dst: str) -> None:
        source = self._resolve_path(src)
        target = self._resolve_path(dst)
        if target.exists():
            raise ValueError("TARGET_EXISTS")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.replace(target)

    async def remove(self, path: str) -> None:
        target = self._resolve_path(path)
        if target == self.root:
            raise ValueError("STORAGE_REMOVE_ROOT_FORBIDDEN")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

    def _resolve_path(self, path: str) -> Path:
        relative = path.strip().replace("\\", "/").strip("/")
        resolved = (self.root / relative).resolve()
        if not self._is_relative_to(resolved, self.root):
            raise ValueError("STORAGE_PATH_OUTSIDE_ROOT")
        return resolved

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
