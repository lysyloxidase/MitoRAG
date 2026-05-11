"""Pre-built mitochondrial graph query templates for Phase 3."""

from __future__ import annotations

MATRIX_LOCALIZATION_COUNT = (
    "MATCH (g:Gene)-[:ENCODED_BY]-(p:Protein)-[:LOCALIZES_TO]->"
    "(c:SubMitoCompartment {name:'matrix'}) RETURN count(p)"
)

MITOMAP_COMPLEX_OXPHOS_PATH = (
    "MATCH path = "
    "(:Variant {hgvs:$hgvs})-[:ASSOCIATED_WITH]->"
    "(:Gene {hgnc_symbol:$gene})-[:PART_OF]->"
    "(:Complex {name:$complex})-[:PARTICIPATES_IN]->"
    "(:Pathway {name:$pathway}) "
    "RETURN path"
)

DRUG_TARGETS = (
    "MATCH (d:Drug)-[r:INHIBITS]->(target) "
    "RETURN d.name AS drug, type(r) AS predicate, labels(target) AS target_labels, "
    "target.name AS target_name"
)

MPTP_CONTROVERSY = (
    "MATCH (a:Hypothesis)-[:CONTRADICTS]->(b:Hypothesis) "
    "WHERE a.name STARTS WITH 'mPTP' AND b.name STARTS WITH 'mPTP' "
    "RETURN a, b"
)


__all__ = [
    "DRUG_TARGETS",
    "MATRIX_LOCALIZATION_COUNT",
    "MITOMAP_COMPLEX_OXPHOS_PATH",
    "MPTP_CONTROVERSY",
]
