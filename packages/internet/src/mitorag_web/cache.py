"""Async cache backends for API response caching."""

from __future__ import annotations

import importlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple


class AsyncCache(Protocol):
    async def get(self, key: str) -> Optional[object]:
        """Return cached JSON-compatible value, or None."""
        ...

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        """Cache a JSON-compatible value."""
        ...


@dataclass
class _CacheEntry:
    value: object
    expires_at: float


class MemoryCache:
    """In-memory async cache useful for tests and local development."""

    def __init__(self) -> None:
        self._items: Dict[str, _CacheEntry] = {}

    async def get(self, key: str) -> Optional[object]:
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._items.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        self._items[key] = _CacheEntry(value=value, expires_at=time.time() + ttl_seconds)


class RedisCache:
    """Optional Redis cache using redis.asyncio when installed."""

    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "mitorag:web") -> None:
        redis_module: Any = importlib.import_module("redis.asyncio")
        self._client: Any = redis_module.from_url(url, decode_responses=True)
        self.prefix = prefix

    async def get(self, key: str) -> Optional[object]:
        raw: Optional[str] = await self._client.get(self._key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        await self._client.setex(self._key(key), ttl_seconds, json.dumps(value))

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"


def cache_key(namespace: str, url: str, params: Tuple[Tuple[str, str], ...]) -> str:
    return f"{namespace}:{url}?{json.dumps(params, sort_keys=True)}"
