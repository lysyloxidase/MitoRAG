"""Agent 10: citation auditor."""

from __future__ import annotations

import re
from typing import List

from mitorag_agents.state import Citation, MitoRAGState, StateUpdate
from mitorag_agents.utils import extract_citations, timed_node

PMID_VALUE_RE = re.compile(r"^\d{5,9}$")
DOI_VALUE_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

KNOWN_PMIDS = {
    "12345678",
    "20510199",
    "25613900",
    "26988832",
    "30000001",
    "33174596",
    "37336870",
    "37607939",
}


def citation_auditor_node(state: MitoRAGState) -> StateUpdate:
    """Validate DOI/PMID syntax and known local citation support."""

    with timed_node(state, "citation_auditor") as update:
        citations = extract_citations(state.answer)
        audited = [audit_citation(citation) for citation in citations]
        invalid = [citation.marker for citation in audited if not citation.valid]
        update["citations"] = audited
        update["invalid_citations"] = invalid
        update["citations_valid"] = len(invalid) == 0 and len(audited) > 0
        if invalid:
            update["citation_retry_count"] = state.citation_retry_count + 1
        return update


def audit_citation(citation: Citation) -> Citation:
    if citation.citation_type == "pmid":
        if not PMID_VALUE_RE.match(citation.value):
            return citation.model_copy(update={"valid": False, "reason": "invalid PMID format"})
        if citation.value not in KNOWN_PMIDS:
            return citation.model_copy(update={"valid": False, "reason": "PMID not in local cache"})
        return citation
    if not DOI_VALUE_RE.match(citation.value):
        return citation.model_copy(update={"valid": False, "reason": "invalid DOI format"})
    return citation


def invalid_citations(answer: str) -> List[str]:
    return [
        citation.marker
        for citation in (audit_citation(item) for item in extract_citations(answer))
        if not citation.valid
    ]
