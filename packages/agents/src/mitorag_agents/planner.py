"""Agent 2: query planner."""

from __future__ import annotations

from typing import Optional

from mitorag_agents.state import MitoRAGState, QueryType, StateUpdate
from mitorag_agents.utils import timed_node


def planner_node(state: MitoRAGState) -> StateUpdate:
    """Decompose the query into 3-5 retrieval and verification sub-queries."""

    with timed_node(state, "planner") as update:
        update["sub_queries"] = plan_sub_queries(state.query, state.query_type)
        return update


def plan_sub_queries(query: str, query_type: Optional[QueryType]) -> list[str]:
    base = query.strip().rstrip("?")
    if query_type == "disease":
        return [
            f"{base} genetic cause and pathogenic variants",
            f"{base} affected mitochondrial pathway or complex",
            f"{base} phenotype and inheritance evidence",
        ]
    if query_type == "therapeutics":
        return [
            f"{base} drug targets and clinical status",
            f"{base} mitochondrial complex or pathway mechanism",
            f"{base} disease indications and evidence",
        ]
    if query_type == "mechanistic":
        return [
            f"{base} molecular mechanism",
            f"{base} key proteins and pathway context",
            f"{base} supporting and contradicting evidence",
        ]
    if query_type == "methods":
        return [
            f"{base} protocol steps",
            f"{base} controls and quality metrics",
            f"{base} limitations and troubleshooting",
        ]
    if query_type == "citation":
        return [
            f"{base} recent primary literature",
            f"{base} highly cited references",
            f"{base} citation graph expansion",
        ]
    return [
        f"{base} direct factual answer",
        f"{base} supporting local evidence",
        f"{base} KG validation",
    ]
