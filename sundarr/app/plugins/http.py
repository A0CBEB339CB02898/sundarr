"""插件可使用的受控 HTTP 能力。"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class PluginHttpClient:
    """带协议、超时和响应大小限制的最小 HTTP 客户端。"""

    plugin_id: str
    timeout_seconds: float = 15.0
    max_response_bytes: int = 4 * 1024 * 1024

    async def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return await asyncio.to_thread(self._get_json_sync, url, headers or {})

    def _get_json_sync(self, url: str, headers: dict[str, str]) -> Any:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("插件 HTTP 仅允许有效的 http/https URL")
        request = Request(
            url,
            headers={
                "User-Agent": f"Sundarr-Plugin/{self.plugin_id}",
                "Accept": "application/json",
                **headers,
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            payload = response.read(self.max_response_bytes + 1)
        if len(payload) > self.max_response_bytes:
            raise ValueError("插件 HTTP 响应超过大小限制")
        return json.loads(payload.decode("utf-8"))


class PluginHttpClientFactory:
    """按插件 ID 创建隔离客户端，避免插件直接取得 Core 内部对象。"""

    def create(self, plugin_id: str) -> PluginHttpClient:
        if not plugin_id.strip():
            raise ValueError("plugin_id 不能为空")
        return PluginHttpClient(plugin_id=plugin_id)


plugin_http_client_factory = PluginHttpClientFactory()
