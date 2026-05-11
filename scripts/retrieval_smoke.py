"""Smoke-test the Phase 2 hybrid retrieval pipeline."""

from __future__ import annotations

import argparse
import time

from mitorag_retrieval import BGEReranker, HybridRetriever, RetrievalDocument


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=int, default=1000)
    parser.add_argument("--top-k", type=int, default=15)
    parser.add_argument("--load-reranker", action="store_true")
    args = parser.parse_args()

    documents = _build_corpus(args.chunks)
    reranker = BGEReranker(load_model=args.load_reranker)
    retriever = HybridRetriever.from_documents(documents, reranker=reranker)

    start = time.perf_counter()
    results = retriever.retrieve("mitochondrial membrane potential Complex I", top_k=args.top_k)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"retrieved={len(results)} elapsed_ms={elapsed_ms:.1f}")
    for result in results[:5]:
        print(f"{result.rank}\t{result.score:.4f}\t{result.id}\t{result.section_path}")
    return 0


def _build_corpus(size: int) -> list[RetrievalDocument]:
    hits = min(20, size)
    documents = [
        RetrievalDocument(
            id=f"hit-{index}",
            text="Mitochondrial membrane potential and Complex I activity were measured by TMRE.",
            paper_id=f"paper-hit-{index}",
            section_path="Results > ETC Activity",
        )
        for index in range(hits)
    ]
    documents.extend(
        RetrievalDocument(
            id=f"distractor-{index}",
            text=f"Unrelated cytosolic signaling assay chunk {index}.",
            paper_id=f"paper-distractor-{index}",
            section_path="Methods",
        )
        for index in range(max(0, size - hits))
    )
    return documents


if __name__ == "__main__":
    raise SystemExit(main())
