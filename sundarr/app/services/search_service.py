import asyncio
import hashlib
import re
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sundarr.app.parsers import extract_cloud_links
from sundarr.app.schemas.search import (
    RawSearchItem,
    ResourceCandidate,
    ResourceLinkResult,
    SearchQuery,
    SearchResponse,
    SourceSearchResult,
)
from sundarr.app.services.link_validator import LinkValidator, link_validator
from sundarr.app.sources import SourceModel, get_registered_sources
from sundarr.app.sources.utils import clean_title, generate_link_name


class SearchService:
    def __init__(self, sources: Iterable[SourceModel] | None = None, validator: LinkValidator | None = None) -> None:
        self.sources = list(sources) if sources is not None else None
        self.validator = validator or link_validator

    def _get_sources(self) -> list[SourceModel]:
        return list(self.sources) if self.sources is not None else get_registered_sources()

    async def search(self, query: SearchQuery) -> SearchResponse:
        sources = self._get_sources()
        raw_items_by_source, errors_by_source = await self._collect_raw_items(query)
        raw_items = [item for group in raw_items_by_source.values() for item in group]
        candidates = [candidate for item in raw_items if (candidate := self._normalize(item, query)) is not None]
        deduped = self._dedupe(candidates)
        ranked = sorted(deduped, key=lambda item: self._score_candidate(item, query), reverse=True)[: query.limit]
        source_results = []
        for source in sources:
            source_candidates = [
                candidate
                for item in raw_items_by_source.get(source.id, [])
                if (candidate := self._normalize(item, query)) is not None
            ]
            source_ranked = sorted(self._dedupe(source_candidates), key=lambda item: self._score_candidate(item, query), reverse=True)[: query.limit]
            source_results.append(
                SourceSearchResult(
                    source_id=source.id,
                    source_name=source.name,
                    count=len(source_ranked),
                    results=source_ranked,
                    error=errors_by_source.get(source.id),
                )
            )
        await self._validate_links([*ranked, *(item for group in source_results for item in group.results)])
        return SearchResponse(query=query.keyword, count=len(ranked), results=ranked, source_results=source_results)

    async def _collect_raw_items(self, query: SearchQuery) -> tuple[dict[str, list[RawSearchItem]], dict[str, str]]:
        sources = self._get_sources()
        results = await asyncio.gather(
            *(self._safe_search(source, query) for source in sources),
            return_exceptions=False,
        )
        items_by_source: dict[str, list[RawSearchItem]] = {}
        errors_by_source: dict[str, str] = {}
        for source_id, items, error in results:
            items_by_source[source_id] = items
            if error:
                errors_by_source[source_id] = error
        return items_by_source, errors_by_source

    async def _safe_search(self, source: SourceModel, query: SearchQuery) -> tuple[str, list[RawSearchItem], str | None]:
        try:
            return source.id, await asyncio.wait_for(source.search_function(query), timeout=10), None
        except TimeoutError:
            return source.id, [], "SEARCH_SOURCE_TIMEOUT"
        except Exception as exc:
            return source.id, [], f"SEARCH_SOURCE_FAILED: {exc}"

    def _normalize(self, item: RawSearchItem, query: SearchQuery) -> ResourceCandidate | None:
        links = extract_cloud_links(item.raw_content)
        if query.result_type != "all":
            links = [link for link in links if link.provider == query.result_type]
        if not links:
            return None
        title = clean_title(item.raw_title)
        year = self._extract_year(item, query)
        quality = item.metadata.get("quality") or self._extract_quality(item.raw_title, item.raw_content)
        link_name = self._extract_link_name(item, title, quality)
        result_links = [
            ResourceLinkResult(
                id=self._stable_id(link.provider, self._normalize_url(link.url)),
                provider=link.provider,
                name=link_name,
                url=link.url,
                code=link.code,
                quality=quality,
                source_id=item.source_id,
                source_url=item.raw_url,
                published_at=item.published_at,
            )
            for link in links
        ]

        return ResourceCandidate(
            id=self._stable_id(title, str(year)),
            title=title,
            normalized_title=self._normalize_title(title),
            original_title=item.raw_title,
            year=year,
            source_id=item.source_id,
            source_url=item.raw_url,
            links=result_links,
        )

    def _dedupe(self, candidates: list[ResourceCandidate]) -> list[ResourceCandidate]:
        merged: dict[tuple[str, int | None], ResourceCandidate] = {}
        seen_links: set[str] = set()
        for candidate in candidates:
            unique_links: list[ResourceLinkResult] = []
            for link in candidate.links:
                link_key = self._link_key(link.provider, link.url)
                if link_key in seen_links:
                    continue
                seen_links.add(link_key)
                unique_links.append(link)
            if not unique_links:
                continue
            candidate.links = unique_links
            key = (candidate.normalized_title, candidate.year)
            existing = merged.get(key)
            if existing is None:
                merged[key] = candidate
                continue
            existing.links.extend(candidate.links)
        return list(merged.values())

    def _score_candidate(self, candidate: ResourceCandidate, query: SearchQuery) -> float:
        score = 0.4
        title_text = candidate.original_title or candidate.title
        if query.keyword.lower() in title_text.lower():
            score += 0.3
        if candidate.year and query.year == candidate.year:
            score += 0.1
        if candidate.links:
            score += 0.2
        return round(score, 4)

    async def _validate_links(self, candidates: list[ResourceCandidate]) -> None:
        links = [link for candidate in candidates for link in candidate.links]
        results = await asyncio.gather(
            *(self.validator.validate(link.provider, link.url) for link in links),
            return_exceptions=True,
        )
        for link, result in zip(links, results, strict=True):
            if isinstance(result, Exception):
                link.valid = None
                link.validation_status = "error"
                link.validation_message = "链接检测失败。"
                continue
            link.valid = result.valid
            link.validation_status = result.status  # type: ignore[assignment]
            link.validation_message = result.message
            link.checked_at = result.checked_at

    def _normalize_title(self, title: str) -> str:
        return re.sub(r"\W+", "", title).lower()

    def _extract_year(self, item: RawSearchItem, query: SearchQuery) -> int | None:
        from sundarr.app.sources.utils import extract_year_from_text

        if isinstance(item.metadata.get("year"), int):
            return item.metadata["year"]
        match = extract_year_from_text(item.raw_title)
        if match is not None:
            return match
        match = extract_year_from_text(item.raw_content)
        return match if match is not None else query.year

    def _extract_quality(self, *texts: str) -> str | None:
        from sundarr.app.sources.utils import extract_quality_from_text

        return extract_quality_from_text(*texts)

    def _extract_link_name(self, item: RawSearchItem, title: str, quality: str | None) -> str:
        for key in ("link_name", "name", "title"):
            value = item.metadata.get(key)
            if isinstance(value, str) and value.strip():
                name = value.strip()
                break
        else:
            name = clean_title(item.raw_title) or title
        return generate_link_name(name, quality)

    def _stable_id(self, *parts: str | None) -> str:
        value = "|".join(part or "" for part in parts)
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]

    def _link_key(self, provider: str, url: str) -> str:
        return f"{provider}:{self._normalize_url(url)}"

    def _normalize_url(self, url: str) -> str:
        if url.lower().startswith("magnet:"):
            return url.strip().lower()
        split = urlsplit(url.strip())
        query = urlencode(sorted(parse_qsl(split.query, keep_blank_values=True)))
        path = split.path.rstrip("/")
        return urlunsplit((split.scheme.lower(), split.netloc.lower(), path, query, ""))


search_service = SearchService()
