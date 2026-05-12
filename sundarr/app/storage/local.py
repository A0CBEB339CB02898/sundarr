import hashlib
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

    async def open_read(self, path: str, offset: int = 0) -> BinaryIO:
        target = self._resolve_path(path)
        if not target.exists() or not target.is_file():
            raise ValueError("STORAGE_PATH_NOT_FOUND")
        handle = target.open("rb")
        if offset:
            handle.seek(offset)
        return handle

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

    async def remove_empty_dir(self, path: str) -> None:
        target = self._resolve_path(path)
        if target == self.root:
            raise ValueError("STORAGE_REMOVE_ROOT_FORBIDDEN")
        target.rmdir()

    async def truncate(self, path: str, size: int = 0) -> None:
        target = self._resolve_path(path)
        if not target.exists():
            return
        with target.open("r+b") as handle:
            handle.truncate(max(0, int(size)))

    async def checksum_md5(self, path: str) -> str:
        target = self._resolve_path(path)
        if not target.exists() or not target.is_file():
            raise ValueError("STORAGE_PATH_NOT_FOUND")
        digest = hashlib.md5(usedforsecurity=False)
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

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
