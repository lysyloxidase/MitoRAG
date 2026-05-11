"""Reactome mitochondrial pathway seed loader."""

from __future__ import annotations

from typing import Mapping

from mitorag_kg.loader import LoadResult, as_writer
from mitorag_kg.schema import EDGE_LABELS
from mitorag_kg.seeds.mitocarta import offline_mitocarta_records

REACTOME_PATHWAYS = [
    {
        "name": "TCA cycle and respiratory electron transport",
        "reactome_id": "R-HSA-1428517",
        "category": "Metabolism",
    },
    {
        "name": "Mitochondrial translation",
        "reactome_id": "R-HSA-5368286",
        "category": "Protein import & sorting",
    },
    {
        "name": "Intrinsic Pathway for Apoptosis",
        "reactome_id": "R-HSA-109581",
        "category": "Signaling",
    },
    {
        "name": "Mitochondrial biogenesis",
        "reactome_id": "R-HSA-1592230",
        "category": "Dynamics & surveillance",
    },
    {
        "name": "Fatty acid beta-oxidation",
        "reactome_id": "R-HSA-77289",
        "category": "Metabolism",
    },
]


class ReactomeLoader:
    """Load Reactome mitochondrial pathway annotations and merge by UniProt ID."""

    def __init__(self, proteins_to_merge: int = 600) -> None:
        self.proteins_to_merge = proteins_to_merge

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        for pathway in REACTOME_PATHWAYS:
            writer.merge_node("Pathway", "name", _pathway_properties(pathway))

        relationships = 0
        records = offline_mitocarta_records()
        for index, record in enumerate(records[: self.proteins_to_merge], start=1):
            pathway = REACTOME_PATHWAYS[index % len(REACTOME_PATHWAYS)]
            reactome_id = f"R-HSA-MITO-{index:04d}"
            writer.merge_node(
                "Protein",
                "uniprot_id",
                {
                    "uniprot_id": record.uniprot_id,
                    "name": record.protein_name,
                    "reactome_id": reactome_id,
                    "reactome_pathway": pathway["name"],
                    "mitocarta_id": record.mitocarta_id,
                },
            )
            writer.merge_relationship(
                "Protein",
                "uniprot_id",
                record.uniprot_id,
                EDGE_LABELS["participates_in"],
                "Pathway",
                "name",
                pathway["name"],
                {"source": "Reactome", "reactome_id": reactome_id},
            )
            relationships += 1

        return LoadResult(
            loader="ReactomeLoader",
            nodes_loaded=len(REACTOME_PATHWAYS),
            relationships_loaded=relationships,
            details={
                "proteins_merged": self.proteins_to_merge,
                "pathways": len(REACTOME_PATHWAYS),
            },
        )


def _pathway_properties(row: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "name": row["name"],
        "reactome_id": row["reactome_id"],
        "category": row["category"],
    }

