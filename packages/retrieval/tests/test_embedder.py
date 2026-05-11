from __future__ import annotations

from mitorag_retrieval.embedder import DenseRetriever, HashingEmbeddingBackend
from mitorag_retrieval.models import RetrievalDocument


def test_dense_retriever_returns_relevant_membrane_potential_chunks_in_top_five() -> None:
    relevant = [
        _doc(f"potential-{index}", "Mitochondrial membrane potential was measured with TMRE.")
        for index in range(5)
    ]
    distractors = [
        _doc("ros", "Reactive oxygen species increased after rotenone exposure."),
        _doc("fission", "DRP1 phosphorylation changed mitochondrial fission."),
        _doc("translation", "Mitoribosomal translation controls respiratory chain abundance."),
        _doc("apoptosis", "Cytochrome c release activated caspase signaling."),
        _doc("metabolite", "Succinate accumulation changed TCA cycle flux."),
    ]
    retriever = DenseRetriever(HashingEmbeddingBackend("dense-test"))
    retriever.index([*relevant, *distractors])

    results = retriever.search("mitochondrial membrane potential", top_k=5)

    assert len(results) == 5
    assert all(result.id.startswith("potential-") for result in results)


def _doc(identifier: str, text: str) -> RetrievalDocument:
    return RetrievalDocument(
        id=identifier,
        text=text,
        paper_id=f"paper-{identifier}",
        section_path="Methods",
    )

