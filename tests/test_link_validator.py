import json

from sundarr.app.services import link_validator as link_validator_module
from sundarr.app.services.link_validator import LinkValidator


class FakeHeaders:
    def get_content_charset(self):
        return "utf-8"


class FakeResponse:
    def __init__(self, text: str, status: int = 200) -> None:
        self.text = text
        self.status = status
        self.headers = FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.text.encode("utf-8")


def test_quark_validator_uses_share_status_api(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        url = request.full_url
        if "sharepage/token" in url:
            return FakeResponse(json.dumps({"message": "ok", "data": {"stoken": "token"}}))
        if "sharepage/detail" in url:
            return FakeResponse(json.dumps({"data": {"share": {"status": 1}}}))
        raise AssertionError(url)

    monkeypatch.setattr(link_validator_module, "urlopen", fake_urlopen)

    result = LinkValidator()._validate_netdisk("quark", "https://pan.quark.cn/s/abc123")

    assert result.valid is True
    assert result.status == "valid"


def test_aliyun_validator_marks_not_found_invalid(monkeypatch) -> None:
    monkeypatch.setattr(
        link_validator_module,
        "urlopen",
        lambda request, timeout: FakeResponse(json.dumps({"code": "NotFound.ShareLink"})),
    )

    result = LinkValidator()._validate_netdisk("aliyun", "https://www.alipan.com/s/missing")

    assert result.valid is False
    assert result.status == "invalid"


def test_baidu_validator_detects_password_page(monkeypatch) -> None:
    monkeypatch.setattr(
        link_validator_module,
        "urlopen",
        lambda request, timeout: FakeResponse("请输入提取码"),
    )

    result = LinkValidator()._validate_netdisk("baidu", "https://pan.baidu.com/s/abc?pwd=1234")

    assert result.valid is True
    assert result.status == "valid"
