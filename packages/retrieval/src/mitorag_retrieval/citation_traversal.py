"""Citation graph traversal for expanding retrieval pools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Optional, Protocol, Sequence

from mitorag_retrieval.embedder import EmbeddingBackend, HashingEmbeddingBackend
from mitorag_retrieval.models import RankedChunk, RetrievalDocument
from mitorag_retrieval.reranker import BGEReranker
from mitorag_retrieval.vector_store import cosine_similarity, normalize_vector


def _empty_metadata() -> dict[str, object]:
    return {}


@dataclass(frozen=True)
class CitationPaper:
    """A paper discovered through references or citations."""

    paper_id: str
    title: str
    abstract: str = ""
    year: Optional[int] = None
    citation_count: int = 0
    metadata: Mapping[str, object] = field(default_factory=_empty_metadata)

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.abstract}".strip()


class CitationClient(Protocol):
    """Client surface needed from Semantic Scholar or a local citation graph."""

    def references(self, paper_id: str, limit: int = 5) -> List[CitationPaper]:
        """Return up to `limit` references for a paper."""
        ...

    def citations(self, paper_id: str, limit: int = 5) -> List[CitationPaper]:
        """Return up to `limit` citing papers for a paper."""
        ...


class CitationTraverser:
    """Follow citation graph to discover relevant papers.

    For each top paper after reranking, this can fetch references and citations,
    embed-and-score them against the query, and return high-scoring paper-level
    retrieval documents that can be appended to a candidate pool.
    """

    def __init__(
        self,
        client: CitationClient,
        embedder: Optional[EmbeddingBackend] = None,
        similarity_threshold: float = 0.65,
        per_direction_limit: int = 5,
    ) -> None:
        self.client = client
        self.embedder = embedder or HashingEmbeddingBackend("citation_traversal")
        self.similarity_threshold = similarity_threshold
        self.per_direction_limit = per_direction_limit

    def expand(
        self,
        query: str,
        top_results: Sequence[RankedChunk],
        top_papers: int = 10,
    ) -> List[RankedChunk]:
        query_vector = normalize_vector(self.embedder.embed([query])[0])
        candidates = self._collect_candidates(top_results[:top_papers])
        ranked: List[RankedChunk] = []
        seen: set[str] = set()
        for paper in candidates:
            if paper.paper_id in seen or not paper.text:
                continue
            seen.add(paper.paper_id)
            paper_vector = normalize_vector(self.embedder.embed([paper.text])[0])
            score = cosine_similarity(query_vector, paper_vector)
            if score < self.similarity_threshold:
                continue
            document = RetrievalDocument(
                id=f"citation:{paper.paper_id}",
                text=paper.text,
                paper_id=paper.paper_id,
                section_path="Citation Graph",
                metadata={
                    "title": paper.title,
                    "year": paper.year,
                    "citation_count": paper.citation_count,
                    **dict(paper.metadata),
                },
            )
            ranked.append(
                RankedChunk(
                    document=document,
                    score=score,
                    rank=0,
                    source="citation_traversal",
                    source_scores={"citation_similarity": score},
                )
            )

        ranked.sort(key=lambda result: result.score, reverse=True)
        return [
            result.with_rank_score_source(
                rank=rank,
                score=result.score,
                source=result.source,
                source_scores=result.source_scores,
            )
            for rank, result in enumerate(ranked, start=1)
        ]

    def expand_and_rerank(
        self,
        query: str,
        top_results: Sequence[RankedChunk],
        reranker: BGEReranker,
        top_k: int = 15,
    ) -> List[RankedChunk]:
        """Append citation hits to a reranked pool and rerank the expanded set."""

        expanded = self.expand(query=query, top_results=top_results, top_papers=10)
        return reranker.rerank(query, [*top_results, *expanded], top_k=top_k)

    def _collect_candidates(self, top_results: Iterable[RankedChunk]) -> List[CitationPaper]:
        papers: List[CitationPaper] = []
        for result in top_results:
            paper_id = result.paper_id
            papers.extend(self.client.references(paper_id, limit=self.per_direction_limit))
            papers.extend(self.client.citations(paper_id, limit=self.per_direction_limit))
        papers.sort(key=lambda paper: paper.citation_count, reverse=True)
        return papers
