"""Controversial mitochondrial hypothesis seed loader."""

from __future__ import annotations

from typing import List, Mapping, cast

from mitorag_kg.loader import LoadResult, as_writer
from mitorag_kg.schema import EDGE_LABELS

HYPOTHESES: List[Mapping[str, object]] = [
    {
        "name": "mPTP = F-ATP synthase",
        "description": "mPTP pore is formed by ATP synthase dimers (Bernardi/Bonora camp)",
        "status": "disputed",
        "supporting": ["PMID:37336870"],
        "contradicting": ["PMID:37607939"],
    },
    {
        "name": "mPTP = ANT-dependent",
        "description": "ANT conformational change forms the pore",
        "status": "disputed",
    },
    {
        "name": "Warburg effect = primary cause",
        "description": "Tumor cells prefer glycolysis due to mitochondrial defects",
        "status": "disputed",
        "note": "Reverse Warburg (stromal cells feed lactate) is alternative",
    },
]


class HypothesisLoader:
    """Load explicitly modeled controversial hypotheses."""

    def load(self, neo4j_driver: object) -> LoadResult:
        writer = as_writer(neo4j_driver)
        relationships = 0
        for hypothesis in HYPOTHESES:
            writer.merge_node("Hypothesis", "name", _hypothesis_properties(hypothesis))
            supporting = cast(List[str], hypothesis.get("supporting", []))
            contradicting = cast(List[str], hypothesis.get("contradicting", []))
            for pmid in supporting:
                writer.merge_node("Paper", "pmid", {"pmid": str(pmid).replace("PMID:", "")})
            for pmid in contradicting:
                writer.merge_node("Paper", "pmid", {"pmid": str(pmid).replace("PMID:", "")})

        writer.merge_relationship(
            "Hypothesis",
            "name",
            "mPTP = F-ATP synthase",
            EDGE_LABELS["contradicts"],
            "Hypothesis",
            "name",
            "mPTP = ANT-dependent",
            {"reason": "Alternative molecular identities for mPTP"},
        )
        writer.merge_relationship(
            "Hypothesis",
            "name",
            "mPTP = ANT-dependent",
            EDGE_LABELS["contradicts"],
            "Hypothesis",
            "name",
            "mPTP = F-ATP synthase",
            {"reason": "Alternative molecular identities for mPTP"},
        )
        relationships += 2

        return LoadResult(
            loader="HypothesisLoader",
            nodes_loaded=len(HYPOTHESES),
            relationships_loaded=relationships,
            details={"hypotheses": len(HYPOTHESES), "contradicts_edges": 2},
        )


def _hypothesis_properties(hypothesis: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "name": hypothesis["name"],
        "description": hypothesis["description"],
        "status": hypothesis["status"],
        "note": hypothesis.get("note"),
    }
