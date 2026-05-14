import asyncio
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
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
        if provider in {"thunder", "ed2k"}:
            return self._result(True, "valid", "下载协议链接格式有效，无法在线确认资源活性。")
        if not self.enable_network:
            return self._result(None, "unknown", "当前环境未启用网络检测。")
        return await asyncio.to_thread(self._validate_netdisk, provider, url)

    def _validate_netdisk(self, provider: str, url: str) -> LinkValidationResult:
        share_id = self._extract_share_id(provider, url)
        if share_id is None:
            return self._validate_http(url)
        try:
            if provider == "quark":
                return self._check_quark(share_id)
            if provider == "aliyun":
                return self._check_aliyun(share_id)
            if provider == "baidu":
                return self._check_baidu(url)
            if provider == "xunlei":
                return self._check_xunlei(share_id)
            if provider == "uc":
                return self._check_html_page(url, invalid_keywords=("失效", "不存在", "违规", "删除", "已过期", "被取消"), valid_keywords=("文件", "分享", "访问码"))
            if provider == "115":
                return self._check_115(share_id)
            if provider == "123pan":
                return self._check_123pan(share_id)
            if provider == "tianyi":
                return self._check_tianyi(share_id)
        except HTTPError as exc:
            if exc.code in {404, 410}:
                return self._result(False, "invalid", f"HTTP {exc.code}")
            return self._result(None, "unknown", f"HTTP {exc.code}")
        except (URLError, TimeoutError) as exc:
            return self._result(None, "error", f"检测失败：{exc}")
        except (ValueError, json.JSONDecodeError) as exc:
            return self._result(None, "error", f"响应解析失败：{exc}")
        return self._validate_http(url)

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

    def _check_quark(self, share_id: str) -> LinkValidationResult:
        body = self._json_request(
            "https://drive.quark.cn/1/clouddrive/share/sharepage/token",
            method="POST",
            data={"pwd_id": share_id, "passcode": ""},
        )
        message = str(body.get("message") or "")
        if message == "需要提取码":
            return self._result(True, "valid", "夸克分享有效，需要提取码。")
        if message != "ok":
            return self._result(False, "invalid", f"夸克分享无效：{message or '未知错误'}")
        token = body.get("data", {}).get("stoken")
        if not token:
            return self._result(False, "invalid", "夸克分享未返回访问令牌。")
        detail_url = f"https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail?pwd_id={share_id}&stoken={quote(token)}&_fetch_share=1"
        detail = self._json_request(detail_url)
        if detail.get("data", {}).get("share", {}).get("status") == 1:
            return self._result(True, "valid", "夸克分享有效。")
        if detail.get("status") == 400:
            return self._result(True, "valid", "夸克分享需要提取码或额外校验。")
        return self._result(False, "invalid", "夸克分享状态无效。")

    def _check_aliyun(self, share_id: str) -> LinkValidationResult:
        body = self._json_request(
            "https://api.aliyundrive.com/adrive/v3/share_link/get_share_by_anonymous",
            method="POST",
            data={"share_id": share_id},
        )
        if body.get("code") == "NotFound.ShareLink":
            return self._result(False, "invalid", "阿里云盘分享不存在。")
        if body.get("has_pwd"):
            return self._result(True, "valid", "阿里云盘分享有效，需要提取码。")
        if body.get("file_infos"):
            return self._result(True, "valid", "阿里云盘分享有效。")
        return self._result(False, "invalid", "阿里云盘分享没有可用文件。")

    def _check_baidu(self, url: str) -> LinkValidationResult:
        return self._check_html_page(
            url,
            invalid_keywords=("分享的文件已经被取消", "分享已过期", "你访问的页面不存在", "你所访问的页面不存在", "分享链接错误"),
            valid_keywords=("请输入提取码", "提取文件", "过期时间", "文件列表"),
        )

    def _check_xunlei(self, share_id: str) -> LinkValidationResult:
        body = self._json_request(
            "https://xluser-ssl.xunlei.com/v1/shield/captcha/init",
            method="POST",
            data={
                "client_id": "Xqp0kJBXWhwaTpB6",
                "device_id": "925b7631473a13716b791d7f28289cad",
                "action": "get:/drive/v1/share",
            },
            headers={"Content-Type": "application/json"},
        )
        token = body.get("captcha_token")
        if not token:
            return self._result(None, "unknown", "迅雷网盘需要验证码校验，无法轻量确认。")
        text = self._text_request(
            f"https://api-pan.xunlei.com/drive/v1/share?{urlencode({'share_id': share_id})}",
            headers={"x-captcha-token": token, "x-client-id": "Xqp0kJBXWhwaTpB6", "x-device-id": "925b7631473a13716b791d7f28289cad"},
        )
        if any(value in text for value in ("NOT_FOUND", "SENSITIVE_RESOURCE", "EXPIRED")):
            return self._result(False, "invalid", "迅雷网盘分享无效。")
        if "PASS_CODE_EMPTY" in text:
            return self._result(True, "valid", "迅雷网盘分享有效，需要提取码。")
        return self._result(True, "valid", "迅雷网盘分享有效。")

    def _check_115(self, share_id: str) -> LinkValidationResult:
        body = self._json_request(f"https://webapi.115.com/share/snap?{urlencode({'share_code': share_id, 'receive_code': ''})}")
        if body.get("state"):
            return self._result(True, "valid", "115 分享有效。")
        if "请输入访问码" in str(body.get("error") or ""):
            return self._result(True, "valid", "115 分享有效，需要访问码。")
        return self._result(False, "invalid", "115 分享无效。")

    def _check_123pan(self, share_id: str) -> LinkValidationResult:
        body = self._json_request(f"https://www.123pan.com/api/share/info?{urlencode({'shareKey': share_id})}")
        if body.get("code") == 0:
            return self._result(True, "valid", "123 网盘分享有效。")
        return self._result(False, "invalid", "123 网盘分享无效。")

    def _check_tianyi(self, share_id: str) -> LinkValidationResult:
        text = self._text_request(
            "https://api.cloud.189.cn/open/share/getShareInfoByCodeV2.action",
            method="POST",
            data={"shareCode": share_id},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if any(value in text for value in ("ShareInfoNotFound", "ShareNotFound", "FileNotFound", "ShareExpiredError", "ShareAuditNotPass")):
            return self._result(False, "invalid", "天翼云盘分享无效。")
        return self._result(True, "valid", "天翼云盘分享有效。")

    def _check_html_page(self, url: str, invalid_keywords: tuple[str, ...], valid_keywords: tuple[str, ...]) -> LinkValidationResult:
        text = self._text_request(url)
        if any(keyword in text for keyword in invalid_keywords):
            return self._result(False, "invalid", "页面提示分享无效。")
        if any(keyword in text for keyword in valid_keywords):
            return self._result(True, "valid", "页面提示分享有效。")
        return self._result(None, "unknown", "页面没有明确的有效性信号。")

    def _json_request(self, url: str, method: str = "GET", data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        text = self._text_request(url, method=method, data=data, headers={"Content-Type": "application/json", **(headers or {})})
        return json.loads(text)

    def _text_request(self, url: str, method: str = "GET", data: dict | None = None, headers: dict[str, str] | None = None) -> str:
        payload = None
        request_headers = {
            "User-Agent": "Mozilla/5.0 Sundarr/0.1 link validator",
            "Accept": "text/html,application/xhtml+xml,application/json",
            **(headers or {}),
        }
        if data is not None:
            if request_headers.get("Content-Type") == "application/json":
                payload = json.dumps(data).encode("utf-8")
            else:
                payload = urlencode(data).encode("utf-8")
        request = Request(url, method=method, headers=request_headers, data=payload)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def _extract_share_id(self, provider: str, url: str) -> str | None:
        patterns = {
            "uc": r"drive\.uc\.cn/s/([A-Za-z0-9_-]+)",
            "aliyun": r"(?:aliyundrive|alipan)\.com/s/([A-Za-z0-9_-]+)",
            "quark": r"pan\.quark\.cn/s/([A-Za-z0-9_-]+)",
            "115": r"(?:115|115cdn|anxia)\.com/s/([A-Za-z0-9_-]+)",
            "123pan": r"(?:123684|123685|123912|123pan|123592)\.(?:com|cn)/s/([A-Za-z0-9_-]+)",
            "tianyi": r"cloud\.189\.cn/(?:t/|web/share\?code=)([A-Za-z0-9]+)",
            "xunlei": r"pan\.xunlei\.com/s/([A-Za-z0-9_-]+)",
            "baidu": r"(?:pan|yun)\.baidu\.com/(?:s/|share/init\?surl=)([A-Za-z0-9_-]+)",
        }
        pattern = patterns.get(provider)
        if pattern is None:
            return None
        match = re.search(pattern, url, flags=re.IGNORECASE)
        return match.group(1) if match else None

    def _result(self, valid: bool | None, status: str, message: str) -> LinkValidationResult:
        return LinkValidationResult(valid=valid, status=status, message=message, checked_at=datetime.now(UTC))


link_validator = LinkValidator()
