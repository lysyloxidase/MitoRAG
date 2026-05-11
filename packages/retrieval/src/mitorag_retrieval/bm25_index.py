"""Sparse BM25 indexing for Phase 2."""

from __future__ import annotations

import math
from collections import Counter
from typing import Counter as CounterType
from typing import Dict, Iterable, List, Sequence

from mitorag_retrieval.models import RankedChunk, RetrievalDocument, tokenize


class BM25Index:
    """In-memory BM25 sparse index with biomedical token preservation."""

    def __init__(
        self,
        documents: Iterable[RetrievalDocument] = (),
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self._documents: List[RetrievalDocument] = []
        self._tokenized_documents: List[List[str]] = []
        self._term_frequencies: List[CounterType[str]] = []
        self._document_frequencies: CounterType[str] = Counter()
        self._idf: Dict[str, float] = {}
        self._average_document_length = 0.0
        self.add_documents(documents)

    @property
    def documents(self) -> Sequence[RetrievalDocument]:
        return self._documents

    def add_documents(self, documents: Iterable[RetrievalDocument]) -> None:
        new_documents = list(documents)
        if not new_documents:
            return
        self._documents.extend(new_documents)
        self._rebuild()

    def search(self, query: str, top_k: int = 100) -> List[RankedChunk]:
        query_terms = tokenize(query)
        if not query_terms or not self._documents:
            return []

        scored: List[tuple[RetrievalDocument, float]] = []
        for index, document in enumerate(self._documents):
            score = self._score(query_terms, index)
            if score > 0.0:
                scored.append((document, score))
        scored.sort(key=lambda item: item[1], reverse=True)

        ranked: List[RankedChunk] = []
        for rank, (document, score) in enumerate(scored[:top_k], start=1):
            ranked.append(
                RankedChunk(
                    document=document,
                    score=score,
                    rank=rank,
                    source="bm25",
                    source_scores={"bm25": score},
                )
            )
        return ranked

    def _rebuild(self) -> None:
        self._tokenized_documents = [tokenize(document.text) for document in self._documents]
        self._term_frequencies = [Counter(tokens) for tokens in self._tokenized_documents]
        self._document_frequencies = Counter()
        total_length = 0
        for tokens in self._tokenized_documents:
            total_length += len(tokens)
            for term in set(tokens):
                self._document_frequencies[term] += 1
        document_count = len(self._documents)
        self._average_document_length = total_length / document_count if document_count else 0.0
        self._idf = {
            term: math.log(1.0 + (document_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in self._document_frequencies.items()
        }

    def _score(self, query_terms: Sequence[str], document_index: int) -> float:
        frequencies = self._term_frequencies[document_index]
        document_length = len(self._tokenized_documents[document_index])
        if document_length == 0 or self._average_document_length == 0.0:
            return 0.0

        score = 0.0
        for term in query_terms:
            term_frequency = frequencies.get(term, 0)
            if term_frequency == 0:
                continue
            idf = self._idf.get(term, 0.0)
            denominator = term_frequency + self.k1 * (
                1.0 - self.b + self.b * document_length / self._average_document_length
            )
            score += idf * term_frequency * (self.k1 + 1.0) / denominator
        return score


def build_bm25_index(documents: Iterable[RetrievalDocument]) -> BM25Index:
    """Convenience factory for a BM25Index."""

    return BM25Index(documents)
