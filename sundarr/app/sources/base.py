from dataclasses import dataclass, field
from collections.abc import Awaitable, Callable
from typing import Any

from sundarr.app.schemas.search import RawSearchItem, SearchQuery

SearchFunction = Callable[[SearchQuery], Awaitable[list[RawSearchItem]]]
FetchDetailFunction = Callable[[str], Awaitable[RawSearchItem | None]]
SourceTestFunction = Callable[[SearchQuery], Awaitable["SourceTestExecution"]]


@dataclass(frozen=True)
class SourceTestEvent:
    step: str
    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceTestExecution:
    items: list[RawSearchItem]
    logs: list[SourceTestEvent]


@dataclass(frozen=True)
class SourceModel:
    id: str
    name: str
    description: str
    homepage_url: str
    search_function: SearchFunction
    test_function: SourceTestFunction | None = None
    fetch_detail_function: FetchDetailFunction | None = None
