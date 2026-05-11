"""Europe PMC REST API client."""

from __future__ import annotations

from typing import List, Mapping, Optional, Sequence, cast

from mitorag_web.cache import AsyncCache, cache_key
from mitorag_web.models import EuropePMCResult
from mitorag_web.rate_limiter import AsyncRateLimiter
from mitorag_web.transport import AsyncHTTPTransport, StdlibAsyncHTTPTransport, normalized_params


class EuropePMCClient:
    """Europe PMC REST API client."""

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(
        self,
        transport: Optional[AsyncHTTPTransport] = None,
        cache: Optional[AsyncCache] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
    ) -> None:
        self.transport = transport or StdlibAsyncHTTPTransport()
        self.cache = cache
        self.rate_limiter = rate_limiter or AsyncRateLimiter(3.0)

    async def search(self, query: str, max_results: int = 25) -> List[EuropePMCResult]:
        params = {
            "query": f"({query}) AND mitochondri*",
            "format": "json",
            "pageSize": max_results,
        }
        payload = await self._get_json(f"{self.BASE_URL}/search", params)
        result_list = _as_mapping(_as_mapping(payload).get("resultList", {}))
        return [parse_europe_pmc(item) for item in _as_list(result_list.get("result", []))]

    async def _get_json(self, url: str, params: Mapping[str, object]) -> object:
        key = cache_key("europe_pmc", url, normalized_params(params))
        if self.cache is not None:
            cached = await self.cache.get(key)
            if cached is not None:
                return cached
        await self.rate_limiter.acquire()
        payload = await self.transport.get_json(url, params=params)
        if self.cache is not None:
            await self.cache.set(key, payload, self.CACHE_TTL_SECONDS)
        return payload


def parse_europe_pmc(value: object) -> EuropePMCResult:
    item = _as_mapping(value)
    return EuropePMCResult(
        id=str(item.get("id", "")),
        source=str(item.get("source", "")),
        title=str(item.get("title", "")),
        abstract=str(item.get("abstractText") or ""),
        year=_optional_int(item.get("pubYear")),
        doi=_optional_str(item.get("doi")),
        pmid=_optional_str(item.get("pmid") or item.get("id")),
        journal=str(item.get("journalTitle") or ""),
    )


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _as_list(value: object) -> Sequence[object]:
    if isinstance(value, list):
        return cast(Sequence[object], value)
    return []


def _optional_int(value: object) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _optional_str(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text or None
