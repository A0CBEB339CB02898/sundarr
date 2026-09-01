"""发现页缺失年份渐进补全测试。"""

from dataclasses import dataclass
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import MediaSubject
from sundarr.app.plugins.contracts import (
    CatalogCapabilities,
    CatalogItem,
    CatalogOperation,
    CatalogPage,
    CatalogQuery,
    MediaType,
)
from sundarr.app.plugins.runtime_registry import catalog_provider_registry


@dataclass
class YearlessCatalogProvider:
    id: str = "yearless-catalog"
    detail_calls: int = 0

    def describe_capabilities(self) -> CatalogCapabilities:
        return CatalogCapabilities(
            operations=frozenset(
                {CatalogOperation.TRENDING, CatalogOperation.DETAIL}
            ),
            identity_namespaces=frozenset({"test.movie"}),
        )

    async def search(self, query: CatalogQuery) -> CatalogPage:
        raise NotImplementedError

    async def trending(self, query: CatalogQuery) -> CatalogPage:
        return CatalogPage(
            items=(
                CatalogItem(
                    external_id="yearless-603",
                    external_id_provider="test.movie",
                    title="等待年份的电影",
                    media_type=MediaType.MOVIE,
                    poster_url="https://image.example.invalid/yearless.jpg",
                ),
            ),
            continuation_token="year-next",
        )

    async def categories(self, query: CatalogQuery) -> CatalogPage:
        raise NotImplementedError

    async def get_detail(
        self,
        external_id: str,
        media_type: MediaType | None = None,
    ) -> CatalogItem:
        self.detail_calls += 1
        return CatalogItem(
            external_id=external_id,
            external_id_provider="test.movie",
            title="等待年份的电影",
            media_type=MediaType.MOVIE,
            year=2026,
            poster_url="https://image.example.invalid/yearless.jpg",
        )


@dataclass
class SearchYearCatalogProvider(YearlessCatalogProvider):
    search_calls: int = 0

    def describe_capabilities(self) -> CatalogCapabilities:
        return CatalogCapabilities(
            operations=frozenset(
                {
                    CatalogOperation.SEARCH,
                    CatalogOperation.TRENDING,
                    CatalogOperation.DETAIL,
                }
            ),
            identity_namespaces=frozenset({"test.movie"}),
        )

    async def search(self, query: CatalogQuery) -> CatalogPage:
        self.search_calls += 1
        return CatalogPage(
            items=(
                CatalogItem(
                    external_id="similar-but-wrong",
                    external_id_provider="test.movie",
                    title=query.keyword or "",
                    media_type=MediaType.MOVIE,
                    year=1999,
                ),
                CatalogItem(
                    external_id="yearless-603",
                    external_id_provider="test.movie",
                    title=query.keyword or "",
                    media_type=MediaType.MOVIE,
                    year=2027,
                ),
            )
        )

    async def get_detail(
        self,
        external_id: str,
        media_type: MediaType | None = None,
    ) -> CatalogItem:
        raise AssertionError("外部 ID 精确搜索已得到年份时不应读取详情")


@pytest.fixture(autouse=True)
def clear_catalog_registry():
    catalog_provider_registry.clear()
    yield
    catalog_provider_registry.clear()


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_year_hydration_persists_and_refreshes_cached_page(
    db_session: Session,
) -> None:
    provider = YearlessCatalogProvider(id=f"yearless-{uuid4().hex}")
    catalog_provider_registry.register(provider.id, provider)
    client = make_client(db_session)
    first_page = client.get(
        "/discover/trending",
        params={"provider_id": provider.id, "refresh": "true"},
    ).json()
    media_subject_id = first_page["items"][0]["media_subject_id"]

    assert first_page["items"][0]["release_year"] is None
    hydrated = client.post(
        "/discover/hydrate-years",
        json={
            "provider_id": provider.id,
            "media_subject_ids": [media_subject_id, "missing-subject"],
        },
    )

    assert hydrated.status_code == 200
    assert hydrated.json()["years"] == {media_subject_id: 2026}
    assert hydrated.json()["unresolved_ids"] == ["missing-subject"]
    assert provider.detail_calls == 1
    assert db_session.get(MediaSubject, media_subject_id).release_year == 2026

    cached_page = client.get(
        "/discover/trending",
        params={"provider_id": provider.id},
    )
    second_hydration = client.post(
        "/discover/hydrate-years",
        json={
            "provider_id": provider.id,
            "media_subject_ids": [media_subject_id, media_subject_id],
        },
    )

    assert cached_page.status_code == 200
    assert cached_page.json()["items"][0]["release_year"] == 2026
    assert second_hydration.json()["years"] == {media_subject_id: 2026}
    assert provider.detail_calls == 1


def test_year_hydration_validates_provider_and_batch_size(
    db_session: Session,
) -> None:
    client = make_client(db_session)
    missing_provider = client.post(
        "/discover/hydrate-years",
        json={"provider_id": "missing", "media_subject_ids": ["subject"]},
    )
    oversized = client.post(
        "/discover/hydrate-years",
        json={
            "provider_id": "missing",
            "media_subject_ids": [f"subject-{index}" for index in range(13)],
        },
    )

    assert missing_provider.status_code == 503
    assert oversized.status_code == 422


def test_year_hydration_prefers_exact_external_id_search(
    db_session: Session,
) -> None:
    provider = SearchYearCatalogProvider(id=f"search-year-{uuid4().hex}")
    catalog_provider_registry.register(provider.id, provider)
    client = make_client(db_session)
    first_page = client.get(
        "/discover/trending",
        params={"provider_id": provider.id, "refresh": "true"},
    ).json()
    media_subject_id = first_page["items"][0]["media_subject_id"]

    hydrated = client.post(
        "/discover/hydrate-years",
        json={
            "provider_id": provider.id,
            "media_subject_ids": [media_subject_id],
        },
    )

    assert hydrated.status_code == 200
    assert hydrated.json()["years"] == {media_subject_id: 2027}
    assert provider.search_calls == 1
    assert provider.detail_calls == 0
    assert db_session.get(MediaSubject, media_subject_id).release_year == 2027
