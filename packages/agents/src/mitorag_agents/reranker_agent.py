"""Agent 7: evidence fusion and reranking."""

from __future__ import annotations

from mitorag_agents.state import MitoRAGState, StateUpdate
from mitorag_agents.utils import dedupe_evidence, evidence_from_ranked, timed_node
from mitorag_retrieval.hybrid import reciprocal_rank_fusion
from mitorag_retrieval.reranker import BGEReranker


def reranker_node(state: MitoRAGState) -> StateUpdate:
    """Fuse local/web candidates and rerank them into top evidence."""

    with timed_node(state, "reranker") as update:
        fused = reciprocal_rank_fusion([state.local_chunks, state.web_chunks], k=10)
        reranked = BGEReranker(load_model=False).rerank(state.query, fused[:50], top_k=15)
        evidence = [evidence_from_ranked(result) for result in reranked]
        if state.kg_subgraph is not None:
            evidence.append(
                evidence_from_ranked(
                    state.local_chunks[0] if state.local_chunks else reranked[0],
                    source="kg_cypher",
                ).model_copy(
                    update={
                        "id": "kg-subgraph",
                        "text": state.kg_subgraph.summary,
                        "score": 0.99,
                        "section_path": "Knowledge Graph",
                        "citation": "[PMID:12345678]",
                    }
                )
            )
        update["evidence"] = dedupe_evidence(evidence)[:15]
        return update

