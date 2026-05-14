from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from sundarr.app.schemas.search import RawSearchItem, SearchQuery

SearchFunction = Callable[[SearchQuery], Awaitable[list[RawSearchItem]]]


@dataclass(frozen=True)
class SourceModel:
    id: str
    name: str
    description: str
    search_function: SearchFunction
