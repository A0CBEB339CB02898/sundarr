"""插件可使用的受控 HTTP 能力。"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class PluginHttpClient:
    """带协议、超时和响应大小限制的最小 HTTP 客户端。"""

    plugin_id: str
    timeout_seconds: float = 15.0
    max_response_bytes: int = 4 * 1024 * 1024
    max_attempts: int = 2
    retry_base_seconds: float = 0.2

    async def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return await asyncio.to_thread(self._get_json_sync, url, headers or {})

    async def get_text(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> str:
        """读取受大小限制的 UTF-8 文本响应。"""

        return await asyncio.to_thread(self._get_text_sync, url, headers or {})

    def _get_json_sync(self, url: str, headers: dict[str, str]) -> Any:
        payload = self._get_bytes_sync(
            url,
            headers,
            accept="application/json",
        )
        return json.loads(payload.decode("utf-8"))

    def _get_text_sync(self, url: str, headers: dict[str, str]) -> str:
        payload = self._get_bytes_sync(
            url,
            headers,
            accept="text/html,text/plain;q=0.9,*/*;q=0.1",
        )
        return payload.decode("utf-8")

    def _get_bytes_sync(
        self,
        url: str,
        headers: dict[str, str],
        *,
        accept: str,
    ) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("插件 HTTP 仅允许有效的 http/https URL")
        request = Request(
            url,
            headers={
                "User-Agent": f"Sundarr-Plugin/{self.plugin_id}",
                "Accept": accept,
                **headers,
            },
        )
        attempts = max(1, self.max_attempts)
        for attempt in range(attempts):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                    payload = response.read(self.max_response_bytes + 1)
                break
            except HTTPError as exc:
                if exc.code not in {408, 429, 500, 502, 503, 504} or attempt + 1 >= attempts:
                    raise
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = _retry_delay(retry_after, self.retry_base_seconds, attempt)
                time.sleep(delay)
            except (URLError, TimeoutError):
                if attempt + 1 >= attempts:
                    raise
                time.sleep(min(2.0, self.retry_base_seconds * (2**attempt)))
        if len(payload) > self.max_response_bytes:
            raise ValueError("插件 HTTP 响应超过大小限制")
        return payload


def _retry_delay(retry_after: str | None, base_seconds: float, attempt: int) -> float:
    if retry_after:
        try:
            return min(2.0, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return min(2.0, max(0.0, base_seconds) * (2**attempt))


class PluginHttpClientFactory:
    """按插件 ID 创建隔离客户端，避免插件直接取得 Core 内部对象。"""

    def create(self, plugin_id: str) -> PluginHttpClient:
        if not plugin_id.strip():
            raise ValueError("plugin_id 不能为空")
        return PluginHttpClient(plugin_id=plugin_id)


plugin_http_client_factory = PluginHttpClientFactory()
