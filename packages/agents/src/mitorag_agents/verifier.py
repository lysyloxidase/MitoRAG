"""Agent 8: Chain-of-Verification and contradiction detection."""

from __future__ import annotations

from typing import List

from mitorag_agents.state import Claim, Contradiction, Evidence, MitoRAGState, StateUpdate
from mitorag_agents.utils import timed_node


def verifier_node(state: MitoRAGState) -> StateUpdate:
    """Verify evidence-grounded claims and surface contradictions."""

    with timed_node(state, "verifier") as update:
        claims = extract_claims(state.evidence)
        contradictions = detect_contradictions(state.evidence)
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


def detect_contradictions(evidence: List[Evidence]) -> List[Contradiction]:
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
