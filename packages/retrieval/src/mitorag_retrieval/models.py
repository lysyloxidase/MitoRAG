"""Shared retrieval models and text utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Protocol

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*")


class ChunkLike(Protocol):
    """Structural type accepted from the ingestion package."""

    id: str
    text: str
    paper_id: str
    section_path: str
    page_number: int
    char_start: int
    char_end: int
    metadata: Mapping[str, object]


def _empty_metadata() -> Dict[str, object]:
    return {}


def _empty_source_scores() -> Dict[str, float]:
    return {}


@dataclass(frozen=True)
class RetrievalDocument:
    """A retrieval-ready document chunk decoupled from ingestion internals."""

    id: str
    text: str
    paper_id: str
    section_path: str
    page_number: int = 1
    char_start: int = 0
    char_end: int = 0
    metadata: Mapping[str, object] = field(default_factory=_empty_metadata)

    @classmethod
    def from_chunk(cls, chunk: ChunkLike) -> RetrievalDocument:
        """Convert a Phase 1 ingestion chunk into a retrieval document."""

        return cls(
            id=chunk.id,
            text=chunk.text,
            paper_id=chunk.paper_id,
            section_path=chunk.section_path,
            page_number=chunk.page_number,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            metadata=dict(chunk.metadata),
        )


@dataclass(frozen=True)
class RankedChunk:
    """A scored chunk returned by sparse, dense, fused, or reranked retrieval."""

    document: RetrievalDocument
    score: float
    rank: int
    source: str
    source_scores: Mapping[str, float] = field(default_factory=_empty_source_scores)

    @property
    def id(self) -> str:
        return self.document.id

    @property
    def text(self) -> str:
        return self.document.text

    @property
    def paper_id(self) -> str:
        return self.document.paper_id

    @property
    def section_path(self) -> str:
        return self.document.section_path

    @property
    def metadata(self) -> Mapping[str, object]:
        return self.document.metadata

    def with_rank_score_source(
        self,
        rank: int,
        score: float,
        source: str,
        source_scores: Mapping[str, float],
    ) -> RankedChunk:
        return RankedChunk(
            document=self.document,
            score=score,
            rank=rank,
            source=source,
            source_scores=dict(source_scores),
        )


def documents_from_chunks(chunks: Iterable[ChunkLike]) -> List[RetrievalDocument]:
    """Convert ingestion chunks into retrieval documents."""

    return [RetrievalDocument.from_chunk(chunk) for chunk in chunks]


def tokenize(text: str) -> List[str]:
    """Tokenize biomedical text while preserving hyphenated gene names."""

    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def unique_preserve_order(tokens: Iterable[str]) -> List[str]:
    seen: Dict[str, None] = {}
    for token in tokens:
        seen.setdefault(token, None)
    return list(seen.keys())
