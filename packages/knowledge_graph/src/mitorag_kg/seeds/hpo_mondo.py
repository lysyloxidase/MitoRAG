"""HPO and MONDO disease/phenotype seed loader."""

from __future__ import annotations

from typing import List, Mapping, Tuple, cast

from mitorag_kg.loader import LoadResult, as_writer
from mitorag_kg.schema import EDGE_LABELS

DISEASE_PHENOTYPES: List[Mapping[str, object]] = [
    {
        "disease": "MELAS syndrome",
        "mondo_id": "MONDO:0010789",
        "omim_id": "540000",
        "phenotypes": [
            ("HP:0003200", "Ragged-red fibers"),
            ("HP:0001250", "Seizure"),
            ("HP:0002123", "Generalized myoclonic seizure"),
        ],
    },
    {
        "disease": "MERRF syndrome",
        "mondo_id": "MONDO:0010788",
        "omim_id": "545000",
        "phenotypes": [
            ("HP:0001336", "Myoclonus"),
            ("HP:0003200", "Ragged-red fibers"),
        ],
    },
    {
        "disease": "Leber hereditary optic neuropathy",
        "mondo_id": "MONDO:0010787",
        "omim_id": "535000",
        "phenotypes": [
            ("HP:0001138", "Optic neuropathy"),
            ("HP:0000572", "Visual loss"),
        ],
    },
    {
        "disease": "Leigh syndrome/NARP spectrum",
        "mondo_id": "MONDO:0009723",
        "omim_id": "516060",
        "phenotypes": [
            ("HP:0001251", "Ataxia"),
            ("HP:0001288", "Gait disturbance"),
        ],
    },
]


class HPOMONDOLoader:
    """Load curated mitochondrial diseases and HPO phenotype edges."""

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        relationships = 0
        phenotype_count = 0
        for row in DISEASE_PHENOTYPES:
            writer.merge_node(
                "Disease",
                "name",
                {
                    "name": row["disease"],
                    "mondo_id": row["mondo_id"],
                    "omim_id": row["omim_id"],
                    "inheritance": "maternal",
                },
            )
            phenotypes = cast(List[Tuple[str, str]], row["phenotypes"])
            for hpo_id, name in phenotypes:
                writer.merge_node("Phenotype", "hpo_id", {"hpo_id": hpo_id, "name": name})
                writer.merge_relationship(
                    "Disease",
                    "name",
                    row["disease"],
                    EDGE_LABELS["associated_with"],
                    "Phenotype",
                    "hpo_id",
                    hpo_id,
                    {"source": "HPO/MONDO"},
                )
                relationships += 1
                phenotype_count += 1

        return LoadResult(
            loader="HPOMONDOLoader",
            nodes_loaded=len(DISEASE_PHENOTYPES) + phenotype_count,
            relationships_loaded=relationships,
            details={"diseases": len(DISEASE_PHENOTYPES), "phenotypes": phenotype_count},
        )
