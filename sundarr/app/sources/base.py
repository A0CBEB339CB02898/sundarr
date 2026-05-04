from abc import ABC, abstractmethod

from sundarr.app.schemas.search import RawSearchItem, SearchQuery


class BaseSource(ABC):
    id: str
    name: str
    source_type: str
    enabled: bool = True

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        raise NotImplementedError
