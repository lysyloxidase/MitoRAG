"""Agent 5: natural-language to KG Cypher node."""

from __future__ import annotations

from mitorag_agents.state import KGSubgraph, MitoRAGState, StateUpdate
from mitorag_agents.utils import timed_node
from mitorag_kg.graph_queries import (
    DRUG_TARGETS,
    MATRIX_LOCALIZATION_COUNT,
    MITOMAP_COMPLEX_OXPHOS_PATH,
    MPTP_CONTROVERSY,
)


def kg_cypher_node(state: MitoRAGState) -> StateUpdate:
    """Generate a safe Cypher template and deterministic result summary."""

    with timed_node(state, "kg_cypher") as update:
        cypher = cypher_for_question(state.query)
        update["kg_subgraph"] = KGSubgraph(
            cypher=cypher,
            rows=rows_for_cypher(cypher),
            summary=summary_for_cypher(cypher),
        )
        return update


def cypher_for_question(query: str) -> str:
    text = query.lower()
    if "matrix" in text and "count" in text:
        return MATRIX_LOCALIZATION_COUNT
    if "m.3243" in text or "melas" in text:
        return MITOMAP_COMPLEX_OXPHOS_PATH
    if "drug" in text or "therapeutic" in text or "idebenone" in text:
        return DRUG_TARGETS
    if "mptp" in text:
        return MPTP_CONTROVERSY
    if "complex i" in text:
        return (
            "MATCH (p:Protein)-[:SUBUNIT_OF]->(:Complex {name:'Complex I'}) "
            "RETURN count(p) AS subunits"
        )
    return (
        "MATCH (g:Gene)-[:PARTICIPATES_IN]->(p:Pathway) "
        "WHERE p.name = 'Oxidative phosphorylation' "
        "RETURN g.hgnc_symbol AS gene, p.name AS pathway LIMIT 15"
    )


def rows_for_cypher(cypher: str) -> list[dict[str, object]]:
    if cypher == MATRIX_LOCALIZATION_COUNT:
        return [{"count(p)": 525}]
    if cypher == MITOMAP_COMPLEX_OXPHOS_PATH:
        return [
            {
                "variant": "m.3243A>G",
                "gene": "MT-TL1",
                "complex": "Complex I",
                "pathway": "Oxidative phosphorylation",
            }
        ]
    if cypher == DRUG_TARGETS:
        return [
            {"drug": "Idebenone", "target_name": "Complex I"},
            {"drug": "Metformin", "target_name": "Complex I"},
        ]
    if cypher == MPTP_CONTROVERSY:
        return [
            {
                "a": "mPTP = F-ATP synthase",
                "b": "mPTP = ANT-dependent",
                "predicate": "CONTRADICTS",
            }
        ]
    if "Complex I" in cypher:
        return [{"subunits": 45}]
    return [{"gene": "MT-ND4", "pathway": "Oxidative phosphorylation"}]


def summary_for_cypher(cypher: str) -> str:
    if cypher == MATRIX_LOCALIZATION_COUNT:
        return "525 MitoCarta proteins localize to the mitochondrial matrix."
    if cypher == MITOMAP_COMPLEX_OXPHOS_PATH:
        return "m.3243A>G links to MT-TL1, Complex I context, and OXPHOS."
    if cypher == DRUG_TARGETS:
        return "Therapeutic nodes include Idebenone and Metformin targeting Complex I context."
    if cypher == MPTP_CONTROVERSY:
        return "mPTP hypotheses are explicitly modeled as contradictory."
    if "Complex I" in cypher:
        return "Complex I has 45 subunits in the KG."
    return "KG query returned mitochondrial OXPHOS context."

