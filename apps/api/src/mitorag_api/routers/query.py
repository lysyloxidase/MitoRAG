"""Main Q&A endpoint boundary."""

from __future__ import annotations

from typing import Dict, List, Mapping, Sequence, cast

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
    status: str = "ok"


@router.post("", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    graph = SimpleMitoRAGGraph()
    state: Dict[str, object] = graph.invoke(
        {"query": request.question},
        config={"configurable": {"thread_id": "api"}},
    )
    latency = _mapping(state.get("latency_ms"))
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
    )


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
