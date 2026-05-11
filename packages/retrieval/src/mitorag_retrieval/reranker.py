"""Cross-encoder reranking for Phase 2."""

from __future__ import annotations

import importlib
import os
from typing import Any, Iterable, List, Mapping, Optional, Sequence, cast

from mitorag_retrieval.models import RankedChunk, tokenize


class LexicalCrossEncoder:
    """Fast local cross-encoder-shaped fallback for offline tests."""

    def score(self, query: str, documents: Sequence[str]) -> List[float]:
        query_tokens = tokenize(query)
        query_set = set(query_tokens)
        if not query_set:
            return [0.0 for _ in documents]

        scores: List[float] = []
        query_phrase = " ".join(query_tokens)
        for document in documents:
            document_tokens = tokenize(document)
            document_set = set(document_tokens)
            overlap = query_set.intersection(document_set)
            union = query_set.union(document_set)
            jaccard = len(overlap) / len(union) if union else 0.0
            coverage = len(overlap) / len(query_set)
            phrase_bonus = 0.15 if query_phrase and query_phrase in document.lower() else 0.0
            exact_gene_bonus = _gene_bonus(query_set, document_set)
            scores.append(coverage + 0.5 * jaccard + phrase_bonus + exact_gene_bonus)
        return scores


class BGEReranker:
    """BAAI/bge-reranker-v2-m3 cross-encoder.

    The heavyweight model is opt-in for local development by passing
    `load_model=True` or setting `MITORAG_LOAD_RERANKER_MODEL=1`. Otherwise this
    class uses a deterministic lexical cross-encoder fallback so CI stays fast.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        fallback_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        load_model: Optional[bool] = None,
        fallback_to_lexical: bool = True,
    ) -> None:
        self.model_name = model_name
        self.fallback_model_name = fallback_model_name
        self._lexical = LexicalCrossEncoder()
        self._model: Optional[Any] = None
        should_load = load_model
        if should_load is None:
            should_load = os.environ.get("MITORAG_LOAD_RERANKER_MODEL") == "1"
        if should_load:
            self._model = self._load_cross_encoder(model_name, fallback_to_lexical)

    @classmethod
    def fast(cls) -> BGEReranker:
        """Use the MiniLM alternative for lower latency experiments."""

        return cls(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            fallback_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            load_model=True,
        )

    def score(self, query: str, documents: Sequence[str]) -> List[float]:
        if self._model is None:
            return self._lexical.score(query, documents)
        pairs = [(query, document) for document in documents]
        raw_scores: object = self._model.predict(pairs)
        return _coerce_scores(raw_scores)

    def rerank(
        self,
        query: str,
        candidates: Sequence[RankedChunk],
        top_k: int = 15,
    ) -> List[RankedChunk]:
        if not candidates:
            return []
        scores = self.score(query, [candidate.text for candidate in candidates])
        paired = list(zip(candidates, scores))
        paired.sort(key=lambda item: item[1], reverse=True)

        ranked: List[RankedChunk] = []
        for rank, (candidate, score) in enumerate(paired[:top_k], start=1):
            source_scores = _merge_scores(candidate.source_scores, {"reranker": score})
            ranked.append(
                candidate.with_rank_score_source(
                    rank=rank,
                    score=score,
                    source="bge_reranker",
                    source_scores=source_scores,
                )
            )
        return ranked

    def _load_cross_encoder(self, model_name: str, fallback_to_lexical: bool) -> Optional[Any]:
        try:
            return _instantiate_cross_encoder(model_name)
        except Exception:
            if not fallback_to_lexical:
                raise
        try:
            return _instantiate_cross_encoder(self.fallback_model_name)
        except Exception:
            if not fallback_to_lexical:
                raise
        return None


def _instantiate_cross_encoder(model_name: str) -> Any:
    module: Any = importlib.import_module("sentence_transformers")
    cross_encoder: Any = getattr(module, "CrossEncoder")
    return cross_encoder(model_name)


def _coerce_scores(value: object) -> List[float]:
    if hasattr(value, "tolist"):
        value = cast(Any, value).tolist()
    if isinstance(value, list):
        return [_coerce_float(item) for item in cast(List[object], value)]
    if isinstance(value, tuple):
        return [_coerce_float(item) for item in cast(tuple[object, ...], value)]
    raise TypeError("Reranker returned non-list scores")


def _coerce_float(value: object) -> float:
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"Expected numeric reranker score, got {type(value).__name__}")


def _merge_scores(left: Mapping[str, float], right: Mapping[str, float]) -> Mapping[str, float]:
    merged = dict(left)
    merged.update(right)
    return merged


def _gene_bonus(query_tokens: Iterable[str], document_tokens: Iterable[str]) -> float:
    gene_tokens = {token for token in query_tokens if "-" in token or token.startswith("mt")}
    if not gene_tokens:
        return 0.0
    return 0.25 if gene_tokens.intersection(set(document_tokens)) else 0.0
