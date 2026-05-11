"""Agent 2: query planner."""

from __future__ import annotations

from typing import Optional

from mitorag_agents.state import MitoRAGState, QueryType, StateUpdate
from mitorag_agents.utils import timed_node


def planner_node(state: MitoRAGState) -> StateUpdate:
    """Decompose the query into 5-6 retrieval and verification sub-queries."""

    with timed_node(state, "planner") as update:
        update["sub_queries"] = plan_sub_queries(state.query, state.query_type)
        return update


def plan_sub_queries(query: str, query_type: Optional[QueryType]) -> list[str]:
    base = query.strip().rstrip("?")
    if query_type == "disease":
        return [
            f"{base} pathogenic variants genetic cause",
            f"{base} affected mitochondrial pathway complex",
            f"{base} phenotype inheritance heteroplasmy threshold",
            f"{base} clinical management treatment options",
            f"{base} recent biomarkers diagnostic criteria",
            f"{base} epidemiology prevalence cohort",
        ]
    if query_type == "therapeutics":
        return [
            f"{base} drug target mechanism of action",
            f"{base} mitochondrial complex pathway involvement",
            f"{base} clinical trial efficacy outcomes",
            f"{base} disease indications approval status",
            f"{base} pharmacokinetics safety adverse effects",
            f"{base} combination therapy biomarkers",
        ]
    if query_type == "mechanistic":
        return [
            f"{base} molecular mechanism structural basis",
            f"{base} key proteins enzymes regulators",
            f"{base} pathway context downstream effects",
            f"{base} supporting experimental evidence",
            f"{base} contradicting models alternative hypotheses",
            f"{base} recent cryo-EM structural findings",
        ]
    if query_type == "methods":
        return [
            f"{base} protocol experimental design",
            f"{base} controls quality metrics validation",
            f"{base} limitations troubleshooting pitfalls",
            f"{base} alternative methods comparison",
            f"{base} recent advances optimization",
        ]
    if query_type == "citation":
        return [
            f"{base} recent primary literature 2023 2024",
            f"{base} highly cited landmark papers",
            f"{base} citation graph expansion related work",
            f"{base} review articles meta-analyses",
            f"{base} controversies open questions",
        ]
    return [
        f"{base} mechanism molecular basis",
        f"{base} mitochondrial pathway context",
        f"{base} clinical or functional evidence",
        f"{base} recent primary literature 2023 2024",
        f"{base} supporting and contradicting findings",
        f"{base} therapeutic or translational implications",
    ]
