import asyncio
import re
from datetime import UTC, datetime
from html import unescape
from urllib.error import URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import BaseSource


class SeedHubSource(BaseSource):
    id = "seedhub"
    name = "SeedHub"
    source_type = "code"
    enabled = True
    description = "参考 seedhub-cli 的代码型搜索源，搜索列表后进入详情页抽取磁力、迅雷和网盘链接。"
    legal_note = "仅聚合公开页面中已展示的链接；不绕过登录、验证码、会员或风控限制。"

    base_url = "https://seedhub.cc"
    timeout_seconds = 8
    max_details = 8

    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        html = await asyncio.to_thread(self._fetch, f"{self.base_url}/search?keyword={quote(query.keyword)}")
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

    def _fetch(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "Sundarr/0.1 (+https://github.com/sundarr; homelab media sync)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def _parse_detail_urls(self, html: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
            if not self._looks_like_detail_href(href):
                continue
            url = urljoin(self.base_url, unescape(href))
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def _looks_like_detail_href(self, href: str) -> bool:
        lowered = href.lower()
        return any(marker in lowered for marker in ("/detail", "/movie", "/resource", "/seed"))

    def _parse_detail(self, detail_url: str, html: str) -> RawSearchItem | None:
        content = self._strip_tags(html)
        if not self._contains_supported_link(content):
            return None
        return RawSearchItem(
            source_id=self.id,
            source_type=self.source_type,
            raw_title=self._extract_title(html) or "SeedHub 搜索结果",
            raw_url=detail_url,
            raw_content=content,
            fetched_at=datetime.now(UTC),
            metadata={"type": "unknown"},
        )

    def _contains_supported_link(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            marker in lowered
            for marker in ("magnet:?xt=urn:btih:", "pan.quark.cn", "aliyundrive.com", "pan.baidu.com", "pan.xunlei.com")
        )

    def _extract_title(self, html: str) -> str | None:
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
