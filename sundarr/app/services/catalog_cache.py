"""Redis 媒体目录缓存；Redis 不可用时自动退化为直连 Provider。"""

from __future__ import annotations

import hashlib
import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any

from redis.asyncio import Redis

from sundarr.app.config import get_settings


logger = logging.getLogger("sundarr.catalog.cache")


class CatalogCache:
    def __init__(self) -> None:
        self._client: Redis | None = None
        self._redis_url: str | None = None
        self._event_loop: asyncio.AbstractEventLoop | None = None

    def make_key(self, namespace: str, values: Mapping[str, Any]) -> str:
        normalized = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"sundarr:catalog:{namespace}:{digest}"

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            value = await self._get_client().get(key)
        except Exception as exc:
            logger.debug("读取目录缓存失败：%s", exc)
            return None
        if value is None:
            return None
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError) as exc:
            logger.warning("目录缓存内容无效，忽略：key=%s error=%s", key, exc)
            return None
        return decoded if isinstance(decoded, dict) else None

    async def set(self, key: str, value: Mapping[str, Any]) -> None:
        settings = get_settings()
        try:
            await self._get_client().setex(
                key,
                settings.catalog_stale_ttl_seconds,
                json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str),
            )
        except Exception as exc:
            logger.debug("写入目录缓存失败：%s", exc)

    async def close(self) -> None:
        client = self._client
        self._client = None
        self._redis_url = None
        self._event_loop = None
        if client is not None:
            try:
                await client.aclose()
            except RuntimeError as exc:
                if "Event loop is closed" not in str(exc):
                    raise

    def _get_client(self) -> Redis:
        redis_url = get_settings().redis_url
        event_loop = asyncio.get_running_loop()
        if (
            self._client is None
            or self._redis_url != redis_url
            or self._event_loop is not event_loop
        ):
            self._client = Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            self._redis_url = redis_url
            self._event_loop = event_loop
        return self._client


catalog_cache = CatalogCache()
