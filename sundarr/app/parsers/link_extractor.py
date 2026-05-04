import re

from sundarr.app.schemas.search import CloudLink

LINK_PATTERNS = {
    "quark": re.compile(r"https?://pan\.example\.invalid/s/[A-Za-z0-9_-]+"),
}
CODE_PATTERN = re.compile(r"(?:提取码|密码|访问码|code)[:：\s]*([A-Za-z0-9]{2,12})", re.IGNORECASE)


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

    return links
