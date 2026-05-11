"""BM25 + dual-dense retrieval with Reciprocal Rank Fusion."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from mitorag_retrieval.bm25_index import BM25Index
from mitorag_retrieval.embedder import DenseRetriever, DualEmbedder
from mitorag_retrieval.models import RankedChunk, RetrievalDocument
from mitorag_retrieval.reranker import BGEReranker


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[RankedChunk]],
    k: int = 60,
) -> List[RankedChunk]:
    """Fuse ranked lists with RRF_score(d) = sum(1 / (k + rank_i(d)))."""

    documents: Dict[str, RankedChunk] = {}
    scores: Dict[str, float] = {}
    source_scores: Dict[str, Dict[str, float]] = {}

    for ranked_list in ranked_lists:
        for rank, result in enumerate(ranked_list, start=1):
            documents.setdefault(result.id, result)
            scores[result.id] = scores.get(result.id, 0.0) + 1.0 / (k + rank)
            per_source = source_scores.setdefault(result.id, {})
            per_source[f"{result.source}_rank"] = float(rank)
            per_source[f"{result.source}_score"] = result.score
            for key, value in result.source_scores.items():
                per_source[key] = value

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    fused: List[RankedChunk] = []
    for rank, (document_id, score) in enumerate(ordered, start=1):
        fused.append(
            documents[document_id].with_rank_score_source(
                rank=rank,
                score=score,
                source="rrf",
                source_scores=source_scores.get(document_id, {}),
            )
        )
    return fused


class HybridRetriever:
    """BM25 + dual-dense + RRF fusion + BGE reranking."""

    def __init__(
        self,
        bm25_index: BM25Index,
        bio_embedder: DenseRetriever,
        gen_embedder: DenseRetriever,
        reranker: BGEReranker,
        corpus_size: int,
        rrf_k: Optional[int] = None,
        candidate_pool_size: int = 100,
        fusion_pool_size: int = 50,
    ) -> None:
        self.bm25_index = bm25_index
        self.bio_embedder = bio_embedder
        self.gen_embedder = gen_embedder
        self.reranker = reranker
        self.corpus_size = corpus_size
        self.rrf_k = rrf_k
        self.candidate_pool_size = candidate_pool_size
        self.fusion_pool_size = fusion_pool_size

    @classmethod
    def from_documents(
        cls,
        documents: Iterable[RetrievalDocument],
        dual_embedder: Optional[DualEmbedder] = None,
        reranker: Optional[BGEReranker] = None,
        rrf_k: Optional[int] = None,
    ) -> HybridRetriever:
        materialized = list(documents)
        bm25_index = BM25Index(materialized)
        embeddings = dual_embedder or DualEmbedder()
        embeddings.index(materialized)
        return cls(
            bm25_index=bm25_index,
            bio_embedder=embeddings.bio_embedder,
            gen_embedder=embeddings.gen_embedder,
            reranker=reranker or BGEReranker(),
            corpus_size=len(materialized),
            rrf_k=rrf_k,
        )

    def retrieve(self, query: str, top_k: int = 15) -> List[RankedChunk]:
        """Full hybrid retrieval pipeline."""

        bm25_results = self.bm25_index.search(query, top_k=self.candidate_pool_size)
        bio_results = self.bio_embedder.search(query, top_k=self.candidate_pool_size)
        gen_results = self.gen_embedder.search(query, top_k=self.candidate_pool_size)

        fused = reciprocal_rank_fusion(
            [bm25_results, bio_results, gen_results],
            k=self._effective_rrf_k(),
        )
        candidates = fused[: self.fusion_pool_size]
        return self.reranker.rerank(query, candidates, top_k=top_k)

    def _effective_rrf_k(self) -> int:
        if self.rrf_k is not None:
            return self.rrf_k
        return 10 if self.corpus_size < 1000 else 60


def chunk_ids(results: Sequence[RankedChunk]) -> List[str]:
    """Return result IDs for tests and diagnostics."""

    return [result.id for result in results]


def source_score(result: RankedChunk, key: str) -> Optional[float]:
    value = result.source_scores.get(key)
    if isinstance(value, float):
        return value
    return None
