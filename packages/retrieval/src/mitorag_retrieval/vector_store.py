"""Vector store adapters for Phase 2."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from mitorag_retrieval.models import RankedChunk, RetrievalDocument

Vector = List[float]


@dataclass(frozen=True)
class VectorRecord:
    document: RetrievalDocument
    vector: Sequence[float]


class InMemoryVectorStore:
    """Small cosine vector store used by local tests and early development."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._records: List[VectorRecord] = []

    def add(self, document: RetrievalDocument, vector: Sequence[float]) -> None:
        self._records.append(VectorRecord(document=document, vector=normalize_vector(vector)))

    def add_many(
        self,
        documents: Iterable[RetrievalDocument],
        vectors: Iterable[Sequence[float]],
    ) -> None:
        for document, vector in zip(documents, vectors):
            self.add(document, vector)

    def search(self, query_vector: Sequence[float], top_k: int = 100) -> List[RankedChunk]:
        normalized_query = normalize_vector(query_vector)
        scored: List[tuple[RetrievalDocument, float]] = []
        for record in self._records:
            score = cosine_similarity(normalized_query, record.vector)
            if score > 0.0:
                scored.append((record.document, score))
        scored.sort(key=lambda item: item[1], reverse=True)

        ranked: List[RankedChunk] = []
        for rank, (document, score) in enumerate(scored[:top_k], start=1):
            ranked.append(
                RankedChunk(
                    document=document,
                    score=score,
                    rank=rank,
                    source=self.name,
                    source_scores={self.name: score},
                )
            )
        return ranked

    def __len__(self) -> int:
        return len(self._records)


def normalize_vector(vector: Sequence[float]) -> Vector:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError(f"Vector dimension mismatch: {len(left)} != {len(right)}")
    return sum(a * b for a, b in zip(left, right))
