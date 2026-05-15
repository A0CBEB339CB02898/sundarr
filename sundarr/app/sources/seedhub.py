import asyncio
import re
from datetime import UTC, datetime
from html import unescape
from http.client import InvalidURL
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from sundarr.app.parsers.link_extractor import LINK_PATTERNS
from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import SourceTestEvent, SourceTestExecution
from sundarr.app.sources.utils import CN_QUALITY_PATTERN, extract_quality_from_text, extract_year_from_text


class SeedHubSource:
    id = "seedhub"
    name = "SeedHub"
    description = "搜索列表后进入详情页抽取磁力、迅雷和网盘链接。"

    base_url = "https://www.seedhub.cc"
    homepage_url = base_url
    timeout_seconds = 30
    max_details = 20
    max_resolved_links_per_detail = 8

    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        html = await asyncio.to_thread(self._fetch, self._search_url(query.keyword))
        detail_urls = self._parse_detail_urls(html)
        results = await asyncio.gather(*(self._fetch_detail_item(detail_url) for detail_url in detail_urls[: self.max_details]))
        return [item for item in results if item is not None]

    async def test_search(self, query: SearchQuery) -> SourceTestExecution:
        logs = [
            SourceTestEvent(
                step="build_search_url",
                status="ok",
                message="已生成搜索地址。",
                data={"url": self._search_url(query.keyword)},
            )
        ]
        search_url = self._search_url(query.keyword)
        html = await asyncio.to_thread(self._fetch, search_url)
        logs.append(SourceTestEvent(step="fetch_search_page", status="ok", message="搜索页请求完成。", data={"bytes": len(html)}))
        detail_urls = self._parse_detail_urls(html)
        logs.append(
            SourceTestEvent(
                step="parse_detail_urls",
                status="ok",
                message="已解析详情页入口。",
                data={"count": len(detail_urls), "preview": detail_urls[: min(3, len(detail_urls))]},
            )
        )
        items: list[RawSearchItem] = []
        for detail_url in detail_urls[: min(query.limit, self.max_details)]:
            try:
                detail_html = await asyncio.to_thread(self._fetch, detail_url)
            except (InvalidURL, URLError, ValueError) as exc:
                logs.append(
                    SourceTestEvent(
                        step="fetch_detail_page",
                        status="error",
                        message="详情页请求失败，已跳过该结果。",
                        data={"url": detail_url, "error": str(exc)},
                    )
                )
                continue
            logs.append(SourceTestEvent(step="fetch_detail_page", status="ok", message="详情页请求完成。", data={"url": detail_url, "bytes": len(detail_html)}))
            item = await self._parse_detail_async(detail_url, detail_html)
            if item is None:
                logs.append(SourceTestEvent(step="extract_links", status="empty", message="详情页未提取到支持的链接。", data={"url": detail_url}))
                continue
            items.append(item)
            logs.append(
                SourceTestEvent(
                    step="extract_links",
                    status="ok",
                    message="已提取候选结果。",
                    data={"url": detail_url, "title": item.raw_title},
                )
            )
        logs.append(SourceTestEvent(step="finish", status="ok", message="测试搜索流程结束。", data={"raw_count": len(items)}))
        return SourceTestExecution(items=items, logs=logs)

    def _search_url(self, keyword: str) -> str:
        return f"{self.base_url}/s/{quote(keyword)}/"

    def _fetch(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36 Sundarr/0.1",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def _parse_detail_urls(self, html: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for title, href in re.findall(r'title="([^"]+)"[^>]*class="image"[^>]*href="(/movies/\d+)/?"', html, flags=re.IGNORECASE):
            url = self._normalize_detail_url(urljoin(self.base_url, unescape(href)))
            if url not in seen:
                seen.add(url)
                urls.append(url)
        for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
            if not self._looks_like_detail_href(href):
                continue
            url = self._normalize_detail_url(urljoin(self.base_url, unescape(href)))
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def _normalize_detail_url(self, url: str) -> str:
        return f"{url.rstrip('/')}/"

    def _looks_like_detail_href(self, href: str) -> bool:
        lowered = href.lower()
        return bool(re.search(r"/movies/\d+/?$", lowered))

    def _parse_detail(self, detail_url: str, html: str) -> RawSearchItem | None:
        content = self._build_detail_content(detail_url, html)
        return self._build_raw_item(detail_url, html, content)

    async def _fetch_detail_item(self, detail_url: str) -> RawSearchItem | None:
        try:
            detail_html = await asyncio.to_thread(self._fetch, detail_url)
        except (InvalidURL, URLError, ValueError):
            return None
        return await self._parse_detail_async(detail_url, detail_html)

    async def _parse_detail_async(self, detail_url: str, html: str) -> RawSearchItem | None:
        content = await self._build_detail_content_async(detail_url, html)
        return self._build_raw_item(detail_url, html, content)

    def _build_raw_item(self, detail_url: str, html: str, content: str) -> RawSearchItem | None:
        if not self._contains_supported_link(content):
            return None
        raw_title = self._extract_title(html) or "SeedHub 搜索结果"
        year = extract_year_from_text(raw_title)
        quality = extract_quality_from_text(raw_title)
        if year is None:
            year = extract_year_from_text(content)
        if quality is None:
            quality = extract_quality_from_text(content)
        if quality is None:
            for link_title in self._extract_download_link_titles(html):
                q = extract_quality_from_text(link_title)
                if q:
                    quality = q
                    break
        metadata: dict[str, object] = {"type": "unknown", "source": "seedhub"}
        if year is not None:
            metadata["year"] = year
        if quality is not None:
            metadata["quality"] = quality
        link_meta = self._extract_link_metadata(html)
        if link_meta:
            metadata["links"] = link_meta
        return RawSearchItem(
            source_id=self.id,
            source_type="code",
            raw_title=raw_title,
            raw_url=detail_url,
            raw_content=content,
            fetched_at=datetime.now(UTC),
            metadata=metadata,
        )

    def _build_detail_content(self, detail_url: str, html: str) -> str:
        parts = [self._strip_tags(html)]
        parts.extend(self._extract_direct_links(html))
        for link in self._extract_seedhub_download_links(html):
            try:
                resolved = self._resolve_seedhub_link(link)
            except (HTTPError, InvalidURL, URLError, TimeoutError, ValueError):
                continue
            if resolved:
                parts.append(resolved)
        return "\n".join(part for part in parts if part)

    async def _build_detail_content_async(self, detail_url: str, html: str) -> str:
        parts = [self._strip_tags(html)]
        parts.extend(self._extract_direct_links(html))
        download_links = self._extract_seedhub_download_links(html)
        resolved_links = await asyncio.gather(
            *(asyncio.to_thread(self._resolve_seedhub_link, link) for link in download_links),
            return_exceptions=True,
        )
        for resolved in resolved_links:
            if isinstance(resolved, Exception):
                continue
            if resolved:
                parts.append(resolved)
        return "\n".join(part for part in parts if part)

    def _extract_direct_links(self, html: str) -> list[str]:
        patterns = [
            r"thunder://[^\s<\"']+",
            r"ed2k://[^\s<\"']+",
            *(pattern.pattern for pattern in LINK_PATTERNS.values()),
        ]
        links: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            for match in re.findall(pattern, html, flags=re.IGNORECASE):
                link = unescape(match).rstrip(".,;，。；")
                if link not in seen:
                    seen.add(link)
                    links.append(link)
        return links

    def _extract_seedhub_download_links(self, html: str) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        for href in re.findall(r'href="(/link_start/\?redirect_to=pan_id_\d+[^"<]*)"', html, flags=re.IGNORECASE):
            link = unescape(href)
            if link in seen:
                continue
            seen.add(link)
            links.append(link)
        return links

    def _extract_download_link_titles(self, html: str) -> list[str]:
        titles: list[str] = []
        for match in re.finditer(r'href="(/link_start/\?redirect_to=pan_id_\d+[^"<]*)"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE):
            text = self._strip_tags(match.group(2)).strip()
            if text:
                titles.append(text)
        return titles

    def _extract_link_metadata(self, html: str) -> dict[str, dict[str, object]]:
        text = self._strip_tags(html)
        result: dict[str, dict[str, object]] = {}
        url_pattern = re.compile(
            r"(?:magnet:\?xt=urn:btih:[A-Za-z0-9]{32,40}[^\s<>'\"，。；、]*"
            r"|https?://pan\.quark\.cn/s/[A-Za-z0-9_-]+"
            r"|https?://(?:www\.)?(?:aliyundrive|alipan)\.com/s/[A-Za-z0-9_-]+"
            r"|https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?"
            r"|https?://pan\.xunlei\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?"
            r"|https?://drive\.uc\.cn/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?"
            r"|https?://(?:www\.)?(?:115|115cdn|anxia)\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?"
            r"|https?://(?:www\.)?(?:123684|123685|123912|123pan|123592)\.(?:com|cn)/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?"
            r"|https?://cloud\.189\.cn/(?:t/[A-Za-z0-9]+|web/share\?code=[A-Za-z0-9]+)(?:[^\s<>'\"，。；、]*)?"
            r"|thunder://[^\s<>'\"，。；、]+"
            r"|ed2k://[^\s<>'\"，。；、]+)",
            re.IGNORECASE,
        )
        code_pattern = re.compile(r"(?:提取码|密码|访问码|code)[:：\s]*[A-Za-z0-9]{2,12}", re.IGNORECASE)
        segments = re.split(r"\n\s*\n|═══.*?═══|\n(?=【|❤|★|●|◎|○|■|□|◆|◇)", text)
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            segment_urls = list(url_pattern.finditer(segment))
            if not segment_urls:
                continue
            quality = extract_quality_from_text(segment)
            if quality is None:
                cn_match = CN_QUALITY_PATTERN.search(segment)
                if cn_match:
                    quality = cn_match.group(1)
            name_text = url_pattern.sub("", segment)
            name_text = code_pattern.sub("", name_text)
            name_text = re.sub(r"\s+", " ", name_text).strip()
            name_text = name_text.rstrip(",;，。；")
            date_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", segment)
            for url_match in segment_urls:
                url = url_match.group(0).rstrip(".,;，。；")
                if url in result:
                    continue
                meta: dict[str, object] = {}
                name = name_text.lstrip(".,;，。； ").strip()
                if name and name not in ("下载", "链接", "提取码"):
                    meta["name"] = name
                if quality:
                    meta["quality"] = quality
                if date_match:
                    meta["published_at"] = date_match.group(1)
                if meta:
                    result[url] = meta
        return result

    def _resolve_seedhub_link(self, link: str) -> str | None:
        html = self._fetch(urljoin(self.base_url, self._normalize_seedhub_download_link(link)))
        links = self._extract_direct_links(html)
        if links:
            return links[0]
        decoded = unquote(html)
        links = self._extract_direct_links(decoded)
        return links[0] if links else None

    def _normalize_seedhub_download_link(self, link: str) -> str:
        split = urlsplit(unescape(link))
        query = [(key, value) for key, value in parse_qsl(split.query, keep_blank_values=True) if key == "redirect_to"]
        return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))

    def _contains_supported_link(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            marker in lowered
            for marker in (
                "magnet:?xt=urn:btih:",
                "thunder://",
                "ed2k://",
                "pan.quark.cn",
                "aliyundrive.com",
                "alipan.com",
                "pan.baidu.com",
                "pan.xunlei.com",
                "drive.uc.cn",
                "cloud.189.cn",
                "115.com",
                "115cdn.com",
                "anxia.com",
                "123684.com",
                "123685.com",
                "123912.com",
                "123pan.com",
                "123592.com",
                "123684.cn",
                "123685.cn",
                "123912.cn",
                "123pan.cn",
                "123592.cn",
            )
        )

    def _extract_title(self, html: str) -> str | None:
        match = re.search(r"<h1[^>]*>.*?</a>\s*([^<]+)", html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return self._strip_tags(match.group(1)).strip() or None
        match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            raw = self._strip_tags(match.group(1)).strip()
            if raw:
                return raw
        match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        title = self._strip_tags(match.group(1))
        title = re.sub(r"\s*[-_|].*$", "", title).strip()
        return title or None

    def _strip_tags(self, html: str) -> str:
        html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", html)
        return " ".join(unescape(text).split())
