"""Typed state flowing through the twelve-agent MitoRAG graph."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from mitorag_retrieval.models import RankedChunk

QueryType = Literal["factual", "mechanistic", "disease", "therapeutics", "methods", "citation"]


def _dict_list() -> List[Dict[str, object]]:
    return []


def _string_list() -> List[str]:
    return []


def _ranked_list() -> List[RankedChunk]:
    return []


def _entity_list() -> List[Entity]:
    return []


def _evidence_list() -> List[Evidence]:
    return []


def _claim_list() -> List[Claim]:
    return []


def _contradiction_list() -> List[Contradiction]:
    return []


def _citation_list() -> List[Citation]:
    return []


def _latency_dict() -> Dict[str, float]:
    return {}


class Entity(BaseModel):
    """Normalized entity linked to an ontology or KG identifier."""

    text: str
    entity_type: str
    normalized_id: Optional[str] = None
    source: str = "heuristic"


class Evidence(BaseModel):
    """Evidence passed into verification and synthesis."""

    id: str
    text: str
    source: str
    score: float = 0.0
    paper_id: str = ""
    section_path: str = ""
    citation: Optional[str] = None


class Claim(BaseModel):
    """A factual claim extracted from evidence or synthesis."""

    text: str
    supporting_evidence_ids: List[str] = Field(default_factory=_string_list)
    contradicting_evidence_ids: List[str] = Field(default_factory=_string_list)
    confidence: float = 0.0


class Contradiction(BaseModel):
    """A detected contradiction that should be surfaced rather than hidden."""

    claim: str
    supporting_evidence_ids: List[str] = Field(default_factory=_string_list)
    contradicting_evidence_ids: List[str] = Field(default_factory=_string_list)
    summary: str


class Citation(BaseModel):
    """Inline citation extracted from the synthesized answer."""

    marker: str
    citation_type: Literal["pmid", "doi"]
    value: str
    valid: bool = True
    reason: Optional[str] = None


class KGSubgraph(BaseModel):
    """Small normalized KG query result passed between agents."""

    cypher: str
    rows: List[Dict[str, object]] = Field(default_factory=_dict_list)
    summary: str = ""


class MitoRAGState(BaseModel):
    """Typed state flowing through the 12-agent graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str
    conversation_history: List[Dict[str, object]] = Field(default_factory=_dict_list)

    query_type: Optional[QueryType] = None
    sub_queries: List[str] = Field(default_factory=_string_list)

    local_chunks: List[RankedChunk] = Field(default_factory=_ranked_list)
    web_chunks: List[RankedChunk] = Field(default_factory=_ranked_list)
    kg_subgraph: Optional[KGSubgraph] = None
    linked_entities: List[Entity] = Field(default_factory=_entity_list)

    evidence: List[Evidence] = Field(default_factory=_evidence_list)

    claims: List[Claim] = Field(default_factory=_claim_list)
    contradictions: List[Contradiction] = Field(default_factory=_contradiction_list)
    verified: bool = False

    answer: str = ""
    citations: List[Citation] = Field(default_factory=_citation_list)
    confidence: float = 0.0

    citations_valid: bool = False
    invalid_citations: List[str] = Field(default_factory=_string_list)
    citation_retry_count: int = 0

    agent_trace: List[str] = Field(default_factory=_string_list)
    latency_ms: Dict[str, float] = Field(default_factory=_latency_dict)


StateUpdate = Dict[str, object]
