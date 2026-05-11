"""Agent 11: mitophysiology specialist."""

from __future__ import annotations

from mitorag_agents.state import Evidence, MitoRAGState, StateUpdate
from mitorag_agents.utils import dedupe_evidence, timed_node


def mitophysiology_node(state: MitoRAGState) -> StateUpdate:
    """Add L1-6 mitochondrial physiology interpretation grounded in evidence."""

    with timed_node(state, "mitophysiology") as update:
        physiology = Evidence(
            id="specialist-mitophysiology",
            text=(
                "Mechanistic interpretation: OXPHOS, membrane potential, Complex I, "
                "and PINK1/Parkin mitophagy should be considered together."
            ),
            source="mitophysiology",
            score=0.76,
            section_path="Specialist > L1-6",
            citation="[PMID:20510199]",
        )
        update["evidence"] = dedupe_evidence([*state.evidence, physiology])[:15]
        return update
