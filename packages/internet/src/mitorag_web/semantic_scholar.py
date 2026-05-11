"""Semantic Scholar Academic Graph API client."""

from __future__ import annotations

import os
from typing import List, Mapping, Optional, Sequence, Tuple, cast

from mitorag_web.cache import AsyncCache, cache_key
from mitorag_web.models import S2Paper
from mitorag_web.rate_limiter import AsyncRateLimiter
from mitorag_web.transport import AsyncHTTPTransport, StdlibAsyncHTTPTransport, normalized_params

S2_FIELDS = (
    "paperId,title,abstract,year,citationCount,externalIds,embedding,"
    "references.paperId,citations.paperId"
)


class SemanticScholarClient:
    """Semantic Scholar Academic Graph API client."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(
        self,
        api_key: Optional[str] = None,
        transport: Optional[AsyncHTTPTransport] = None,
        cache: Optional[AsyncCache] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("S2_API_KEY")
        self.transport = transport or StdlibAsyncHTTPTransport()
        self.cache = cache
        self.rate_limiter = rate_limiter or AsyncRateLimiter(1.0 if self.api_key else 0.5)

    async def search(
        self,
        query: str,
        max_results: int = 25,
        year_range: Optional[Tuple[int, int]] = None,
    ) -> List[S2Paper]:
        params: dict[str, object] = {
            "query": query,
            "limit": max_results,
            "fields": S2_FIELDS,
        }
        if year_range is not None:
            params["year"] = f"{year_range[0]}-{year_range[1]}"
        payload = await self._get_json(f"{self.BASE_URL}/paper/search", params)
        return [parse_s2_paper(item) for item in _as_list(_as_mapping(payload).get("data", []))]

    async def get_paper(self, paper_id: str) -> S2Paper:
        payload = await self._get_json(
            f"{self.BASE_URL}/paper/{paper_id}",
            {"fields": S2_FIELDS},
        )
        return parse_s2_paper(payload)

    async def get_references(self, paper_id: str, limit: int = 5) -> List[S2Paper]:
        payload = await self._get_json(
            f"{self.BASE_URL}/paper/{paper_id}/references",
            {"limit": limit, "fields": S2_FIELDS},
        )
        papers: List[S2Paper] = []
        for item in _as_list(_as_mapping(payload).get("data", [])):
            cited = _as_mapping(item).get("citedPaper")
            if cited is not None:
                papers.append(parse_s2_paper(cited))
        return papers

    async def get_citations(self, paper_id: str, limit: int = 5) -> List[S2Paper]:
        payload = await self._get_json(
            f"{self.BASE_URL}/paper/{paper_id}/citations",
            {"limit": limit, "fields": S2_FIELDS},
        )
        papers: List[S2Paper] = []
        for item in _as_list(_as_mapping(payload).get("data", [])):
            citing = _as_mapping(item).get("citingPaper")
            if citing is not None:
                papers.append(parse_s2_paper(citing))
        return papers

    async def _get_json(self, url: str, params: Mapping[str, object]) -> object:
        key = cache_key("semantic_scholar", url, normalized_params(params))
        if self.cache is not None:
            cached = await self.cache.get(key)
            if cached is not None:
                return cached
        await self.rate_limiter.acquire()
        payload = await self.transport.get_json(url, params=params, headers=self._headers())
        if self.cache is not None:
            await self.cache.set(key, payload, self.CACHE_TTL_SECONDS)
        return payload

    def _headers(self) -> Optional[Mapping[str, str]]:
        if not self.api_key:
            return None
        return {"x-api-key": self.api_key}


def parse_s2_paper(value: object) -> S2Paper:
    item = _as_mapping(value)
    external_ids = _string_mapping(item.get("externalIds", {}))
    embedding = _parse_embedding(item.get("embedding"))
    return S2Paper(
        paper_id=str(item.get("paperId", "")),
        title=str(item.get("title", "")),
        abstract=str(item.get("abstract") or ""),
        year=_optional_int(item.get("year")),
        citation_count=_optional_int(item.get("citationCount")) or 0,
        doi=external_ids.get("DOI"),
        pmid=external_ids.get("PMID"),
        external_ids=external_ids,
        embedding=embedding,
    )


def _parse_embedding(value: object) -> List[float]:
    item = _as_mapping(value)
    vector = item.get("vector")
    if not isinstance(vector, list):
        return []
    parsed: List[float] = []
    for element in cast(Sequence[object], vector):
        if isinstance(element, (int, float, str)):
            parsed.append(float(element))
    return parsed


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _as_list(value: object) -> Sequence[object]:
    if isinstance(value, list):
        return cast(Sequence[object], value)
    return []


def _string_mapping(value: object) -> Mapping[str, str]:
    mapping = _as_mapping(value)
    return {str(key): str(item) for key, item in mapping.items() if item is not None}


def _optional_int(value: object) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
