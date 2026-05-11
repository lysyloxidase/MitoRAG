"""KEGG mitochondrial pathway seed loader."""

from __future__ import annotations

from typing import Mapping

from mitorag_kg.loader import LoadResult, as_writer

KEGG_PATHWAYS = [
    {"name": "Oxidative phosphorylation", "kegg_id": "hsa00190", "category": "OXPHOS"},
    {"name": "TCA cycle", "kegg_id": "hsa00020", "category": "Metabolism"},
    {"name": "Fatty acid degradation", "kegg_id": "hsa00071", "category": "Metabolism"},
    {
        "name": "Mitochondrial protein import",
        "kegg_id": "hsa03060",
        "category": "Protein import & sorting",
    },
]


class KEGGLoader:
    """Load core mitochondrial KEGG pathways."""

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        for pathway in KEGG_PATHWAYS:
            writer.merge_node("Pathway", "name", _pathway_properties(pathway))
        return LoadResult(
            loader="KEGGLoader",
            nodes_loaded=len(KEGG_PATHWAYS),
            details={"pathways": len(KEGG_PATHWAYS)},
        )


def _pathway_properties(row: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "name": row["name"],
        "kegg_id": row["kegg_id"],
        "category": row["category"],
    }

