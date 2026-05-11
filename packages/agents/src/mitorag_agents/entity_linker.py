"""Agent 6: entity linker."""

from __future__ import annotations

from typing import List

from mitorag_agents.state import Entity, MitoRAGState, StateUpdate
from mitorag_agents.utils import timed_node

ENTITY_PATTERNS = {
    "Complex I": ("Complex", "Complex I"),
    "MELAS": ("Disease", "MONDO:0010789"),
    "m.3243A>G": ("Variant", "m.3243A>G"),
    "MT-TL1": ("Gene", "MT-TL1"),
    "MT-ND4": ("Gene", "MT-ND4"),
    "PINK1": ("Gene", "PINK1"),
    "Parkin": ("Gene", "PRKN"),
    "Idebenone": ("Drug", "DB09081"),
    "mPTP": ("Hypothesis", "mPTP"),
}


def entity_linker_node(state: MitoRAGState) -> StateUpdate:
    """Normalize query/evidence mentions to KG IDs."""

    with timed_node(state, "entity_linker") as update:
        haystack = " ".join(
            [
                state.query,
                *(chunk.text for chunk in state.local_chunks),
                *(chunk.text for chunk in state.web_chunks),
            ]
        )
        update["linked_entities"] = link_entities(haystack)
        return update


def link_entities(text: str) -> List[Entity]:
    linked: List[Entity] = []
    lowered = text.lower()
    for mention, (entity_type, normalized_id) in ENTITY_PATTERNS.items():
        if mention.lower() in lowered:
            linked.append(
                Entity(
                    text=mention,
                    entity_type=entity_type,
                    normalized_id=normalized_id,
                    source="heuristic",
                )
            )
    return linked

