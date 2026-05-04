from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(frozen=True)
class CloudFile:
    id: str
    path: str
    name: str
    size: int


class CloudProvider(ABC):
    name: str

    @abstractmethod
    async def save_share(self, url: str, code: str | None, target_dir: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def list_files(self, path: str) -> list[CloudFile]:
        raise NotImplementedError

    @abstractmethod
    async def open_file_stream(self, file_id: str, offset: int = 0) -> AsyncIterator[bytes]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, path: str) -> None:
        raise NotImplementedError
