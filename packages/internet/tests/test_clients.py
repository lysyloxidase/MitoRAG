from __future__ import annotations

import asyncio
import time
from typing import Mapping, Optional

from mitorag_agents.web_rag import WebRAGAgent
from mitorag_web.biorxiv import BioRxivClient
from mitorag_web.cache import MemoryCache
from mitorag_web.europe_pmc import EuropePMCClient
from mitorag_web.pubmed import PubMedClient
from mitorag_web.pubtator import PubTatorClient
from mitorag_web.rate_limiter import AsyncRateLimiter
from mitorag_web.semantic_scholar import SemanticScholarClient
from mitorag_web.transport import Params

PUBMED_XML = """\
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>{pmid}</PMID>
      <Article>
        <ArticleTitle>Complex I cryo-EM architecture in mitochondria</ArticleTitle>
        <Abstract>
          <AbstractText>Mitochondrial Complex I contains ND1-ND6 and ND4L subunits.</AbstractText>
        </Abstract>
        <Journal><Title>Nature Mitochondria</Title></Journal>
        <JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList><ArticleId IdType="doi">10.1234/complex-i</ArticleId></ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object], Optional[Mapping[str, str]]]] = []

    async def get_json(
        self,
        url: str,
        params: Optional[Params] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> object:
        params_dict = dict(params or {})
        self.calls.append(("json", url, params_dict, headers))
        if "esearch.fcgi" in url:
            return {"esearchresult": {"idlist": ["33174596", "1", "2", "3", "4"]}}
        if "elink.fcgi" in url:
            return {"linksets": [{"linksetdbs": [{"links": ["101", "102"]}]}]}
        if "semanticscholar.org" in url and url.endswith("/paper/search"):
            return {
                "data": [
                    {
                        "paperId": "S2A",
                        "title": "Mitophagy and PINK1 signaling",
                        "abstract": "PINK1 recruits Parkin to depolarized mitochondria.",
                        "year": 2023,
                        "citationCount": 42,
                        "externalIds": {"DOI": "10.5555/pink1", "PMID": "90001"},
                        "embedding": {"vector": [0.1, 0.2]},
                    }
                ]
            }
        if "europepmc" in url:
            return {
                "resultList": {
                    "result": [
                        {
                            "id": "90002",
                            "pmid": "90002",
                            "source": "MED",
                            "title": "Complex I subunits in mitochondrial disease",
                            "abstractText": "MT-ND4 and other subunits are disease relevant.",
                            "pubYear": "2022",
                            "doi": "10.7777/europepmc",
                            "journalTitle": "Europe PMC Test Journal",
                        }
                    ]
                }
            }
        if "api.biorxiv.org" in url:
            return {
                "collection": [
                    {
                        "doi": "10.1101/2026.01.02.123456",
                        "title": "PINK1 mitophagy preprint",
                        "abstract": "A preprint on mitochondrial quality control and Parkin.",
                        "date": "2026-01-02",
                        "server": "biorxiv",
                        "category": "cell_biology",
                        "authors": "A Author",
                    }
                ]
            }
        if "pubtator3-api" in url:
            return {
                "documents": [
                    {
                        "id": "33174596",
                        "passages": [
                            {
                                "annotations": [
                                    {
                                        "text": "mitochondrial",
                                        "infons": {"type": "Species", "identifier": "9606"},
                                        "locations": [{"offset": 0, "length": 13}],
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }
        raise AssertionError(f"Unhandled JSON URL: {url}")

    async def get_text(
        self,
        url: str,
        params: Optional[Params] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> str:
        params_dict = dict(params or {})
        self.calls.append(("text", url, params_dict, headers))
        if "efetch.fcgi" in url:
            return PUBMED_XML.format(pmid=params_dict.get("id", "33174596"))
        raise AssertionError(f"Unhandled text URL: {url}")


def fast_limiter() -> AsyncRateLimiter:
    return AsyncRateLimiter(1_000_000.0)


def build_agent(transport: FakeTransport, cache: MemoryCache) -> WebRAGAgent:
    return WebRAGAgent(
        pubmed=PubMedClient(transport=transport, cache=cache, rate_limiter=fast_limiter()),
        semantic_scholar=SemanticScholarClient(
            transport=transport,
            cache=cache,
            rate_limiter=fast_limiter(),
        ),
        europe_pmc=EuropePMCClient(transport=transport, cache=cache, rate_limiter=fast_limiter()),
        biorxiv=BioRxivClient(transport=transport, cache=cache, rate_limiter=fast_limiter()),
        pubtator=PubTatorClient(transport=transport, cache=cache, rate_limiter=fast_limiter()),
    )


def test_pubmed_search_adds_mitochondrial_filter_and_returns_pmids() -> None:
    transport = FakeTransport()
    client = PubMedClient(transport=transport, rate_limiter=fast_limiter())

    results = asyncio.run(client.search("Complex I cryo-EM", max_results=5))

    assert len(results) >= 5
    assert all(result.pmid for result in results)
    term = transport.calls[0][2]["term"]
    assert "Complex I cryo-EM" in str(term)
    assert "mitochondri*" in str(term)


def test_semantic_scholar_search_returns_dois() -> None:
    transport = FakeTransport()
    client = SemanticScholarClient(transport=transport, rate_limiter=fast_limiter())

    papers = asyncio.run(client.search("mitophagy PINK1"))

    assert papers[0].doi == "10.5555/pink1"
    assert papers[0].paper_id == "S2A"


def test_europe_pmc_search_works_without_api_key() -> None:
    transport = FakeTransport()
    client = EuropePMCClient(transport=transport, rate_limiter=fast_limiter())

    results = asyncio.run(client.search("Complex I subunits"))

    assert results[0].pmid == "90002"
    assert transport.calls[0][3] is None


def test_biorxiv_search_returns_preprints_with_dates() -> None:
    transport = FakeTransport()
    client = BioRxivClient(transport=transport, rate_limiter=fast_limiter())

    preprints = asyncio.run(client.search("PINK1", max_results=5))

    assert preprints[0].doi.startswith("10.1101/")
    assert preprints[0].date == "2026-01-02"


def test_pubtator_annotates_pubmed_ids() -> None:
    transport = FakeTransport()
    client = PubTatorClient(transport=transport, rate_limiter=fast_limiter())

    annotations = asyncio.run(client.annotate_pmids(["33174596"]))

    assert annotations[0].pmid == "33174596"
    assert annotations[0].text == "mitochondrial"


def test_web_rag_fanout_returns_results_within_five_seconds() -> None:
    transport = FakeTransport()
    agent = build_agent(transport, MemoryCache())

    start = time.perf_counter()
    chunks = asyncio.run(agent.search("Complex I cryo-EM"))
    elapsed = time.perf_counter() - start

    assert elapsed < 5
    assert len(chunks) >= 4
    assert {chunk.source for chunk in chunks} >= {"pubmed", "semantic_scholar", "europe_pmc"}
    assert any(
        annotation.text == "mitochondrial"
        for chunk in chunks
        for annotation in chunk.annotations
    )


def test_cached_repeated_web_query_does_not_issue_new_api_calls() -> None:
    transport = FakeTransport()
    agent = build_agent(transport, MemoryCache())

    asyncio.run(agent.search("Complex I cryo-EM"))
    first_count = len(transport.calls)
    asyncio.run(agent.search("Complex I cryo-EM"))

    assert len(transport.calls) == first_count
