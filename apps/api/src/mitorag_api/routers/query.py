"""Main Q&A endpoint boundary."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, cast

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mitorag_agents.graph import SimpleMitoRAGGraph
from mitorag_agents.state import Citation, Contradiction

router = APIRouter()


def _citation_list() -> List[Citation]:
    return []


def _contradiction_list() -> List[Contradiction]:
    return []


def _string_list() -> List[str]:
    return []


def _latency_dict() -> Dict[str, float]:
    return {}


class SourcePaper(BaseModel):
    """Paper-level evidence used to construct the answer."""

    citation: str
    title: str = ""
    source: str = ""
    pmid: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    score: float = 0.0
    snippet: str = ""
    url: Optional[str] = None


def _source_list() -> List[SourcePaper]:
    return []


class QueryRequest(BaseModel):
    question: str
    deep: bool = False


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=_citation_list)
    contradictions: List[Contradiction] = Field(default_factory=_contradiction_list)
    agent_trace: List[str] = Field(default_factory=_string_list)
    latency_ms: Dict[str, float] = Field(default_factory=_latency_dict)
    confidence: float = 0.0
    sources: List[SourcePaper] = Field(default_factory=_source_list)
    status: str = "ok"


@router.post("", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    graph = SimpleMitoRAGGraph()
    state: Dict[str, object] = graph.invoke(
        {"query": request.question},
        config={"configurable": {"thread_id": "api"}},
    )
    latency = _mapping(state.get("latency_ms"))
    sources = _collect_sources(state)
    return QueryResponse(
        answer=str(state.get("answer", "")),
        citations=[Citation.model_validate(item) for item in _sequence(state.get("citations"))],
        contradictions=[
            Contradiction.model_validate(item)
            for item in _sequence(state.get("contradictions"))
        ],
        agent_trace=[str(item) for item in _sequence(state.get("agent_trace"))],
        latency_ms={str(key): _float(value) for key, value in latency.items()},
        confidence=_float(state.get("confidence")),
        sources=sources,
    )


def _collect_sources(state: Mapping[str, object]) -> List[SourcePaper]:
    """Build a deduped source-paper list from web + local chunks."""
    seen: Dict[str, SourcePaper] = {}
    for bucket_name in ("web_chunks", "local_chunks"):
        for chunk in _sequence(state.get(bucket_name)):
            paper = _chunk_to_source(chunk, bucket=bucket_name)
            if paper is None:
                continue
            key = paper.citation or paper.title
            if not key:
                continue
            existing = seen.get(key)
            if existing is None or paper.score > existing.score:
                seen[key] = paper
    return sorted(seen.values(), key=lambda item: item.score, reverse=True)[:12]


def _chunk_to_source(chunk: object, *, bucket: str) -> Optional[SourcePaper]:
    doc, score = _unpack_chunk(chunk)
    if not doc:
        return None
    paper_id = str(doc.get("paper_id", "") or "")
    text = str(doc.get("text", "") or "")
    metadata = doc.get("metadata") if isinstance(doc, dict) else None
    meta: Mapping[str, Any] = (
        cast(Mapping[str, Any], metadata) if isinstance(metadata, Mapping) else {}
    )
    citation = str(meta.get("citation") or _infer_citation(paper_id) or "")
    title = str(meta.get("title") or "")
    source_api = str(meta.get("source_api") or bucket)
    pmid = _maybe_str(meta.get("pmid")) or _pmid_from_citation(citation)
    doi = _maybe_str(meta.get("doi")) or _doi_from_citation(citation)
    year_value = meta.get("year")
    year: Optional[int] = None
    if isinstance(year_value, int):
        year = year_value
    elif isinstance(year_value, str) and year_value.isdigit():
        year = int(year_value)
    snippet = _shorten(text, 280)
    if not (citation or title or snippet):
        return None
    return SourcePaper(
        citation=citation,
        title=title or _shorten(text, 90),
        source=source_api,
        pmid=pmid,
        doi=doi,
        year=year,
        score=score,
        snippet=snippet,
        url=_url_for(pmid, doi),
    )


def _unpack_chunk(chunk: object) -> tuple[Mapping[str, Any], float]:
    if isinstance(chunk, Mapping):
        chunk_map = cast(Mapping[str, Any], chunk)
        document_obj = chunk_map.get("document")
        score_value = _float(chunk_map.get("score"))
        if isinstance(document_obj, Mapping):
            return cast(Mapping[str, Any], document_obj), score_value
        return chunk_map, score_value
    if hasattr(chunk, "document"):
        document_attr = getattr(chunk, "document")
        if hasattr(document_attr, "model_dump"):
            document: Mapping[str, Any] = document_attr.model_dump()
        else:
            document = dict(getattr(document_attr, "__dict__", {}))
        score = _float(getattr(chunk, "score", 0.0))
        return cast(Mapping[str, Any], document), score
    return {}, 0.0


def _infer_citation(paper_id: str) -> Optional[str]:
    if not paper_id:
        return None
    if paper_id.startswith("PMID:"):
        return f"[{paper_id}]"
    if paper_id.startswith("10."):
        return f"[doi:{paper_id}]"
    if paper_id.isdigit():
        return f"[PMID:{paper_id}]"
    return None


def _pmid_from_citation(citation: str) -> Optional[str]:
    if citation.startswith("[PMID:") and citation.endswith("]"):
        return citation[6:-1]
    return None


def _doi_from_citation(citation: str) -> Optional[str]:
    if citation.startswith("[doi:") and citation.endswith("]"):
        return citation[5:-1]
    return None


def _url_for(pmid: Optional[str], doi: Optional[str]) -> Optional[str]:
    if pmid:
        return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    if doi:
        return f"https://doi.org/{doi}"
    return None


def _maybe_str(value: object) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def _shorten(text: str, limit: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, list):
        return cast(Sequence[object], value)
    return []


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _float(value: object) -> float:
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0
