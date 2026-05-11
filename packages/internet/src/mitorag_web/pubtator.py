"""PubTator3 API for named entity recognition."""

from __future__ import annotations

from typing import List, Mapping, Optional, Sequence, cast

from mitorag_web.cache import AsyncCache, cache_key
from mitorag_web.models import PubTatorAnnotation
from mitorag_web.rate_limiter import AsyncRateLimiter
from mitorag_web.transport import AsyncHTTPTransport, StdlibAsyncHTTPTransport, normalized_params


class PubTatorClient:
    """PubTator3 BioC JSON export client."""

    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
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

    async def annotate_pmids(self, pmids: List[str]) -> List[PubTatorAnnotation]:
        if not pmids:
            return []
        params = {"pmids": ",".join(pmids)}
        payload = await self._get_json(
            f"{self.BASE_URL}/publications/export/biocjson",
            params,
        )
        return parse_pubtator_annotations(payload)

    async def _get_json(self, url: str, params: Mapping[str, object]) -> object:
        key = cache_key("pubtator", url, normalized_params(params))
        if self.cache is not None:
            cached = await self.cache.get(key)
            if cached is not None:
                return cached
        await self.rate_limiter.acquire()
        payload = await self.transport.get_json(url, params=params)
        if self.cache is not None:
            await self.cache.set(key, payload, self.CACHE_TTL_SECONDS)
        return payload


def parse_pubtator_annotations(payload: object) -> List[PubTatorAnnotation]:
    annotations: List[PubTatorAnnotation] = []
    for document in _documents(payload):
        pmid = str(_as_mapping(document).get("id", ""))
        for passage in _as_list(_as_mapping(document).get("passages", [])):
            for annotation in _as_list(_as_mapping(passage).get("annotations", [])):
                item = _as_mapping(annotation)
                infons = _as_mapping(item.get("infons", {}))
                start, end = _location(item)
                annotations.append(
                    PubTatorAnnotation(
                        pmid=pmid,
                        text=str(item.get("text", "")),
                        entity_type=str(infons.get("type") or infons.get("biotype") or ""),
                        identifier=_optional_str(infons.get("identifier")),
                        start=start,
                        end=end,
                    )
                )
    return annotations


def _documents(payload: object) -> Sequence[object]:
    mapping = _as_mapping(payload)
    documents = mapping.get("documents")
    if isinstance(documents, list):
        return cast(Sequence[object], documents)
    if isinstance(payload, list):
        return cast(Sequence[object], payload)
    return []


def _location(item: Mapping[str, object]) -> tuple[Optional[int], Optional[int]]:
    locations = _as_list(item.get("locations", []))
    if not locations:
        return None, None
    location = _as_mapping(locations[0])
    offset = _optional_int(location.get("offset"))
    length = _optional_int(location.get("length"))
    if offset is None:
        return None, None
    return offset, offset + (length or 0)


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
