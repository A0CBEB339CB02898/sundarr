"""海报中继的网络边界测试。"""

from email.message import Message

import pytest

from sundarr.app.services import poster_proxy_service as poster_module
from sundarr.app.services.poster_proxy_service import (
    MAX_POSTER_BYTES,
    PosterFetchError,
    PosterProxyService,
)


class FakeResponse:
    def __init__(self, body: bytes, content_type: str, content_length: int | None = None) -> None:
        self.body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int) -> bytes:
        return self.body[:size]


class FakeOpener:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.request = None

    def open(self, request, timeout: int):  # type: ignore[no-untyped-def]
        self.request = request
        assert timeout == 15
        return self.response


@pytest.mark.parametrize(
    "url",
    [
        "http://images.example/poster.jpg",
        "https://localhost/poster.jpg",
        "https://127.0.0.1/poster.jpg",
        "https://10.0.0.8/poster.jpg",
        "https://user:password@images.example/poster.jpg",
    ],
)
def test_poster_url_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(PosterFetchError):
        PosterProxyService._validate_url(url)


def test_poster_download_sends_referer_and_accepts_supported_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = FakeOpener(FakeResponse(b"jpeg-data", "image/jpeg"))
    monkeypatch.setattr(poster_module, "build_opener", lambda *handlers: opener)

    payload = PosterProxyService()._download_sync(
        "https://images.example/poster.jpg",
        "https://catalog.example/",
    )

    assert payload.body == b"jpeg-data"
    assert payload.media_type == "image/jpeg"
    assert opener.request.get_header("Referer") == "https://catalog.example/"


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (FakeResponse(b"<html>blocked</html>", "text/html"), "图片格式"),
        (
            FakeResponse(b"small", "image/jpeg", MAX_POSTER_BYTES + 1),
            "大小限制",
        ),
        (FakeResponse(b"", "image/jpeg"), "空海报"),
    ],
)
def test_poster_download_rejects_invalid_upstream(
    response: FakeResponse,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        poster_module,
        "build_opener",
        lambda *handlers: FakeOpener(response),
    )

    with pytest.raises(PosterFetchError, match=message):
        PosterProxyService()._download_sync("https://images.example/poster.jpg", None)
