from datetime import UTC, datetime

from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import BaseSource


class ExampleSource(BaseSource):
    id = "example_source"
    name = "示例媒体源"
    source_type = "code"
    enabled = True

    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        if query.keyword.lower() not in {"interstellar", "星际穿越"}:
            return []

        return [
            RawSearchItem(
                source_id=self.id,
                source_type=self.source_type,
                raw_title="星际穿越 Interstellar 2014 1080p",
                raw_url="https://example.invalid/detail/interstellar",
                raw_content="夸克：https://pan.example.invalid/s/interstellar 提取码：1234",
                fetched_at=datetime.now(UTC),
                metadata={"quality": "1080p", "year": 2014, "type": "movie"},
            )
        ]
