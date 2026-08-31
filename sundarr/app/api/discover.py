"""媒体发现 Core API。"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.plugins.contracts import CatalogQuery, CatalogSort, MediaType
from sundarr.app.schemas.discover import (
    CatalogProviderResponse,
    DiscoverPageResponse,
    FollowResponse,
    MediaSubjectDetail,
    WatchlistPageResponse,
    WatchlistSyncResponse,
    YearHydrationRequest,
    YearHydrationResponse,
)
from sundarr.app.services.media_discovery_service import (
    CatalogProviderUnavailableError,
    CatalogQueryUnsupportedError,
    MediaIdentityConflictError,
    media_discovery_service,
)
from sundarr.app.services.poster_proxy_service import (
    PosterFetchError,
    PosterNotFoundError,
    PosterProviderUnavailableError,
    PosterSourceMismatchError,
    poster_proxy_service,
)
from sundarr.app.services.watchlist_service import (
    WatchlistProviderUnavailableError,
    WatchlistSyncFailedError,
    watchlist_service,
)


router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("/providers", response_model=list[CatalogProviderResponse])
def list_catalog_providers() -> list[CatalogProviderResponse]:
    return media_discovery_service.list_providers()


@router.get("/search", response_model=DiscoverPageResponse)
async def search_catalog(
    q: str = Query(min_length=1),
    provider_id: str | None = None,
    media_type: MediaType | None = None,
    genre: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
    year_from: int | None = Query(default=None, ge=1),
    year_to: int | None = Query(default=None, ge=1),
    sort: CatalogSort | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    continuation_token: str | None = None,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> DiscoverPageResponse:
    query = _catalog_query(q, media_type, genre, region, year_from, year_to, sort, limit, continuation_token)
    return await _run_query(db, "search", query, provider_id, refresh)


@router.get("/trending", response_model=DiscoverPageResponse)
async def trending_catalog(
    provider_id: str | None = None,
    media_type: MediaType | None = None,
    genre: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
    year_from: int | None = Query(default=None, ge=1),
    year_to: int | None = Query(default=None, ge=1),
    sort: CatalogSort | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    continuation_token: str | None = None,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> DiscoverPageResponse:
    query = _catalog_query(None, media_type, genre, region, year_from, year_to, sort, limit, continuation_token)
    return await _run_query(db, "trending", query, provider_id, refresh)


@router.get("/categories", response_model=DiscoverPageResponse)
async def category_catalog(
    provider_id: str | None = None,
    media_type: MediaType | None = None,
    genre: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
    year_from: int | None = Query(default=None, ge=1),
    year_to: int | None = Query(default=None, ge=1),
    sort: CatalogSort | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    continuation_token: str | None = None,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> DiscoverPageResponse:
    query = _catalog_query(None, media_type, genre, region, year_from, year_to, sort, limit, continuation_token)
    return await _run_query(db, "categories", query, provider_id, refresh)


@router.get("/watchlist", response_model=WatchlistPageResponse)
def list_watchlist(
    provider_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> WatchlistPageResponse:
    return watchlist_service.list_entries(db, provider_id=provider_id, limit=limit)


@router.post("/hydrate-years", response_model=YearHydrationResponse)
async def hydrate_discover_years(
    data: YearHydrationRequest,
    db: Session = Depends(get_db),
) -> YearHydrationResponse:
    try:
        return await media_discovery_service.hydrate_years(
            db,
            data.provider_id,
            data.media_subject_ids,
        )
    except CatalogQueryUnsupportedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CatalogProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/watchlist/{provider_id}/sync", response_model=WatchlistSyncResponse)
async def sync_watchlist(
    provider_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> WatchlistSyncResponse:
    try:
        return await watchlist_service.sync(db, provider_id, limit=limit)
    except WatchlistProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except WatchlistSyncFailedError as exc:
        raise HTTPException(status_code=502, detail=f"想看同步失败：{exc}") from exc


@router.get("/{media_subject_id}", response_model=MediaSubjectDetail)
async def get_media_subject(
    media_subject_id: str,
    provider_id: str | None = None,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> MediaSubjectDetail:
    try:
        result = await media_discovery_service.get_detail(
            db,
            media_subject_id,
            provider_id=provider_id,
            refresh=refresh,
        )
    except CatalogQueryUnsupportedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MediaIdentityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="媒体主体不存在")
    return result


@router.get("/{media_subject_id}/poster", response_class=Response)
async def get_media_subject_poster(
    media_subject_id: str,
    request: Request,
    provider_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> Response:
    unknown_parameters = set(request.query_params.keys()) - {"provider_id"}
    if unknown_parameters:
        names = "、".join(sorted(unknown_parameters))
        raise HTTPException(status_code=422, detail=f"海报中继不接受参数：{names}")
    try:
        payload = await poster_proxy_service.fetch(db, media_subject_id, provider_id)
    except PosterNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PosterSourceMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PosterProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PosterFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(
        content=payload.body,
        media_type=payload.media_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{media_subject_id}/follow", response_model=FollowResponse)
def follow_media_subject(
    media_subject_id: str,
    db: Session = Depends(get_db),
) -> FollowResponse:
    result = media_discovery_service.set_followed(db, media_subject_id, True)
    if result is None:
        raise HTTPException(status_code=404, detail="媒体主体不存在")
    return result


@router.delete("/{media_subject_id}/follow", response_model=FollowResponse)
def unfollow_media_subject(
    media_subject_id: str,
    db: Session = Depends(get_db),
) -> FollowResponse:
    result = media_discovery_service.set_followed(db, media_subject_id, False)
    if result is None:
        raise HTTPException(status_code=404, detail="媒体主体不存在")
    return result


def _catalog_query(
    keyword: str | None,
    media_type: MediaType | None,
    genres: list[str],
    regions: list[str],
    year_from: int | None,
    year_to: int | None,
    sort: CatalogSort | None,
    limit: int,
    continuation_token: str | None,
) -> CatalogQuery:
    try:
        return CatalogQuery(
            keyword=keyword,
            media_type=media_type,
            genres=tuple(genres),
            regions=tuple(regions),
            year_from=year_from,
            year_to=year_to,
            sort=sort,
            limit=limit,
            continuation_token=continuation_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _run_query(
    db: Session,
    action: str,
    query: CatalogQuery,
    provider_id: str | None,
    refresh: bool,
) -> DiscoverPageResponse:
    try:
        return await media_discovery_service.query(
            db,
            action,  # type: ignore[arg-type]
            query,
            provider_id=provider_id,
            refresh=refresh,
        )
    except CatalogQueryUnsupportedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MediaIdentityConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CatalogProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
