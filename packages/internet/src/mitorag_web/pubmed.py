"""NCBI E-utilities API client."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Mapping, Optional, Sequence, cast

from mitorag_web.cache import AsyncCache, cache_key
from mitorag_web.models import PubMedAbstract, PubMedResult
from mitorag_web.rate_limiter import AsyncRateLimiter, pubmed_rate_limiter
from mitorag_web.transport import AsyncHTTPTransport, StdlibAsyncHTTPTransport, normalized_params


class PubMedClient:
    """NCBI E-utilities API client."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(
        self,
        email: str = "user@example.com",
        tool: str = "MitoRAG",
        api_key: Optional[str] = None,
        transport: Optional[AsyncHTTPTransport] = None,
        cache: Optional[AsyncCache] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
    ) -> None:
        self.email = email
        self.tool = tool
        self.api_key = api_key
        self.transport = transport or StdlibAsyncHTTPTransport()
        self.cache = cache
        self.rate_limiter = rate_limiter or pubmed_rate_limiter(api_key)

    async def search(self, query: str, max_results: int = 30) -> List[PubMedResult]:
        """Search PubMed. Auto-appends mitochondrial domain filter."""

        mito_query = f"({query}) AND mitochondri*"
        params = self._base_params(
            {
                "db": "pubmed",
                "term": mito_query,
                "retmax": max_results,
                "retmode": "json",
            }
        )
        payload = await self._get_json(f"{self.BASE_URL}/esearch.fcgi", params)
        result = _as_mapping(payload).get("esearchresult", {})
        ids = _as_string_list(_as_mapping(result).get("idlist", []))
        return [PubMedResult(pmid=pmid) for pmid in ids]

    async def fetch_abstract(self, pmid: str) -> PubMedAbstract:
        """Fetch full abstract and metadata for a PMID."""

        params = self._base_params(
            {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml",
            }
        )
        xml_text = await self._get_text(f"{self.BASE_URL}/efetch.fcgi", params)
        return parse_pubmed_xml(xml_text, pmid)

    async def get_citations(self, pmid: str, direction: str = "both") -> List[str]:
        """Get citing and/or cited-by PMIDs."""

        linknames: List[str] = []
        if direction in {"both", "cited_by", "citing"}:
            linknames.append("pubmed_pubmed_citedin")
        if direction in {"both", "references", "cited"}:
            linknames.append("pubmed_pubmed_refs")

        citations: List[str] = []
        for linkname in linknames:
            params = self._base_params(
                {
                    "dbfrom": "pubmed",
                    "id": pmid,
                    "linkname": linkname,
                    "retmode": "json",
                }
            )
            payload = await self._get_json(f"{self.BASE_URL}/elink.fcgi", params)
            citations.extend(parse_elink_pmids(payload))
        return _dedupe(citations)

    def _base_params(self, params: Mapping[str, object]) -> dict[str, object]:
        merged = dict(params)
        merged["tool"] = self.tool
        merged["email"] = self.email
        if self.api_key:
            merged["api_key"] = self.api_key
        return merged

    async def _get_json(self, url: str, params: Mapping[str, object]) -> object:
        key = cache_key("pubmed", url, normalized_params(params))
        if self.cache is not None:
            cached = await self.cache.get(key)
            if cached is not None:
                return cached
        await self.rate_limiter.acquire()
        payload = await self.transport.get_json(url, params=params)
        if self.cache is not None:
            await self.cache.set(key, payload, self.CACHE_TTL_SECONDS)
        return payload

    async def _get_text(self, url: str, params: Mapping[str, object]) -> str:
        key = cache_key("pubmed", url, normalized_params(params))
        if self.cache is not None:
            cached = await self.cache.get(key)
            if isinstance(cached, str):
                return cached
        await self.rate_limiter.acquire()
        payload = await self.transport.get_text(url, params=params)
        if self.cache is not None:
            await self.cache.set(key, payload, self.CACHE_TTL_SECONDS)
        return payload


def parse_pubmed_xml(xml_text: str, fallback_pmid: str) -> PubMedAbstract:
    root = ET.fromstring(xml_text)
    article = root.find(".//PubmedArticle")
    if article is None:
        return PubMedAbstract(pmid=fallback_pmid, title="", abstract="")

    pmid = _text(article.find(".//PMID")) or fallback_pmid
    title = _text(article.find(".//ArticleTitle")) or ""
    abstract_parts = [_text(node) for node in article.findall(".//Abstract/AbstractText")]
    abstract = " ".join(part for part in abstract_parts if part)
    journal = _text(article.find(".//Journal/Title")) or ""
    year = _parse_year(_text(article.find(".//PubDate/Year")))
    doi = None
    for article_id in article.findall(".//ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            doi = _text(article_id)
            break
    authors: List[str] = []
    for author in cast(Sequence[ET.Element], article.findall(".//Author")):
        name_parts = [_text(author.find("ForeName")), _text(author.find("LastName"))]
        authors.append(" ".join(part for part in name_parts if part))
    return PubMedAbstract(
        pmid=pmid,
        title=title,
        abstract=abstract,
        journal=journal,
        year=year,
        doi=doi,
        authors=[author for author in authors if author],
    )


def parse_elink_pmids(payload: object) -> List[str]:
    root = _as_mapping(payload)
    sets = _as_list(root.get("linksets", []))
    pmids: List[str] = []
    for linkset in sets:
        for database in _as_list(_as_mapping(linkset).get("linksetdbs", [])):
            links = _as_list(_as_mapping(database).get("links", []))
            pmids.extend(str(link) for link in links)
    return pmids


def _text(element: Optional[ET.Element]) -> Optional[str]:
    if element is None or element.text is None:
        return None
    return element.text.strip()


def _parse_year(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _as_list(value: object) -> Sequence[object]:
    if isinstance(value, list):
        return cast(Sequence[object], value)
    return []


def _as_string_list(value: object) -> List[str]:
    return [str(item) for item in _as_list(value)]


def _dedupe(values: Sequence[str]) -> List[str]:
    seen: dict[str, None] = {}
    for value in values:
        seen.setdefault(value, None)
    return list(seen.keys())
