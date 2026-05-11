"""Shared helpers for agent nodes."""

from __future__ import annotations

import re
import time
from contextlib import contextmanager
from typing import Dict, Generator, List, Mapping, Optional

from mitorag_agents.state import Citation, Evidence, MitoRAGState, StateUpdate
from mitorag_retrieval.models import RankedChunk, RetrievalDocument

PMID_RE = re.compile(r"\[PMID:(\d{5,9})\]")
DOI_RE = re.compile(r"\[doi:(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\]", re.IGNORECASE)


@contextmanager
def timed_node(state: MitoRAGState, node_name: str) -> Generator[StateUpdate, None, None]:
    start = time.perf_counter()
    update: StateUpdate = {
        "agent_trace": [*state.agent_trace, node_name],
        "latency_ms": dict(state.latency_ms),
    }
    try:
        yield update
    finally:
        latency = (time.perf_counter() - start) * 1000
        cast_latency = update["latency_ms"]
        if isinstance(cast_latency, dict):
            cast_latency[node_name] = latency


def ranked_chunk(
    identifier: str,
    text: str,
    paper_id: str,
    section_path: str,
    score: float,
    rank: int,
    source: str,
    citation: str,
) -> RankedChunk:
    document = RetrievalDocument(
        id=identifier,
        text=text,
        paper_id=paper_id,
        section_path=section_path,
        metadata={"citation": citation},
    )
    return RankedChunk(
        document=document,
        score=score,
        rank=rank,
        source=source,
        source_scores={source: score},
    )


def evidence_from_ranked(result: RankedChunk, source: Optional[str] = None) -> Evidence:
    citation = result.metadata.get("citation")
    return Evidence(
        id=result.id,
        text=result.text,
        source=source or result.source,
        score=result.score,
        paper_id=result.paper_id,
        section_path=result.section_path,
        citation=str(citation) if citation else None,
    )


def dedupe_evidence(evidence: List[Evidence]) -> List[Evidence]:
    seen: Dict[str, Evidence] = {}
    for item in evidence:
        seen.setdefault(item.id, item)
    return sorted(seen.values(), key=lambda item: item.score, reverse=True)


def extract_citations(answer: str) -> List[Citation]:
    citations: List[Citation] = []
    for match in PMID_RE.finditer(answer):
        citations.append(
            Citation(marker=match.group(0), citation_type="pmid", value=match.group(1))
        )
    for match in DOI_RE.finditer(answer):
        citations.append(Citation(marker=match.group(0), citation_type="doi", value=match.group(1)))
    return citations


def merge_updates(state: MitoRAGState, update: Mapping[str, object]) -> MitoRAGState:
    data = state.model_dump()
    data.update(update)
    return MitoRAGState.model_validate(data)
