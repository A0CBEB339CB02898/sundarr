from abc import ABC, abstractmethod
from dataclasses import dataclass

from sundarr.app.schemas.search import RawSearchItem, SearchQuery


@dataclass(frozen=True)
class SourceDescriptor:
    id: str
    name: str
    source_type: str
    enabled: bool
    description: str
    legal_note: str | None = None


class BaseSource(ABC):
    id: str
    name: str
    source_type: str
    enabled: bool = True
    description: str = ""
    legal_note: str | None = None

    def describe(self) -> SourceDescriptor:
        return SourceDescriptor(
            id=self.id,
            name=self.name,
            source_type=self.source_type,
            enabled=self.enabled,
            description=self.description,
            legal_note=self.legal_note,
        )

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        raise NotImplementedError
