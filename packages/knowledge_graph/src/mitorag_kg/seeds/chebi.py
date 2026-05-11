"""ChEBI metabolite seed loader."""

from __future__ import annotations

from mitorag_kg.loader import LoadResult, as_writer

CHEBI_METABOLITES = [
    {"chebi_id": "CHEBI:15846", "name": "NAD+", "formula": "C21H28N7O14P2", "mass_da": 664.4},
    {"chebi_id": "CHEBI:16908", "name": "NADH", "formula": "C21H29N7O14P2", "mass_da": 665.4},
    {"chebi_id": "CHEBI:15378", "name": "H+", "formula": "H", "mass_da": 1.0},
    {"chebi_id": "CHEBI:15422", "name": "ATP", "formula": "C10H16N5O13P3", "mass_da": 507.2},
    {"chebi_id": "CHEBI:456216", "name": "ADP", "formula": "C10H15N5O10P2", "mass_da": 427.2},
    {"chebi_id": "CHEBI:16526", "name": "CO2", "formula": "CO2", "mass_da": 44.0},
    {"chebi_id": "CHEBI:30031", "name": "succinate", "formula": "C4H4O4", "mass_da": 116.1},
    {"chebi_id": "CHEBI:30769", "name": "citrate", "formula": "C6H5O7", "mass_da": 192.1},
]


class ChEBILoader:
    """Load core mitochondrial metabolites from ChEBI."""

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        for metabolite in CHEBI_METABOLITES:
            writer.merge_node("Metabolite", "chebi_id", metabolite)
        return LoadResult(
            loader="ChEBILoader",
            nodes_loaded=len(CHEBI_METABOLITES),
            details={"metabolites": len(CHEBI_METABOLITES)},
        )

