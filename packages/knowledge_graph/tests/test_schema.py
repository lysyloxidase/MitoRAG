from __future__ import annotations

from mitorag_kg.schema import EDGE_LABELS, EDGE_TYPES, NODE_TYPES, constraint_queries


def test_schema_contains_biolink_node_and_edge_types() -> None:
    assert "Gene" in NODE_TYPES
    assert "Variant" in NODE_TYPES
    assert "Hypothesis" in NODE_TYPES
    assert "encoded_by" in EDGE_TYPES
    assert EDGE_LABELS["encoded_by"] == "ENCODED_BY"
    assert EDGE_LABELS["localizes_to"] == "LOCALIZES_TO"


def test_constraint_queries_cover_core_labels() -> None:
    queries = constraint_queries()
    joined = "\n".join(queries)
    assert "FOR (n:Gene) REQUIRE n.hgnc_symbol IS UNIQUE" in joined
    assert "FOR (n:Variant) REQUIRE n.hgvs IS UNIQUE" in joined
    assert "FOR (n:Protein) REQUIRE n.uniprot_id IS UNIQUE" in joined

