"""bioRxiv and medRxiv content API client."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Mapping, Optional, Sequence, cast

from mitorag_web.cache import AsyncCache, cache_key
from mitorag_web.models import BioRxivPreprint
from mitorag_web.rate_limiter import AsyncRateLimiter
from mitorag_web.transport import AsyncHTTPTransport, StdlibAsyncHTTPTransport, normalized_params


class BioRxivClient:
    """bioRxiv/medRxiv content API client."""

    BASE_URL = "https://api.biorxiv.org"
    CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(
        self,
        server: str = "biorxiv",
        transport: Optional[AsyncHTTPTransport] = None,
        cache: Optional[AsyncCache] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
    ) -> None:
        if server not in {"biorxiv", "medrxiv"}:
            raise ValueError("server must be biorxiv or medrxiv")
        self.server = server
        self.transport = transport or StdlibAsyncHTTPTransport()
        self.cache = cache
        self.rate_limiter = rate_limiter or AsyncRateLimiter(1.0)

    async def search(
        self,
        query: str,
        max_results: int = 20,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
    ) -> List[BioRxivPreprint]:
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=365))
        url = (
            f"{self.BASE_URL}/details/{self.server}/"
            f"{start.isoformat()}/{end.isoformat()}/0/json"
        )
        payload = await self._get_json(url, {})
        preprints = [parse_preprint(item, self.server) for item in _as_collection(payload)]
        filtered = _filter_preprints(preprints, query=query, category=category)
        return filtered[:max_results]

    async def _get_json(self, url: str, params: Mapping[str, object]) -> object:
        key = cache_key("biorxiv", url, normalized_params(params))
        if self.cache is not None:
            cached = await self.cache.get(key)
            if cached is not None:
                return cached
        await self.rate_limiter.acquire()
        payload = await self.transport.get_json(url, params=params)
        if self.cache is not None:
            await self.cache.set(key, payload, self.CACHE_TTL_SECONDS)
        return payload


def parse_preprint(value: object, server: str) -> BioRxivPreprint:
    item = _as_mapping(value)
    return BioRxivPreprint(
        doi=str(item.get("doi", "")),
        title=str(item.get("title", "")),
        abstract=str(item.get("abstract") or ""),
        date=str(item.get("date") or item.get("posted") or ""),
        server=str(item.get("server") or server),
        category=str(item.get("category") or ""),
        authors=str(item.get("authors") or ""),
    )


def _filter_preprints(
    preprints: Sequence[BioRxivPreprint],
    query: str,
    category: Optional[str],
) -> List[BioRxivPreprint]:
    terms = [term.lower() for term in query.split() if term]
    output: List[BioRxivPreprint] = []
    for preprint in preprints:
        if category and category.lower() != preprint.category.lower():
            continue
        haystack = f"{preprint.title} {preprint.abstract} {preprint.category}".lower()
        if not terms or any(term in haystack for term in terms):
            output.append(preprint)
    return output or list(preprints)


def _as_collection(payload: object) -> Sequence[object]:
    mapping = _as_mapping(payload)
    collection = mapping.get("collection")
    if isinstance(collection, list):
        return cast(Sequence[object], collection)
    return []


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}
