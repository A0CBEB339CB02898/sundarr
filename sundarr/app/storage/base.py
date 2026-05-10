from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageWriter(ABC):
    name: str

    @abstractmethod
    async def exists(self, path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def size(self, path: str) -> int:
        raise NotImplementedError

    @abstractmethod
    async def mkdirs(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def open_append(self, path: str) -> BinaryIO:
        raise NotImplementedError

    @abstractmethod
    async def open_read(self, path: str, offset: int = 0) -> BinaryIO:
        raise NotImplementedError

    @abstractmethod
    async def rename(self, src: str, dst: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_empty_dir(self, path: str) -> None:
        raise NotImplementedError

    async def truncate(self, path: str, size: int = 0) -> None:
        """Truncate an existing file to ``size`` bytes. Default clears the file."""
        raise NotImplementedError
