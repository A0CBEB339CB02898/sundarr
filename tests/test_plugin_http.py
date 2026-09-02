"""插件受控 HTTP 客户端测试。"""

import asyncio
from unittest.mock import patch

import pytest

from sundarr.app.plugins.http import PluginHttpClient


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self.payload[:size]


def test_plugin_http_reads_json_and_utf8_text_with_controlled_headers() -> None:
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        payload = (
            b'{"ok": true}'
            if request.headers["Accept"] == "application/json"
            else "公开想看列表".encode()
        )
        return FakeResponse(payload)

    client = PluginHttpClient(plugin_id="fixture", timeout_seconds=3)
    with patch("sundarr.app.plugins.http.urlopen", fake_urlopen):
        json_payload = asyncio.run(client.get_json("https://example.com/data"))
        text_payload = asyncio.run(
            client.get_text(
                "https://example.com/page",
                headers={"Referer": "https://example.com/"},
            )
        )

    assert json_payload == {"ok": True}
    assert text_payload == "公开想看列表"
    assert requests[0][0].headers["User-agent"] == "Sundarr-Plugin/fixture"
    assert requests[1][0].headers["Referer"] == "https://example.com/"
    assert requests[0][1] == requests[1][1] == 3


def test_plugin_http_text_keeps_protocol_and_size_guards() -> None:
    client = PluginHttpClient(plugin_id="fixture", max_response_bytes=3)

    with pytest.raises(ValueError, match="有效的 http/https URL"):
        asyncio.run(client.get_text("file:///tmp/private"))

    with patch(
        "sundarr.app.plugins.http.urlopen",
        lambda request, timeout: FakeResponse(b"four"),
    ):
        with pytest.raises(ValueError, match="响应超过大小限制"):
            asyncio.run(client.get_text("https://example.com/page"))
