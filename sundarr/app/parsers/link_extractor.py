import re

from sundarr.app.schemas.search import CloudLink

LINK_PATTERNS = {
    "magnet": re.compile(r"magnet:\?xt=urn:btih:[A-Za-z0-9]{32,40}(?:[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "quark": re.compile(r"https?://pan\.quark\.cn/s/[A-Za-z0-9_-]+", re.IGNORECASE),
    "aliyun": re.compile(r"https?://www\.aliyundrive\.com/s/[A-Za-z0-9_-]+", re.IGNORECASE),
    "baidu": re.compile(r"https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "xunlei": re.compile(r"https?://pan\.xunlei\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?", re.IGNORECASE),
}
CODE_PATTERN = re.compile(r"(?:提取码|密码|访问码|code)[:：\s]*([A-Za-z0-9]{2,12})", re.IGNORECASE)
LEGACY_EXAMPLE_PATTERN = re.compile(r"https?://pan\.example\.invalid/s/[A-Za-z0-9_-]+", re.IGNORECASE)


def extract_cloud_links(text: str) -> list[CloudLink]:
    code_match = CODE_PATTERN.search(text)
    code = code_match.group(1) if code_match else None
    links: list[CloudLink] = []

    for provider, pattern in LINK_PATTERNS.items():
        for match in pattern.finditer(text):
            url = match.group(0)
            links.append(
                CloudLink(
                    provider=provider,
                    url=url,
                    code=code,
                    raw_text=text,
                    confidence=0.95,
                )
            )

    for match in LEGACY_EXAMPLE_PATTERN.finditer(text):
        links.append(
            CloudLink(
                provider="quark",
                url=match.group(0),
                code=code,
                raw_text=text,
                confidence=0.5,
            )
        )

    return links
