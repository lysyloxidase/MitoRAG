"""Agent 4: web RAG retrieval node."""

from __future__ import annotations

from typing import List

from mitorag_agents.state import MitoRAGState, StateUpdate
from mitorag_agents.utils import ranked_chunk, timed_node
from mitorag_retrieval.models import RankedChunk


def web_rag_node(state: MitoRAGState) -> StateUpdate:
    """Fetch web literature snippets.

    This phase uses deterministic snippets; Phase 5 will replace this with the
    PubMed/Semantic Scholar/Europe PMC clients.
    """

    with timed_node(state, "web_rag") as update:
        update["web_chunks"] = state.web_chunks or web_fixture_chunks(state.query)
        return update


def web_fixture_chunks(query: str) -> List[RankedChunk]:
    del query
    return [
        ranked_chunk(
            "web-oxphos-review",
            "OXPHOS integrates Complexes I-V in the inner mitochondrial membrane.",
            "PMID:12345678",
            "Review > OXPHOS",
            0.83,
            1,
            "web_rag",
            "[PMID:12345678]",
        ),
        ranked_chunk(
            "web-idebenone",
            "Idebenone is approved in Europe for Leber hereditary optic neuropathy.",
            "PMID:26988832",
            "Therapeutics > LHON",
            0.81,
            2,
            "web_rag",
            "[PMID:26988832]",
        ),
        ranked_chunk(
            "web-pink1-parkin",
            "PINK1 accumulation recruits Parkin to depolarized mitochondria during mitophagy.",
            "PMID:20510199",
            "Mechanism > Mitophagy",
            0.79,
            3,
            "web_rag",
            "[PMID:20510199]",
        ),
    ]
