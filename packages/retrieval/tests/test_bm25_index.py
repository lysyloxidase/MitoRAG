from __future__ import annotations

from mitorag_retrieval.bm25_index import BM25Index
from mitorag_retrieval.models import RetrievalDocument


def test_bm25_retrieves_complex_i_subunits_with_nd1_nd6() -> None:
    documents = [
        _doc(
            "complex-i",
            "Complex I subunits include mtDNA encoded ND1 ND2 ND3 ND4 ND4L ND5 ND6.",
        ),
        _doc("calcium", "Mitochondrial calcium uptake depends on MCU and MICU1."),
        _doc("fusion", "OPA1 and MFN2 regulate mitochondrial fusion dynamics."),
    ]
    index = BM25Index(documents)

    results = index.search("Complex I subunits", top_k=3)

    assert results
    assert results[0].id == "complex-i"
    assert "ND1" in results[0].text
    assert "ND6" in results[0].text


def test_bm25_finds_literal_gene_token_mt_nd4() -> None:
    documents = [
        _doc("mt-nd4", "The MT-ND4 variant altered Complex I assembly in cybrids."),
        _doc("ndufv1", "NDUFV1 defects reduce NADH dehydrogenase activity."),
    ]
    index = BM25Index(documents)

    results = index.search("MT-ND4", top_k=2)

    assert [result.id for result in results] == ["mt-nd4"]


def _doc(identifier: str, text: str) -> RetrievalDocument:
    return RetrievalDocument(
        id=identifier,
        text=text,
        paper_id=f"paper-{identifier}",
        section_path="Results",
    )

