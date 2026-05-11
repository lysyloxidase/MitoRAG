"""Agent 1: query-type router."""

from __future__ import annotations

from mitorag_agents.state import MitoRAGState, QueryType, StateUpdate
from mitorag_agents.utils import timed_node


def router_node(state: MitoRAGState) -> StateUpdate:
    """Classify query type with a deterministic fallback router."""

    with timed_node(state, "router") as update:
        update["query_type"] = classify_query(state.query)
        return update


def classify_query(query: str) -> QueryType:
    text = query.lower()
    if any(term in text for term in ["paper", "papers", "recent", "citation", "cite"]):
        return "citation"
    if any(term in text for term in ["drug", "treat", "therapy", "therapeutic", "idebenone"]):
        return "therapeutics"
    if any(term in text for term in ["disease", "melas", "merrf", "leigh", "lhon", "causes"]):
        return "disease"
    mechanistic_terms = ["how does", "mechanism", "work", "pathway", "pink1", "parkin"]
    if any(term in text for term in mechanistic_terms):
        return "mechanistic"
    if any(term in text for term in ["isolate", "protocol", "method", "assay", "measure"]):
        return "methods"
    return "factual"
