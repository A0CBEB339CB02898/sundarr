import re

TITLE_TAG_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9])(720p|1080p|2160p|4k|blu-?ray|web-?dl|remux|hdr|x26[45]|h\.26[45])(?![a-zA-Z0-9])",
    re.IGNORECASE,
)
CN_QUALITY_PATTERN = re.compile(r"(?<![a-zA-Z0-9])(蓝光|高清|高码|无损|杜比|iNT组)(?![a-zA-Z0-9])")
YEAR_PATTERN = re.compile(r"(?<![a-zA-Z0-9])(19\d{2}|20\d{2})(?![a-zA-Z0-9])")


def extract_year_from_text(text: str) -> int | None:
    match = YEAR_PATTERN.search(text)
    return int(match.group(1)) if match else None


def extract_quality_from_text(*texts: str) -> str | None:
    for text in texts:
        match = TITLE_TAG_PATTERN.search(text)
        if match:
            raw = match.group(1).upper()
            raw = raw.replace("BLURAY", "BluRay").replace("BLU-RAY", "BluRay")
            return raw
        match = CN_QUALITY_PATTERN.search(text)
        if match:
            return match.group(1)
    return None


def generate_link_name(title: str, quality: str | None) -> str:
    if quality and quality.lower() not in title.lower():
        return f"{title} {quality}"
    return title


def clean_title(raw_title: str) -> str:
    title = TITLE_TAG_PATTERN.sub("", raw_title)
    title = YEAR_PATTERN.sub("", title)
    return " ".join(title.split())
