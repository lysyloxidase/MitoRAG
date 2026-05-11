from __future__ import annotations

import time
from typing import List, Sequence

from mitorag_retrieval.embedder import DualEmbedder, EmbeddingBackend, Vector
from mitorag_retrieval.hybrid import HybridRetriever, reciprocal_rank_fusion
from mitorag_retrieval.models import RankedChunk, RetrievalDocument
from mitorag_retrieval.reranker import BGEReranker


class ZeroEmbeddingBackend:
    name = "zero"
    dimension = 768

    def embed(self, texts: Sequence[str]) -> List[Vector]:
        return [[0.0] * self.dimension for _ in texts]


def test_rrf_fusion_recovers_more_relevant_documents_than_any_single_ranker() -> None:
    relevant_ids = {"rel-a", "rel-b", "rel-c"}
    ranker_a = [
        _ranked(_doc("rel-a"), 1, "a"),
        *[_ranked(_doc(f"a-{i}"), i, "a") for i in range(2, 20)],
    ]
    ranker_b = [
        _ranked(_doc("rel-b"), 1, "b"),
        *[_ranked(_doc(f"b-{i}"), i, "b") for i in range(2, 20)],
    ]
    ranker_c = [
        _ranked(_doc("rel-c"), 1, "c"),
        *[_ranked(_doc(f"c-{i}"), i, "c") for i in range(2, 20)],
    ]

    fused = reciprocal_rank_fusion([ranker_a, ranker_b, ranker_c], k=60)

    single_best = max(
        _recall_at_15(results, relevant_ids) for results in [ranker_a, ranker_b, ranker_c]
    )
    fused_recall = _recall_at_15(fused, relevant_ids)
    assert fused_recall > single_best


def test_hybrid_pipeline_retrieves_literal_gene_when_dense_misses() -> None:
    documents = [
        _doc("gene-hit", "The MT-ND4 mutation impaired Complex I proton pumping."),
        _doc("dense-distractor", "Mitochondrial morphology changed during mitophagy."),
    ]
    zero_backend: EmbeddingBackend = ZeroEmbeddingBackend()
    retriever = HybridRetriever.from_documents(
        documents,
        dual_embedder=DualEmbedder(bio_backend=zero_backend, general_backend=zero_backend),
        reranker=BGEReranker(load_model=False),
    )

    results = retriever.retrieve("MT-ND4", top_k=1)

    assert results[0].id == "gene-hit"


def test_hybrid_pipeline_query_over_1000_chunks_under_two_seconds() -> None:
    documents = [
        _doc(
            f"hit-{index}",
            "Mitochondrial membrane potential and Complex I activity were measured by TMRE.",
        )
        for index in range(20)
    ]
    documents.extend(
        _doc(f"distractor-{index}", f"Unrelated assay chunk {index} about cytosolic signaling.")
        for index in range(980)
    )
    retriever = HybridRetriever.from_documents(documents, reranker=BGEReranker(load_model=False))

    start = time.perf_counter()
    results = retriever.retrieve("mitochondrial membrane potential Complex I", top_k=15)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0
    assert results
    assert all(result.id.startswith("hit-") for result in results[:5])


def _recall_at_15(results: Sequence[RankedChunk], relevant_ids: set[str]) -> int:
    return len({result.id for result in results[:15]}.intersection(relevant_ids))


def _doc(identifier: str, text: str | None = None) -> RetrievalDocument:
    return RetrievalDocument(
        id=identifier,
        text=text or f"Document {identifier}",
        paper_id=f"paper-{identifier}",
        section_path="Results",
    )


def _ranked(document: RetrievalDocument, rank: int, source: str) -> RankedChunk:
    return RankedChunk(
        document=document,
        score=1.0 / rank,
        rank=rank,
        source=source,
        source_scores={source: 1.0 / rank},
    )
