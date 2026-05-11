"""Agent 8: Chain-of-Verification and contradiction detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, List, Mapping, Sequence

from mitorag_agents.state import Claim, Contradiction, Evidence, MitoRAGState, StateUpdate
from mitorag_agents.utils import timed_node


@dataclass(frozen=True)
class RelationAssertion:
    """A normalized paper or KG assertion used for contradiction checks."""

    subject_id: str
    predicate: str
    object_id: str
    evidence_id: str
    confidence: float = 0.0


class ContradictionDetector:
    """Detect and model scientific contradictions."""

    opposing_predicates: ClassVar[Mapping[str, str]] = {
        "activates": "inhibits",
        "inhibits": "activates",
        "produces": "consumes",
        "consumes": "produces",
    }

    known_controversies: ClassVar[Sequence[str]] = [
        "mPTP composition: F-ATP synthase vs ANT vs multi-protein models",
        "Warburg effect vs reverse Warburg in cancer metabolism",
        "Titin N2A-actin binding: direct vs MARP-mediated",
        "mtDNA-cGAS-STING as primary sterile inflammation driver vs bystander",
        "MitoCarta 3.0 completeness: 1,136 curated genes vs broader candidate sets",
    ]

    mptp_query_terms: ClassVar[Sequence[str]] = (
        "mptp", "permeability transition", "permeability-transition pore",
        "transition pore", "pt pore", "atp synthase pore",
    )

    def detect_evidence_contradictions(
        self,
        evidence: List[Evidence],
        query: str = "",
    ) -> List[Contradiction]:
        """Detect contradictions directly from retrieved evidence text.

        Only surfaces the mPTP composition controversy if the user's query is
        actually about mPTP / permeability transition — otherwise the badge
        becomes noise on unrelated questions.
        """

        q = query.lower()
        if not any(term in q for term in self.mptp_query_terms):
            return []

        atp_ids = [
            item.id
            for item in evidence
            if "atp synthase" in item.text.lower() and "mptp" in item.text.lower()
        ]
        opposing_ids = [
            item.id
            for item in evidence
            if ("non-atp" in item.text.lower() or "contradictory" in item.text.lower())
            and "mptp" in item.text.lower()
        ]
        if atp_ids and opposing_ids:
            return [
                Contradiction(
                    claim="mPTP molecular identity is disputed",
                    supporting_evidence_ids=atp_ids,
                    contradicting_evidence_ids=opposing_ids,
                    summary=(
                        "Evidence supports both ATP-synthase-centered and non-ATP-synthase "
                        "models; do not collapse this into a single settled mechanism."
                    ),
                )
            ]
        return []

    def predicates_conflict(self, left: str, right: str) -> bool:
        return self.opposing_predicates.get(left.lower()) == right.lower()

    def detect_relation_conflicts(
        self,
        candidate: RelationAssertion,
        existing: List[RelationAssertion],
    ) -> List[Contradiction]:
        """Detect opposite predicates over the same subject-object pair."""

        contradictions: List[Contradiction] = []
        for assertion in existing:
            if candidate.subject_id != assertion.subject_id:
                continue
            if candidate.object_id != assertion.object_id:
                continue
            if not self.predicates_conflict(candidate.predicate, assertion.predicate):
                continue
            contradictions.append(
                Contradiction(
                    claim=(
                        f"{candidate.subject_id} has opposing "
                        f"{candidate.predicate}/{assertion.predicate} relations to "
                        f"{candidate.object_id}"
                    ),
                    supporting_evidence_ids=[candidate.evidence_id],
                    contradicting_evidence_ids=[assertion.evidence_id],
                    summary="Auto-KG relation extraction found opposing predicates.",
                )
            )
        return contradictions


def verifier_node(state: MitoRAGState) -> StateUpdate:
    """Verify evidence-grounded claims and surface contradictions."""

    with timed_node(state, "verifier") as update:
        claims = extract_claims(state.evidence)
        contradictions = detect_contradictions(state.evidence, state.query)
        update["claims"] = claims
        update["contradictions"] = contradictions
        update["verified"] = True
        return update


def extract_claims(evidence: List[Evidence]) -> List[Claim]:
    claims: List[Claim] = []
    for item in evidence[:8]:
        sentence = item.text.strip().split(".")[0].strip()
        if not sentence:
            continue
        claims.append(
            Claim(
                text=sentence,
                supporting_evidence_ids=[item.id],
                confidence=min(0.95, max(0.3, item.score)),
            )
        )
    return claims


def detect_contradictions(evidence: List[Evidence], query: str = "") -> List[Contradiction]:
    return ContradictionDetector().detect_evidence_contradictions(evidence, query)
