"""外部目录海报的受控同源中继。"""

from __future__ import annotations

import asyncio
import ipaddress
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from sqlalchemy.orm import Session

from sundarr.app.models import MediaSubject
from sundarr.app.plugins.runtime_registry import catalog_provider_registry


MAX_POSTER_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
)


class PosterNotFoundError(LookupError):
    pass


class PosterSourceMismatchError(RuntimeError):
    pass


class PosterProviderUnavailableError(RuntimeError):
    pass


class PosterFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class PosterPayload:
    body: bytes
    media_type: str


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class PosterProxyService:
    async def fetch(
        self,
        db: Session,
        media_subject_id: str,
        provider_id: str,
    ) -> PosterPayload:
        subject = db.get(MediaSubject, media_subject_id)
        if subject is None or not subject.last_known_poster_url:
            raise PosterNotFoundError("媒体主体不存在或没有可用海报")
        if subject.snapshot_source != provider_id:
            raise PosterSourceMismatchError("海报来源与请求的目录 Provider 不一致")

        provider = catalog_provider_registry.get(provider_id)
        if provider is None:
            raise PosterProviderUnavailableError("目录 Provider 当前未启用")
        attribution = provider.describe_capabilities().attribution
        referer = attribution.image_referer_url if attribution is not None else None
        self._validate_url(subject.last_known_poster_url)
        return await self._download(subject.last_known_poster_url, referer)

    async def _download(self, url: str, referer: str | None) -> PosterPayload:
        return await asyncio.to_thread(self._download_sync, url, referer)

    def _download_sync(self, url: str, referer: str | None) -> PosterPayload:
        headers = {
            "Accept": "image/avif,image/webp,image/png,image/jpeg,image/gif;q=0.8,*/*;q=0.1",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"
            ),
        }
        if referer:
            headers["Referer"] = referer
        request = Request(url, headers=headers, method="GET")
        try:
            with build_opener(_RejectRedirects()).open(request, timeout=15) as response:
                media_type = response.headers.get_content_type().lower()
                if media_type not in ALLOWED_IMAGE_TYPES:
                    raise PosterFetchError("上游没有返回受支持的图片格式")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_POSTER_BYTES:
                    raise PosterFetchError("上游海报超过大小限制")
                body = response.read(MAX_POSTER_BYTES + 1)
        except PosterFetchError:
            raise
        except (HTTPError, URLError, OSError, ValueError) as exc:
            raise PosterFetchError("上游海报读取失败") from exc
        if len(body) > MAX_POSTER_BYTES:
            raise PosterFetchError("上游海报超过大小限制")
        if not body:
            raise PosterFetchError("上游返回了空海报")
        return PosterPayload(body=body, media_type=media_type)

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise PosterFetchError("海报地址必须是有效的 HTTPS URL")
        if parsed.username or parsed.password:
            raise PosterFetchError("海报地址不能包含认证信息")
        hostname = parsed.hostname.rstrip(".").lower()
        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise PosterFetchError("海报地址不能指向本机")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            return
        if not address.is_global:
            raise PosterFetchError("海报地址不能指向本机或内网")


poster_proxy_service = PosterProxyService()
