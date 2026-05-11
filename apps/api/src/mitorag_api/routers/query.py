"""Main Q&A endpoint boundary."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    status: str = "not_implemented"


@router.post("", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    return QueryResponse(
        answer=f"Phase 4 agents are not wired yet. Received question: {request.question}",
    )
