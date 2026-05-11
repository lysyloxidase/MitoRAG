"""Agent 4: web RAG retrieval node."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, replace
from typing import Iterable, List, Mapping, Optional, Sequence, Union, cast

from mitorag_agents.state import MitoRAGState, StateUpdate
from mitorag_agents.utils import ranked_chunk, timed_node
from mitorag_retrieval.embedder import EmbeddingBackend, HashingEmbeddingBackend
from mitorag_retrieval.models import RankedChunk
from mitorag_retrieval.vector_store import cosine_similarity, normalize_vector
from mitorag_web.biorxiv import BioRxivClient
from mitorag_web.cache import AsyncCache, RedisCache
from mitorag_web.europe_pmc import EuropePMCClient
from mitorag_web.models import (
    BioRxivPreprint,
    EuropePMCResult,
    PubMedAbstract,
    PubMedResult,
    PubTatorAnnotation,
    S2Paper,
    WebChunk,
    paper_key,
)
from mitorag_web.pubmed import PubMedClient
from mitorag_web.pubtator import PubTatorClient
from mitorag_web.semantic_scholar import SemanticScholarClient

WebSearchResult = Union[PubMedResult, S2Paper, EuropePMCResult, BioRxivPreprint]


@dataclass(frozen=True)
class _PaperCandidate:
    key: str
    source: str
    title: str
    abstract: str = ""
    pmid: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    score_hint: float = 0.0


class WebRAGAgent:
    """Fan-out internet search across free scientific databases."""

    def __init__(
        self,
        pubmed: Optional[PubMedClient] = None,
        semantic_scholar: Optional[SemanticScholarClient] = None,
        europe_pmc: Optional[EuropePMCClient] = None,
        biorxiv: Optional[BioRxivClient] = None,
        pubtator: Optional[PubTatorClient] = None,
        embedding_backend: Optional[EmbeddingBackend] = None,
    ) -> None:
        cache = _default_cache()
        self.pubmed = pubmed or PubMedClient(
            email=os.environ.get("NCBI_EMAIL", "user@example.com"),
            api_key=os.environ.get("NCBI_API_KEY") or None,
            cache=cache,
        )
        self.semantic_scholar = semantic_scholar or SemanticScholarClient(cache=cache)
        self.europe_pmc = europe_pmc or EuropePMCClient(cache=cache)
        self.biorxiv = biorxiv or BioRxivClient(cache=cache)
        self.pubtator = pubtator or PubTatorClient(cache=cache)
        self.embedding_backend = embedding_backend or HashingEmbeddingBackend(
            "pubmedbert-web",
            salt="web-pubmedbert",
        )

    async def search(self, query: str) -> List[WebChunk]:
        """Search all scientific APIs, dedupe papers, annotate, and score abstracts."""

        responses = await asyncio.gather(
            self.pubmed.search(query),
            self.semantic_scholar.search(query),
            self.europe_pmc.search(query),
            self.biorxiv.search(query),
            return_exceptions=True,
        )
        merged = self._deduplicate(_flatten_results(responses))
        abstracts = await self._fetch_abstracts(merged[:30])
        annotations = await self._annotate_pmids(_pmids(abstracts))
        return self._embed_chunks(query, abstracts, annotations)

    async def search_many(self, queries: Sequence[str]) -> List[WebChunk]:
        """Run search for several planner sub-queries and merge the result pool."""

        outputs = await asyncio.gather(*(self.search(query) for query in queries))
        by_key: dict[str, WebChunk] = {}
        for chunk in (item for result in outputs for item in result):
            key = paper_key(chunk.doi, chunk.pmid, chunk.id)
            existing = by_key.get(key)
            if existing is None or chunk.score > existing.score:
                by_key[key] = chunk
        return sorted(by_key.values(), key=lambda item: item.score, reverse=True)

    async def search_ranked(self, query: str, sub_queries: Sequence[str] = ()) -> List[RankedChunk]:
        queries = list(sub_queries) or [query]
        chunks = await self.search_many(queries)
        return web_chunks_to_ranked(chunks)

    def _deduplicate(self, results: Sequence[WebSearchResult]) -> List[_PaperCandidate]:
        candidates = [_candidate_from_result(result, index) for index, result in enumerate(results)]
        by_key: dict[str, _PaperCandidate] = {}
        for candidate in candidates:
            existing = by_key.get(candidate.key)
            if existing is None or _candidate_rank(candidate) > _candidate_rank(existing):
                by_key[candidate.key] = candidate
        return sorted(by_key.values(), key=_candidate_rank, reverse=True)

    async def _fetch_abstracts(
        self,
        candidates: Sequence[_PaperCandidate],
    ) -> List[_PaperCandidate]:
        hydrated = await asyncio.gather(
            *(self._hydrate_pubmed(candidate) for candidate in candidates),
            return_exceptions=True,
        )
        output: List[_PaperCandidate] = []
        for original, item in zip(candidates, hydrated):
            if isinstance(item, Exception):
                output.append(original)
            else:
                output.append(cast(_PaperCandidate, item))
        return output

    async def _hydrate_pubmed(self, candidate: _PaperCandidate) -> _PaperCandidate:
        if candidate.source != "pubmed" or not candidate.pmid:
            return candidate
        abstract = await self.pubmed.fetch_abstract(candidate.pmid)
        return _candidate_from_pubmed_abstract(abstract, candidate.score_hint)

    async def _annotate_pmids(self, pmids: Sequence[str]) -> Mapping[str, List[PubTatorAnnotation]]:
        if not pmids:
            return {}
        try:
            annotations = await self.pubtator.annotate_pmids(list(pmids))
        except Exception:
            return {}
        grouped: dict[str, List[PubTatorAnnotation]] = {}
        for annotation in annotations:
            grouped.setdefault(annotation.pmid, []).append(annotation)
        return grouped

    def _embed_chunks(
        self,
        query: str,
        candidates: Sequence[_PaperCandidate],
        annotations: Mapping[str, Sequence[PubTatorAnnotation]],
    ) -> List[WebChunk]:
        texts = [_chunk_text(candidate) for candidate in candidates]
        if not texts:
            return []
        vectors = self.embedding_backend.embed([query, *texts])
        if len(vectors) != len(texts) + 1:
            raise RuntimeError("Web embedding backend returned unexpected vector count")
        query_vector = normalize_vector(vectors[0])

        chunks: List[WebChunk] = []
        for index, candidate in enumerate(candidates):
            text = texts[index]
            vector = normalize_vector(vectors[index + 1])
            semantic_score = cosine_similarity(query_vector, vector)
            score = semantic_score + candidate.score_hint
            citation = _citation(candidate.pmid, candidate.doi)
            chunks.append(
                WebChunk(
                    id=f"web-{candidate.key.replace(':', '-')}",
                    text=text,
                    source=candidate.source,
                    title=candidate.title,
                    score=score,
                    pmid=candidate.pmid,
                    doi=candidate.doi,
                    year=candidate.year,
                    citation=citation,
                    annotations=annotations.get(candidate.pmid or "", []),
                )
            )
        return sorted(chunks, key=lambda item: item.score, reverse=True)


def web_rag_node(state: MitoRAGState) -> StateUpdate:
    """Fetch web literature snippets or run live scientific API search."""

    with timed_node(state, "web_rag") as update:
        if state.web_chunks:
            update["web_chunks"] = state.web_chunks
        elif os.environ.get("MITORAG_ENABLE_LIVE_WEB") == "1":
            update["web_chunks"] = _run_live_web_search(state)
        else:
            update["web_chunks"] = web_fixture_chunks(state.query)
        return update


def web_chunks_to_ranked(chunks: Sequence[WebChunk]) -> List[RankedChunk]:
    ranked: List[RankedChunk] = []
    for rank, chunk in enumerate(chunks, start=1):
        paper_id = chunk.pmid or chunk.doi or chunk.id
        citation = chunk.citation or _citation(chunk.pmid, chunk.doi) or "[PMID:12345678]"
        metadata = {
            "citation": citation,
            "title": chunk.title,
            "source_api": chunk.source,
            "year": chunk.year or "",
            "annotations": [annotation.text for annotation in chunk.annotations],
        }
        ranked.append(
            ranked_chunk(
                chunk.id,
                chunk.text,
                paper_id,
                f"Web > {chunk.source}",
                chunk.score,
                rank,
                "web_rag",
                citation,
            ).with_rank_score_source(
                rank=rank,
                score=chunk.score,
                source="web_rag",
                source_scores={"web_rag": chunk.score, chunk.source: chunk.score},
            )
        )
        document = ranked[-1].document
        ranked[-1] = RankedChunk(
            document=replace(document, metadata=metadata),
            score=ranked[-1].score,
            rank=ranked[-1].rank,
            source=ranked[-1].source,
            source_scores=ranked[-1].source_scores,
        )
    return ranked


def web_fixture_chunks(query: str) -> List[RankedChunk]:
    del query
    return [
        ranked_chunk(
            "web-oxphos-review",
            "OXPHOS integrates Complexes I-V in the inner mitochondrial membrane.",
            "PMID:12345678",
            "Review > OXPHOS",
            0.83,
            1,
            "web_rag",
            "[PMID:12345678]",
        ),
        ranked_chunk(
            "web-idebenone",
            "Idebenone is approved in Europe for Leber hereditary optic neuropathy.",
            "PMID:26988832",
            "Therapeutics > LHON",
            0.81,
            2,
            "web_rag",
            "[PMID:26988832]",
        ),
        ranked_chunk(
            "web-pink1-parkin",
            "PINK1 accumulation recruits Parkin to depolarized mitochondria during mitophagy.",
            "PMID:20510199",
            "Mechanism > Mitophagy",
            0.79,
            3,
            "web_rag",
            "[PMID:20510199]",
        ),
    ]


def _run_live_web_search(state: MitoRAGState) -> List[RankedChunk]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(WebRAGAgent().search_ranked(state.query, state.sub_queries))
    return web_fixture_chunks(state.query)


def _default_cache() -> Optional[AsyncCache]:
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    try:
        return RedisCache(url)
    except Exception:
        return None


def _flatten_results(responses: Sequence[object]) -> List[WebSearchResult]:
    results: List[WebSearchResult] = []
    for response in responses:
        if isinstance(response, Exception):
            continue
        if isinstance(response, list):
            results.extend(cast(List[WebSearchResult], response))
    return results


def _candidate_from_result(result: WebSearchResult, index: int) -> _PaperCandidate:
    score_hint = max(0.0, 1.0 - (index * 0.01))
    if isinstance(result, PubMedResult):
        key = paper_key(result.doi, result.pmid, f"pubmed:{result.pmid}")
        return _PaperCandidate(
            key=key,
            source="pubmed",
            title=result.title,
            pmid=result.pmid,
            doi=result.doi,
            year=result.year,
            score_hint=score_hint,
        )
    if isinstance(result, S2Paper):
        key = paper_key(result.doi, result.pmid, f"s2:{result.paper_id}")
        return _PaperCandidate(
            key=key,
            source="semantic_scholar",
            title=result.title,
            abstract=result.abstract,
            pmid=result.pmid,
            doi=result.doi,
            year=result.year,
            score_hint=score_hint + min(result.citation_count / 10000.0, 0.2),
        )
    if isinstance(result, EuropePMCResult):
        key = paper_key(result.doi, result.pmid, f"europe_pmc:{result.id}")
        return _PaperCandidate(
            key=key,
            source="europe_pmc",
            title=result.title,
            abstract=result.abstract,
            pmid=result.pmid,
            doi=result.doi,
            year=result.year,
            score_hint=score_hint,
        )
    key = paper_key(result.doi, None, f"biorxiv:{result.doi}")
    return _PaperCandidate(
        key=key,
        source=result.server,
        title=result.title,
        abstract=result.abstract,
        doi=result.doi,
        year=_year_from_date(result.date),
        score_hint=score_hint,
    )


def _candidate_from_pubmed_abstract(
    abstract: PubMedAbstract,
    score_hint: float,
) -> _PaperCandidate:
    return _PaperCandidate(
        key=paper_key(abstract.doi, abstract.pmid, f"pubmed:{abstract.pmid}"),
        source="pubmed",
        title=abstract.title,
        abstract=abstract.abstract,
        pmid=abstract.pmid,
        doi=abstract.doi,
        year=abstract.year,
        score_hint=score_hint,
    )


def _candidate_rank(candidate: _PaperCandidate) -> float:
    abstract_bonus = 0.1 if candidate.abstract else 0.0
    id_bonus = 0.05 if candidate.pmid or candidate.doi else 0.0
    return candidate.score_hint + abstract_bonus + id_bonus


def _chunk_text(candidate: _PaperCandidate) -> str:
    if candidate.abstract:
        return f"{candidate.title}\n\n{candidate.abstract}".strip()
    return candidate.title


def _pmids(candidates: Iterable[_PaperCandidate]) -> List[str]:
    seen: dict[str, None] = {}
    for candidate in candidates:
        if candidate.pmid:
            seen.setdefault(candidate.pmid, None)
    return list(seen.keys())


def _citation(pmid: Optional[str], doi: Optional[str]) -> Optional[str]:
    if pmid:
        return f"[PMID:{pmid}]"
    if doi:
        return f"[doi:{doi}]"
    return None


def _year_from_date(value: str) -> Optional[int]:
    if len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None
