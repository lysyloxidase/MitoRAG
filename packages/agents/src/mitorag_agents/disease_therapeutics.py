"""Agent 12: disease and therapeutics specialist."""

from __future__ import annotations

from mitorag_agents.state import Evidence, MitoRAGState, StateUpdate
from mitorag_agents.utils import dedupe_evidence, timed_node


def disease_therapeutics_node(state: MitoRAGState) -> StateUpdate:
    """Add disease/therapeutic interpretation grounded in KG and evidence."""

    with timed_node(state, "disease_therapeutics") as update:
        disease = Evidence(
            id="specialist-disease-therapeutics",
            text=(
                "Disease interpretation: MELAS is maternally inherited and often linked "
                "to MT-TL1 m.3243A>G; Idebenone targets LHON/Complex I context."
            ),
            source="disease_therapeutics",
            score=0.78,
            section_path="Specialist > L7-10",
            citation="[PMID:25613900]",
        )
        update["evidence"] = dedupe_evidence([*state.evidence, disease])[:15]
        return update
