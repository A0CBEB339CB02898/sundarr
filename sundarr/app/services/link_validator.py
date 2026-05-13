import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LinkValidationResult:
    valid: bool | None
    status: str
    message: str
    checked_at: datetime


class LinkValidator:
    def __init__(self, timeout_seconds: float = 4.0, enable_network: bool = True) -> None:
        self.timeout_seconds = timeout_seconds
        self.enable_network = enable_network

    async def validate(self, provider: str, url: str) -> LinkValidationResult:
        if provider == "magnet":
            return self._result(True, "valid", "磁力链接格式有效，无法在线确认资源活性。")
        if not self.enable_network:
            return self._result(None, "unknown", "当前环境未启用网络检测。")
        return await asyncio.to_thread(self._validate_http, url)

    def _validate_http(self, url: str) -> LinkValidationResult:
        for method in ("HEAD", "GET"):
            try:
                request = Request(
                    url,
                    method=method,
                    headers={
                        "User-Agent": "Sundarr/0.1 link validator",
                        "Accept": "text/html,application/xhtml+xml",
                    },
                )
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    if 200 <= response.status < 400:
                        return self._result(True, "valid", f"HTTP {response.status}")
                    if response.status in {404, 410}:
                        return self._result(False, "invalid", f"HTTP {response.status}")
                    return self._result(None, "unknown", f"HTTP {response.status}")
            except HTTPError as exc:
                if exc.code in {404, 410}:
                    return self._result(False, "invalid", f"HTTP {exc.code}")
                if exc.code in {401, 403, 405, 429}:
                    return self._result(None, "unknown", f"HTTP {exc.code}")
            except URLError as exc:
                return self._result(None, "error", f"检测失败：{exc.reason}")
            except TimeoutError:
                return self._result(None, "error", "检测超时。")
        return self._result(None, "unknown", "目标不支持轻量 HTTP 检测。")

    def _result(self, valid: bool | None, status: str, message: str) -> LinkValidationResult:
        return LinkValidationResult(valid=valid, status=status, message=message, checked_at=datetime.now(UTC))


link_validator = LinkValidator()
