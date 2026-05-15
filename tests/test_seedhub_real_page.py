"""基于真实页面快照的 SeedHub 解析测试"""
from pathlib import Path

import pytest

from sundarr.app.sources.seedhub import SeedHubSource


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "seedhub_detail_page.html"


@pytest.fixture
def seedhub_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_title_extraction(seedhub_html: str) -> None:
    source = SeedHubSource()
    title = source._extract_title(seedhub_html)
    assert title == "好东西"


def test_seed_list_parsing(seedhub_html: str) -> None:
    source = SeedHubSource()
    metas = source._extract_per_link_metas(seedhub_html)
    seed_metas = [m for m in metas if m.get("published_at")]
    assert len(seed_metas) == 33, f"期望 33 个种子链接，实际 {len(seed_metas)}"
    first = seed_metas[0]
    assert "好东西" in first["name"]
    assert first["quality"] == "蓝光"
    assert first["published_at"] == "2025-05-28 21:27"


def test_pan_links_parsing(seedhub_html: str) -> None:
    source = SeedHubSource()
    metas = source._extract_per_link_metas(seedhub_html)
    pan_metas = [m for m in metas if not m.get("published_at")]
    assert len(pan_metas) == 143, f"期望 143 个网盘链接，实际 {len(pan_metas)}"
    first = pan_metas[0]
    assert "好东西" in first["name"]


def test_raw_title_contains_no_quality_or_year(seedhub_html: str) -> None:
    source = SeedHubSource()
    title = source._extract_title(seedhub_html)
    assert "4K" not in title
    assert "2024" not in title
    assert "2025" not in title
