from __future__ import annotations

import time

from mitorag_retrieval.models import RankedChunk, RetrievalDocument
from mitorag_retrieval.reranker import BGEReranker


def test_bge_reranker_scores_50_pairs_under_500ms_with_local_fallback() -> None:
    reranker = BGEReranker(load_model=False)
    candidates = [
        RankedChunk(
            document=RetrievalDocument(
                id=f"doc-{index}",
                text="Complex I subunits and mitochondrial membrane potential were analyzed.",
                paper_id=f"paper-{index}",
                section_path="Results",
            ),
            score=0.0,
            rank=index + 1,
            source="rrf",
        )
        for index in range(50)
    ]

    start = time.perf_counter()
    results = reranker.rerank("Complex I membrane potential", candidates, top_k=15)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.5
    assert len(results) == 15
    assert all("reranker" in result.source_scores for result in results)

