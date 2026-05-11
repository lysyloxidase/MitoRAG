"""MITOMAP mtDNA variant seed loader."""

from __future__ import annotations

from typing import List, Mapping

from mitorag_kg.loader import LoadResult, as_writer
from mitorag_kg.schema import EDGE_LABELS

CANONICAL_VARIANTS: List[Mapping[str, object]] = [
    {
        "hgvs": "m.3243A>G",
        "position": 3243,
        "gene": "MT-TL1",
        "pathogenicity": "pathogenic",
        "heteroplasmy_threshold": 0.80,
        "disease": "MELAS syndrome",
        "omim_id": "540000",
        "mondo_id": "MONDO:0010789",
    },
    {
        "hgvs": "m.8344A>G",
        "position": 8344,
        "gene": "MT-TK",
        "pathogenicity": "pathogenic",
        "heteroplasmy_threshold": 0.85,
        "disease": "MERRF syndrome",
        "omim_id": "545000",
        "mondo_id": "MONDO:0010788",
    },
    {
        "hgvs": "m.11778G>A",
        "position": 11778,
        "gene": "MT-ND4",
        "pathogenicity": "pathogenic",
        "heteroplasmy_threshold": 1.0,
        "disease": "Leber hereditary optic neuropathy",
        "omim_id": "535000",
        "mondo_id": "MONDO:0010787",
    },
    {
        "hgvs": "m.8993T>G",
        "position": 8993,
        "gene": "MT-ATP6",
        "pathogenicity": "pathogenic",
        "heteroplasmy_threshold": 0.90,
        "disease": "Leigh syndrome/NARP spectrum",
        "omim_id": "516060",
        "mondo_id": "MONDO:0009723",
    },
    {
        "hgvs": "m.13513G>A",
        "position": 13513,
        "gene": "MT-ND5",
        "pathogenicity": "pathogenic",
        "heteroplasmy_threshold": 0.70,
        "disease": "MELAS overlap syndrome",
        "omim_id": "540000",
        "mondo_id": "MONDO:0010789",
    },
]


class MITOMAPLoader:
    """Load canonical pathogenic mtDNA variants from MITOMAP."""

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        relationships = 0
        for variant in CANONICAL_VARIANTS:
            writer.merge_node("Variant", "hgvs", _variant_properties(variant))
            writer.merge_node("Disease", "name", _disease_properties(variant))
            writer.merge_node(
                "Gene",
                "hgnc_symbol",
                {
                    "hgnc_symbol": variant["gene"],
                    "name": variant["gene"],
                    "mtdna_encoded": True,
                    "chromosome": "MT",
                },
            )
            writer.merge_relationship(
                "Variant",
                "hgvs",
                variant["hgvs"],
                EDGE_LABELS["associated_with"],
                "Gene",
                "hgnc_symbol",
                variant["gene"],
                {"source": "MITOMAP", "role": "variant_gene"},
            )
            writer.merge_relationship(
                "Variant",
                "hgvs",
                variant["hgvs"],
                EDGE_LABELS["causes"],
                "Disease",
                "name",
                variant["disease"],
                {"source": "MITOMAP"},
            )
            writer.merge_relationship(
                "Gene",
                "hgnc_symbol",
                variant["gene"],
                EDGE_LABELS["mutated_in"],
                "Disease",
                "name",
                variant["disease"],
                {"source": "MITOMAP"},
            )
            relationships += 3

        return LoadResult(
            loader="MITOMAPLoader",
            nodes_loaded=len(CANONICAL_VARIANTS) * 2,
            relationships_loaded=relationships,
            details={"canonical_variants": len(CANONICAL_VARIANTS)},
        )


def _variant_properties(variant: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "hgvs": variant["hgvs"],
        "position": variant["position"],
        "gene": variant["gene"],
        "pathogenicity": variant["pathogenicity"],
        "heteroplasmy_threshold": variant["heteroplasmy_threshold"],
    }


def _disease_properties(variant: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "name": variant["disease"],
        "mondo_id": variant["mondo_id"],
        "omim_id": variant["omim_id"],
        "inheritance": "maternal",
    }

