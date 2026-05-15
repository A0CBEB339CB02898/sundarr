import re

from sundarr.app.schemas.search import CloudLink

LINK_PATTERNS = {
    "magnet": re.compile(r"magnet:\?xt=urn:btih:[A-Za-z0-9]{32,40}(?:[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "quark": re.compile(r"https?://pan\.quark\.cn/s/[A-Za-z0-9_-]+", re.IGNORECASE),
    "aliyun": re.compile(r"https?://(?:www\.)?(?:aliyundrive|alipan)\.com/s/[A-Za-z0-9_-]+", re.IGNORECASE),
    "baidu": re.compile(r"https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "xunlei": re.compile(r"https?://pan\.xunlei\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "uc": re.compile(r"https?://drive\.uc\.cn/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "115": re.compile(r"https?://(?:www\.)?(?:115|115cdn|anxia)\.com/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "123pan": re.compile(r"https?://(?:www\.)?(?:123684|123685|123912|123pan|123592)\.(?:com|cn)/s/[A-Za-z0-9_-]+(?:\?[^\s<>'\"，。；、]*)?", re.IGNORECASE),
    "tianyi": re.compile(r"https?://cloud\.189\.cn/(?:t/[A-Za-z0-9]+|web/share\?code=[A-Za-z0-9]+)(?:[^\s<>'\"，。；、]*)?", re.IGNORECASE),
}
CODE_PATTERN = re.compile(r"(?:提取码|密码|访问码|code)[:：\s]*([A-Za-z0-9]{2,12})", re.IGNORECASE)
LEGACY_EXAMPLE_PATTERN = re.compile(r"https?://pan\.example\.invalid/s/[A-Za-z0-9_-]+", re.IGNORECASE)


def extract_cloud_links(text: str) -> list[CloudLink]:
    links: list[CloudLink] = []

    for provider, pattern in LINK_PATTERNS.items():
        for match in pattern.finditer(text):
            url = match.group(0)
            start = max(0, match.start() - 200)
            end = min(len(text), match.end() + 200)
            context = text[start:end]
            code_match = CODE_PATTERN.search(context)
            code = code_match.group(1) if code_match else None
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
        url = match.group(0)
        start = max(0, match.start() - 200)
        end = min(len(text), match.end() + 200)
        context = text[start:end]
        code_match = CODE_PATTERN.search(context)
        code = code_match.group(1) if code_match else None
        links.append(
            CloudLink(
                provider="quark",
                url=url,
                code=code,
                raw_text=text,
                confidence=0.5,
            )
        )

    return links
