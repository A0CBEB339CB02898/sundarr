import asyncio
import re
from datetime import UTC, datetime
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin
from urllib.request import Request, urlopen

from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import SourceTestEvent, SourceTestExecution


class SeedHubSource:
    id = "seedhub"
    name = "SeedHub"
    description = "搜索列表后进入详情页抽取磁力、迅雷和网盘链接。"

    base_url = "https://www.seedhub.cc"
    homepage_url = base_url
    timeout_seconds = 30
    max_details = 8
    max_resolved_links_per_detail = 8

    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        html = await asyncio.to_thread(self._fetch, self._search_url(query.keyword))
        detail_urls = self._parse_detail_urls(html)
        items: list[RawSearchItem] = []
        for detail_url in detail_urls[: self.max_details]:
            try:
                detail_html = await asyncio.to_thread(self._fetch, detail_url)
            except URLError:
                continue
            item = self._parse_detail(detail_url, detail_html)
            if item is not None:
                items.append(item)
        return items

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
            except URLError as exc:
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
            item = self._parse_detail(detail_url, detail_html)
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
        if not self._contains_supported_link(content):
            return None
        return RawSearchItem(
            source_id=self.id,
            source_type="code",
            raw_title=self._extract_title(html) or "SeedHub 搜索结果",
            raw_url=detail_url,
            raw_content=content,
            fetched_at=datetime.now(UTC),
            metadata={"type": "unknown", "source": "seedhub"},
        )

    def _build_detail_content(self, detail_url: str, html: str) -> str:
        parts = [self._strip_tags(html)]
        parts.extend(self._extract_direct_links(html))
        for link in self._extract_seedhub_download_links(html)[: self.max_resolved_links_per_detail]:
            try:
                resolved = self._resolve_seedhub_link(link)
            except (HTTPError, URLError, TimeoutError):
                continue
            if resolved:
                parts.append(resolved)
        return "\n".join(part for part in parts if part)

    def _extract_direct_links(self, html: str) -> list[str]:
        patterns = [
            r"magnet:\?xt=urn:btih:[^\s<\"']+",
            r"thunder://[^\s<\"']+",
            r"ed2k://[^\s<\"']+",
            r"https?://(?:pan\.quark\.cn|pan\.baidu\.com|www\.aliyundrive\.com|www\.alipan\.com|pan\.xunlei\.com|drive\.uc\.cn|cloud\.189\.cn)[^\s<\"']+",
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

    def _resolve_seedhub_link(self, link: str) -> str | None:
        html = self._fetch(urljoin(self.base_url, link))
        links = self._extract_direct_links(html)
        if links:
            return links[0]
        decoded = unquote(html)
        links = self._extract_direct_links(decoded)
        return links[0] if links else None

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
            )
        )

    def _extract_title(self, html: str) -> str | None:
        match = re.search(r"<h1[^>]*>.*?</a>\s*([^<]+)", html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return self._strip_tags(match.group(1)).strip() or None
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
