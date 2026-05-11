from __future__ import annotations

from mitorag_agents.planner import plan_sub_queries
from mitorag_agents.router import classify_query


def test_router_classifies_factual_query() -> None:
    assert classify_query("How many subunits does Complex I have?") == "factual"


def test_router_classifies_disease_query() -> None:
    assert classify_query("What causes MELAS?") == "disease"


def test_planner_returns_three_to_seven_subqueries_for_complex_query() -> None:
    sub_queries = plan_sub_queries(
        "What causes MELAS and what mitochondrial pathway is affected?",
        "disease",
    )

    assert 3 <= len(sub_queries) <= 7
    assert any("variant" in query or "pathway" in query for query in sub_queries)

