"""Gene Ontology mitochondrial compartment seed loader."""

from __future__ import annotations

from mitorag_kg.loader import LoadResult, as_writer
from mitorag_kg.schema import ensure_schema

GO_COMPARTMENTS = {
    "matrix": "GO:0005759",
    "IMM": "GO:0005743",
    "IMS": "GO:0005758",
    "OMM": "GO:0005741",
}


class GeneOntologyLoader:
    """Load GO:0005739 mitochondrial hierarchy nodes used for localization."""

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        ensure_schema(writer)
        for name, go_id in GO_COMPARTMENTS.items():
            writer.merge_node(
                "SubMitoCompartment",
                "name",
                {
                    "name": name,
                    "go_id": go_id,
                    "parent_go_id": "GO:0005739",
                },
            )
        return LoadResult(
            loader="GeneOntologyLoader",
            nodes_loaded=len(GO_COMPARTMENTS),
            details={"root": "GO:0005739"},
        )

