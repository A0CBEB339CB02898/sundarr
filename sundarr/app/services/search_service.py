import asyncio
import hashlib
import re
from collections.abc import Iterable

from sundarr.app.parsers import extract_cloud_links
from sundarr.app.schemas.search import (
    RawSearchItem,
    ResourceCandidate,
    ResourceLinkResult,
    SearchQuery,
    SearchResponse,
)
from sundarr.app.sources import BaseSource, ExampleSource

TITLE_TAG_PATTERN = re.compile(r"\b(720p|1080p|2160p|4k|bluray|web-dl)\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")


class SearchService:
    def __init__(self, sources: Iterable[BaseSource] | None = None) -> None:
        self.sources = list(sources) if sources is not None else [ExampleSource()]
        self._resource_cache: dict[str, ResourceCandidate] = {}

    async def search(self, query: SearchQuery) -> SearchResponse:
        raw_items = await self._collect_raw_items(query)
        candidates = [self._normalize(item, query) for item in raw_items]
        deduped = self._dedupe(candidates)
        ranked = sorted(deduped, key=lambda item: item.score, reverse=True)[: query.limit]
        self._resource_cache.update({item.id: item for item in ranked})
        return SearchResponse(query=query.keyword, count=len(ranked), results=ranked)

    def get_resource(self, resource_id: str) -> ResourceCandidate | None:
        return self._resource_cache.get(resource_id)

    async def _collect_raw_items(self, query: SearchQuery) -> list[RawSearchItem]:
        enabled_sources = [source for source in self.sources if source.enabled]
        results = await asyncio.gather(
            *(self._safe_search(source, query) for source in enabled_sources),
            return_exceptions=False,
        )
        return [item for group in results for item in group]

    async def _safe_search(self, source: BaseSource, query: SearchQuery) -> list[RawSearchItem]:
        try:
            return await asyncio.wait_for(source.search(query), timeout=10)
        except Exception:
            return []

    def _normalize(self, item: RawSearchItem, query: SearchQuery) -> ResourceCandidate:
        links = extract_cloud_links(item.raw_content)
        title = self._clean_title(item.raw_title)
        year = self._extract_year(item, query)
        media_type = item.metadata.get("type") or query.type
        quality = item.metadata.get("quality") or self._extract_quality(item.raw_title)
        result_links = [
            ResourceLinkResult(
                id=self._stable_id(link.provider, link.url),
                provider=link.provider,
                url=link.url,
                code=link.code,
            )
            for link in links
        ]

        score = 0.4
        if query.keyword.lower() in item.raw_title.lower():
            score += 0.3
        if year and query.year == year:
            score += 0.1
        if result_links:
            score += 0.2

        return ResourceCandidate(
            id=self._stable_id(title, str(year), item.source_id),
            title=title,
            normalized_title=self._normalize_title(title),
            original_title=item.raw_title,
            type=media_type,
            year=year,
            quality=quality,
            score=round(score, 4),
            explanation="基于标题、年份和链接可用性生成基础评分。",
            source_id=item.source_id,
            source_url=item.raw_url,
            links=result_links,
        )

    def _dedupe(self, candidates: list[ResourceCandidate]) -> list[ResourceCandidate]:
        merged: dict[tuple[str, int | None, str], ResourceCandidate] = {}
        for candidate in candidates:
            key = (candidate.normalized_title, candidate.year, candidate.type)
            existing = merged.get(key)
            if existing is None:
                merged[key] = candidate
                continue
            existing_links = {link.url for link in existing.links}
            existing.links.extend(link for link in candidate.links if link.url not in existing_links)
            existing.score = max(existing.score, candidate.score)
        return list(merged.values())

    def _clean_title(self, raw_title: str) -> str:
        title = TITLE_TAG_PATTERN.sub("", raw_title)
        title = YEAR_PATTERN.sub("", title)
        return " ".join(title.split())

    def _normalize_title(self, title: str) -> str:
        return re.sub(r"\W+", "", title).lower()

    def _extract_year(self, item: RawSearchItem, query: SearchQuery) -> int | None:
        if isinstance(item.metadata.get("year"), int):
            return item.metadata["year"]
        match = YEAR_PATTERN.search(item.raw_title)
        return int(match.group(1)) if match else query.year

    def _extract_quality(self, raw_title: str) -> str | None:
        match = TITLE_TAG_PATTERN.search(raw_title)
        return match.group(1) if match else None

    def _stable_id(self, *parts: str | None) -> str:
        value = "|".join(part or "" for part in parts)
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


search_service = SearchService()
