"""Drug and therapeutic seed loader."""

from __future__ import annotations

from typing import List, Mapping, Tuple, cast

from mitorag_kg.loader import LoadResult, as_writer
from mitorag_kg.schema import EDGE_LABELS

DRUGS: List[Mapping[str, object]] = [
    {
        "name": "Idebenone",
        "target": "Complex I bypass (electron carrier)",
        "clinical_status": "EMA-approved for LHON (2015)",
        "drugbank_id": "DB09081",
        "target_node": ("Complex", "name", "Complex I"),
        "disease": "Leber hereditary optic neuropathy",
    },
    {
        "name": "Coenzyme Q10",
        "target": "ETC electron carrier",
        "clinical_status": "Supplement, Phase 2-3 various",
        "drugbank_id": None,
        "target_node": ("Pathway", "name", "Oxidative phosphorylation"),
    },
    {
        "name": "MitoQ",
        "target": "TPP+-conjugated ubiquinone (matrix-targeted antioxidant)",
        "clinical_status": "Phase 2",
        "drugbank_id": None,
        "target_node": ("SubMitoCompartment", "name", "matrix"),
    },
    {
        "name": "SS-31 (Elamipretide)",
        "target": "Cardiolipin stabilization (IMM)",
        "clinical_status": "Phase 2 heart failure",
        "drugbank_id": None,
        "target_node": ("SubMitoCompartment", "name", "IMM"),
    },
    {
        "name": "Urolithin A",
        "target": "Mitophagy inducer (PINK1/Parkin)",
        "clinical_status": "Phase 2 muscle endurance, Phase 1 immune aging",
        "drugbank_id": None,
        "target_node": ("Pathway", "name", "Mitochondrial biogenesis"),
    },
    {
        "name": "NMN",
        "target": "NAD+ precursor",
        "clinical_status": "Phase 2",
        "drugbank_id": None,
        "target_node": ("Metabolite", "chebi_id", "CHEBI:15846"),
    },
    {
        "name": "NR (Nicotinamide Riboside)",
        "target": "NAD+ precursor",
        "clinical_status": "Phase 2",
        "drugbank_id": None,
        "target_node": ("Metabolite", "chebi_id", "CHEBI:15846"),
    },
    {
        "name": "Metformin",
        "target": "Complex I IF site inhibition -> AMPK activation",
        "clinical_status": "Approved (T2DM), off-label aging",
        "drugbank_id": "DB00331",
        "target_node": ("Complex", "name", "Complex I"),
    },
    {
        "name": "Rapamycin",
        "target": "mTOR inhibition -> autophagy/mitophagy",
        "clinical_status": "Approved (transplant), off-label aging",
        "drugbank_id": "DB00877",
        "target_node": ("Pathway", "name", "Mitochondrial biogenesis"),
    },
    {
        "name": "ISRIB",
        "target": "ISR inhibitor (eIF2B agonist)",
        "clinical_status": "Preclinical",
        "drugbank_id": None,
        "target_node": ("Pathway", "name", "Mitochondrial translation"),
    },
]


class TherapeuticsLoader:
    """Load mitochondrial therapeutics and target edges."""

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        relationships = 0
        for drug in DRUGS:
            writer.merge_node("Drug", "name", _drug_properties(drug))
            label, key, value = cast(Tuple[str, str, object], drug["target_node"])
            writer.merge_relationship(
                "Drug",
                "name",
                drug["name"],
                EDGE_LABELS["inhibits"],
                str(label),
                str(key),
                value,
                {"target_description": drug["target"]},
            )
            relationships += 1
            disease = drug.get("disease")
            if disease:
                writer.merge_relationship(
                    "Drug",
                    "name",
                    drug["name"],
                    EDGE_LABELS["treats"],
                    "Disease",
                    "name",
                    disease,
                )
                relationships += 1

        return LoadResult(
            loader="TherapeuticsLoader",
            nodes_loaded=len(DRUGS),
            relationships_loaded=relationships,
            details={"drugs": len(DRUGS), "target_edges": len(DRUGS)},
        )


def _drug_properties(drug: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "name": drug["name"],
        "drugbank_id": drug["drugbank_id"],
        "mechanism": drug["target"],
        "target": drug["target"],
        "clinical_status": drug["clinical_status"],
    }
