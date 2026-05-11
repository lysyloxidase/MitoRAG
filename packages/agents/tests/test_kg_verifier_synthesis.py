from __future__ import annotations

from mitorag_agents.citation_auditor import citation_auditor_node
from mitorag_agents.kg_cypher import cypher_for_question, kg_cypher_node
from mitorag_agents.local_rag import local_fixture_chunks
from mitorag_agents.state import MitoRAGState
from mitorag_agents.synthesizer import synthesizer_node
from mitorag_agents.utils import evidence_from_ranked, merge_updates
from mitorag_agents.verifier import ContradictionDetector, RelationAssertion, verifier_node


def test_kg_cypher_generates_valid_cypher_and_result() -> None:
    query = "What causes MELAS?"
    cypher = cypher_for_question(query)
    assert "MATCH" in cypher
    assert "m.3243A>G" in cypher or "$hgvs" in cypher

    state = merge_updates(MitoRAGState(query=query), kg_cypher_node(MitoRAGState(query=query)))
    assert state.kg_subgraph is not None
    assert state.kg_subgraph.rows


def test_verifier_detects_mptp_contradiction() -> None:
    chunks = local_fixture_chunks("What is the mPTP?")
    evidence = [evidence_from_ranked(chunk) for chunk in chunks]
    state = MitoRAGState(query="What is the mPTP?", evidence=evidence)

    verified = merge_updates(state, verifier_node(state))

    assert verified.verified
    assert verified.contradictions
    assert "mPTP" in verified.contradictions[0].claim


def test_contradiction_detector_detects_opposing_relations() -> None:
    detector = ContradictionDetector()
    candidate = RelationAssertion("PINK1", "inhibits", "PRKN", "new-paper", 0.9)
    existing = [RelationAssertion("PINK1", "activates", "PRKN", "seed-kg", 0.95)]

    contradictions = detector.detect_relation_conflicts(candidate, existing)

    assert contradictions
    assert "opposing" in contradictions[0].claim


def test_synthesizer_outputs_at_least_three_inline_pmid_citations() -> None:
    chunks = local_fixture_chunks("How many subunits does Complex I have?")
    evidence = [evidence_from_ranked(chunk) for chunk in chunks]
    state = MitoRAGState(
        query="How many subunits does Complex I have?",
        local_chunks=chunks,
        evidence=evidence,
        verified=True,
    )

    synthesized = merge_updates(state, synthesizer_node(state))

    assert synthesized.answer.count("[PMID:") >= 3
    assert len(synthesized.citations) >= 3


def test_citation_auditor_catches_fabricated_pmid_and_triggers_retry() -> None:
    state = MitoRAGState(
        query="What causes MELAS?",
        answer="This fabricated claim cites an invented paper [PMID:99999999].",
    )

    audited = merge_updates(state, citation_auditor_node(state))

    assert not audited.citations_valid
    assert audited.invalid_citations == ["[PMID:99999999]"]
    assert audited.citation_retry_count == 1
