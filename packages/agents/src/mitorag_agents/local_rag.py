"""Agent 3: local RAG retrieval node."""

from __future__ import annotations

from typing import List

from mitorag_agents.state import MitoRAGState, StateUpdate
from mitorag_agents.utils import ranked_chunk, timed_node
from mitorag_retrieval.models import RankedChunk


def local_rag_node(state: MitoRAGState) -> StateUpdate:
    """Retrieve local paper chunks.

    Phase 4 uses deterministic built-in chunks when no retrieval service has
    populated state.local_chunks yet.
    """

    with timed_node(state, "local_rag") as update:
        update["local_chunks"] = state.local_chunks or local_fixture_chunks(state.query)
        return update


def local_fixture_chunks(query: str) -> List[RankedChunk]:
    del query
    return [
        ranked_chunk(
            "local-complex-i",
            "Complex I contains 45 subunits, including seven mtDNA-encoded ND subunits.",
            "PMID:33174596",
            "Results > Complex I",
            0.97,
            1,
            "local_rag",
            "[PMID:33174596]",
        ),
        ranked_chunk(
            "local-melas",
            "The m.3243A>G variant in MT-TL1 is a canonical cause of MELAS syndrome.",
            "PMID:25613900",
            "Disease > MELAS",
            0.92,
            2,
            "local_rag",
            "[PMID:25613900]",
        ),
        ranked_chunk(
            "local-mptp-atp",
            "One disputed model proposes the mPTP is formed by ATP synthase dimers.",
            "PMID:37336870",
            "Discussion > mPTP",
            0.88,
            3,
            "local_rag",
            "[PMID:37336870]",
        ),
        ranked_chunk(
            "local-mptp-ant",
            "Contradictory synthase-null evidence supports non-ATP-synthase mPTP opening.",
            "PMID:37607939",
            "Discussion > mPTP",
            0.87,
            4,
            "local_rag",
            "[PMID:37607939]",
        ),
        ranked_chunk(
            "local-methods",
            "Mitochondrial isolation uses differential centrifugation and purity controls.",
            "PMID:30000001",
            "Methods > Isolation",
            0.74,
            5,
            "local_rag",
            "[PMID:30000001]",
        ),
    ]
